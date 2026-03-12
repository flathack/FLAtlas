from __future__ import annotations

from pathlib import Path


def persist_zone_link_file(linked_path: str | Path | None, *, visible: bool, text: str) -> bool:
    if not visible or not linked_path:
        return False
    Path(linked_path).write_text(str(text), encoding="utf-8")
    return True
