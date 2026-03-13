#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export CMP orientation diagnostics as JSON.",
    )
    parser.add_argument("model_path", help="Path to .cmp/.3db model")
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from fl_editor.cmp_loader import load_native_freelancer_model
    from fl_editor.cmp_orientation_debug import build_cmp_orientation_debug_snapshot

    mesh_data = load_native_freelancer_model(Path(args.model_path))
    payload = {
        "file": str(Path(args.model_path)),
        "format": mesh_data.format,
        "orientation_debug": build_cmp_orientation_debug_snapshot(mesh_data),
    }
    if args.pretty:
        print(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True))
    else:
        print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
