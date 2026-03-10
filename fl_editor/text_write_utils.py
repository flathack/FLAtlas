from __future__ import annotations

from pathlib import Path


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
        target.write_text(text, encoding=primary_encoding)
        return primary_encoding
    except UnicodeEncodeError:
        target.write_text(text, encoding=fallback_encoding)
        return fallback_encoding
