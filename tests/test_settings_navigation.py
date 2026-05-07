from __future__ import annotations

from fl_editor.settings_navigation import canonical_global_settings_tab_key


def test_canonical_global_settings_tab_key_maps_aliases():
    assert canonical_global_settings_tab_key("allgemein") == "general"
    assert canonical_global_settings_tab_key("savegame_editor") == "suite_apps"
    assert canonical_global_settings_tab_key("konfiguration") == "config"
    assert canonical_global_settings_tab_key("dev") == "dev_status"


def test_canonical_global_settings_tab_key_falls_back_to_general():
    assert canonical_global_settings_tab_key("unknown") == "general"
