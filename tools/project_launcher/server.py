"""Linux checkout supervisor. Authority comes from process lifetimes, never ports.

The guardian remains the session leader until every owned child has stopped.
Every signal uses a pidfd opened before identity verification. A killed guardian
leaves evidence and an unknown state; another command never guesses orphan ownership.
"""

import argparse
from contextlib import contextmanager
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
import uuid

from . import ENGINE_VERSION
from .config import LauncherError, action_cwd, expand, read_json


def supported():
    return (sys.platform == "linux" and hasattr(os, "pidfd_open") and
            hasattr(signal, "pidfd_send_signal"))


def support_check():
    if not supported():
        return {"ok": False, "detail": "Requires Linux and Python 3.9+ pidfd APIs; use the foreground action"}
    try:
        fd = os.pidfd_open(os.getpid())
        try:
            signal.pidfd_send_signal(fd, 0)
        finally:
            os.close(fd)
        identity(os.getpid())
        Path("/proc/net/tcp").read_text()
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
    except (OSError, ValueError, LauncherError) as error:
        return {"ok": False, "detail": "Kernel/procfs or loopback socket capability unavailable: " + str(error)}
    return {"ok": True, "detail": "Kernel pidfds, own process/network procfs and loopback binding work"}


def require_support():
    result = support_check()
    if not result["ok"]:
        raise LauncherError(result["detail"])


def runtime(root, create=False):
    current = root
    for name in (".run", "launcher"):
        current = current / name
        if current.is_symlink():
            raise LauncherError("Runtime path is a symlink: " + str(current))
        if create:
            current.mkdir(mode=0o700, exist_ok=True)
        if current.exists() and not current.is_dir():
            raise LauncherError("Runtime path must be a directory: " + str(current))
    if current.exists() and (current.stat().st_uid != os.getuid() or current.stat().st_mode & 0o077):
        # Existing .run can be shared with old scripts; the manager's own directory cannot.
        raise LauncherError("Managed runtime directory must be owned by you with mode 0700: " + str(current))
    return current


def private_file(path, flags):
    fd = os.open(str(path), flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        os.close(fd)
        raise LauncherError("Runtime file must be a private regular file: " + str(path))
    return fd


def write_state(directory, value):
    fd, name = tempfile.mkstemp(prefix=".state-", dir=str(directory))
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream)
            stream.write("\n")
        destination = directory / "state.json"
        if destination.is_symlink():
            raise LauncherError("Refusing symlink state file")
        os.replace(name, str(destination))
    finally:
        if os.path.exists(name):
            os.unlink(name)


def read_state(directory, root):
    path = directory / "state.json"
    if not path.exists() and not path.is_symlink():
        return None
    fd = private_file(path, os.O_RDONLY)
    try:
        with os.fdopen(fd, "r") as stream:
            value = json.load(stream)
    except (ValueError, UnicodeError) as error:
        raise LauncherError("Malformed state; inspect it before proceeding") from error
    if (not isinstance(value, dict) or type(value.get("schema_version")) is not int or value.get("schema_version") != 1 or
            value.get("root") != str(root) or not isinstance(value.get("run_id"), str) or
            not isinstance(value.get("guardian"), dict) or
            type(value.get("guardian", {}).get("pid")) is not int or
            not isinstance(value.get("host"), str) or
            type(value.get("port")) is not int or not 0 <= value["port"] <= 65535 or
            type(value.get("requested_port")) is not int or not 0 <= value["requested_port"] <= 65535 or
            not isinstance(value.get("members"), list) or
            value.get("phase") not in ("starting", "ready", "unhealthy", "stopped", "failed", "unknown")):
        raise LauncherError("Invalid checkout state; inspect it before proceeding")
    return value


@contextmanager
def operation(directory, timeout):
    import fcntl
    fd = private_file(directory / "operation.lock", os.O_CREAT | os.O_RDWR)
    try:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise LauncherError("Another lifecycle operation is still in progress")
                time.sleep(0.05)
        yield
    finally:
        os.close(fd)


