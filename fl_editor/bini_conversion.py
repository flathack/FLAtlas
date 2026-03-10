"""Helpers for converting BINI-backed INI files in folders."""

from __future__ import annotations

from pathlib import Path
from typing import Callable


def convert_bini_in_folder_in_place(
    folder: str,
    *,
    decode_bini_to_ini_text: Callable[[bytes], str],
    pump_ui: Callable[[str], None] | None = None,
    loading_message: str = "",
    skip_rel_paths: set[str] | None = None,
) -> tuple[bool, int, int, str]:
    root = Path(str(folder or "").strip())
    if not root.exists() or not root.is_dir():
        return False, 0, 0, "Folder not found"
    scanned = 0
    converted = 0
    warnings: list[str] = []
    try:
        ini_files = sorted(path for path in root.rglob("*.ini") if path.is_file())
    except Exception as exc:
        return False, 0, 0, str(exc)
    skip_set = {str(item).replace("\\", "/").lower() for item in (skip_rel_paths or set())}
    for ini_path in ini_files:
        scanned += 1
        if pump_ui is not None and (scanned % 40) == 0:
            pump_ui(str(loading_message or ""))
        try:
            try:
                rel = ini_path.relative_to(root).as_posix().lower()
            except Exception:
                rel = str(ini_path).replace("\\", "/").lower()
            if rel in skip_set:
                continue
            raw = ini_path.read_bytes()
            if raw[:4] != b"BINI":
                continue
            text = decode_bini_to_ini_text(raw)
            try:
                ini_path.write_text(text, encoding="cp1252")
            except Exception:
                ini_path.write_text(text, encoding="utf-8")
            converted += 1
        except Exception as exc:
            warnings.append(f"{ini_path}: {exc}")
            continue
    warning_message = ""
    if warnings:
        head = warnings[:10]
        warning_message = " | ".join(head)
        if len(warnings) > len(head):
            warning_message += f" | +{len(warnings) - len(head)} more"
    return True, scanned, converted, warning_message
