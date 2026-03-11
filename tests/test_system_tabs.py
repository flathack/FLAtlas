from __future__ import annotations

from fl_editor.system_tabs import (
    apply_dirty_system_tab_title,
    center_system_tab_spec,
    system_tab_key,
    system_tab_title,
)


def test_center_system_tab_spec_uses_explicit_or_current_key():
    specs = [
        {"key": "mods"},
        {"key": "system:abc", "path": r"C:\LI01\li01.ini"},
    ]

    assert center_system_tab_spec(specs, key="system:abc") == specs[1]
    assert center_system_tab_spec(specs, current_key="system:abc") == specs[1]
    assert center_system_tab_spec(specs, key="mods") is None


def test_system_tab_key_wraps_normalized_key():
    assert system_tab_key(r"C:\LI01\li01.ini", r"c:\li01\li01.ini") == r"system:c:\li01\li01.ini"


def test_system_tab_title_prefers_nick_and_display_name():
    result = system_tab_title(
        r"C:\tmp\li01.ini",
        system_display_name_func=lambda nick: "New York" if nick == "LI01" else "",
        unknown_title="?",
    )
    assert result == "LI01 - New York"

    fallback = system_tab_title(
        r"C:\tmp\custom.ini",
        system_display_name_func=lambda _nick: "",
        unknown_title="?",
    )
    assert fallback == "CUSTOM"


def test_apply_dirty_system_tab_title_adds_single_prefix():
    assert apply_dirty_system_tab_title("LI01", True) == "* LI01"
    assert apply_dirty_system_tab_title("* LI01", True) == "* LI01"
    assert apply_dirty_system_tab_title("LI01", False) == "LI01"
