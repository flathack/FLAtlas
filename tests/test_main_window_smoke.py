from __future__ import annotations
from pathlib import Path

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QTreeWidgetItem

from fl_editor import config as config_module
from fl_editor.i18n import get_language, tr
from fl_editor.dialogs import MeshPreviewDialog
from fl_editor.main_window import MainWindow
from fl_editor.models import SolarObject
from fl_editor.native_scene_runtime import NativeSceneRuntimeEvent


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


def test_ids_toolchain_header_notice_visibility(main_window, monkeypatch):
    monkeypatch.setattr(main_window, "_has_ids_resource_toolchain", lambda: False)
    monkeypatch.setattr(main_window, "_ids_toolchain_install_supported_platform", lambda: True)

    main_window._refresh_ids_toolchain_header_notice()

    assert not main_window._ids_toolchain_notice_lbl.isHidden()
    assert not main_window._ids_toolchain_install_btn.isHidden()


def test_qt3d_header_notice_visibility(main_window, monkeypatch):
    monkeypatch.setattr("fl_editor.main_window.QT3D_AVAILABLE", False)
    monkeypatch.setattr(main_window, "_has_ids_resource_toolchain", lambda: True)
    monkeypatch.setattr(main_window, "_ids_toolchain_install_supported_platform", lambda: True)

    main_window._refresh_ids_toolchain_header_notice()

    assert not main_window._qt3d_notice_lbl.isHidden()


def test_linux_ids_toolchain_manual_text_for_unsupported_distribution(main_window, monkeypatch):
    monkeypatch.setattr("fl_editor.main_window.shutil.which", lambda _name: None)

    text = main_window._linux_ids_toolchain_manual_text()

    assert "FLAtlas IDS Toolchain Installer (Linux)" in text
    assert "ERROR: Unsupported distribution. Install required tools manually:" in text
    assert "lld-link (or ld.lld)" in text
    assert "llvm-windres (or x86_64-w64-mingw32-windres / i686-w64-mingw32-windres / windres / llvm-rc)" in text


def test_resource_toolchain_accepts_generic_windres(monkeypatch):
    def _fake_resolve(exe_name: str):
        mapping = {
            "windres": "/usr/bin/windres",
            "ld.lld": "/usr/bin/ld.lld",
        }
        return mapping.get(exe_name)

    monkeypatch.setattr("fl_editor.main_window.sys.platform", "linux")
    monkeypatch.setattr(MainWindow, "_resolve_tool_exe", staticmethod(_fake_resolve))

    toolchain = MainWindow._resource_toolchain_commands()

    assert callable(toolchain)
    compile_cmd, link_cmd = toolchain("input.rc", "out.res", "out.dll")
    assert compile_cmd == ["/usr/bin/windres", "--target=pe-i386", "input.rc", "out.res"]
    assert link_cmd == ["/usr/bin/ld.lld", "-flavor", "link", "/NOENTRY", "/DLL", "/MACHINE:X86", "/OUT:out.dll", "out.res"]


def test_candidate_tool_dirs_splits_flatlas_toolchain_dir(monkeypatch):
    monkeypatch.setenv("FLATLAS_TOOLCHAIN_DIR", "/opt/one:/opt/two")
    dirs = MainWindow._candidate_tool_dirs()
    as_text = {str(p).replace("\\", "/") for p in dirs}
    assert "/opt/one" in as_text
    assert "/opt/two" in as_text


def test_auto_detect_ids_toolchain_dir_collects_common_linux_paths(monkeypatch):
    def _fake_resolve(exe_name: str):
        mapping = {
            "ld.lld": "/usr/bin/ld.lld",
            "llvm-windres": "/var/run/host/usr/bin/llvm-windres",
        }
        return mapping.get(exe_name)

    monkeypatch.setattr("fl_editor.main_window.sys.platform", "linux")
    monkeypatch.setattr(
        "fl_editor.main_window.Path.is_dir",
        lambda path_obj: str(path_obj) in {"/usr/bin", "/var/run/host/usr/bin"},
    )
    monkeypatch.setattr(MainWindow, "_resolve_tool_exe", staticmethod(_fake_resolve))

    detected = MainWindow._auto_detect_ids_toolchain_dir()

    parts = set(detected.split(":"))
    assert "/usr/bin" in parts
    assert "/var/run/host/usr/bin" in parts


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


