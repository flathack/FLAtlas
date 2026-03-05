#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "Creating virtualenv at .venv ..."
  python3 -m venv .venv
fi

PY=".venv/bin/python"

if [[ ! -x "$PY" ]]; then
  echo "Missing python executable at $PY"
  exit 1
fi

echo "Installing build dependencies ..."
"$PY" -m pip install --upgrade pip wheel
"$PY" -m pip install --upgrade -r requirements-build.txt
if [[ -f "requirements-build-linux.txt" ]]; then
  "$PY" -m pip install --upgrade -r requirements-build-linux.txt
fi

echo "Collecting build environment data ..."
mkdir -p build
"$PY" - <<'PY' > build/linux-build-info.txt
import platform
import sys
from datetime import datetime, timezone

def _safe_ver(mod_name):
    try:
        mod = __import__(mod_name)
        return getattr(mod, "__version__", "unknown")
    except Exception as exc:
        return f"missing ({exc})"

lines = [
    f"timestamp_utc={datetime.now(timezone.utc).isoformat()}",
    f"python={sys.version.split()[0]}",
    f"platform={platform.platform()}",
    f"machine={platform.machine()}",
    f"pyinstaller={_safe_ver('PyInstaller')}",
    f"pyside6={_safe_ver('PySide6')}",
    f"pefile={_safe_ver('pefile')}",
]
print("\n".join(lines))
PY

echo "Linux build preparation finished."
echo "Environment snapshot: $ROOT_DIR/build/linux-build-info.txt"
echo "Next step (when you want to build): scripts/build_linux.sh"
