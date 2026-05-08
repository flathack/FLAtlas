#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

unset SNAP
unset GTK_PATH
unset LD_LIBRARY_PATH
unset QT_PLUGIN_PATH
unset QML2_IMPORT_PATH

exec .venv/bin/python fl_atlas.py "$@"