def test_mod_manager_shows_setup_notice_and_has_no_sidebar_settings_button(main_window):
    main_window._open_mod_manager_view()

    assert not hasattr(main_window, "mm_open_settings_btn")
    assert main_window.mm_setup_notice_lbl.text()
    assert "href=\"settings\"" in main_window.mm_setup_notice_lbl.text()


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


def test_ini_editor_unsupported_model_file_shows_placeholder(main_window, tmp_path: Path):
    model_path = tmp_path / "ship.cmp"
    model_path.write_bytes(b"CMP")
    item = QTreeWidgetItem(["ship.cmp"])
    item.setData(0, Qt.UserRole, str(model_path))
    item.setData(0, Qt.UserRole + 1, "file")

    main_window._ini_editor_open_tree_item(item)

    text = main_window.ini_code_edit.toPlainText()
    assert "3D" in text
    assert "ship.cmp" in text
    assert main_window._ini_editor_current_file == ""
    assert not main_window.ini_save_btn.isEnabled()


def test_ini_editor_unsupported_file_shows_placeholder(main_window, tmp_path: Path):
    bin_path = tmp_path / "random.dll"
    bin_path.write_bytes(b"MZ")
    item = QTreeWidgetItem(["random.dll"])
    item.setData(0, Qt.UserRole, str(bin_path))
    item.setData(0, Qt.UserRole + 1, "file")

    main_window._ini_editor_open_tree_item(item)

    text = main_window.ini_code_edit.toPlainText()
    assert "not" in text.lower() or "nicht" in text.lower()
    assert "random.dll" in text
    assert main_window._ini_editor_current_file == ""
    assert not main_window.ini_save_btn.isEnabled()


def test_open_current_system_ini_uses_integrated_ini_editor(main_window, monkeypatch, tmp_path: Path):
    ini_path = tmp_path / "DATA" / "UNIVERSE" / "LI01" / "li01.ini"
    ini_path.parent.mkdir(parents=True)
    ini_path.write_text("[SystemInfo]\n", encoding="utf-8")
    main_window._filepath = str(ini_path)

    calls: list[str] = []
    item = QTreeWidgetItem(["li01.ini"])
    item.setData(0, Qt.UserRole, str(ini_path))
    item.setData(0, Qt.UserRole + 1, "file")

    monkeypatch.setattr(main_window, "_open_ini_editor_view", lambda: calls.append("open_ini_editor"))
    monkeypatch.setattr(main_window, "_ini_editor_find_tree_item_by_path", lambda _path: item)
    monkeypatch.setattr(main_window, "_ini_editor_open_tree_item", lambda i, _c=0: calls.append(f"open_item:{i.text(0)}"))

    main_window._open_current_system_ini()

    assert calls == ["open_ini_editor", "open_item:li01.ini"]


def test_ini_editor_can_open_multiple_files_as_tabs_with_state(main_window, monkeypatch, tmp_path: Path):
    root = tmp_path / "mod"
    f1 = root / "DATA" / "a.ini"
    f2 = root / "DATA" / "b.ini"
    f1.parent.mkdir(parents=True)
    f1.write_text("[a]\nvalue = 1\n", encoding="utf-8")
    f2.write_text("[b]\nvalue = 2\n", encoding="utf-8")

    monkeypatch.setattr(main_window, "_ini_editor_context_root", lambda: root)
    main_window._open_ini_editor_view()

    i1 = QTreeWidgetItem(["a.ini"])
    i1.setData(0, Qt.UserRole, str(f1))
    i1.setData(0, Qt.UserRole + 1, "file")
    i1.setData(0, Qt.UserRole + 2, "primary")
    i2 = QTreeWidgetItem(["b.ini"])
    i2.setData(0, Qt.UserRole, str(f2))
    i2.setData(0, Qt.UserRole + 1, "file")
    i2.setData(0, Qt.UserRole + 2, "primary")

    main_window._ini_editor_open_tree_item(i1)
    key1 = main_window._ini_editor_tab_key(str(f1))
    assert main_window._center_tab_index_for_key(key1) >= 0
    main_window.ini_code_edit.setPlainText("[a]\nvalue = 111\n")

    main_window._ini_editor_open_tree_item(i2)
    key2 = main_window._ini_editor_tab_key(str(f2))
    idx2 = main_window._center_tab_index_for_key(key2)
    assert idx2 >= 0
    assert main_window.ini_code_edit.toPlainText().startswith("[b]")

    idx1 = main_window._center_tab_index_for_key(key1)
    main_window._on_center_tab_changed(idx1)
    assert "111" in main_window.ini_code_edit.toPlainText()


