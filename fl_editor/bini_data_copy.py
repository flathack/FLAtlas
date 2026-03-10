"""Helpers for detecting and copying BINI-backed DATA trees."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable


def find_bini_ini_files_under_data(
    game_root: str,
    *,
    ci_find_func: Callable[[Path, str], Path | None],
    is_bini_file_func: Callable[[Path], bool],
) -> list[Path]:
    out: list[Path] = []
    data_dir = ci_find_func(Path(game_root), "DATA")
    if not data_dir or not data_dir.is_dir():
        return out
    try:
        ini_files = sorted(path for path in data_dir.rglob("*.ini") if path.is_file())
    except Exception:
        ini_files = []
    for path in ini_files:
        if is_bini_file_func(path):
            out.append(path)
    return out


def copy_data_ini_to_mod_with_bini_decode(
    vanilla_path: str,
    mod_path: str,
    *,
    ci_find_func: Callable[[Path, str], Path | None],
    decode_bini_to_ini_text: Callable[[bytes], str],
) -> tuple[bool, int, int, str]:
    data_dir = ci_find_func(Path(vanilla_path), "DATA")
    if not data_dir or not data_dir.is_dir():
        return False, 0, 0, "Vanilla DATA folder not found"
    mod_root = Path(mod_path)
    mod_root.mkdir(parents=True, exist_ok=True)
    written = 0
    converted = 0
    try:
        ini_files = sorted(path for path in data_dir.rglob("*.ini") if path.is_file())
    except Exception as exc:
        return False, 0, 0, str(exc)
    for src in ini_files:
        try:
            try:
                rel = src.relative_to(Path(vanilla_path))
            except Exception:
                rel = src.relative_to(data_dir.parent)
            dst = mod_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            raw = src.read_bytes()
            if raw[:4] == b"BINI":
                text = decode_bini_to_ini_text(raw)
                try:
                    dst.write_text(text, encoding="cp1252")
                except Exception:
                    dst.write_text(text, encoding="utf-8")
                converted += 1
            else:
                shutil.copy2(src, dst)
            written += 1
        except Exception as exc:
            return False, written, converted, f"{src}: {exc}"
    return True, written, converted, ""
