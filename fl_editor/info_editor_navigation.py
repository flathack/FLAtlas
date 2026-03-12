"""Helpers for navigating to infocard rows in the info editor."""

from __future__ import annotations


def safe_int(raw: str | int | None) -> int:
    try:
        return int(str(raw or "").strip() or "0")
    except Exception:
        return 0


def find_info_editor_row_index(rows: list[object], ids_value: int) -> int | None:
    target = int(ids_value or 0)
    if target <= 0:
        return None
    for index, row in enumerate(rows):
        if isinstance(row, dict) and safe_int(row.get("global_id")) == target:
            return index
    return None
