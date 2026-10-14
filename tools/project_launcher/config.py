"""Validate data only. Never import or execute code from an inspected project."""

import json
import ipaddress
import math
import re
import sys
from pathlib import Path

CORE_ACTIONS = ("help", "info", "doctor", "menu")
MANAGED_ACTIONS = ("managed-start", "managed-stop", "managed-restart", "managed-status", "managed-logs")
SERVICE_ACTIONS = ("service-install", "service-start", "service-stop", "service-restart", "service-status", "service-logs", "service-enable", "service-disable", "service-remove")
RESERVED_ACTIONS = set(CORE_ACTIONS + MANAGED_ACTIONS + SERVICE_ACTIONS) | {"run", "start", "stop", "restart", "status", "logs", "open", "setup", "build", "dev", "update"}
MAX_JSON_BYTES = 1024 * 1024


class LauncherError(ValueError):
    pass


def read_json(path):
    def unique_fields(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise LauncherError("Duplicate JSON field: " + key)
            result[key] = value
        return result
    try:
        with Path(path).open("rb") as stream:
            data = stream.read(MAX_JSON_BYTES + 1)
        if len(data) > MAX_JSON_BYTES:
            raise LauncherError("JSON file is too large: {}".format(path))
        return json.loads(data, object_pairs_hook=unique_fields)
    except (OSError, ValueError, UnicodeError) as error:
        raise LauncherError("Cannot read {}: {}".format(path, error)) from error


def fields(value, allowed, required, label):
    if not isinstance(value, dict):
        raise LauncherError(label + " must be an object")
    unknown = set(value) - set(allowed)
    missing = set(required) - set(value)
    if unknown or missing:
        raise LauncherError("{}: unknown fields {}; missing fields {}".format(label, sorted(unknown), sorted(missing)))


def string(value, label):
    if not isinstance(value, str) or not value or "\0" in value:
        raise LauncherError(label + " must be a nonempty string without NUL characters")


def relative_path(value, label):
    string(value, label)
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or ".git" in path.parts:
        raise LauncherError(label + " must be a project-relative path without .. or .git")


def validate(manifest):
    fields(manifest, {"schema_version", "name", "adapter", "default_action", "argument_mode", "actions", "requirements", "preparation", "scope", "server"},
           {"schema_version", "name", "adapter", "default_action", "actions"}, "manifest")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise LauncherError("Unsupported launcher schema_version; expected 1")
    string(manifest["name"], "name")
    if manifest["adapter"] not in ("foreground", "delegated", "server"):
        raise LauncherError("Supported adapters: foreground, delegated, server")
    if manifest.get("argument_mode", "strict") not in ("strict", "default-action-passthrough"):
        raise LauncherError("Invalid argument_mode")
    if manifest.get("scope", "checkout") not in ("checkout", "installed-app"):
        raise LauncherError("Invalid scope")
    if "preparation" in manifest:
        string(manifest["preparation"], "preparation")
    requirements = manifest.get("requirements", [])
    if not isinstance(requirements, list):
        raise LauncherError("requirements must be an array of executable names/paths")
    for requirement in requirements:
        string(requirement, "requirement")
    actions = manifest["actions"]
    if not isinstance(actions, dict) or not actions:
        raise LauncherError("actions must be a nonempty object")
    for name, action in actions.items():
        if not re.fullmatch(r"[a-z][a-z0-9-]*", name) or name in CORE_ACTIONS + MANAGED_ACTIONS + SERVICE_ACTIONS:
            raise LauncherError("Invalid or reserved action name: " + name)
        fields(action, {"argv", "cwd", "forward_args", "env", "description", "required_files"}, {"argv"}, "action " + name)
        argv = action["argv"]
        if not isinstance(argv, list) or not argv:
            raise LauncherError("action argv must be a nonempty array")
        for arg in argv:
            if not isinstance(arg, str) or "\0" in arg:
                raise LauncherError("argv entries must be strings without NUL characters")
        string(argv[0], "argv executable")
        cwd = action.get("cwd", "project")
        if cwd not in ("project", "caller"):
            relative_path(cwd, "cwd")
        if "forward_args" in action and type(action["forward_args"]) is not bool:
            raise LauncherError("forward_args must be boolean")
        required_files = action.get("required_files", [])
        if not isinstance(required_files, list):
            raise LauncherError("required_files must be an array of project-relative paths")
        for path in required_files:
            relative_path(path, "required file")
        env = action.get("env", {})
        if not isinstance(env, dict):
            raise LauncherError("env must be an object of environment defaults")
        for key, value in env.items():
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) or not isinstance(value, str) or "\0" in value:
                raise LauncherError("Invalid environment default")
        if "description" in action:
            string(action["description"], "description")
    string(manifest["default_action"], "default_action")
    if manifest["default_action"] not in actions and manifest["default_action"] != "menu" and not (
            manifest["adapter"] == "server" and manifest["default_action"] in MANAGED_ACTIONS):
        raise LauncherError("default_action must name an action or menu")
    if manifest["adapter"] == "server":
        server = manifest.get("server")
        fields(server, {"action", "service_action", "args", "host", "port", "port_env", "host_env", "port_attempts", "startup_timeout",
                        "stop_timeout", "health_path", "health_status"},
               {"action", "args", "host", "port"}, "server")
        string(server["action"], "server.action")
        if server["action"] not in actions:
            raise LauncherError("server.action must name a foreground action")
        if actions[server["action"]].get("cwd", "project") == "caller":
            raise LauncherError("Managed server action must use a checkout-relative cwd")
        if not actions[server["action"]].get("forward_args", False):
            raise LauncherError("Managed server action must accept arguments")
        if "service_action" in server:
            service_action = server["service_action"]
            string(service_action, "server.service_action")
            if (service_action not in actions or not actions[service_action].get("forward_args", False)
                    or actions[service_action].get("cwd", "project") == "caller"):
                raise LauncherError("server.service_action must name a foreground action accepting arguments with checkout-relative cwd")
        string(server["host"], "server.host")
        try:
            ipaddress.ip_address(server["host"])
        except ValueError as error:
            raise LauncherError("server.host must be a numeric IP address") from error
        if type(server["port"]) is not int or not 0 <= server["port"] <= 65535:
            raise LauncherError("server.port must be an integer from 0 to 65535")
        args = server["args"]
        if not isinstance(args, list) or not all(isinstance(a, str) and "\0" not in a for a in args):
            raise LauncherError("server.args must be an array of strings")
        if not any("{port}" in a for a in args):
            raise LauncherError("server.args must pass {port} to the foreground action")
        if server["port"] == 0 and not any("{endpoint_file}" in a for a in args):
            raise LauncherError("Port 0 needs {endpoint_file} reporting")
        for key in ("port_env", "host_env"):
            if key in server and (not isinstance(server[key], str) or
                    not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", server[key])):
                raise LauncherError("Invalid server." + key)
        attempts = server.get("port_attempts", 1)
        if type(attempts) is not int or not 1 <= attempts <= 20:
            raise LauncherError("server.port_attempts must be from 1 to 20")
        for key, maximum in (("startup_timeout", 120), ("stop_timeout", 30)):
            value = server.get(key, 10 if key == "startup_timeout" else 3)
            if type(value) not in (int, float) or not math.isfinite(value) or not 0.1 <= value <= maximum:
                raise LauncherError("Invalid server." + key)
        path = server.get("health_path", "/")
        if not isinstance(path, str) or not path.startswith("/") or "\0" in path or "\r" in path or "\n" in path:
            raise LauncherError("server.health_path must be an HTTP path")
        status = server.get("health_status", 200)
        if type(status) is not int or not 100 <= status <= 599:
            raise LauncherError("Invalid server.health_status")
        if manifest.get("scope", "checkout") != "checkout":
            raise LauncherError("Managed server scope must be checkout")
    elif "server" in manifest:
        raise LauncherError("server configuration requires the server adapter")
    return manifest


def load(root):
    return validate(read_json(Path(root) / "launcher.json"))


def expand(value, root):
    return value.replace("{root}", str(Path(root).resolve())).replace("{python}", sys.executable)


def action_cwd(action, root):
    cwd = action.get("cwd", "project")
    if cwd == "caller":
        return Path.cwd()
    root = Path(root).resolve()
    destination = root if cwd == "project" else (root / cwd).resolve()
    try:
        destination.relative_to(root)
    except ValueError as error:
        raise LauncherError("Action cwd escapes the project through a symlink") from error
    return destination
