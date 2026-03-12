"""Helpers for building and syncing the object selection combo."""

from __future__ import annotations


def build_object_combo_rows(
    objects,
    zones,
    *,
    object_label,
    no_items_label: str,
) -> list[tuple[str, object | None]]:
    rows: list[tuple[str, object | None]] = []
    for obj in objects:
        rows.append((f"[OBJ] {object_label(obj)}", obj))
    for zone in zones:
        rows.append((f"[ZONE] {getattr(zone, 'nickname', '')}", zone))
    if not rows:
        rows.append((str(no_items_label), None))
    return rows


def object_combo_selected_index(items, selected) -> int:
    if selected is None:
        return -1
    for index, item in enumerate(items):
        if item is selected:
            return index
    return -1


def object_combo_item_at_index(items, index: int):
    if index < 0 or index >= len(items):
        return None
    return items[index]