def identity(pid):
    if type(pid) is not int or pid <= 1:
        raise LauncherError("Invalid process identity")
    proc = Path("/proc") / str(pid)
    fields = (proc / "stat").read_text().rsplit(") ", 1)[1].split()
    if fields[0] in ("Z", "X"):
        raise ProcessLookupError(pid)
    return {"pid": pid, "start": fields[19], "pgid": int(fields[2]), "sid": int(fields[3]),
            "uid": proc.stat().st_uid,
            "boot": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
            "command": hashlib.sha256((proc / "cmdline").read_bytes()).hexdigest()}


def alive(record):
    try:
        return identity(record["pid"]) == record
    except (OSError, ValueError, KeyError, LauncherError):
        return False


def send(record, number):
    try:
        descriptor = os.pidfd_open(record["pid"])
    except ProcessLookupError:
        return False
    try:
        if not alive(record):
            raise LauncherError("Process identity changed; no signal sent")
        signal.pidfd_send_signal(descriptor, number)
        return True
    except ProcessLookupError:
        return False
    finally:
        os.close(descriptor)


def members(guardian):
    # Call only while the recorded guardian is verified alive, or from the guardian.
    found = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) == guardian["pid"]:
            continue
        try:
            record = identity(int(proc.name))
            if record["sid"] == guardian["sid"] and record["uid"] == guardian["uid"]:
                found.append(record)
        except (OSError, ValueError, LauncherError):
            continue
    return found


def owned_listener(records, host, port):
    if not port:
        return False
    inodes = set()
    address = ipaddress.ip_address(host)
    # procfs prints IPv4 in little-endian; IPv6 in four native-endian words.
    packed = address.packed
    encoded = (packed[::-1] if address.version == 4 else
               b"".join(packed[i:i + 4][::-1] for i in range(0, 16, 4))).hex().upper()
    table = "/proc/net/tcp" if address.version == 4 else "/proc/net/tcp6"
    try:
        for line in Path(table).read_text().splitlines()[1:]:
            fields = line.split()
            local, number = fields[1].split(":")
            if fields[3] == "0A" and int(number, 16) == port and local == encoded:
                inodes.add("socket:[{}]".format(fields[9]))
        for record in records:
            if not alive(record):
                continue
            for fd in (Path("/proc") / str(record["pid"]) / "fd").iterdir():
                try:
                    if os.readlink(str(fd)) in inodes and alive(record):
                        return True
                except OSError:
                    continue
    except OSError:
        return False
    return False


def url(host, port):
    display = "127.0.0.1" if host == "0.0.0.0" else "::1" if host == "::" else host
    return "http://{}:{}".format("[{}]".format(display) if ":" in display else display, port)


def healthy(records, host, port, server):
    if not owned_listener(records, host, port):
        return False
    probe_host = "127.0.0.1" if host == "0.0.0.0" else "::1" if host == "::" else host
    connection = http.client.HTTPConnection(probe_host, port, timeout=0.3)
    try:
        connection.request("GET", server.get("health_path", "/"))
        response = connection.getresponse()
        return response.status == server.get("health_status", 200) and owned_listener(records, host, port)
    except (OSError, http.client.HTTPException):
        return False
    finally:
        connection.close()


def cleanup(guardian, timeout):
    deadline = time.monotonic() + timeout
    while True:
        records = members(guardian)
        if not records:
            return True
        number = signal.SIGTERM if time.monotonic() < deadline else signal.SIGKILL
        for record in records:
            try:
                send(record, number)
            except (OSError, LauncherError):
                pass  # A child can exec/exit; resample its lifetime on the next pass.
        if time.monotonic() > deadline + 2:
            return not members(guardian)
        time.sleep(0.05)


def endpoint(directory, state, records):
    if state["requested_port"]:
        return state["requested_port"]
    path = directory / ("endpoint-" + state["run_id"] + ".json")
    if not path.exists():
        return 0
    fd = private_file(path, os.O_RDONLY)
    with os.fdopen(fd, "r") as stream:
        value = json.load(stream)
    if (not isinstance(value, dict) or value.get("schema_version") != 1 or
            value.get("host") != state["host"] or type(value.get("port")) is not int or
            not 1 <= value["port"] <= 65535 or
            value.get("pid") not in [record["pid"] for record in records]):
        raise LauncherError("Endpoint report does not belong to this server attempt")
    return value["port"]


