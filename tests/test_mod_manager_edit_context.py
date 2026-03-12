from __future__ import annotations

from pathlib import Path

import pytest

from fl_editor import config as config_module
from fl_editor import mod_manager_workflow
from fl_editor.main_window import MainWindow


@pytest.fixture
def main_window(monkeypatch, qapp, tmp_path):
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "config.json")
    window = MainWindow()
    yield window
    window.close()


def test_mod_manager_switch_edit_context_repo_updates_overlay_state(
    main_window: MainWindow,
    monkeypatch,
    tmp_path: Path,
):
    source = tmp_path / "mods" / "mod_a"
    source.mkdir(parents=True)
    clean_root = tmp_path / "clean"
    clean_root.mkdir()
    profile = {"id": "mod-a", "name": "Mod A", "mode": "repo"}

    seen: dict[str, object] = {}

    monkeypatch.setattr(main_window, "_mod_manager_profile_source", lambda _profile: source)
    monkeypatch.setattr(main_window, "_mod_manager_clean_root_path", lambda: clean_root)
    monkeypatch.setattr(mod_manager_workflow, "find_universe_ini", lambda path: clean_root if str(path).strip() else None)
    monkeypatch.setattr(main_window, "_seed_mod_universe_if_missing", lambda: seen.setdefault("seeded", True))
    monkeypatch.setattr(main_window, "_mod_manager_save_state", lambda: seen.setdefault("saved", True))
    monkeypatch.setattr(main_window, "_update_active_mod_indicator", lambda: seen.setdefault("indicator", True))
    monkeypatch.setattr(main_window, "_refresh_ids_toolchain_header_notice", lambda: seen.setdefault("ids_notice", True))
    monkeypatch.setattr(main_window, "_persist_storage", lambda: seen.setdefault("persisted", True))
    monkeypatch.setattr(main_window, "_refresh_game_path_actions", lambda path: seen.setdefault("refresh_path", path))
    monkeypatch.setattr(main_window, "_load_universe", lambda path: seen.setdefault("loaded_path", path))
    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(source))
    monkeypatch.setattr(main_window.browser, "set_game_path", lambda path, scan=True: seen.setdefault("browser_path", (path, scan)))

    ok, msg = main_window._mod_manager_switch_edit_context(profile)

    assert ok is True
    assert msg
    assert main_window._storage_mode == "overlay"
    assert main_window._vanilla_game_path == str(clean_root)
    assert main_window._mod_game_path == str(source)
    assert main_window._mm_editing_mod_id == "mod-a"
    assert seen["browser_path"] == (str(source), True)
    assert seen["refresh_path"] == str(source)
    assert seen["loaded_path"] == str(source)


def test_mod_manager_clear_edit_context_resets_editing_id(main_window: MainWindow, monkeypatch):
    messages: list[str] = []

    main_window._mm_editing_mod_id = "mod-a"
    monkeypatch.setattr(main_window, "_mod_manager_save_state", lambda: None)
    monkeypatch.setattr(main_window, "_update_active_mod_indicator", lambda: None)
    monkeypatch.setattr(main_window, "_refresh_game_path_actions", lambda _path: None)
    monkeypatch.setattr(main_window.statusBar(), "showMessage", lambda text: messages.append(str(text)))

    ok, msg = main_window._mod_manager_clear_edit_context()

    assert ok is True
    assert msg
    assert main_window._mm_editing_mod_id == ""
    assert messages
