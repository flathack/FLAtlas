from __future__ import annotations

from pathlib import Path

import pytest

from fl_editor import config as config_module
from fl_editor.main_window import MainWindow


@pytest.fixture
def main_window(monkeypatch, qapp, tmp_path):
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "config.json")
    window = MainWindow()
    yield window
    window.close()


def test_mod_settings_tab_tracks_edit_context(main_window: MainWindow, monkeypatch, tmp_path: Path):
    mod_root = tmp_path / "mods" / "mod_a"
    mod_root.mkdir(parents=True)
    clean_root = tmp_path / "clean"
    clean_root.mkdir()

    main_window._mm_profiles = [{"id": "mod-a", "name": "Mod A", "mode": "repo"}]

    monkeypatch.setattr(main_window, "_mod_manager_profile_source", lambda _profile: mod_root)
    monkeypatch.setattr(main_window, "_mod_manager_clean_root_path", lambda: clean_root)
    monkeypatch.setattr(main_window, "_has_valid_storage_setup", lambda: True)
    monkeypatch.setattr(main_window, "_savegame_editor_launch_path", lambda: None)
    monkeypatch.setattr(main_window, "_mod_settings_refresh", lambda: None)

    main_window._mm_editing_mod_id = "mod-a"
    main_window._refresh_game_path_actions(str(mod_root))

    assert main_window._center_tab_index_for_key("mod_settings") >= 0

    main_window._mm_editing_mod_id = ""
    main_window._refresh_game_path_actions("")

    assert main_window._center_tab_index_for_key("mod_settings") < 0