def supervise(manifest, root, args):
    require_support()
    if len(args) != 3:
        raise LauncherError("Invalid supervisor invocation")
    run_id, host, text_port = args
    uuid.UUID(run_id)
    ipaddress.ip_address(host)
    port = int(text_port)
    directory = runtime(root, create=True)
    guardian = identity(os.getpid())
    if guardian["sid"] != guardian["pid"] or guardian["pgid"] != guardian["pid"]:
        raise LauncherError("Supervisor must lead its own session")
    state = {"schema_version": 1, "engine_version": ENGINE_VERSION, "root": str(root),
             "run_id": run_id, "guardian": guardian, "phase": "starting", "members": [],
             "host": host, "port": 0, "requested_port": port,
             "config_digest": hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()}
    stopped = []
    signal.signal(signal.SIGTERM, lambda *_: stopped.append(True))
    signal.signal(signal.SIGINT, lambda *_: stopped.append(True))
    server = manifest["server"]
    child = None
    endpoint_path = directory / ("endpoint-" + run_id + ".json")
    try:
        write_state(directory, state)
        action = manifest["actions"][server["action"]]
        values = {"{host}": host, "{port}": str(port), "{endpoint_file}": str(endpoint_path)}
        extra = []
        for arg in server["args"]:
            for key, value in values.items():
                arg = arg.replace(key, value)
            extra.append(arg)
        env = dict(os.environ)
        for key, value in action.get("env", {}).items():
            env.setdefault(key, expand(value, root))
        child = subprocess.Popen([expand(arg, root) for arg in action["argv"]] + extra,
                                 cwd=str(action_cwd(action, root)), env=env, stdin=subprocess.DEVNULL)
        deadline = time.monotonic() + server.get("startup_timeout", 10)
        was_ready = False
        while not stopped:
            records = members(guardian)
            state["members"] = records
            if child.poll() is not None:
                state.update(phase="failed", detail="Server exited with code {}".format(child.returncode))
                break
            state["port"] = endpoint(directory, state, records)
            ready = healthy(records, host, state["port"], server)
            state["phase"] = "ready" if ready else "unhealthy" if was_ready else "starting"
            was_ready = was_ready or ready
            if not was_ready and time.monotonic() > deadline:
                state.update(phase="failed", detail="Server did not become ready before the deadline")
                break
            write_state(directory, state)
            time.sleep(0.2 if not was_ready else 0.5)
    except Exception as error:
        print("supervisor: " + str(error), file=sys.stderr, flush=True)
        state.update(phase="failed", detail="Server startup or supervision failed; inspect logs")
    finally:
        cleaned = cleanup(guardian, server.get("stop_timeout", 3))
        if child is not None:
            try:
                child.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                cleaned = False
        state["members"] = members(guardian)
        if not cleaned:
            state.update(phase="unknown", detail="Some owned descendants could not be stopped")
        elif stopped:
            state["phase"] = "stopped"
        write_state(directory, state)
        if cleaned and endpoint_path.exists() and not endpoint_path.is_symlink():
            try:
                report = read_json(endpoint_path)
                if report.get("pid") == (child.pid if child is not None else None):
                    endpoint_path.unlink()
            except (LauncherError, AttributeError):
                pass
    return 0 if cleaned and stopped else 1


def live_state(state, manifest):
    if not state:
        return "stopped", []
    guardian = state["guardian"]
    try:
        expected = [sys.executable, "-B", str(Path(state["root"]) / "tools/project_launcher"),
                    "--project", state["root"], "_server-worker", state["run_id"],
                    state["host"], str(state["requested_port"])]
        command_matches = hashlib.sha256(b"\0".join(os.fsencode(arg) for arg in expected) + b"\0").hexdigest() == guardian.get("command")
    except (KeyError, TypeError):
        return "unknown", []
    if not command_matches:
        return "unknown", []
    if not alive(guardian):
        # Completed cleanup is recorded by the guardian, before it exits.
        if state["phase"] in ("stopped", "failed") and not state.get("members"):
            return "stopped", []
        return "unknown", []
    if guardian.get("uid") != os.getuid() or guardian.get("sid") != guardian.get("pid"):
        return "unknown", []
    records = members(guardian)
    if not alive(guardian):
        return "unknown", []
    return ("ready" if healthy(records, state["host"], state["port"], manifest["server"]) else
            "starting" if state["phase"] == "starting" else "unhealthy"), records


