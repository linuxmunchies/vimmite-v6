"""Launcher CLI. Foreground/delegated execution uses exec to preserve signals."""

import json
import os
import shutil
import sys
from pathlib import Path

from . import ENGINE_VERSION
from .config import CORE_ACTIONS, MANAGED_ACTIONS, SERVICE_ACTIONS, RESERVED_ACTIONS, LauncherError, action_cwd, expand, load


def metadata(manifest):
    return {"schema_version": 1, "engine_version": ENGINE_VERSION,
            "name": manifest["name"], "adapter": manifest["adapter"],
            "default_action": manifest["default_action"],
            "argument_mode": manifest.get("argument_mode", "strict"),
            "actions": list(manifest["actions"]) + (list(MANAGED_ACTIONS + SERVICE_ACTIONS) if manifest["adapter"] == "server" else []), "core_actions": list(CORE_ACTIONS),
            "requirements": manifest.get("requirements", []),
            "preparation": manifest.get("preparation", "None declared"),
            "scope": manifest.get("scope", "checkout")}


def executable_available(command, cwd, env):
    if os.sep in command:
        path = Path(command)
        if not path.is_absolute():
            path = cwd / path
        return path.is_file() and os.access(str(path), os.X_OK)
    return shutil.which(command, path=env.get("PATH")) is not None


def doctor(manifest, root, action_name=None):
    checks = []
    if action_name is not None and action_name not in manifest["actions"]:
        raise LauncherError("doctor --action must name a declared foreground/project action")
    if manifest["adapter"] == "server" and action_name is None:
        from .server import support_check
        support = support_check()
        checks.append({"item": "managed server Linux pidfds/procfs", "available": support["ok"], "detail": support["detail"]})
    for requirement in manifest.get("requirements", []) if action_name is None else []:
        checks.append({"item": requirement, "available": executable_available(expand(requirement, root), root, os.environ)})
    for name, action in manifest["actions"].items():
        if action_name is not None and name != action_name:
            continue
        cwd = action_cwd(action, root)
        env = dict(os.environ)
        for key, value in action.get("env", {}).items():
            env.setdefault(key, expand(value, root))
        checks.append({"item": name + " working directory", "available": cwd.is_dir()})
        checks.append({"item": name + " executable", "available": executable_available(expand(action["argv"][0], root), cwd, env)})
        for relative in action.get("required_files", []):
            path = (Path(root) / relative).resolve()
            try:
                path.relative_to(Path(root).resolve())
                available = path.is_file() and os.access(str(path), os.R_OK)
            except ValueError:
                available = False
            checks.append({"item": name + " required file: " + relative, "available": available})
    return {"name": manifest["name"], "ok": all(c["available"] for c in checks),
            "checks": checks, "preparation": manifest.get("preparation", "None declared"),
            "note": "Static checks only; application readiness and hook prerequisites are unverified."}


def execute(manifest, root, name, args):
    action = manifest["actions"][name]
    if args and not action.get("forward_args", False):
        raise LauncherError("Action {} does not accept arguments".format(name))
    argv = [expand(arg, root) for arg in action["argv"]] + args
    env = dict(os.environ)
    for key, value in action.get("env", {}).items():
        env.setdefault(key, expand(value, root))
    os.chdir(str(action_cwd(action, root)))
    try:
        os.execvpe(argv[0], argv, env)
    except FileNotFoundError:
        print("launcher: executable not found: " + argv[0], file=sys.stderr)
        return 127
    except PermissionError:
        print("launcher: executable is not permitted: " + argv[0], file=sys.stderr)
        return 126


