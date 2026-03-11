from __future__ import annotations

from PySide6.QtWidgets import QWidget

from fl_editor.center_tabs import (
    center_apply_saved_tab_order,
    center_fallback_tab_index_after_close,
    center_move_tab,
    center_register_tab,
    center_set_tab_enabled,
    center_tab_index_for_key,
    center_tab_index_for_widget,
    center_tab_session_payload,
)


def test_center_register_tab_updates_existing_spec(qapp):
    widget_a = QWidget()
    widget_b = QWidget()
    specs: list[dict[str, object]] = []

    index_a = center_register_tab(specs, widget=widget_a, title="Mods", key="mods", closable=False)
    index_b = center_register_tab(specs, widget=widget_b, title="Mods 2", key="mods", closable=True)

    assert index_a == 0
    assert index_b == 0
    assert len(specs) == 1
    assert specs[0]["widget"] is widget_b
    assert specs[0]["title"] == "Mods 2"
    assert specs[0]["closable"] is True


def test_center_tab_index_helpers_find_key_and_widget(qapp):
    widget = QWidget()
    specs = [{"widget": widget, "title": "Universe", "key": "universe", "closable": False}]

    assert center_tab_index_for_key(specs, "universe") == 0
    assert center_tab_index_for_key(specs, "missing") == -1
    assert center_tab_index_for_widget(specs, widget) == 0
    assert center_tab_index_for_widget(specs, QWidget()) == -1


def test_center_set_tab_enabled_and_fallback_index():
    specs = [{"key": "mods", "enabled": True}, {"key": "ini", "enabled": True}]

    assert center_set_tab_enabled(specs, "ini", False) is True
    assert specs[1]["enabled"] is False
    assert center_set_tab_enabled(specs, "ini", False) is False
    assert center_fallback_tab_index_after_close(specs, 1) == 0


def test_center_session_payload_skips_fixed_tabs():
    specs = [
        {"key": "mods", "title": "Mods"},
        {"key": "settings", "title": "Settings"},
        {"key": "system:li01", "title": "LI01", "path": r"C:\LI01\li01.ini"},
    ]

    payload = center_tab_session_payload(specs, "system:li01")

    assert payload == {
        "current": "system:li01",
        "order": ["mods", "settings", "system:li01"],
        "tabs": [
            {"key": "settings"},
            {"key": "system:li01", "path": r"C:\LI01\li01.ini"},
        ],
    }


def test_center_move_and_apply_saved_order():
    specs = [
        {"key": "mods"},
        {"key": "trade"},
        {"key": "ini"},
    ]

    assert center_move_tab(specs, 2, 1) is True
    assert [spec["key"] for spec in specs] == ["mods", "ini", "trade"]

    ordered = center_apply_saved_tab_order(specs, ["trade", "mods"])

    assert [spec["key"] for spec in ordered] == ["trade", "mods", "ini"]
