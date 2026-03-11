from __future__ import annotations
from pathlib import Path

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QDialog

from fl_editor import config as config_module
from fl_editor.i18n import get_language, tr
from fl_editor.dialogs import MeshPreviewDialog
from fl_editor.main_window import MainWindow
from fl_editor.models import SolarObject


@pytest.fixture
def main_window(monkeypatch, qapp, tmp_path):
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "config.json")
    window = MainWindow()
    yield window
    window.close()


def test_main_window_skips_startup_update_timer_in_test_mode(monkeypatch, qapp, tmp_path):
    calls: list[tuple[int, object]] = []

    def _record_single_shot(delay, callback):
        calls.append((delay, callback))

    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setenv("FLATLAS_DISABLE_STARTUP_UPDATE_CHECK", "1")
    monkeypatch.setattr("fl_editor.main_window.QTimer.singleShot", _record_single_shot)

    window = MainWindow()
    try:
        delays = [delay for delay, _callback in calls]
        assert 0 in delays
        assert 900 not in delays
    finally:
        window.close()


def test_main_window_starts_with_core_navigation(main_window):
    assert main_window.center_stack.count() > 0
    assert main_window.nav_settings_btn.text()
    assert main_window.nav_savegame_btn.text()


def test_navigation_views_can_be_opened_without_real_game_data(main_window, monkeypatch, tmp_path: Path):
    monkeypatch.setattr(main_window, "_data_lookup_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_populate_trade_routes_data", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window, "_populate_name_editor_data", lambda *_args, **_kwargs: None)

    main_window._open_mod_manager_view()
    assert main_window.center_stack.currentWidget() is main_window.mod_manager_page

    main_window._open_trade_routes_view()
    assert main_window.center_stack.currentWidget() is main_window.trade_routes_page

    main_window._open_name_editor_view()
    assert main_window.center_stack.currentWidget() is main_window.name_editor_page

    main_window._open_global_settings_view("mod_manager")
    assert main_window.center_stack.currentWidget() is main_window.global_settings_page
    assert main_window.gs_tabs.currentWidget() is main_window.gs_mod_manager_tab


def test_mode_switch_and_language_switch_update_visible_state(main_window):
    main_window._set_name_editor_sub_view("info")
    assert main_window.name_info_stack.currentIndex() == 1

    main_window._set_name_editor_sub_view("name")
    assert main_window.name_info_stack.currentIndex() == 0

    old_lang = get_language()
    new_lang = "de" if old_lang == "en" else "en"
    main_window._set_language(new_lang)

    assert get_language() == new_lang
    assert main_window.nav_settings_btn.text()
    assert main_window.welcome_help_btn.text()
    assert main_window.gs_title_lbl.text()
    assert main_window.mm_title_lbl.text()
    assert main_window.mm_new_repo_btn.text()
    assert main_window.trade_title_lbl.text()
    assert main_window.name_title_lbl.text()
    assert main_window.ini_title_lbl.text()


def test_ini_editor_can_open_context_tree_and_sections(main_window, monkeypatch, tmp_path: Path):
    data_root = tmp_path / "mod"
    data_root.mkdir()
    ini_file = data_root / "test.ini"
    ini_file.write_text("[system]\nnickname = test\n\n[object]\n", encoding="utf-8")
    monkeypatch.setattr(main_window, "_ini_editor_context_root", lambda: data_root)

    main_window._open_ini_editor_view()

    assert main_window.center_stack.currentWidget() is main_window.ini_editor_page
    assert main_window.ini_tree.topLevelItemCount() == 1

    top = main_window.ini_tree.topLevelItem(0)
    child = top.child(0)
    main_window._ini_editor_open_tree_item(child)

    assert main_window._ini_editor_current_file.endswith("test.ini")
    assert main_window.ini_sections_list.count() == 2


def test_dev_status_page_refresh_populates_rows(main_window):
    main_window._refresh_dev_status_page()

    assert main_window.gs_dev_table.rowCount() >= 1
    assert main_window.gs_dev_table.item(0, 0) is not None


def test_help_dialog_opens_without_blocking(main_window, monkeypatch):
    calls: list[str] = []

    def _fake_exec(dialog: QDialog):
        calls.append(dialog.windowTitle())
        return 0

    monkeypatch.setattr(QDialog, "exec", _fake_exec)

    main_window._show_help()

    assert calls


def test_external_savegame_editor_button_tracks_configured_launcher(main_window, monkeypatch):
    monkeypatch.setattr(main_window, "_savegame_editor_launch_path", lambda: None)
    main_window._refresh_game_path_actions()
    assert main_window.nav_savegame_btn.isHidden()

    monkeypatch.setattr(main_window, "_savegame_editor_launch_path", lambda: Path("/tmp/external-savegame-editor.exe"))
    main_window._refresh_game_path_actions()
    assert not main_window.nav_savegame_btn.isHidden()
    assert main_window.nav_savegame_btn.isEnabled()


