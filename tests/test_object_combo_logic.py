from __future__ import annotations

from types import SimpleNamespace

from fl_editor.object_combo_logic import (
    build_object_combo_rows,
    object_combo_item_at_index,
    object_combo_selected_index,
)


def test_build_object_combo_rows_builds_object_and_zone_entries():
    obj = SimpleNamespace(nickname="obj_a")
    zone = SimpleNamespace(nickname="zone_a")

    rows = build_object_combo_rows(
        [obj],
        [zone],
        object_label=lambda item: f"Label {item.nickname}",
        no_items_label="No items",
    )

    assert rows == [
        ("[OBJ] Label obj_a", obj),
        ("[ZONE] zone_a", zone),
    ]


def test_build_object_combo_rows_returns_fallback_when_empty():
    rows = build_object_combo_rows([], [], object_label=lambda _item: "", no_items_label="No items")

    assert rows == [("No items", None)]


def test_object_combo_selected_index_and_item_lookup():
    first = object()
    second = object()
    items = [first, second]

    assert object_combo_selected_index(items, second) == 1
    assert object_combo_selected_index(items, None) == -1
    assert object_combo_selected_index(items, object()) == -1
    assert object_combo_item_at_index(items, 0) is first
    assert object_combo_item_at_index(items, -1) is None
    assert object_combo_item_at_index(items, 3) is None
