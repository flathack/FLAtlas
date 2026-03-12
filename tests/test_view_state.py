from __future__ import annotations

from fl_editor.view_state import global_settings_tab_index, name_editor_sub_view_state


def test_global_settings_tab_index_normalizes_and_clamps():
    tab_order = {
        "general": 0,
        "system_editor": 1,
        "mod_manager": 2,
        "editors": 3,
        "dev_status": 4,
    }

    assert global_settings_tab_index("mod_manager", tab_order, 5) == 2
    assert global_settings_tab_index("allgemein", tab_order, 5) == 0
    assert global_settings_tab_index("missing", {"general": -1}, 2) == 0


def test_name_editor_sub_view_state_switches_name_and_info_modes():
    name_state = name_editor_sub_view_state("name")
    info_state = name_editor_sub_view_state("info")

    assert name_state == {
        "show_info": False,
        "stack_index": 0,
        "show_name_actions": True,
        "show_info_actions": False,
    }
    assert info_state == {
        "show_info": True,
        "stack_index": 1,
        "show_name_actions": False,
        "show_info_actions": True,
    }