def public(state, phase, root, directory):
    return {"state": phase, "owned": phase in ("starting", "ready", "unhealthy"),
            "scope": "checkout", "root": str(root), "engine_version": ENGINE_VERSION,
            "pid": state["guardian"]["pid"] if state and phase != "stopped" else None,
            "host": state.get("host") if state else None, "port": state.get("port") if state else None,
            "url": url(state["host"], state["port"]) if state and state.get("port") else None,
            "log": str(directory / "server.log"),
            "detail": state.get("detail") if state else None}


def stop(state, manifest, directory, root):
    phase, _ = live_state(state, manifest)
    if phase == "stopped":
        return
    if phase == "unknown":
        raise LauncherError("Ownership is unknown; inspect retained state. No process was stopped")
    send(state["guardian"], signal.SIGTERM)
    deadline = time.monotonic() + manifest["server"].get("stop_timeout", 3) + 4
    while time.monotonic() < deadline:
        current = read_state(directory, root)
        if not alive(state["guardian"]):
            if live_state(current, manifest)[0] == "stopped":
                return
            raise LauncherError("Supervisor exited without verified cleanup; inspect retained state")
        time.sleep(0.05)
    raise LauncherError("Supervisor did not finish cleanup; state retained")


def free(host, port):
    try:
        with socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET) as sock:
            # Match ordinary HTTP servers: TIME_WAIT is not a live foreign listener.
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
        return True
    except OSError as error:
        if error.errno in (98, 99):
            return False
        raise


def log_tail(directory, count=30):
    path = directory / "server.log"
    if not path.exists():
        return ""
    fd = private_file(path, os.O_RDONLY)
    with os.fdopen(fd, "rb") as stream:
        stream.seek(0, os.SEEK_END)
        stream.seek(max(0, stream.tell() - 65536))
        return "\n".join(stream.read().decode(errors="replace").splitlines()[-count:])


def start(manifest, root, directory, host, port, explicit):
    current = read_state(directory, root)
    phase, _ = live_state(current, manifest)
    if phase == "unknown":
        raise LauncherError("Previous supervisor ownership is unknown; inspect state before starting")
    if phase == "ready":
        if current["host"] != host or (explicit and port and current["port"] != port):
            raise LauncherError("An owned server uses another endpoint; use managed-restart")
        return current
    if phase != "stopped":
        raise LauncherError("An owned server is not ready; use managed-restart")
    server = manifest["server"]
    attempts = 1 if explicit or port == 0 else server.get("port_attempts", 1)
    for candidate in range(port, min(65535, port + attempts - 1) + 1):
        if candidate and not free(host, candidate):
            continue
        run_id = str(uuid.uuid4())
        fd = private_file(directory / "server.log", os.O_CREAT | os.O_WRONLY | os.O_APPEND)
        with os.fdopen(fd, "a") as log:
            guardian = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve().parent),
                                         "--project", str(root), "_server-worker", run_id, host, str(candidate)],
                                        cwd=str(root), stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                        start_new_session=True)
        launched_identity = identity(guardian.pid)
        deadline = time.monotonic() + server.get("startup_timeout", 10) + 3
        state = None
        try:
            while time.monotonic() < deadline:
                state = read_state(directory, root)
                if state and state["run_id"] == run_id:
                    current_phase, _ = live_state(state, manifest)
                    if state["phase"] == "ready" and current_phase == "ready":
                        return state
                if guardian.poll() is not None:
                    break
                time.sleep(0.05)
        except BaseException:
            if state and state["run_id"] == run_id:
                stop(state, manifest, directory, root)
            elif alive(launched_identity):
                send(launched_identity, signal.SIGTERM)
                guardian.wait(timeout=server.get("stop_timeout", 3) + 4)
            raise
        if state and state["run_id"] == run_id and alive(state["guardian"]):
            stop(state, manifest, directory, root)
        try:
            guardian.wait(timeout=server.get("stop_timeout", 3) + 4)
        except subprocess.TimeoutExpired as error:
            raise LauncherError("Supervisor cleanup timed out; inspect retained state") from error
        if candidate == port + attempts - 1 or not free(host, candidate):
            # Retry a lost bind race only when the next candidate is declared.
            if candidate < port + attempts - 1:
                continue
        raise LauncherError("Server startup failed. Recent logs:\n" + log_tail(directory))
    raise LauncherError("Requested address/port is occupied; no foreign process was stopped")


