#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Missing virtualenv at .venv/. Create it first."
  exit 1
fi

PY=".venv/bin/python"

"$PY" -m pip install --upgrade pip wheel
"$PY" -m pip install --upgrade pyinstaller

"$PY" -m PyInstaller --noconfirm --clean FLAtlas.spec

echo "Build finished: $ROOT_DIR/dist/FLAtlas"