def test_simple_zone_creation_defers_ui_follow_up_safely(main_window, monkeypatch):
    main_window._filepath = "/tmp/test_system.ini"
    main_window._scale = 1.0
    main_window.zone_cb.setChecked(True)
    main_window._pending_simple_zone = {
        "mode": "simple",
        "name": "test_zone",
        "comment": "",
        "shape": "SPHERE",
        "sort": 76,
        "damage": 0,
    }

    monkeypatch.setattr(main_window, "_write_to_file", lambda reload=False: None)
    monkeypatch.setattr(main_window, "_push_undo_action", lambda *_a, **_k: None)
    monkeypatch.setattr(main_window, "_append_change_log", lambda *_a, **_k: None)
    monkeypatch.setattr(main_window, "_refresh_3d_scene", lambda *args, **kwargs: None)

    main_window._create_simple_zone(QPointF(150.0, 220.0), 600.0, 900.0)
    QApplication.processEvents()

    assert len(main_window._zones) == 1
    zone = main_window._zones[0]
    assert main_window._selected is zone
    assert main_window.obj_combo.count() >= 1
    assert "nickname = " in main_window.editor.toPlainText().lower()


def test_close_event_uses_current_mode_for_unsaved_prompt(main_window, monkeypatch):
    calls: list[str] = []

    def _record_confirm(action_desc: str) -> bool:
        calls.append(action_desc)
        return True

    monkeypatch.setattr(main_window, "_confirm_save_if_dirty", _record_confirm)

    main_window._filepath = "/tmp/test_system.ini"
    main_window.closeEvent(QCloseEvent())
    assert calls[-1] == tr("action.close_app")

    main_window._filepath = None
    main_window.closeEvent(QCloseEvent())
    assert calls[-1] == tr("action.close_app")


def test_open_model_file_does_not_trigger_unsaved_prompt(main_window, monkeypatch, tmp_path: Path):
    model_path = tmp_path / "sample.obj"
    model_path.write_text("o mesh\n", encoding="utf-8")

    calls: list[str] = []
    dialog_titles: list[str] = []

    monkeypatch.setattr(
        "fl_editor.main_window.QFileDialog.getOpenFileName",
        lambda *_args, **_kwargs: (str(model_path), ""),
    )
    monkeypatch.setattr("fl_editor.main_window.QT3D_AVAILABLE", True)
    monkeypatch.setattr(main_window, "_confirm_save_if_dirty", lambda action_desc: calls.append(action_desc) or True)
    monkeypatch.setattr(MeshPreviewDialog, "exec", lambda dialog: dialog_titles.append(dialog.windowTitle()) or 0)

    main_window._filepath = "/tmp/test_system.ini"
    main_window._dirty = True

    main_window._open_model_file()

    assert calls == []
    assert dialog_titles == [f"3D Preview — {model_path.name}"]


def test_load_universe_resets_dirty_state(main_window, monkeypatch, tmp_path: Path):
    universe_ini = tmp_path / "universe.ini"
    universe_ini.write_text(
        "[System]\n"
        "nickname = li01\n"
        "file = DATA\\UNIVERSE\\LI01\\li01.ini\n"
        "pos = 0, 0\n",
        encoding="utf-8",
    )
    system_ini = tmp_path / "li01.ini"
    system_ini.write_text("[SystemInfo]\nspace_color = 0, 0, 0\n", encoding="utf-8")

    main_window._dirty = True
    main_window._filepath = "/tmp/previous_system.ini"

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_find_universe_ini_read", lambda _game_path: universe_ini)
    monkeypatch.setattr(
        main_window,
        "_find_all_systems",
        lambda _game_path: [{"nickname": "li01", "path": str(system_ini), "pos": (0.0, 0.0), "ids_name": ""}],
    )
    monkeypatch.setattr(main_window, "_refresh_3d_scene", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_build_standard_menu_bar", lambda *args, **kwargs: None)

    main_window._load_universe(str(tmp_path))

    assert main_window._filepath is None
    assert main_window._dirty is False


def test_select_object_does_not_dirty_via_quick_editor_fill(main_window):
    main_window._filepath = "/tmp/test_system.ini"
    main_window._dirty = False
    obj = SolarObject(
        {
            "nickname": "test_object",
            "archetype": "planet_earth",
            "loadout": "planet_loadout",
            "reputation": "li_n_grp, 0.9",
            "_entries": [
                ("nickname", "test_object"),
                ("archetype", "planet_earth"),
                ("loadout", "planet_loadout"),
                ("reputation", "li_n_grp, 0.9"),
                ("pos", "0, 0, 0"),
            ],
        },
        1.0,
    )
    main_window._objects.append(obj)

    main_window._select(obj)

    assert main_window._dirty is False
    assert main_window.arch_cb.currentText() == "planet_earth"
    assert main_window.loadout_cb.currentText() == "planet_loadout"
