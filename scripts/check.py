#!/usr/bin/env python3
"""Non-mutating source checks; never execute an image's setup commands."""

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*args, **kwargs):
    return subprocess.run(args, cwd=ROOT, check=True, text=True, **kwargs)


def shell_files():
    # Limit traversal to source trees: ISO workspaces may contain entire images.
    return sorted(
        path for directory in (ROOT / "files", ROOT / "scripts")
        for path in directory.rglob("*")
        if path.is_file() and path.open("rb").readline().rstrip()
        in (b"#!/usr/bin/env bash", b"#!/bin/bash")
    )


def bash_check():
    paths = shell_files()
    for path in paths:
        run("bash", "-n", str(path))
    print(f"Bash syntax: {len(paths)} scripts passed", flush=True)


def shellcheck():
    # Warnings/errors block builds; informational style suggestions do not.
    run("shellcheck", "--severity=warning", *(str(p) for p in shell_files()))
    print("ShellCheck passed", flush=True)


def just_check():
    for path in sorted((ROOT / "files/justfiles").glob("*.just")):
        result = run("just", "--justfile", str(path), "--dump", "--dump-format", "json",
                     capture_output=True)
        recipes = json.loads(result.stdout)["recipes"]
        with tempfile.TemporaryDirectory(prefix="vimmite-just-check-") as temp:
            for name, recipe in recipes.items():
                run("just", "--justfile", str(path), "--dry-run", name, capture_output=True)
                variables = set()

                def fragment(value):
                    if isinstance(value, str):
                        return value
                    # Just's parsed interpolation representation. Keep shell
                    # variable syntax, so lint checks quoting instead of data.
                    if (len(value) == 1 and len(value[0]) == 2
                            and value[0][0] == "variable"):
                        variables.add(value[0][1])
                        return "${" + value[0][1] + "}"
                    raise ValueError(f"{path}:{name}: unsupported interpolation {value!r}")

                body = "\n".join("".join(fragment(part) for part in line)
                                 for line in recipe["body"])
                for helper in re.findall(r"/usr/libexec/(vimmite-[\w-]+)", body):
                    target = ROOT / "files/vimmite/usr/libexec" / helper
                    if not target.is_file() or not target.stat().st_mode & 0o111:
                        raise ValueError(f"{path}:{name}: missing executable helper {helper}")
                # These are shell inputs supplied by Just at runtime.
                inputs = "".join(f"{variable}=validation\n" for variable in sorted(variables))
                source = Path(temp) / f"{name}.sh"
                source.write_text("#!/usr/bin/env bash\n" + inputs + body + "\n")
                print(f"Checking Just recipe: {name}", flush=True)
                run("bash", "-n", str(source))
                run("shellcheck", "--severity=warning", str(source))
        print(f"Just parsing and embedded shell: {len(recipes)} recipes passed", flush=True)


def recipe_check():
    import yaml

    visited = set()

    def require_file(path):
        if not path.is_file():
            raise ValueError(f"Missing recipe input: {path.relative_to(ROOT)}")

    def visit(path):
        if path in visited:
            return
        require_file(path)
        visited.add(path)
        document = yaml.safe_load(path.read_text())
        for module in document.get("modules", [document]):
            if "from-file" in module:
                visit(ROOT / "recipes" / module["from-file"])
            if module.get("type") == "script":
                for script in module.get("scripts", []):
                    require_file(ROOT / "files/scripts" / script)
            if module.get("type") == "files":
                for entry in module.get("files", []):
                    source = ROOT / "files" / entry["source"]
                    if not source.exists():
                        raise ValueError(f"Missing overlay source: {source}")

    for path in sorted((ROOT / "recipes").glob("*.yml")):
        visit(path)
        run("bluebuild", "validate", str(path.relative_to(ROOT)))
    print(f"Recipe validation and local inputs: {len(visited)} YAML files passed", flush=True)


if __name__ == "__main__":
    checks = {"bash": bash_check, "shellcheck": shellcheck,
              "just": just_check, "recipes": recipe_check}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=["all", *checks], nargs="?", default="all")
    selected = parser.parse_args().check
    try:
        for name, check in checks.items():
            if selected in ("all", name):
                check()
    except (subprocess.CalledProcessError, OSError, ValueError) as error:
        parser.exit(1, f"Validation failed: {error}\n")