def test_ini_editor_dirty_tab_can_be_closed_via_discard(main_window, monkeypatch, tmp_path: Path):
    root = tmp_path / "mod"
    f1 = root / "DATA" / "close.ini"
    f1.parent.mkdir(parents=True)
    f1.write_text("[x]\n", encoding="utf-8")

    monkeypatch.setattr(main_window, "_ini_editor_context_root", lambda: root)
    main_window._open_ini_editor_view()

    item = QTreeWidgetItem(["close.ini"])
    item.setData(0, Qt.UserRole, str(f1))
    item.setData(0, Qt.UserRole + 1, "file")
    item.setData(0, Qt.UserRole + 2, "primary")
    main_window._ini_editor_open_tree_item(item)
    main_window.ini_code_edit.setPlainText("[x]\nchanged = 1\n")

    tab_key = main_window._ini_editor_tab_key(str(f1))
    idx = main_window._center_tab_index_for_key(tab_key)
    assert idx >= 0
    monkeypatch.setattr(
        "fl_editor.main_window.QMessageBox.question",
        lambda *_args, **_kwargs: QMessageBox.Discard,
    )

    before = len(main_window._center_tab_specs)
    main_window._on_center_tab_close_requested(idx)
    after = len(main_window._center_tab_specs)

    assert after == before - 1
    assert main_window._center_tab_index_for_key(tab_key) < 0


def test_ini_editor_opening_new_file_closes_unedited_ini_tabs(main_window, monkeypatch, tmp_path: Path):
    root = tmp_path / "mod"
    f1 = root / "DATA" / "a.ini"
    f2 = root / "DATA" / "b.ini"
    f1.parent.mkdir(parents=True)
    f1.write_text("[a]\n", encoding="utf-8")
    f2.write_text("[b]\n", encoding="utf-8")

    monkeypatch.setattr(main_window, "_ini_editor_context_root", lambda: root)
    main_window._open_ini_editor_view()

    i1 = QTreeWidgetItem(["a.ini"])
    i1.setData(0, Qt.UserRole, str(f1))
    i1.setData(0, Qt.UserRole + 1, "file")
    i1.setData(0, Qt.UserRole + 2, "primary")
    i2 = QTreeWidgetItem(["b.ini"])
    i2.setData(0, Qt.UserRole, str(f2))
    i2.setData(0, Qt.UserRole + 1, "file")
    i2.setData(0, Qt.UserRole + 2, "primary")

    main_window._ini_editor_open_tree_item(i1)
    key1 = main_window._ini_editor_tab_key(str(f1))
    assert main_window._center_tab_index_for_key(key1) >= 0

    main_window._ini_editor_open_tree_item(i2)
    key2 = main_window._ini_editor_tab_key(str(f2))
    assert main_window._center_tab_index_for_key(key2) >= 0
    assert main_window._center_tab_index_for_key(key1) < 0


def test_ini_editor_opening_new_file_keeps_edited_ini_tabs(main_window, monkeypatch, tmp_path: Path):
    root = tmp_path / "mod"
    f1 = root / "DATA" / "a.ini"
    f2 = root / "DATA" / "b.ini"
    f1.parent.mkdir(parents=True)
    f1.write_text("[a]\n", encoding="utf-8")
    f2.write_text("[b]\n", encoding="utf-8")

    monkeypatch.setattr(main_window, "_ini_editor_context_root", lambda: root)
    main_window._open_ini_editor_view()

    i1 = QTreeWidgetItem(["a.ini"])
    i1.setData(0, Qt.UserRole, str(f1))
    i1.setData(0, Qt.UserRole + 1, "file")
    i1.setData(0, Qt.UserRole + 2, "primary")
    i2 = QTreeWidgetItem(["b.ini"])
    i2.setData(0, Qt.UserRole, str(f2))
    i2.setData(0, Qt.UserRole + 1, "file")
    i2.setData(0, Qt.UserRole + 2, "primary")

    main_window._ini_editor_open_tree_item(i1)
    key1 = main_window._ini_editor_tab_key(str(f1))
    assert main_window._center_tab_index_for_key(key1) >= 0
    main_window.ini_code_edit.setPlainText("[a]\nchanged = 1\n")

    main_window._ini_editor_open_tree_item(i2)
    key2 = main_window._ini_editor_tab_key(str(f2))
    assert main_window._center_tab_index_for_key(key2) >= 0
    assert main_window._center_tab_index_for_key(key1) >= 0


