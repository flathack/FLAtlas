#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d "dist/FLAtlas" ]]; then
  echo "Missing dist/FLAtlas. Run scripts/build_linux.sh first."
  exit 1
fi

VERSION="$(
  python3 - <<'PY'
import re
from pathlib import Path
txt = Path("fl_atlas.py").read_text(encoding="utf-8")
m = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', txt, re.M)
print(m.group(1) if m else "0.0.0")
PY
)"

RELEASE_DIR="release/v${VERSION}"
OUT_BASE="FLAtlas-v${VERSION}-linux-x86_64"
OUT_DIR="${RELEASE_DIR}/${OUT_BASE}"
ARCHIVE="${RELEASE_DIR}/${OUT_BASE}.tar.gz"
CHECKSUM="${ARCHIVE}.sha256"

mkdir -p "$RELEASE_DIR"
rm -rf "$OUT_DIR"
cp -a dist/FLAtlas "$OUT_DIR"

tar -czf "$ARCHIVE" -C "$RELEASE_DIR" "$OUT_BASE"
sha256sum "$ARCHIVE" > "$CHECKSUM"

echo "Release package created:"
echo "  $ARCHIVE"
echo "  $CHECKSUM"