def dispatch(manifest, root, args):
    if not args:
        name, rest = manifest["default_action"], []
    elif args[0] == "--":
        name, rest = manifest["default_action"], args[1:]
    elif args[0] in manifest["actions"] or args[0] in RESERVED_ACTIONS:
        name, rest = args[0], args[1:]
        if rest[:1] == ["--"] and name not in CORE_ACTIONS:
            rest = rest[1:]
    elif manifest.get("argument_mode", "strict") == "default-action-passthrough":
        name, rest = manifest["default_action"], args
    else:
        raise LauncherError("Unknown action {}; use help".format(args[0]))
    if name == "help":
        if rest:
            raise LauncherError("Usage: ./run.sh help")
        info = metadata(manifest)
        print("{} launcher ({})".format(info["name"], ENGINE_VERSION))
        print("Default: {} | adapter: {} | scope: {}".format(info["default_action"], info["adapter"], info["scope"]))
        print("Preparation: " + info["preparation"])
        print("Core actions: help, info [--json], doctor [--action ACTION] [--json], menu")
        for action, definition in manifest["actions"].items():
            print("  {}{}  {}".format(action, " -- APP_ARGS" if definition.get("forward_args") else "", definition.get("description", "")))
        if manifest["adapter"] == "server":
            print("Managed server: " + ", ".join(MANAGED_ACTIONS))
            print("  managed-start/restart [--host IP] [--port PORT] [--json]")
            print("  managed-status/stop [--json]; managed-logs [--lines N] [--follow]")
            print("Optional Linux user service: " + ", ".join(SERVICE_ACTIONS))
            print("  service-install [--host IP] [--port PORT] [--apply]; service-remove [--apply]")
            print("  service-status [--json]; service-logs [--lines N] [--follow]")
            print("Service installation only previews by default. Enable/start are separate explicit commands.")
        print("Use ACTION -- ARGS to separate launcher actions from application arguments.")
        return 0
    if name in ("info", "doctor"):
        from .server import Options
        parser = Options(prog="./run.sh " + name, add_help=False)
        parser.add_argument("--json", action="store_true")
        if name == "doctor":
            parser.add_argument("--action")
        options = parser.parse_args(rest)
        value = metadata(manifest) if name == "info" else doctor(manifest, root, options.action)
        if options.json or name == "info":
            print(json.dumps(value, indent=2))
        else:
            print(value["name"] + ": " + ("prerequisites available" if value["ok"] else "missing prerequisites"))
            for check in value["checks"]:
                print("  {}: {}".format(check["item"], "available" if check["available"] else "missing"))
            print(value["note"])
            print("Preparation: " + value["preparation"])
        return 0 if value.get("ok", True) else 1
    if name == "menu":
        if rest:
            raise LauncherError("menu takes no arguments")
        from .menu import pick
        choice = pick(manifest)
        return dispatch(manifest, root, [choice]) if choice else 0
    if name in SERVICE_ACTIONS:
        if manifest["adapter"] != "server":
            raise LauncherError("Persistent service requires a server manifest")
        from .service import command
        return command(manifest, root, name, rest)
    if name in MANAGED_ACTIONS:
        if manifest["adapter"] != "server":
            raise LauncherError("Managed server is not configured")
        from .server import command
        return command(manifest, root, name, rest)
    if name not in manifest["actions"]:
        raise LauncherError("Unsupported action {} for {}; use help".format(name, manifest["name"]))
    return execute(manifest, root, name, rest)


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if len(args) < 2 or args[0] != "--project":
            raise LauncherError("Engine usage: python3 tools/project_launcher --project ROOT [ACTION]")
        root = Path(args[1]).resolve()
        manifest = load(root)
        if args[2:3] == ["_service-worker"]:
            from .service import worker
            code = worker(manifest, root, args[3:])
        elif args[2:3] == ["_server-worker"]:
            from .server import supervise
            code = supervise(manifest, root, args[3:])
        else:
            code = dispatch(manifest, root, args[2:])
    except (LauncherError, OSError) as error:
        print("launcher: " + str(error), file=sys.stderr)
        code = 2
    except KeyboardInterrupt:
        code = 130
    sys.exit(code)