def test_ini_editor_save_uses_writable_overlay_path(main_window, monkeypatch, tmp_path: Path):
    fallback_file = tmp_path / "fallback" / "DATA" / "test.ini"
    writable_file = tmp_path / "mod" / "DATA" / "test.ini"
    fallback_file.parent.mkdir(parents=True)
    writable_file.parent.mkdir(parents=True)

    main_window._ini_editor_current_file = str(fallback_file)
    main_window.ini_code_edit.setPlainText("[system]\n")

    monkeypatch.setattr(main_window, "_ensure_writable_path", lambda _p: writable_file)
    captured: dict[str, str] = {}

    def _fake_save(path: str, text: str):
        captured["path"] = path
        captured["text"] = text
        return True, path

    monkeypatch.setattr("fl_editor.main_window.ini_editor_save_file", _fake_save)

    main_window._ini_editor_save_current()

    assert captured["path"] == str(writable_file)
    assert main_window._ini_editor_current_file == str(writable_file)


def test_ini_editor_copy_tree_item_to_mod_updates_item(main_window, monkeypatch, tmp_path: Path):
    src_file = tmp_path / "fallback" / "DATA" / "copy.ini"
    dst_file = tmp_path / "mod" / "DATA" / "copy.ini"
    src_file.parent.mkdir(parents=True)
    src_file.write_text("[test]\n", encoding="utf-8")
    dst_file.parent.mkdir(parents=True)
    dst_file.write_text("[test]\n", encoding="utf-8")

    item = QTreeWidgetItem(["copy.ini [fallback]"])
    item.setData(0, Qt.UserRole, str(src_file))
    item.setData(0, Qt.UserRole + 1, "file")
    item.setData(0, Qt.UserRole + 2, "fallback")
    main_window._ini_editor_current_file = str(src_file)

    monkeypatch.setattr(main_window, "_ensure_writable_path", lambda _p: dst_file)

    main_window._ini_editor_copy_tree_item_to_mod(item)

    assert item.data(0, Qt.UserRole) == str(dst_file)
    assert item.data(0, Qt.UserRole + 2) == "primary"
    assert item.text(0) == "copy.ini"
    assert main_window._ini_editor_current_file == str(dst_file)


def test_ini_editor_can_delete_only_primary_mod_files(main_window, monkeypatch, tmp_path: Path):
    mod_file = tmp_path / "mod" / "DATA" / "file.ini"
    mod_file.parent.mkdir(parents=True)
    mod_file.write_text("[x]\n", encoding="utf-8")

    fallback_file = tmp_path / "fallback" / "DATA" / "file.ini"
    fallback_file.parent.mkdir(parents=True)
    fallback_file.write_text("[x]\n", encoding="utf-8")

    monkeypatch.setattr(main_window, "_is_overlay_mode", lambda: True)
    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path / "mod"))

    primary_item = QTreeWidgetItem(["file.ini"])
    primary_item.setData(0, Qt.UserRole, str(mod_file))
    primary_item.setData(0, Qt.UserRole + 1, "file")
    primary_item.setData(0, Qt.UserRole + 2, "primary")
    assert main_window._ini_editor_can_delete_tree_item(primary_item) is True

    fallback_item = QTreeWidgetItem(["file.ini [fallback]"])
    fallback_item.setData(0, Qt.UserRole, str(fallback_file))
    fallback_item.setData(0, Qt.UserRole + 1, "file")
    fallback_item.setData(0, Qt.UserRole + 2, "fallback")
    assert main_window._ini_editor_can_delete_tree_item(fallback_item) is False

    monkeypatch.setattr(main_window, "_is_overlay_mode", lambda: False)
    assert main_window._ini_editor_can_delete_tree_item(primary_item) is False


