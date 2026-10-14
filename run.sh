#!/bin/sh
# Resolve PATH symlinks before finding this project's bundled launcher.
set -eu
exec python3 -c '
import os, shutil, sys
from pathlib import Path
entry = Path(sys.argv[1])
if not entry.exists():
    entry = Path(shutil.which(sys.argv[1]) or sys.argv[1])
root = entry.resolve().parent
os.execv(sys.executable, [sys.executable, "-B", str(root / "tools/project_launcher"), "--project", str(root)] + sys.argv[2:])
' "$0" "$@"
