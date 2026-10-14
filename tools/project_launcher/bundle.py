"""Read launcher manifests and verify bundled files without running project code."""

import hashlib
import re
import stat
from pathlib import Path

from . import ENGINE_VERSION
from .cli import metadata
from .config import LauncherError, load, read_json

BUNDLE_PATH = "tools/project_launcher/BUNDLE.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def managed_path(name):
    if name in ("run.sh", "launcher.json", ".gitignore"):
        return True
    path = Path(name)
    return (len(path.parts) == 3 and path.parts[:2] == ("tools", "project_launcher")
            and (path.name in ("VERSION", "wrapper.sh", "BUNDLE.json") or re.fullmatch(r"[a-z_]+\.py", path.name) is not None))


def checked_path(root, name):
    """Refuse symlinks in a managed path, including broken links and ancestors."""
    root = Path(root).resolve()
    path = Path(name)
    if path.is_absolute() or not path.parts or any(p in ("..", ".git") for p in path.parts):
        raise LauncherError("Invalid project-relative path: " + str(name))
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise LauncherError("Refusing symlink in launcher path: " + str(current))
    return current


def file_record(path):
    if not path.is_file():
        raise LauncherError("Expected regular file: " + str(path))
    return {"sha256": digest(path.read_bytes()), "mode": stat.S_IMODE(path.stat().st_mode)}


def source_payload():
    source = Path(__file__).resolve().parent
    data = {}
    for path in sorted(source.iterdir()):
        if path.suffix == ".py" or path.name in ("VERSION", "wrapper.sh"):
            data["tools/project_launcher/" + path.name] = (path.read_bytes(), 0o644)
    data["run.sh"] = ((source / "wrapper.sh").read_bytes(), 0o755)
    return data


def bundle_record(payload):
    return {"schema_version": 1, "engine_version": ENGINE_VERSION,
            "files": {name: {"sha256": digest(value[0]), "mode": value[1]} for name, value in sorted(payload.items())}}


def read_bundle(root):
    record = read_json(checked_path(root, BUNDLE_PATH))
    if (not isinstance(record, dict) or set(record) != {"schema_version", "engine_version", "files"}
            or type(record["schema_version"]) is not int or record["schema_version"] != 1
            or not isinstance(record["engine_version"], str)
            or not re.fullmatch(r"\d+\.\d+\.\d+", record["engine_version"])):
        raise LauncherError("Invalid launcher bundle metadata")
    files = record["files"]
    if not isinstance(files, dict) or not {"run.sh", "tools/project_launcher/__main__.py", "tools/project_launcher/VERSION"} <= set(files):
        raise LauncherError("Incomplete launcher bundle metadata")
    for name, value in files.items():
        if (not managed_path(name) or name in (BUNDLE_PATH, "launcher.json", ".gitignore")
                or not isinstance(value, dict) or set(value) != {"sha256", "mode"}
                or not isinstance(value["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", value["sha256"])
                or type(value["mode"]) is not int or value["mode"] not in (0o644, 0o755)):
            raise LauncherError("Invalid managed file metadata: " + name)
    return record


def inspect(root):
    root = Path(root).resolve()
    result = {"state": "missing", "engine_version": None}
    manifest_path = root / "launcher.json"
    if not manifest_path.exists() and not manifest_path.is_symlink():
        if (root / BUNDLE_PATH).exists():
            result.update(state="incomplete", error="launcher.json is missing")
        return result
    try:
        checked_path(root, "launcher.json")
        manifest = load(root)  # Only JSON; never execute a repository's engine.
        result.update(metadata(manifest))
        result["engine_version"] = None
        if not (root / BUNDLE_PATH).is_file():
            result.update(state="incomplete", error="Bundled engine metadata is missing")
            return result
        bundle = read_bundle(root)
        result["engine_version"] = bundle["engine_version"]
        changes = []
        for name, expected in bundle["files"].items():
            try:
                if file_record(checked_path(root, name)) != expected:
                    changes.append(name)
            except LauncherError:
                changes.append(name)
        version = checked_path(root, "tools/project_launcher/VERSION").read_text().strip()
        if version != bundle["engine_version"]:
            changes.append("tools/project_launcher/VERSION")
        if bundle["engine_version"] == ENGINE_VERSION:
            expected_files = bundle_record(source_payload())["files"]
            if bundle["files"] != expected_files:
                changes.append(BUNDLE_PATH)
        if changes:
            result.update(state="modified", changed_files=sorted(set(changes)), error="Generated launcher files differ from the recorded bundle")
        else:
            installed = tuple(map(int, bundle["engine_version"].split(".")))
            available = tuple(map(int, ENGINE_VERSION.split(".")))
            result["state"] = "current" if installed == available else "newer" if installed > available else "outdated"
    except (LauncherError, OSError, UnicodeError) as error:
        result.update(state="invalid", error=str(error))
    return result
