from __future__ import annotations

from pathlib import Path
import shutil


def _write_text_preserve_newlines(target: Path, text: str, *, encoding: str) -> None:
    with target.open("w", encoding=encoding, newline="") as handle:
        handle.write(text)


def write_text_with_fallback(
    path: str | Path,
    text: str,
    *,
    primary_encoding: str = "cp1252",
    fallback_encoding: str = "utf-8",
    ensure_parent: bool = False,
) -> str:
    target = Path(path)
    if ensure_parent:
        target.parent.mkdir(parents=True, exist_ok=True)
    try:
        _write_text_preserve_newlines(target, text, encoding=primary_encoding)
        return primary_encoding
    except UnicodeEncodeError:
        _write_text_preserve_newlines(target, text, encoding=fallback_encoding)
        return fallback_encoding


def write_text_atomic(path: str | Path, text: str, *, encoding: str = "utf-8") -> Path:
    target = Path(path)
    tmp_path = Path(str(target) + ".tmp")
    _write_text_preserve_newlines(tmp_path, text, encoding=encoding)
    shutil.move(str(tmp_path), str(target))
    return target