def test_ini_editor_delete_tree_item_removes_mod_file(main_window, monkeypatch, tmp_path: Path):
    mod_file = tmp_path / "mod" / "DATA" / "delete.ini"
    mod_file.parent.mkdir(parents=True)
    mod_file.write_text("[x]\n", encoding="utf-8")

    item = QTreeWidgetItem(["delete.ini"])
    item.setData(0, Qt.UserRole, str(mod_file))
    item.setData(0, Qt.UserRole + 1, "file")
    item.setData(0, Qt.UserRole + 2, "primary")

    monkeypatch.setattr(main_window, "_is_overlay_mode", lambda: True)
    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path / "mod"))
    monkeypatch.setattr(
        "fl_editor.main_window.QMessageBox.question",
        lambda *_args, **_kwargs: QMessageBox.Yes,
    )
    monkeypatch.setattr(main_window, "_ini_editor_reload_tree", lambda: None)

    main_window._ini_editor_current_file = str(mod_file)
    main_window._ini_editor_delete_tree_item(item)

    assert not mod_file.exists()
    assert main_window._ini_editor_current_file == ""


def test_dev_status_page_refresh_populates_rows(main_window):
    main_window._refresh_dev_status_page()

    assert main_window.gs_dev_table.rowCount() >= 1
    assert main_window.gs_dev_table.item(0, 0) is not None