class Options(argparse.ArgumentParser):
    def error(self, message):
        raise LauncherError(message)


def requested_address(server, options):
    raw_host = getattr(options, "host", None) or os.getenv(server.get("host_env", "")) or server["host"]
    try:
        host = str(ipaddress.ip_address(raw_host))
        env_port = os.getenv(server.get("port_env", ""))
        port = getattr(options, "port", None)
        port = port if port is not None else int(env_port) if env_port else server["port"]
    except ValueError as error:
        raise LauncherError("Host must be numeric and port must be an integer") from error
    if not 0 <= port <= 65535 or (port == 0 and not any("{endpoint_file}" in a for a in server["args"])):
        raise LauncherError("Port must be 1..65535, or 0 with endpoint reporting")
    return host, port


def command(manifest, root, name, args):
    parser = Options(prog="./run.sh " + name, add_help=False)
    parser.add_argument("--json", action="store_true")
    if name in ("managed-start", "managed-restart"):
        parser.add_argument("--host")
        parser.add_argument("--port", type=int)
    if name == "managed-logs":
        parser.add_argument("--lines", type=int, default=80)
        parser.add_argument("--follow", action="store_true")
    options = parser.parse_args(args)
    require_support()
    root = Path(root).resolve()
    mutating = name in ("managed-start", "managed-restart", "managed-stop")
    directory = runtime(root, create=mutating)
    if name == "managed-logs":
        if options.json or not 1 <= options.lines <= 10000:
            raise LauncherError("managed-logs takes --lines 1..10000 and optional --follow")
        print(log_tail(directory, options.lines), flush=True)
        if options.follow:
            # tail follows only a verified private file; it has no lifecycle authority.
            fd = private_file(directory / "server.log", os.O_RDONLY)
            try:
                os.set_inheritable(fd, True)
                os.execvp("tail", ["tail", "-n", "0", "-f", "/proc/self/fd/" + str(fd)])
            finally:
                os.close(fd)
        return 0
    if not mutating:
        state = read_state(directory, root)
        phase, _ = live_state(state, manifest)
        if phase == "stopped":
            host, port = requested_address(manifest["server"], options)
            if port and not free(host, port):
                phase = "external"
        result = public(state, phase, root, directory)
        if phase == "external":
            result.update(host=host, port=port, url=url(host, port))
    else:
        server = manifest["server"]
        # Stop acts on the recorded instance, independently of new endpoint overrides.
        host, port = requested_address(server, options) if name != "managed-stop" else (None, None)
        with operation(directory, server.get("startup_timeout", 10) + server.get("stop_timeout", 3) + 6):
            state = read_state(directory, root)
            if name in ("managed-stop", "managed-restart"):
                stop(state, manifest, directory, root)
            if name in ("managed-start", "managed-restart"):
                state = start(manifest, root, directory, host, port, getattr(options, "port", None) is not None)
            else:
                state = read_state(directory, root)
            phase, _ = live_state(state, manifest)
            result = public(state, phase, root, directory)
    if options.json:
        print(json.dumps(result, indent=2))
    else:
        print("{}{} · log: {}".format(result["state"], " " + result["url"] if result["url"] else "", result["log"]))
    return 1 if result["state"] in ("unknown", "unhealthy", "external") else 0
