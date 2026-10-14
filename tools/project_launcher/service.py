"""Opt-in systemd user services. Never install dependencies or capture secrets."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

from .config import LauncherError

HEADER = "# project-launcher-service: "


def manifest_digest(manifest):
    return hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()


def unit_name(root):
    return "project-launcher-" + hashlib.sha256(os.fsencode(str(Path(root).resolve()))).hexdigest()[:20] + ".service"


def unit_path(root):
    base = Path(os.getenv("XDG_CONFIG_HOME") or str(Path.home() / ".config"))
    if not base.is_absolute():
        raise LauncherError("XDG_CONFIG_HOME must be absolute")
    path = base / "systemd" / "user" / unit_name(root)
    for part in (path,) + tuple(path.parents):
        if part.is_symlink():
            raise LauncherError("Refusing symlinked service path: " + str(part))
    return path


def quote(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t") + '"'


def render(settings):
    argv = [settings["python"], "-B", settings["root"] + "/tools/project_launcher", "--project",
            settings["root"], "_service-worker", settings["manifest_digest"], settings["host"], str(settings["port"])]
    return (HEADER + json.dumps(settings, sort_keys=True) + "\n"
            "[Unit]\nDescription=Project launcher user service\nStartLimitIntervalSec=60\nStartLimitBurst=5\n\n"
            "[Service]\nType=simple\nWorkingDirectory=/\n"
            "ExecStart=:" + " ".join(quote(arg) for arg in argv) + "\n"
            "Environment=" + quote("PATH=" + settings["path"]) + "\nEnvironment=PYTHONUNBUFFERED=1\n"
            "Restart=on-failure\nRestartSec=5\nKillMode=control-group\nTimeoutStopSec=10\n"
            "StandardOutput=journal\nStandardError=journal\n\n[Install]\nWantedBy=default.target\n")


def read(root):
    path = unit_path(root)
    if not path.exists():
        return None
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise LauncherError("Service unit must be a regular file owned by you, without group/other write access")
    if info.st_size > 65536:
        raise LauncherError("Service unit is too large")
    content = path.read_text()
    try:
        settings = json.loads(content.splitlines()[0][len(HEADER):]) if content.startswith(HEADER) else None
        if (not isinstance(settings, dict) or set(settings) != {"root", "python", "path", "host", "port", "manifest_digest"}
                or settings["root"] != str(Path(root).resolve())
                or any(not isinstance(settings[k], str) or "\0" in settings[k] for k in ("root", "python", "path", "host", "manifest_digest"))
                or not Path(settings["python"]).is_absolute()
                or type(settings["port"]) is not int or not 1 <= settings["port"] <= 65535
                or not re.fullmatch(r"[0-9a-f]{64}", settings["manifest_digest"])):
            raise ValueError("invalid metadata")
        from ipaddress import ip_address
        ip_address(settings["host"])
        if content != render(settings):
            raise ValueError("modified unit")
    except (ValueError, TypeError, KeyError, IndexError) as error:
        raise LauncherError("Unmanaged or edited service unit; inspect it before proceeding: " + str(path)) from error
    return settings


def systemctl(*args, check=True):
    if sys.platform != "linux" or not shutil.which("systemctl"):
        raise LauncherError("Persistent services require Linux systemd and a reachable user manager")
    try:
        result = subprocess.run(["systemctl", "--user", "--no-pager", *args], stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired as error:
        raise LauncherError("systemd user manager timed out") from error
    if check and result.returncode:
        raise LauncherError(result.stderr.strip() or result.stdout.strip() or "systemd user command failed")
    return result


def properties(root):
    result = systemctl("show", unit_name(root), "--property=LoadState,ActiveState,SubState,UnitFileState,MainPID,Result,FragmentPath,DropInPaths")
    values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    # Unit aliases or manager overrides must not redirect our controls to another fragment.
    if values.get("FragmentPath") and Path(values["FragmentPath"]) != unit_path(root):
        raise LauncherError("User manager loaded another service fragment; no control command sent")
    if values.get("DropInPaths"):
        raise LauncherError("Service has manager overrides; inspect them before using launcher controls")
    return values


def inactive(root):
    values = properties(root)
    if values.get("ActiveState") not in ("inactive", "failed"):
        raise LauncherError("Stop the user service before changing or removing its unit")
    return values


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".project-launcher-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
        os.chmod(name, 0o600)
        os.replace(name, str(path))
    finally:
        if os.path.exists(name):
            os.unlink(name)


def worker(manifest, root, args):
    if len(args) != 3 or manifest["adapter"] != "server" or args[0] != manifest_digest(manifest):
        raise LauncherError("Service configuration changed; stop and reinstall the unit before restarting")
    from .server import live_state, read_state, runtime, free, requested_address, require_support
    require_support()
    host, port = requested_address(manifest["server"], argparse.Namespace(host=args[1], port=int(args[2])))
    if not port:
        raise LauncherError("Persistent services require a stable nonzero port")
    state = read_state(runtime(root), root)
    if live_state(state, manifest)[0] != "stopped":
        raise LauncherError("Temporary managed ownership is active or unknown; review/stop it before service startup")
    if not free(host, port):
        raise LauncherError("Service address/port is occupied; no foreign process was stopped")
    extra = [arg.replace("{host}", host).replace("{port}", str(port)) for arg in manifest["server"]["args"]]
    # A nonzero port does not require endpoint reporting, but existing hooks may accept it.
    if any("{endpoint_file}" in arg for arg in extra):
        raise LauncherError("This foreground hook requires endpoint reporting; use managed lifecycle for this project")
    from .cli import execute
    return execute(manifest, root, manifest["server"].get("service_action", manifest["server"]["action"]), extra)


def command(manifest, root, name, args):
    from .server import Options, requested_address
    parser = Options(prog="./run.sh " + name, add_help=False)
    parser.add_argument("--json", action="store_true")
    if name in ("service-install", "service-remove"):
        parser.add_argument("--apply", action="store_true")
    if name == "service-install":
        parser.add_argument("--host")
        parser.add_argument("--port", type=int)
    if name == "service-logs":
        parser.add_argument("--lines", type=int, default=80)
        parser.add_argument("--follow", action="store_true")
    options = parser.parse_args(args)
    root = Path(root).resolve()
    path = unit_path(root)
    installed = read(root)
    if name == "service-install":
        host, port = requested_address(manifest["server"], options)
        if not port or any("{endpoint_file}" in a for a in manifest["server"]["args"]):
            raise LauncherError("User services need a nonzero port and a foreground hook without endpoint reporting")
        settings = {"root": str(root), "python": sys.executable, "host": host, "port": port,
                    "path": os.environ.get("PATH", os.defpath), "manifest_digest": manifest_digest(manifest)}
        content = render(settings)
        if options.apply:
            if installed:
                inactive(root)
            else:
                systemctl("show-environment")  # Check availability before writing.
            write(path, content)
            systemctl("daemon-reload")
        result = {"unit": unit_name(root), "path": str(path), "applied": options.apply, "content": content,
                  "note": "Start and enable are separate commands. Boot/logout persistence requires a user manager that survives logout (for example, loginctl enable-linger)."}
    elif not installed:
        if name == "service-status":
            result = {"unit": unit_name(root), "state": "not-installed", "readiness": "unverified"}
        else:
            raise LauncherError("Service is not installed; preview with service-install, then service-install --apply")
    elif name == "service-remove":
        if options.apply:
            values = inactive(root)
            if values.get("UnitFileState") not in ("disabled", "static"):
                raise LauncherError("Disable the service before removing it")
            path.unlink()
            systemctl("daemon-reload")
        result = {"unit": unit_name(root), "path": str(path), "applied": options.apply}
    elif name == "service-logs":
        if options.json or not 1 <= options.lines <= 10000:
            raise LauncherError("service-logs takes --lines 1..10000 and optional --follow")
        properties(root)
        if not shutil.which("journalctl"):
            raise LauncherError("journalctl is missing")
        argv = ["journalctl", "--user", "--no-pager", "-u", unit_name(root), "-n", str(options.lines)]
        if options.follow:
            argv.append("-f")
        os.execvp(argv[0], argv)
    else:
        values = properties(root)
        if name != "service-status":
            if name in ("service-start", "service-restart", "service-enable") and installed["manifest_digest"] != manifest_digest(manifest):
                raise LauncherError("Manifest changed; stop and reinstall the service first")
            systemctl(name[len("service-"):], unit_name(root))
            values = properties(root)
        result = {"unit": unit_name(root), "state": values.get("ActiveState", "unknown"),
                  "substate": values.get("SubState"), "enabled": values.get("UnitFileState"),
                  "pid": values.get("MainPID"), "readiness": "unverified", "result": values.get("Result")}
    if options.json:
        print(json.dumps(result, indent=2))
    elif "content" in result:
        print(("Installed: " if result["applied"] else "Preview: ") + result["path"] + "\n" + result["content"] + result["note"])
    else:
        print(json.dumps(result, indent=2))
    return 1 if result.get("state") == "failed" else 0