def test_dev_status_row_activation_opens_details(main_window, monkeypatch):
    captured: dict[str, str] = {}

    def _capture(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(main_window, "_dev_status_open_details", _capture)
    main_window._refresh_dev_status_page()
    item = main_window.gs_dev_table.item(0, 0)

    main_window._on_dev_status_item_activated(item)

    assert captured.get("nav_key")
    assert captured.get("nav_label")


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


def test_unsaved_prompts_can_be_disabled_via_env(main_window, monkeypatch):
    asked: list[str] = []

    monkeypatch.setenv("FLATLAS_DISABLE_UNSAVED_PROMPTS", "1")
    monkeypatch.setattr(
        "fl_editor.main_window.QMessageBox.question",
        lambda *_args, **_kwargs: asked.append("asked") or 0,
    )

    main_window._filepath = "/tmp/test_system.ini"
    main_window._dirty = True

    assert main_window._confirm_save_if_dirty(tr("action.close_app")) is True
    assert asked == []


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


def test_native_scene_debug_snapshot_without_runtime(main_window):
    obj = SolarObject(
        {
            "nickname": "test_native_debug",
            "archetype": "planet_earth",
            "_entries": [("nickname", "test_native_debug"), ("archetype", "planet_earth")],
        },
        1.0,
    )
    main_window._selected = obj

    monkeypatch_path = Path("/tmp/test_native_model.cmp")
    main_window._on_native_scene_runtime_event(
        NativeSceneRuntimeEvent(kind="cache_miss", model_path=monkeypatch_path, detail="")
    )
    main_window._native_model_path_for_object = lambda _obj: monkeypatch_path

    snapshot = main_window._native_scene_debug_state_snapshot()

    assert snapshot["runtime_initialized"] is False
    assert snapshot["selected_object_nickname"] == "test_native_debug"
    assert snapshot["selected_model_path"] == monkeypatch_path
    assert len(snapshot["events"]) == 1
    assert snapshot["events"][0].kind == "cache_miss"


def test_native_scene_debug_snapshot_includes_runtime_state(main_window, monkeypatch):
    model_path = Path("/tmp/native_detail.cmp")
    obj = SolarObject(
        {
            "nickname": "li01_station",
            "archetype": "space_police01",
            "_entries": [("nickname", "li01_station"), ("archetype", "space_police01")],
        },
        1.0,
    )
    main_window._selected = obj
    monkeypatch.setattr(main_window, "_native_model_path_for_object", lambda _obj: model_path)

    runtime = main_window._native_scene_runtime()
    main_window._on_native_scene_runtime_event(
        NativeSceneRuntimeEvent(kind="load_queued", model_path=model_path, detail="")
    )

    snapshot = main_window._native_scene_debug_state_snapshot()

    assert snapshot["runtime_initialized"] is True
    assert snapshot["selected_object_nickname"] == "li01_station"
    assert snapshot["selected_model_path"] == model_path
    assert snapshot["stats"] == runtime.get_debug_state()["stats"]
    assert any(event.kind == "load_queued" for event in snapshot["events"])


def test_sync_view3d_selected_native_scene_data_aborts_stale_selection(main_window, monkeypatch):
    first = SolarObject(
        {
            "nickname": "first_obj",
            "archetype": "space_police01",
            "_entries": [("nickname", "first_obj"), ("archetype", "space_police01")],
        },
        1.0,
    )
    second = SolarObject(
        {
            "nickname": "second_obj",
            "archetype": "space_police02",
            "_entries": [("nickname", "second_obj"), ("archetype", "space_police02")],
        },
        1.0,
    )
    main_window._selected = first

    calls: list[tuple[object, object]] = []

    class _FakeView3D:
        def set_selected_native_scene_data(self, obj, scene_data):
            calls.append((obj, scene_data))

    class _FakeSwitch:
        def isChecked(self):
            return True

    main_window.view3d = _FakeView3D()
    main_window.view3d_switch = _FakeSwitch()
    monkeypatch.setattr(main_window, "_native_model_path_for_object", lambda obj: Path(f"/tmp/{getattr(obj, 'nickname', 'none')}.cmp") if obj is not None else None)

    def _resolve(obj):
        assert obj is first
        main_window._selected = second
        return object()

    monkeypatch.setattr(main_window, "_resolve_native_scene_data_for_object", _resolve)

    main_window._sync_view3d_selected_native_scene_data()

    assert all(obj is not first for obj, _scene_data in calls)
    snapshot = main_window._native_scene_debug_state_snapshot()
    assert snapshot["selected_object_nickname"] == "second_obj"
    assert any(event.kind == "sync_aborted_selection_changed" for event in snapshot["events"])


def test_sync_view3d_selected_native_scene_data_clears_when_selection_is_none(main_window):
    calls: list[tuple[object, object]] = []

    class _FakeView3D:
        def set_selected_native_scene_data(self, obj, scene_data):
            calls.append((obj, scene_data))

    main_window.view3d = _FakeView3D()
    main_window._selected = None

    main_window._sync_view3d_selected_native_scene_data()

    assert calls == [(None, None)]
    snapshot = main_window._native_scene_debug_state_snapshot()
    assert any(event.kind == "sync_cleared_no_selection" for event in snapshot["events"])


def test_sync_view3d_selected_native_scene_data_skips_when_3d_is_disabled(main_window, monkeypatch):
    obj = SolarObject(
        {
            "nickname": "disabled_obj",
            "archetype": "space_police01",
            "_entries": [("nickname", "disabled_obj"), ("archetype", "space_police01")],
        },
        1.0,
    )
    main_window._selected = obj
    calls: list[tuple[object, object]] = []

    class _FakeView3D:
        def set_selected_native_scene_data(self, req_obj, scene_data):
            calls.append((req_obj, scene_data))

    class _FakeSwitch:
        def isChecked(self):
            return False

    main_window.view3d = _FakeView3D()
    main_window.view3d_switch = _FakeSwitch()
    monkeypatch.setattr(main_window, "_native_model_path_for_object", lambda _obj: Path("/tmp/disabled_obj.cmp"))

    main_window._sync_view3d_selected_native_scene_data()

    assert calls == [(obj, None)]
    snapshot = main_window._native_scene_debug_state_snapshot()
    assert any(event.kind == "sync_skipped_3d_disabled" for event in snapshot["events"])


def test_create_solar_without_ids_toolchain_uses_zero_ids(main_window, monkeypatch):
    main_window._filepath = "/tmp/li01.ini"
    main_window._scale = 1.0
    main_window._pending_create = {
        "kind": "sun",
        "nickname": "li01_sun_01",
        "ids_name_text": "Sun Name",
        "archetype": "sun_1000",
        "burn_color": "",
        "radius": 1000,
        "damage": 100,
        "star": "med_white_sun",
        "atmosphere_range": 5000,
    }
    monkeypatch.setattr(main_window, "_has_ids_resource_toolchain", lambda: False)
    monkeypatch.setattr(main_window, "_refresh_3d_scene", lambda *args, **kwargs: None)

    main_window._create_solar_at_pos(QPointF(10.0, 20.0))

    obj = main_window._objects[-1]
    assert str(obj.data.get("ids_name", "")).strip() == "0"
    assert str(obj.data.get("ids_info", "")).strip() == "0"


def test_create_buoy_entries_without_ids_toolchain_uses_zero_ids(main_window, monkeypatch):
    main_window._filepath = "/tmp/li01.ini"
    main_window._scale = 1.0
    monkeypatch.setattr(main_window, "_has_ids_resource_toolchain", lambda: False)
    monkeypatch.setattr(main_window, "_next_auto_object_nickname", lambda _prefix: "li01_nav_buoy_001")

    entries = main_window._create_buoy_entries("nav_buoy", QPointF(0.0, 0.0), 0)
    values = {k: v for k, v in entries}

    assert values["ids_name"] == "0"
    assert values["ids_info"] == "0"
