from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QCloseEvent, QImage, QPixmap, QColor
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QTreeWidgetItem, QWidget

from fl_editor import config as config_module
from fl_editor import main_window as main_window_module
from fl_editor.i18n import get_language, tr
from fl_editor.dialogs import MeshPreviewDialog
from fl_editor.main_window import MainWindow
from fl_editor.model_viewer_dialog import ModelViewerEntry
from fl_editor.models import SolarObject
from fl_editor.freelancer_mesh_data import FreelancerBounds
from fl_editor.native_preview_geometry import NativePreviewGeometry
from fl_editor.native_preview_scene_data import NativePreviewSceneData
from fl_editor.native_scene_runtime import NativeSceneRuntimeEvent
from fl_editor.system_tab_runtime import open_system_tab


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


def test_restore_tabs_on_startup_defaults_disabled(main_window):
    assert main_window._restore_tabs_on_startup_enabled() is False


def test_apply_global_settings_persists_restore_tabs_on_startup(main_window, monkeypatch):
    monkeypatch.setattr("fl_editor.main_window.QMessageBox.information", lambda *args, **kwargs: None)
    main_window.gs_restore_tabs_cb.setChecked(True)

    main_window._apply_global_settings()

    assert bool(main_window._cfg.get("settings.restore_tabs_on_startup", False)) is True

    main_window._open_trade_routes_view()
    assert main_window.center_stack.currentWidget() is main_window.trade_routes_page

    main_window._open_name_editor_view()
    assert main_window.center_stack.currentWidget() is main_window.name_editor_page

    main_window._open_global_settings_view("mod_manager")
    assert main_window.center_stack.currentWidget() is main_window.global_settings_page
    assert main_window.gs_tabs.currentWidget() is main_window.gs_mod_manager_tab


def test_switching_edit_context_closes_all_closable_tabs(main_window, monkeypatch, tmp_path: Path):
    profile_root = tmp_path / "ModA"
    profile_root.mkdir(parents=True)
    universe_ini = profile_root / "DATA" / "UNIVERSE" / "universe.ini"
    universe_ini.parent.mkdir(parents=True)
    universe_ini.write_text("[System]\nnickname = li01\nfile = systems\\li01.ini\n", encoding="utf-8")
    profile = {"id": "mod-a", "name": "Mod A", "mode": "direct"}

    main_window._mm_editing_mod_id = "mod-b"
    close_calls: list[str] = []
    browser_calls: list[tuple[str, bool]] = []
    refresh_calls: list[str] = []
    load_calls: list[str] = []
    monkeypatch.setattr(main_window, "_mod_manager_profile_source", lambda _profile: profile_root)
    monkeypatch.setattr(main_window, "_center_close_all_closable_tabs", lambda: close_calls.append("closed"))
    monkeypatch.setattr(main_window, "_mod_manager_save_state", lambda: None)
    monkeypatch.setattr(main_window, "_update_active_mod_indicator", lambda: None)
    monkeypatch.setattr(main_window, "_refresh_ids_toolchain_header_notice", lambda: None)
    monkeypatch.setattr(main_window, "_persist_storage", lambda: None)
    monkeypatch.setattr(main_window, "_refresh_game_path_actions", lambda path: refresh_calls.append(path))
    monkeypatch.setattr(main_window, "_load_universe", lambda path: load_calls.append(path))
    monkeypatch.setattr(main_window.browser, "set_game_path", lambda path, scan=True: browser_calls.append((path, scan)))

    ok, _msg = main_window._mod_manager_switch_edit_context(profile)

    assert ok is True
    assert close_calls == ["closed"]
    assert main_window._mm_editing_mod_id == "mod-a"
    assert browser_calls == [(str(profile_root), True)]
    assert refresh_calls == [str(profile_root)]
    assert load_calls == [str(profile_root)]


def test_mod_settings_persists_top_view_icon_mod_toggle(main_window, tmp_path: Path):
    profile_root = tmp_path / "TestMod"
    profile_root.mkdir(parents=True)
    profile = {"id": "mod-1", "name": "Test Mod", "mode": "repo", "repo_folder": "TestMod", "repo_root": str(tmp_path)}
    main_window._mm_profiles = [profile]
    main_window._mm_editing_mod_id = "mod-1"

    main_window._mod_settings_apply_top_view_icon_toggle(True)

    cfg = main_window._mod_settings_read_profile_config(profile)
    assert bool(cfg.get("top_view_icons_mod_content_enabled", False)) is True


def test_mod_settings_prewarm_top_view_icon_cache_builds_mod_icons(main_window, monkeypatch, tmp_path: Path):
    profile_root = tmp_path / "TestMod"
    profile_root.mkdir(parents=True)
    model_path = profile_root / "DATA" / "SOLAR" / "station.cmp"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"cmp")
    profile = {"id": "mod-1", "name": "Test Mod", "mode": "repo", "repo_folder": "TestMod", "repo_root": str(tmp_path)}
    main_window._mm_profiles = [profile]
    main_window._mm_editing_mod_id = "mod-1"

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(profile_root))

    def _build_index(_game_path: str):
        main_window._arch_model_map = {"mod_station": "solar/station.cmp"}

    monkeypatch.setattr(main_window, "_build_archetype_model_index", _build_index)
    monkeypatch.setattr(main_window, "_native_model_path_for_archetype_cached", lambda archetype, game_path: model_path)
    monkeypatch.setattr(
        "fl_editor.main_window.load_native_scene_data",
        lambda _path: SimpleNamespace(scene_data=SimpleNamespace(geometries=(object(),))),
    )
    monkeypatch.setattr(
        "fl_editor.main_window.render_native_scene_top_view_icon",
        lambda _scene_data: QPixmap(16, 16).toImage(),
    )
    saved_paths: list[Path] = []
    monkeypatch.setattr(
        "fl_editor.main_window.save_top_view_icon",
        lambda cache_path, image: saved_paths.append(cache_path) or True,
    )
    monkeypatch.setattr("fl_editor.main_window.QMessageBox.information", lambda *args, **kwargs: QMessageBox.Ok)

    class _Progress:
        def __init__(self, maximum: int):
            self._maximum = maximum
            self._value = 0

        def maximum(self):
            return self._maximum

        def setValue(self, value):
            self._value = value

        def close(self):
            return None

        def setLabelText(self, _text):
            return None

    monkeypatch.setattr(main_window, "_make_mod_manager_progress", lambda label, maximum: _Progress(maximum))
    monkeypatch.setattr(main_window, "_update_mod_manager_progress", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_set_loading_visible", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_refresh_all_top_view_icons", lambda: None)

    main_window._mod_settings_prewarm_top_view_icon_cache()

    cfg = main_window._mod_settings_read_profile_config(profile)
    assert bool(cfg.get("top_view_icons_mod_content_enabled", False)) is True
    assert len(saved_paths) == 1


def test_resolve_top_view_icon_for_object_uses_disk_cache_without_rerender(main_window, monkeypatch, tmp_path: Path):
    obj = SimpleNamespace(
        nickname="li01_station_01",
        data={"archetype": "space_station01"},
    )
    cache_path = tmp_path / "cached-icon.png"
    image = QImage(24, 24, QImage.Format.Format_ARGB32)
    image.fill(QColor(20, 120, 220))
    assert image.save(str(cache_path), "PNG")

    monkeypatch.setattr(main_window, "_top_view_icon_cache_path_for_object", lambda _obj: cache_path)
    monkeypatch.setattr("fl_editor.main_window.load_cached_top_view_icon", lambda path: QPixmap(str(path)))
    monkeypatch.setattr(
        "fl_editor.main_window.render_native_scene_top_view_icon",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("renderer should not run when disk cache exists")),
    )
    monkeypatch.setattr(
        "fl_editor.main_window.render_planet_texture_top_view_icon",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("planet renderer should not run when disk cache exists")),
    )

    pixmap = main_window._resolve_top_view_icon_for_object(obj)

    assert pixmap is not None
    assert not pixmap.isNull()
    assert str(cache_path) in main_window._top_view_icon_pixmap_cache


def test_collect_3d_model_viewer_entries_groups_core_categories(main_window, monkeypatch, tmp_path: Path):
    data_dir = tmp_path / "DATA"
    (data_dir / "SOLAR").mkdir(parents=True)
    (data_dir / "SHIPS").mkdir(parents=True)
    (data_dir / "EQUIPMENT").mkdir(parents=True)
    (data_dir / "SOLAR" / "solararch.ini").write_text(
        "[Solar]\n"
        "nickname = planet_test_1000\n"
        "da_archetype = solar\\planets\\planet_test.sph\n"
        "material_library = solar\\planets\\planet_test.mat\n"
        "ids_name = 1000\n"
        "\n"
        "[Solar]\n"
        "nickname = station_test\n"
        "type = station\n"
        "da_archetype = solar\\stations\\station_test.cmp\n",
        encoding="utf-8",
    )
    (data_dir / "SHIPS" / "shiparch.ini").write_text(
        "[Ship]\n"
        "nickname = ge_fighter\n"
        "da_archetype = ships\\ge_fighter\\ge_fighter.cmp\n"
        "ids_name = 2000\n",
        encoding="utf-8",
    )
    (data_dir / "EQUIPMENT" / "weapon_equip.ini").write_text(
        "[Gun]\n"
        "nickname = ge_gun01_mark01\n"
        "da_archetype = equipment\\models\\weapon\\ge_gun01.cmp\n"
        "ids_name = 3000\n",
        encoding="utf-8",
    )
    for rel in (
        "SOLAR/PLANETS/planet_test.sph",
        "SOLAR/PLANETS/planet_test.mat",
        "SOLAR/STATIONS/station_test.cmp",
        "SHIPS/GE_FIGHTER/ge_fighter.cmp",
        "EQUIPMENT/MODELS/WEAPON/ge_gun01.cmp",
    ):
        path = data_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_display_name_from_ids_name", lambda raw: f"Name {raw}")

    entries = main_window._collect_3d_model_viewer_entries()

    by_nick = {entry.nickname: entry for entry in entries}
    assert by_nick["planet_test_1000"].category_key == "planets"
    assert by_nick["station_test"].category_key == "stations"
    assert by_nick["ge_fighter"].category_key == "ships"
    assert by_nick["ge_gun01_mark01"].category_key == "weapons"
    assert by_nick["planet_test_1000"].display_name == "Name 1000"


def test_open_3d_model_viewer_opens_manager_tab(main_window, monkeypatch, tmp_path: Path):
    ini_path = tmp_path / "DATA" / "SHIPS" / "shiparch.ini"
    ini_path.parent.mkdir(parents=True, exist_ok=True)
    ini_path.write_text("", encoding="utf-8")
    model_path = tmp_path / "DATA" / "SHIPS" / "ship.cmp"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_bytes(b"x")
    entry = ModelViewerEntry(
        category_key="ships",
        category_label="Ships",
        nickname="test_ship",
        display_name="Test Ship",
        archetype="test_ship",
        da_archetype="ships\\ship.cmp",
        model_path=model_path,
        source_ini_path=ini_path,
        source_section="Ship",
        render_kind="Freelancer Native",
    )
    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_collect_3d_model_viewer_entries", lambda: [entry])

    main_window._open_3d_model_viewer()

    assert getattr(main_window, "model_viewer_page", None) is not None
    assert main_window.center_stack.currentWidget() is main_window.model_viewer_page
    assert getattr(main_window, "_center_current_tab_key", None) == "model_viewer"


def test_open_3d_model_viewer_builds_embedded_preview(main_window, monkeypatch, tmp_path: Path):
    ini_path = tmp_path / "DATA" / "SHIPS" / "shiparch.ini"
    ini_path.parent.mkdir(parents=True, exist_ok=True)
    ini_path.write_text("", encoding="utf-8")
    model_path = tmp_path / "DATA" / "SHIPS" / "ship.cmp"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_bytes(b"x")
    entry = ModelViewerEntry(
        category_key="ships",
        category_label="Ships",
        nickname="test_ship",
        display_name="Test Ship",
        archetype="test_ship",
        da_archetype="ships\\ship.cmp",
        model_path=model_path,
        source_ini_path=ini_path,
        source_section="Ship",
        render_kind="Freelancer Native",
    )
    built: list[str] = []
    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_collect_3d_model_viewer_entries", lambda: [entry])
    monkeypatch.setattr(
        main_window,
        "_build_embedded_model_viewer_preview_widget",
        lambda current_entry, parent: built.append(current_entry.nickname) or QLabel("preview", parent),
    )

    main_window._open_3d_model_viewer()

    assert built == ["test_ship"]


def test_restore_center_tab_session_reopens_model_viewer(main_window, monkeypatch, tmp_path: Path):
    ini_path = tmp_path / "DATA" / "SHIPS" / "shiparch.ini"
    ini_path.parent.mkdir(parents=True, exist_ok=True)
    ini_path.write_text("", encoding="utf-8")
    model_path = tmp_path / "DATA" / "SHIPS" / "ship.cmp"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_bytes(b"x")
    entry = ModelViewerEntry(
        category_key="ships",
        category_label="Ships",
        nickname="test_ship",
        display_name="Test Ship",
        archetype="test_ship",
        da_archetype="ships\\ship.cmp",
        model_path=model_path,
        source_ini_path=ini_path,
        source_section="Ship",
        render_kind="Freelancer Native",
    )
    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_mod_manager_editing_profile", lambda: object())
    monkeypatch.setattr(main_window, "_collect_3d_model_viewer_entries", lambda: [entry])
    main_window._cfg.set(
        "tabs.session",
        {
            "tabs": [{"key": "model_viewer"}],
            "order": ["model_viewer"],
            "current": "model_viewer",
        },
    )

    main_window._restore_center_tab_session()

    assert getattr(main_window, "model_viewer_page", None) is not None
    assert main_window.center_stack.currentWidget() is main_window.model_viewer_page
    assert getattr(main_window, "_center_current_tab_key", None) == "model_viewer"


def test_trade_route_analysis_uses_selected_commodity(main_window, monkeypatch, tmp_path: Path):
    market_file = tmp_path / "DATA" / "EQUIPMENT" / "market_commodities.ini"
    market_file.parent.mkdir(parents=True)
    market_file.write_text("[BaseGood]\nbase = li01_01_base\n", encoding="utf-8")

    calls: list[dict] = []

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(
        main_window,
        "_resolve_game_path_case_insensitive",
        lambda _game_path, _rel: market_file,
    )

    class _Parser:
        def parse(self, _path):
            return [("BaseGood", [("base", "li01_01_base")])]

    monkeypatch.setattr(main_window, "_parser", _Parser())
    monkeypatch.setattr(
        "fl_editor.main_window.open_trade_route_analysis_dialog",
        lambda *_args, **kwargs: calls.append(kwargs),
    )

    main_window._trade_route_base_index = {
        "li01_01_base": {"base_nick": "li01_01_base", "display_name": "Manhattan", "system": "LI01", "pos": (0, 0)}
    }
    main_window._trade_route_commodity_base_prices = {"commodity_gold": 200}
    main_window._trade_route_commodity_display_map = {"commodity_gold": "Gold"}

    from PySide6.QtWidgets import QTableWidgetItem

    main_window.trade_routes_table.setRowCount(1)
    item = QTableWidgetItem("Gold")
    item.setData(
        Qt.UserRole,
        {
            "commodity": "commodity_gold",
            "buy_loc": "li01_01_base",
            "sell_loc": "li01_01_base",
        },
    )
    main_window.trade_routes_table.setItem(0, 0, item)
    main_window.trade_routes_table.setCurrentCell(0, 0)

    main_window._open_trade_route_analysis()

    assert len(calls) == 1
    assert calls[0]["initial_commodity"] == "commodity_gold"


def test_trade_route_sidebar_buttons_open_market_tools(main_window, monkeypatch, tmp_path: Path):
    market_file = tmp_path / "DATA" / "EQUIPMENT" / "market_commodities.ini"
    market_file.parent.mkdir(parents=True)
    market_file.write_text("[BaseGood]\nbase = li01_01_base\n", encoding="utf-8")

    analysis_calls: list[dict] = []
    market_calls: list[dict] = []

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(
        main_window,
        "_resolve_game_path_case_insensitive",
        lambda _game_path, _rel: market_file,
    )

    class _Parser:
        def parse(self, _path):
            return [("BaseGood", [("base", "li01_01_base")])]

    monkeypatch.setattr(main_window, "_parser", _Parser())
    monkeypatch.setattr(
        "fl_editor.main_window.open_trade_route_analysis_dialog",
        lambda *_args, **kwargs: analysis_calls.append(kwargs),
    )
    monkeypatch.setattr(
        "fl_editor.main_window.open_market_editor_dialog",
        lambda *_args, **kwargs: (market_calls.append(kwargs), (None, False))[1],
    )

    main_window._trade_route_base_index = {
        "li01_01_base": {"base_nick": "li01_01_base", "display_name": "Manhattan", "system": "LI01", "pos": (0, 0)}
    }
    main_window._trade_route_commodity_base_prices = {"commodity_gold": 200}
    main_window._trade_route_commodity_display_map = {"commodity_gold": "Gold"}

    main_window.trade_sidebar_market_editor_btn.click()
    main_window.trade_sidebar_analysis_btn.click()

    assert len(market_calls) == 1
    assert market_calls[0]["base_index"] == main_window._trade_route_base_index
    assert len(analysis_calls) == 1


def test_ini_editor_select_section_containing_jumps_to_match(main_window):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QListWidgetItem

    item_a = QListWidgetItem("[Good]  nickname = commodity_silver")
    item_a.setData(Qt.UserRole, 1)
    item_b = QListWidgetItem("[Good]  nickname = commodity_gold")
    item_b.setData(Qt.UserRole, 5)
    main_window.ini_sections_list.addItem(item_a)
    main_window.ini_sections_list.addItem(item_b)

    calls: list[str] = []
    main_window._ini_editor_jump_to_section = lambda item: calls.append(item.text())

    assert main_window._ini_editor_select_section_containing("nickname = commodity_gold")
    assert calls == ["[Good]  nickname = commodity_gold"]
    assert main_window.ini_sections_list.currentItem().text() == "[Good]  nickname = commodity_gold"


def test_ini_editor_current_search_term_prefers_selection_and_word_under_cursor(main_window):
    from PySide6.QtGui import QTextCursor

    main_window.ini_code_edit.setPlainText("nickname = commodity_gold\n")
    cursor = main_window.ini_code_edit.textCursor()
    cursor.setPosition(11)
    main_window.ini_code_edit.setTextCursor(cursor)

    assert main_window._ini_editor_current_search_term() == "commodity_gold"

    cursor = main_window.ini_code_edit.textCursor()
    cursor.setPosition(11)
    cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len("commodity_gold"))
    main_window.ini_code_edit.setTextCursor(cursor)

    assert main_window._ini_editor_current_search_term() == "commodity_gold"


def test_ini_editor_find_usages_scans_mod_and_vanilla_roots(main_window, tmp_path: Path):
    mod_root = tmp_path / "mod"
    vanilla_root = tmp_path / "vanilla"
    mod_file = mod_root / "DATA" / "goods.ini"
    vanilla_file = vanilla_root / "DATA" / "market_commodities.ini"
    mod_file.parent.mkdir(parents=True)
    vanilla_file.parent.mkdir(parents=True)
    mod_file.write_text("[Good]\nnickname = commodity_gold\n", encoding="utf-8")
    vanilla_file.write_text("[BaseGood]\nMarketGood = commodity_gold, 0, -1, 0, 0, 1, 1\n", encoding="utf-8")

    main_window._ini_editor_root = str(mod_root)
    main_window._ini_editor_fallback_root = str(vanilla_root)

    results = main_window._ini_editor_find_usages("commodity_gold")

    assert len(results) == 2
    assert {Path(str(row["path"])).name for row in results} == {"goods.ini", "market_commodities.ini"}
    assert {str(row["source"]) for row in results} == {"primary", "fallback"}


def test_ini_editor_open_usage_result_opens_file_and_jumps_to_line(main_window, monkeypatch, tmp_path: Path):
    target = tmp_path / "DATA" / "goods.ini"
    target.parent.mkdir(parents=True)
    target.write_text("[Good]\nnickname = commodity_gold\n", encoding="utf-8")

    opened: list[tuple[str, str]] = []
    jumped: list[int] = []
    monkeypatch.setattr(main_window, "_ini_editor_open_file_in_tab", lambda path, source="primary", ensure_workspace=True: opened.append((path, source)))
    monkeypatch.setattr(main_window, "_ini_editor_jump_to_line", lambda line: jumped.append(line))

    main_window._ini_editor_open_usage_result(
        {
            "path": str(target),
            "source": "fallback",
            "line": 2,
            "line_text": "nickname = commodity_gold",
        }
    )

    assert opened == [(str(target), "fallback")]
    assert jumped == [2]


def test_ini_editor_section_inspector_updates_selected_field(main_window, monkeypatch):
    from PySide6.QtWidgets import QTableWidget

    main_window.ini_code_edit.setPlainText(
        "[BaseGood]\n"
        "base = Li01_01_base\n"
        "MarketGood = commodity_gold, 0, -1, 1, 1, 0, 1\n"
    )
    main_window._ini_editor_current_file = "C:/tmp/test.ini"
    main_window._ini_editor_refresh_sections()
    main_window.ini_sections_list.setCurrentRow(0)

    def _fake_exec(dialog: QDialog):
        table = dialog.findChild(QTableWidget)
        assert table is not None
        table.item(1, 1).setText("commodity_gold, 0, -1, 150, 500, 0, 0.05")
        apply_btn = next(btn for btn in dialog.findChildren(type(main_window.ini_save_btn)) if btn.text())
        for btn in dialog.findChildren(type(main_window.ini_save_btn)):
            if "Apply" in btn.text() or "uebernehmen" in btn.text().lower():
                btn.click()
                break
        return 0

    monkeypatch.setattr(QDialog, "exec", _fake_exec)

    main_window._ini_editor_open_section_inspector()

    assert "commodity_gold, 0, -1, 150, 500, 0, 0.05" in main_window.ini_code_edit.toPlainText()


def test_ini_editor_validate_dialog_uses_current_text(main_window, monkeypatch):
    captured: list[list[str]] = []

    main_window.ini_code_edit.setPlainText(
        "[Good]\n"
        "nickname = commodity_gold\n"
        "ids_name = \n"
        "\n"
        "[Good]\n"
        "nickname = commodity_gold\n"
    )

    monkeypatch.setattr(main_window, "_ini_editor_show_validation_dialog", lambda findings: captured.append(findings))

    main_window._ini_editor_open_validation_dialog()

    assert len(captured) == 1
    assert any("Duplicate nickname 'commodity_gold'" in finding for finding in captured[0])
    assert any("Empty value for 'ids_name'" in finding for finding in captured[0])


def test_trade_route_open_goods_ini_opens_selected_commodity(main_window, monkeypatch, tmp_path: Path):
    goods_file = tmp_path / "DATA" / "EQUIPMENT" / "goods.ini"
    goods_file.parent.mkdir(parents=True)
    goods_file.write_text("[Good]\nnickname = commodity_gold\n", encoding="utf-8")

    opened: list[str] = []
    selected: list[str] = []

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(
        main_window,
        "_resolve_game_path_case_insensitive",
        lambda _game_path, rel: goods_file if rel == "DATA/EQUIPMENT/goods.ini" else None,
    )
    monkeypatch.setattr(main_window, "_ini_editor_open_file_in_tab", lambda path, *args, **kwargs: opened.append(path))
    monkeypatch.setattr(main_window, "_ini_editor_select_section_containing", lambda text: selected.append(text) or True)

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QTableWidgetItem

    main_window.trade_routes_table.setRowCount(1)
    item = QTableWidgetItem("Gold")
    item.setData(Qt.UserRole, {"commodity": "commodity_gold"})
    main_window.trade_routes_table.setItem(0, 0, item)
    main_window.trade_routes_table.setCurrentCell(0, 0)

    main_window._trade_route_open_goods_ini()

    assert opened == [str(goods_file)]
    assert selected == ["nickname = commodity_gold"]


def test_trade_route_open_market_section_opens_selected_base(main_window, monkeypatch, tmp_path: Path):
    market_file = tmp_path / "DATA" / "EQUIPMENT" / "market_commodities.ini"
    market_file.parent.mkdir(parents=True)
    market_file.write_text("[BaseGood]\nbase = li01_01_base\n", encoding="utf-8")

    opened: list[str] = []
    selected: list[str] = []

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(
        main_window,
        "_resolve_game_path_case_insensitive",
        lambda _game_path, rel: market_file if rel == "DATA/EQUIPMENT/market_commodities.ini" else None,
    )
    monkeypatch.setattr(main_window, "_ini_editor_open_file_in_tab", lambda path, *args, **kwargs: opened.append(path))
    monkeypatch.setattr(main_window, "_ini_editor_select_section_containing", lambda text: selected.append(text) or True)

    main_window._trade_route_open_market_section({"buy_loc": "li01_01_base"}, "buy")

    assert opened == [str(market_file)]
    assert selected == ["base = li01_01_base"]


def test_trade_route_jump_to_base_opens_system_and_selects_base(main_window, monkeypatch, tmp_path: Path):
    opened: list[str] = []
    selected: list[str] = []

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_find_all_systems", lambda _game_path: ["dummy"])
    monkeypatch.setattr("fl_editor.main_window.linked_system_path", lambda _systems, _nick: str(tmp_path / "Li01.ini"))
    monkeypatch.setattr(main_window, "_open_system_tab", lambda path, new_tab=False: opened.append(path))
    monkeypatch.setattr(main_window, "_trade_route_select_base_object", lambda base_nick: selected.append(base_nick) or True)

    main_window._trade_route_base_index = {
        "li01_01_base": {"base_nick": "li01_01_base", "display_name": "Manhattan", "system": "LI01", "pos": (0, 0)}
    }

    main_window._trade_route_jump_to_base(
        {
            "buy_loc": "li01_01_base",
            "buy_system": "LI01",
        },
        "buy",
    )

    assert opened == [str(tmp_path / "Li01.ini")]
    assert selected == ["li01_01_base"]


def test_trade_route_select_base_object_prefers_base_marker(main_window, monkeypatch):
    from PySide6.QtWidgets import QGraphicsScene

    base_obj = SolarObject(
        {
            "nickname": "planet_manhattan",
            "archetype": "planet",
            "base": "li01_01_base",
            "pos": "0, 0, 0",
        },
        1.0,
    )
    ring_obj = SolarObject(
        {
            "nickname": "li01_to_ring",
            "archetype": "dock_ring",
            "dock_with": "li01_01_base",
            "pos": "100, 0, 0",
        },
        1.0,
    )
    scene = QGraphicsScene()
    scene.addItem(base_obj)
    scene.addItem(ring_obj)
    main_window._objects = [ring_obj, base_obj]

    selected: list[str] = []
    centered_2d: list[str] = []
    centered_3d: list[str] = []

    monkeypatch.setattr(main_window, "_select", lambda obj: selected.append(obj.nickname))
    monkeypatch.setattr(main_window.view, "centerOn", lambda obj: centered_2d.append(obj.nickname))
    monkeypatch.setattr(main_window, "_jump_view3d_to_item_preserving_camera", lambda obj: centered_3d.append(obj.nickname))

    assert main_window._trade_route_select_base_object("li01_01_base")
    assert selected == ["planet_manhattan"]
    assert centered_2d == ["planet_manhattan"]
    assert centered_3d == ["planet_manhattan"]


def test_jump_view3d_to_item_preserving_camera_prefers_translation_only(main_window):
    calls: list[tuple[str, object]] = []

    class _FakeView3D:
        def jump_to_item_preserving_view(self, item):
            calls.append(("jump", item))

        def center_on_item(self, item):
            calls.append(("center", item))

    item = object()
    main_window.view3d = _FakeView3D()

    main_window._jump_view3d_to_item_preserving_camera(item)

    assert calls == [("jump", item)]


def test_trade_route_nav_cache_skips_non_dockable_planet_bases(main_window, monkeypatch, tmp_path: Path):
    system_path = tmp_path / "li01.ini"
    system_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(main_window, "_find_universe_ini_read", lambda _game_path: None)
    monkeypatch.setattr(
        main_window,
        "_find_all_systems",
        lambda _game_path: [{"nickname": "LI01", "path": str(system_path), "pos": (0.0, 0.0)}],
    )

    class _Parser:
        def parse(self, _path):
            return []

        def get_objects(self, _secs):
            return [
                {"nickname": "planet_a", "archetype": "planet", "base": "li01_01_base", "pos": "0,0,0"},
                {"nickname": "planet_b", "archetype": "planet", "base": "li01_02_base", "pos": "100,0,0"},
                {"nickname": "ring_b", "archetype": "dock_ring", "dock_with": "li01_02_base", "pos": "110,0,0"},
                {"nickname": "station_c", "archetype": "station", "base": "li01_03_base", "pos": "200,0,0"},
                {"nickname": "miner_d", "archetype": "station", "base": "gd_im_silver_miner", "pos": "300,0,0"},
                {"nickname": "miner_dock", "archetype": "dock_ring", "dock_with": "gd_im_silver_miner", "pos": "310,0,0"},
            ]

        def get_zones(self, _secs):
            return []

    monkeypatch.setattr(main_window, "_parser", _Parser())

    main_window._build_trade_route_nav_cache(str(tmp_path))

    assert "li01_01_base" not in main_window._trade_route_base_index
    assert "li01_02_base" in main_window._trade_route_base_index
    assert "li01_03_base" in main_window._trade_route_base_index
    assert "gd_im_silver_miner" not in main_window._trade_route_base_index


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
    assert main_window.trade_connections_lbl.text()
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
    assert "[install]" in child.text(0).lower()
    main_window._ini_editor_open_tree_item(child)

    assert main_window._ini_editor_current_file.endswith("test.ini")
    assert main_window.ini_sections_list.count() == 2
    assert "test.ini" in main_window.ini_status_summary_val.text()
    assert main_window.ini_status_summary_val.text()


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


def test_open_current_system_ini_opens_file_directly_when_tree_item_is_missing(main_window, monkeypatch, tmp_path: Path):
    ini_path = tmp_path / "DATA" / "UNIVERSE" / "LI01" / "li01.ini"
    ini_path.parent.mkdir(parents=True)
    ini_path.write_text("[SystemInfo]\n", encoding="utf-8")
    main_window._filepath = str(ini_path)

    calls: list[str] = []
    monkeypatch.setattr(main_window, "_open_ini_editor_view", lambda: calls.append("open_ini_editor"))
    monkeypatch.setattr(main_window, "_ini_editor_find_tree_item_by_path", lambda _path: None)
    monkeypatch.setattr(
        main_window,
        "_ini_editor_open_file_in_tab",
        lambda path, source="primary", ensure_workspace=True: calls.append(
            f"open_file:{path}|{source}|{ensure_workspace}"
        ),
    )

    main_window._open_current_system_ini()

    assert calls == [f"open_ini_editor", f"open_file:{ini_path}|primary|False"]


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


def test_closing_active_ini_tab_loads_adjacent_ini_document(main_window, monkeypatch, tmp_path: Path):
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
    main_window.ini_code_edit.setPlainText("[a]\nvalue = 111\n")
    main_window._ini_editor_open_tree_item(i2)

    idx2 = main_window._center_tab_index_for_key(main_window._ini_editor_tab_key(str(f2)))
    assert idx2 >= 0

    main_window._on_center_tab_close_requested(idx2)

    assert main_window._center_current_tab_key == main_window._ini_editor_tab_key(str(f1))
    assert "111" in main_window.ini_code_edit.toPlainText()
    assert main_window._ini_editor_current_file.endswith("a.ini")


def test_closing_current_settings_tab_restores_name_editor_sidebar(main_window, monkeypatch, tmp_path: Path):
    monkeypatch.setattr(main_window, "_data_lookup_game_path", lambda: str(tmp_path))
    monkeypatch.setattr("fl_editor.main_window.start_async_view_load", lambda *args, **kwargs: None)

    main_window._open_name_editor_view()
    assert main_window.center_stack.currentWidget() is main_window.name_editor_page

    main_window._open_global_settings_view()
    settings_idx = main_window._center_tab_index_for_key("settings")
    assert settings_idx >= 0

    main_window._on_center_tab_close_requested(settings_idx)

    assert main_window.center_stack.currentWidget() is main_window.name_editor_page
    assert main_window.left_stack.currentWidget() is main_window.left_name_panel


def test_closing_current_system_tab_prefers_universe_view(main_window, monkeypatch):
    main_window._filepath = ""
    main_window._dirty = False
    universe_widget = main_window.view
    system_widget = object()
    main_window._center_tab_specs = [
        {"widget": universe_widget, "title": "Universe", "key": "universe", "closable": False},
        {"widget": system_widget, "title": "Li01", "key": "system:li01", "closable": True, "host_key": "primary"},
    ]
    main_window._center_current_tab_key = "system:li01"
    requested_indices: list[int] = []
    universe_idx = 0

    def _activate(index: int):
        requested_indices.append(int(index))
        return int(index) == universe_idx

    monkeypatch.setattr(main_window, "_activate_center_fallback_after_close", _activate)

    main_window._on_center_tab_close_requested(1)

    assert requested_indices[0] == universe_idx


def test_sync_view3d_camera_to_2d_view_uses_current_center_and_zoom(main_window, monkeypatch):
    monkeypatch.setattr(main_window.view, "mapToScene", lambda _point: QPointF(120.0, -340.0))
    monkeypatch.setattr(main_window, "_filepath", "/tmp/li01.ini")
    monkeypatch.setattr(main_window, "_current_system_boundary_radius_world", lambda: 20000.0)

    captured: dict[str, object] = {}

    class _FakeView3D:
        def get_camera_state(self):
            return {"target_x": 1.0, "target_y": 9.0, "target_z": 2.0, "distance": 300.0, "yaw": 0.0, "pitch": 1.42}

        def set_camera_state(self, state):
            captured["camera_state"] = dict(state)

        def set_zoom_factor(self, value: float):
            captured["zoom_factor"] = float(value)

        def minimum_zoom_factor(self) -> float:
            return 0.25

        def maximum_zoom_factor(self) -> float:
            return 3.5

        def set_orbit_target_plane_y(self, value: float):
            captured["plane_y"] = float(value)

        def set_reference_radius_scene(self, value: float):
            captured["reference_radius_scene"] = float(value)

    main_window.view3d = _FakeView3D()
    monkeypatch.setattr(main_window.view, "current_zoom_factor", lambda: 1.75)
    expected_zoom = main_window._map_2d_zoom_factor_to_view3d(1.75)

    main_window._sync_view3d_camera_to_2d_view()

    assert captured["camera_state"]["target_x"] == 120.0
    assert captured["camera_state"]["target_y"] == 0.0
    assert captured["camera_state"]["target_z"] == -340.0
    assert captured["zoom_factor"] == pytest.approx(expected_zoom)
    assert captured["plane_y"] == 0.0
    assert captured["reference_radius_scene"] > 0.0


def test_sync_2d_view_to_view3d_camera_uses_current_target_and_zoom(main_window, monkeypatch):
    centered: list[QPointF] = []
    captured: dict[str, float] = {}

    class _FakeView3D:
        def get_camera_state(self):
            return {"target_x": 420.0, "target_y": 9.0, "target_z": -180.0, "distance": 300.0, "yaw": 0.0, "pitch": 1.42}

        def get_zoom_factor(self) -> float:
            return 2.25

        def minimum_zoom_factor(self) -> float:
            return 0.25

        def maximum_zoom_factor(self) -> float:
            return 3.5

    main_window.view3d = _FakeView3D()
    monkeypatch.setattr(main_window.view, "centerOn", lambda point: centered.append(point))
    monkeypatch.setattr(main_window.view, "set_zoom_factor", lambda value: captured.setdefault("zoom_factor", float(value)))
    expected_zoom = main_window._map_view3d_zoom_factor_to_2d(2.25)

    main_window._sync_2d_view_to_view3d_camera()

    assert len(centered) == 1
    assert centered[0].x() == 420.0
    assert centered[0].y() == -180.0
    assert captured["zoom_factor"] == pytest.approx(expected_zoom)


def test_toggle_3d_view_off_preserves_current_3d_view_in_2d(main_window, monkeypatch):
    centered: list[QPointF] = []
    captured: dict[str, float] = {}
    monkeypatch.setattr(main_window.view3d, "is_free_camera_active", lambda: False)
    monkeypatch.setattr(
        main_window.view3d,
        "get_camera_state",
        lambda: {"target_x": 75.0, "target_y": 0.0, "target_z": 155.0, "distance": 240.0, "yaw": 0.3, "pitch": 1.1},
    )
    monkeypatch.setattr(main_window.view3d, "get_zoom_factor", lambda: 1.6)
    monkeypatch.setattr(main_window.view, "centerOn", lambda point: centered.append(point))
    monkeypatch.setattr(main_window.view, "set_zoom_factor", lambda value: captured.setdefault("zoom_factor", float(value)))
    monkeypatch.setattr(main_window, "_sync_flight_button_visibility", lambda: None)
    main_window.center_stack.setCurrentWidget(main_window.view3d)
    expected_zoom = main_window._map_view3d_zoom_factor_to_2d(1.6)

    main_window._toggle_3d_view(False)

    assert main_window.center_stack.currentWidget() is main_window.view
    assert len(centered) == 1
    assert centered[0].x() == 75.0
    assert centered[0].y() == 155.0
    assert captured["zoom_factor"] == pytest.approx(expected_zoom)


def test_toggle_3d_view_on_preserves_camera_when_refreshing_scene(main_window, monkeypatch):
    calls: list[bool] = []
    main_window._filepath = "/tmp/li01.ini"
    monkeypatch.setattr(main_window, "_refresh_3d_scene", lambda preserve_camera=False: calls.append(bool(preserve_camera)))
    monkeypatch.setattr(main_window, "_sync_view3d_camera_to_2d_view", lambda: None)
    monkeypatch.setattr(main_window, "_sync_flight_button_visibility", lambda: None)

    main_window._toggle_3d_view(True)

    assert calls
    assert all(call is True for call in calls)
    assert main_window.center_stack.currentWidget() is main_window.view3d


def test_toggle_3d_view_on_uses_loading_bar(main_window, monkeypatch):
    loading_calls: list[tuple[bool, object]] = []
    main_window._filepath = "/tmp/li01.ini"
    monkeypatch.setattr(main_window, "_sync_view3d_camera_to_2d_view", lambda: None)
    monkeypatch.setattr(main_window, "_refresh_3d_scene", lambda preserve_camera=False: None)
    monkeypatch.setattr(main_window, "_sync_flight_button_visibility", lambda: None)
    monkeypatch.setattr(main_window, "_set_loading_visible", lambda visible, message=None: loading_calls.append((bool(visible), message)))
    monkeypatch.setattr(main_window, "_set_loading_progress", lambda value, message=None: None)

    main_window._toggle_3d_view(True)

    assert loading_calls[0][0] is True
    assert loading_calls[-1][0] is False


def test_toggle_3d_view_on_preserves_zone_visibility_setting(main_window, monkeypatch):
    main_window._filepath = "/tmp/li01.ini"
    main_window.zone_cb.setChecked(True)
    monkeypatch.setattr(main_window, "_sync_view3d_camera_to_2d_view", lambda: None)
    monkeypatch.setattr(main_window, "_refresh_3d_scene", lambda preserve_camera=False: None)
    monkeypatch.setattr(main_window, "_sync_flight_button_visibility", lambda: None)
    monkeypatch.setattr(main_window, "_set_loading_visible", lambda visible, message=None: None)
    monkeypatch.setattr(main_window, "_set_loading_progress", lambda value, message=None: None)

    main_window._toggle_3d_view(True)

    assert main_window.zone_cb.isChecked() is True


def test_restore_view_settings_applies_3d_grid_visibility(main_window, monkeypatch):
    calls: list[bool] = []
    main_window._cfg.set("view.show_3d_grid", False)
    monkeypatch.setattr(main_window.view3d, "set_reference_overlay_visible", lambda enabled: calls.append(bool(enabled)))

    main_window._restore_view_settings()

    assert main_window._view3d_reference_grid_visible is False
    assert calls[-1] is False


def test_on_view3d_context_menu_jump_action_uses_preserved_camera_jump(main_window, monkeypatch):
    calls: list[tuple[str, object]] = []

    class _FakeSolarObject:
        pass

    class _FakeAction:
        def __init__(self):
            self._callbacks = []
            self.triggered = SimpleNamespace(connect=self._callbacks.append)

        def fire(self):
            for callback in list(self._callbacks):
                callback()

    class _FakeMenu:
        def __init__(self, _parent):
            self._actions: list[_FakeAction] = []

        def addAction(self, _text):
            action = _FakeAction()
            self._actions.append(action)
            return action

        def addSeparator(self):
            return None

        def actions(self):
            return list(self._actions)

        def exec(self, _global_pos):
            if self._actions:
                self._actions[0].fire()

    monkeypatch.setattr(main_window_module, "SolarObject", _FakeSolarObject)
    monkeypatch.setattr("PySide6.QtWidgets.QMenu", _FakeMenu)
    monkeypatch.setattr(main_window, "_select", lambda item: calls.append(("select", item)))
    monkeypatch.setattr(main_window, "_jump_view3d_to_item_preserving_camera", lambda item: calls.append(("jump", item)))
    main_window._selected = None
    main_window._multi_selected = []
    item = _FakeSolarObject()

    main_window._on_view3d_context_menu(item, object())

    assert calls == [("select", item), ("jump", item)]


def test_active_system_editor_widget_for_current_mode_tracks_3d_switch(main_window):
    main_window.view3d_switch.setChecked(False)
    assert main_window._active_system_editor_widget_for_current_mode() is main_window.view

    main_window._filepath = "/tmp/li01.ini"
    main_window.view3d_switch.setChecked(True)
    assert main_window._active_system_editor_widget_for_current_mode() is main_window.view3d


def test_zoom_slider_controls_3d_view_when_active(main_window):
    calls: list[float] = []
    main_window.view3d.set_zoom_factor = lambda value: calls.append(float(value))
    main_window.center_stack.setCurrentWidget(main_window.view3d)

    main_window._on_zoom_slider_changed(main_window._zoom_slider_value_for_factor(1.6))

    assert calls == [pytest.approx(1.6, rel=0.005)]


def test_sync_zoom_slider_from_view_defers_2d_label_refresh(main_window, monkeypatch, qtbot):
    main_window.center_stack.setCurrentWidget(main_window.view)
    main_window._viewer_text_visible = True
    main_window._avoid_label_overlap = False
    calls: list[str] = []
    monkeypatch.setattr(main_window, "_apply_2d_object_zoom_style", lambda _zoom: calls.append("style"))
    monkeypatch.setattr(main_window, "_reset_2d_label_positions", lambda: calls.append("reset"))
    monkeypatch.setattr(main_window, "_reflow_2d_labels", lambda: calls.append("reflow"))

    main_window._sync_zoom_slider_from_view(1.25)

    assert calls == ["style"]
    qtbot.wait(40)
    assert calls == ["style", "reset"]


def test_refresh_3d_scene_suppresses_native_preview_refresh_during_rebuild(main_window, monkeypatch):
    calls: list[tuple] = []
    main_window._filepath = "/tmp/li01.ini"
    main_window.view3d_switch.blockSignals(True)
    main_window.view3d_switch.setChecked(True)
    main_window.view3d_switch.blockSignals(False)
    monkeypatch.setattr(main_window.view3d, "set_native_preview_refresh_suppressed", lambda enabled: calls.append(("suppress", bool(enabled))))
    monkeypatch.setattr(main_window.view3d, "set_data", lambda objects, zones, scale: calls.append(("set_data", len(objects), len(zones), float(scale))))
    monkeypatch.setattr(main_window.view3d, "set_selected", lambda obj: calls.append(("set_selected", obj)))
    monkeypatch.setattr(main_window, "_apply_viewer_text_visibility", lambda: calls.append(("labels",)))
    monkeypatch.setattr(main_window, "_apply_group_visibility", lambda: calls.append(("groups",)))
    monkeypatch.setattr(main_window, "_sync_view3d_selected_native_scene_data", lambda: calls.append(("sync_selected",)))

    main_window._refresh_3d_scene()

    assert calls[0] == ("suppress", True)
    assert ("set_data", len(main_window._objects), len(main_window._zones if main_window.zone_cb.isChecked() else []), float(main_window._scale)) in calls
    assert calls[-1] == ("suppress", False)


def test_view3d_native_preview_progress_updates_loading_bar(main_window):
    visible_calls: list[tuple[bool, object]] = []
    progress_calls: list[tuple[int | float, object]] = []
    main_window.center_stack.setCurrentWidget(main_window.view3d)
    main_window._set_loading_visible = lambda visible, message=None: visible_calls.append((bool(visible), message))
    main_window._set_loading_progress = lambda value, message=None: progress_calls.append((value, message))

    main_window._on_view3d_native_preview_progress({"active": True, "done": 2, "total": 5})
    main_window._on_view3d_native_preview_progress({"active": False, "done": 5, "total": 5})

    assert visible_calls[0][0] is True
    assert visible_calls[-1][0] is False
    assert any("2/5" in str(message) for _value, message in progress_calls)


def test_open_activity_view_creates_center_tab(main_window):
    main_window._open_activity_view()

    assert getattr(main_window, "activity_page", None) is not None
    assert main_window.center_stack.currentWidget() is main_window.activity_page
    assert main_window._center_tab_index_for_key("activity") >= 0


def test_status_message_updates_activity_log(main_window):
    main_window._open_activity_view()

    main_window.statusBar().showMessage("Background task example")

    assert any(
        str(entry.get("message", "")) == "Background task example"
        for entry in getattr(main_window, "_activity_log_entries", [])
    )
    assert "Background task example" in main_window.activity_details_view.toPlainText()


def test_activity_log_classifies_3d_and_ini_messages(main_window):
    main_window._append_activity_log("Loading 3D objects... 2/5", source="STATUS")
    main_window._append_activity_log("Opened INI file: test.ini", source="STATUS")

    categories = [str(entry.get("category", "")) for entry in main_window._activity_log_entries[-2:]]

    assert categories == ["3D", "INI"]


def test_activity_view_filters_by_category(main_window):
    main_window._open_activity_view()
    main_window._append_activity_log("Loading 3D objects... 2/5", source="STATUS")
    main_window._append_activity_log("Opened INI file: test.ini", source="STATUS")

    index = main_window.activity_filter_cb.findData("INI")
    assert index >= 0
    main_window.activity_filter_cb.setCurrentIndex(index)

    text = main_window.activity_details_view.toPlainText()

    assert "Opened INI file: test.ini" in text
    assert "Loading 3D objects... 2/5" not in text


def test_set_free_camera_mode_toggles_view3d_and_button(main_window):
    calls: list[bool] = []
    main_window._filepath = "C:/tmp/li01.ini"
    main_window_module = __import__("fl_editor.main_window", fromlist=["QT3D_AVAILABLE"])
    original_qt3d_available = bool(getattr(main_window_module, "QT3D_AVAILABLE", False))
    setattr(main_window_module, "QT3D_AVAILABLE", True)
    main_window.view3d_switch.blockSignals(True)
    main_window.view3d_switch.setChecked(True)
    main_window.view3d_switch.blockSignals(False)
    main_window.view3d.set_free_camera_active = lambda enabled: calls.append(bool(enabled))
    try:
        main_window._set_free_camera_mode(True)
        main_window._set_free_camera_mode(False)
    finally:
        setattr(main_window_module, "QT3D_AVAILABLE", original_qt3d_available)

    assert calls == [True, False]
    assert main_window._free_camera_action.isChecked() is False


def test_system_zoom_controls_swap_points_with_3d_distance(main_window):
    main_window.center_stack.setCurrentWidget(main_window.view)
    main_window._set_system_zoom_controls_visible(True)

    assert main_window._menu_zoom_host.parent() is main_window.left_ini_panel
    assert main_window._point_size_lbl.isHidden() is False
    assert main_window._point_size_slider.isHidden() is False
    assert main_window._native_preview_dist_lbl.isHidden() is True
    assert main_window._native_preview_dist_slider.isHidden() is True
    assert main_window._native_preview_controls_host.parent() is main_window.left_ini_panel
    assert main_window._native_preview_dist_slider.parent().parent() is main_window._native_preview_controls_host

    main_window.center_stack.setCurrentWidget(main_window.view3d)
    main_window._set_system_zoom_controls_visible(True)

    assert main_window._menu_zoom_host.isHidden() is False
    assert main_window._point_size_lbl.isHidden() is True
    assert main_window._point_size_slider.isHidden() is True
    assert main_window._native_preview_controls_host.isHidden() is False
    assert main_window._native_preview_dist_lbl.isHidden() is False
    assert main_window._native_preview_dist_slider.isHidden() is False
    assert main_window._native_preview_dist_value_lbl.isHidden() is False


def test_toggle_3d_view_auto_disables_zones(main_window, monkeypatch):
    main_window._filepath = "/tmp/li01.ini"
    main_window.zone_cb.setChecked(True)
    monkeypatch.setattr(main_window, "_sync_view3d_camera_to_2d_view", lambda: None)
    monkeypatch.setattr(main_window, "_refresh_3d_scene", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_sync_flight_button_visibility", lambda: None)

    main_window._toggle_3d_view(True)

    assert main_window.zone_cb.isChecked() is False
    assert main_window.center_stack.currentWidget() is main_window.view3d


def test_enforce_responsive_splitter_layout_clamps_right_sidebar(main_window):
    splitter = getattr(main_window, "_main_splitter", None)
    assert splitter is not None
    splitter.resize(1800, 1000)
    splitter.setSizes([220, 200, 1380])

    main_window._enforce_responsive_splitter_layout()

    sizes = splitter.sizes()
    total = int(splitter.size().width()) or int(main_window.size().width())
    assert len(sizes) >= 3
    assert sizes[2] <= max(170, int(total * 0.33))
    assert sizes[1] >= 220


def test_center_set_current_widget_syncs_zoom_from_active_3d_view(main_window):
    captured: list[float] = []

    main_window._filepath = "/tmp/li01.ini"
    main_window.view3d_switch.blockSignals(True)
    main_window.view3d_switch.setChecked(True)
    main_window.view3d_switch.blockSignals(False)
    main_window._sync_zoom_slider_from_view = lambda zoom: captured.append(float(zoom))
    main_window.view3d.get_zoom_factor = lambda: 2.25

    main_window._center_set_current_widget(main_window.view3d, "system:li01")

    assert captured[-1] == 2.25


def test_open_system_tab_restores_saved_3d_widget(main_window, monkeypatch, tmp_path: Path):
    system_path = tmp_path / "Li01.ini"
    system_path.write_text("[SystemInfo]\nspace_color = 0, 0, 0\n", encoding="utf-8")
    tab_key = main_window._system_tab_key(str(system_path))
    host = main_window._ensure_system_tab_host(tab_key)
    idx = main_window._center_register_tab(host.view, "Li01", tab_key, closable=True)
    main_window._center_tab_specs[idx]["host_key"] = host.key
    main_window._center_tab_specs[idx]["path"] = str(system_path)
    main_window._center_tab_specs[idx]["document"] = main_window._system_document_factory(
        path=str(system_path),
        sections=[],
        dirty=False,
        use_3d=True,
        camera_state={"target_x": 5.0, "target_y": 0.0, "target_z": -7.0, "distance": 123.0, "yaw": 0.2, "pitch": 0.9},
    )
    main_window._filepath = ""
    monkeypatch.setattr(
        main_window,
        "_apply_system_document",
        lambda path, sections, restore=None, dirty=False, doc=None: setattr(main_window, "_filepath", path),
    )
    monkeypatch.setattr(main_window, "_refresh_3d_scene", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        main_window,
        "_toggle_3d_view",
        lambda enabled: main_window.center_stack.setCurrentWidget(main_window.view3d if enabled else main_window.view),
    )
    monkeypatch.setattr(main_window.browser, "highlight_current", lambda _path: None)

    open_system_tab(main_window, str(system_path), new_tab=False)

    assert main_window.center_stack.currentWidget() is main_window.view3d
    assert main_window.view3d_switch.isChecked() is True


def test_system_reference_overlay_draws_freelancer_grid_labels(main_window, tmp_path: Path):
    system_path = tmp_path / "li01.ini"
    system_path.write_text("[SystemInfo]\nspace_color = 0, 0, 0\n", encoding="utf-8")
    main_window._filepath = str(system_path)
    main_window._scale = 1.0

    main_window._draw_system_reference_overlay(10000.0)

    texts = {
        item.toPlainText()
        for item in main_window.view._scene.items()
        if hasattr(item, "toPlainText")
    }
    text_items = {
        item.toPlainText(): item
        for item in main_window.view._scene.items()
        if hasattr(item, "toPlainText")
    }

    assert "PHYSICAL MAP" in texts
    assert "SYSTEM LI01" in texts or "LI01" in texts
    assert {"A", "H", "1", "8", "0,0,0"}.issubset(texts)
    assert text_items["A"].font().pointSize() >= 13
    assert text_items["PHYSICAL MAP"].font().pointSize() >= 16
    assert main_window.view.sceneRect().width() > 0.0
    assert main_window.view.sceneRect().height() > 0.0


def test_fit_uses_system_reference_scene_rect_for_loaded_system(main_window, monkeypatch):
    main_window._filepath = "C:/mods/DATA/UNIVERSE/li01.ini"
    main_window.view._scene.setSceneRect(QRectF(-120.0, -80.0, 340.0, 300.0))
    captured: list[QRectF] = []
    monkeypatch.setattr(main_window.view, "fitInView", lambda rect, _mode: captured.append(QRectF(rect)))
    monkeypatch.setattr(main_window, "_sync_zoom_slider_from_view", lambda _zoom: None)

    main_window._fit()

    assert len(captured) == 1
    assert captured[0] == main_window.view.sceneRect()


def test_zoom_slider_bounds_follow_2d_system_fit(main_window, tmp_path: Path):
    system_path = tmp_path / "li01.ini"
    system_path.write_text("[SystemInfo]\nspace_color = 0, 0, 0\n", encoding="utf-8")
    main_window._filepath = str(system_path)
    main_window.center_stack.setCurrentWidget(main_window.view)
    main_window.view3d_switch.setChecked(False)
    main_window.view.resize(800, 600)
    main_window.view.set_zoom_out_limit_to_scene(True)
    main_window.view.set_zoom_out_reference_rect(QRectF(-200.0, -150.0, 400.0, 300.0))

    minimum, maximum = main_window._zoom_slider_bounds_for_active_view()

    assert minimum > 0.0
    assert maximum > minimum
    assert main_window._zoom_slider_value_for_factor(minimum) == main_window._zoom_slider.minimum()
    assert main_window._zoom_slider_value_for_factor(maximum) == main_window._zoom_slider.maximum()


def test_system_reference_half_extent_uses_freelancer_navmap_default(main_window, tmp_path: Path):
    system_path = tmp_path / "ku03.ini"
    system_path.write_text("[SystemInfo]\nspace_color = 0, 0, 0\n", encoding="utf-8")
    main_window._filepath = str(system_path)
    main_window._uni_sections = [
        (
            "system",
            [
                ("nickname", "ku03"),
                ("file", "systems\\ku03\\ku03.ini"),
            ],
        )
    ]

    assert main_window._system_reference_half_extent_world(10000.0) == pytest.approx(13600.0)


def test_system_reference_half_extent_prefers_explicit_navmap_scale(main_window, tmp_path: Path):
    system_path = tmp_path / "li01.ini"
    system_path.write_text("[SystemInfo]\nspace_color = 0, 0, 0\n", encoding="utf-8")
    main_window._filepath = str(system_path)
    main_window._uni_sections = [
        (
            "system",
            [
                ("nickname", "li01"),
                ("NavMapScale", "2.0"),
            ],
        )
    ]

    assert main_window._system_reference_half_extent_world(35000.0) == pytest.approx(70000.0)


def test_resolve_system_boundary_radius_world_uses_declared_system_light_range(main_window, tmp_path: Path):
    system_path = tmp_path / "li01.ini"
    system_path.write_text("[SystemInfo]\nspace_color = 0, 0, 0\n", encoding="utf-8")
    main_window._filepath = str(system_path)
    main_window._uni_sections = [
        (
            "system",
            [
                ("nickname", "li01"),
                ("NavMapScale", "1.36"),
            ],
        )
    ]

    boundary = main_window._resolve_system_boundary_radius_world(
        str(system_path),
        sections=[
            (
                "LightSource",
                [
                    ("nickname", "li01_system_light"),
                    ("range", "120000"),
                    ("type", "DIRECTIONAL"),
                ],
            )
        ],
        raw_objects=[],
    )

    total_extent = main_window._system_reference_half_extent_world(boundary) * 2.0

    assert total_extent == pytest.approx(120000.0)


def test_resolve_system_boundary_radius_world_prefers_declared_map_extent_over_large_zone_bounds(main_window, tmp_path: Path):
    system_path = tmp_path / "iw05.ini"
    system_path.write_text("[SystemInfo]\nspace_color = 0, 0, 0\n", encoding="utf-8")
    main_window._filepath = str(system_path)
    main_window._uni_sections = [
        (
            "system",
            [
                ("nickname", "iw05"),
                ("NavMapScale", "2.0"),
            ],
        )
    ]

    boundary = main_window._resolve_system_boundary_radius_world(
        str(system_path),
        sections=[
            (
                "LightSource",
                [
                    ("nickname", "iw05_system_light"),
                    ("range", "100000"),
                    ("type", "DIRECTIONAL"),
                ],
            )
        ],
        raw_objects=[
            {
                "pos": "-41821, 0, -5743",
                "size": "46146, 11876, 90840",
            }
        ],
    )

    assert boundary == pytest.approx(25000.0)
    assert main_window._system_reference_half_extent_world(boundary) * 2.0 == pytest.approx(100000.0)


def test_resolve_system_boundary_radius_world_expands_when_objects_exceed_declared_map_extent(main_window, tmp_path: Path):
    system_path = tmp_path / "bw05.ini"
    system_path.write_text("[SystemInfo]\nspace_color = 0, 0, 0\n", encoding="utf-8")
    main_window._filepath = str(system_path)
    main_window._uni_sections = [
        (
            "system",
            [
                ("nickname", "bw05"),
                ("NavMapScale", "2.0"),
            ],
        )
    ]

    boundary = main_window._resolve_system_boundary_radius_world(
        str(system_path),
        sections=[
            (
                "LightSource",
                [
                    ("nickname", "bw05_system_light"),
                    ("range", "50000"),
                    ("type", "DIRECTIONAL"),
                ],
            )
        ],
        raw_objects=[
            {
                "pos": "2076, 0, 42897",
                "size": "1, 1, 1",
            }
        ],
    )

    assert boundary == pytest.approx(21448.5)
    assert main_window._system_reference_half_extent_world(boundary) * 2.0 == pytest.approx(85794.0)


def test_create_system_at_pos_opens_new_system_without_reloading_universe(main_window, monkeypatch, tmp_path: Path):
    universe_dir = tmp_path / "DATA" / "UNIVERSE"
    universe_dir.mkdir(parents=True)
    uni_ini = universe_dir / "universe.ini"
    uni_ini.write_text("[Base]\n", encoding="utf-8")

    main_window._pending_new_system = {
        "game_path": str(tmp_path),
        "prefix": "TE",
        "name": "Taharka",
        "size": 120000,
        "local_faction": "li_n_grp",
        "space_color": "1, 2, 3",
        "music_space": "music_space",
        "music_danger": "music_danger",
        "music_battle": "music_battle",
        "ambient_color": "4, 5, 6",
        "bg_basic": "basic",
        "bg_complex": "complex",
        "bg_nebulae": "nebula",
        "light_color": "7, 8, 9",
    }
    main_window._scale = 1.0

    loaded_paths: list[str] = []
    highlighted: list[str] = []
    set_game_path_calls: list[tuple[str, bool]] = []
    universe_load_calls: list[str] = []

    monkeypatch.setattr(main_window, "_find_all_systems", lambda _game_path: [])
    monkeypatch.setattr(main_window, "_ensure_ids_name_in_user_dll", lambda _old, _text: "1234")
    monkeypatch.setattr(main_window, "_find_universe_ini_write", lambda _game_path: uni_ini)
    monkeypatch.setattr(main_window, "_ensure_writable_path", lambda path: path)
    monkeypatch.setattr(main_window, "_faction_from_ui", lambda value: value)
    monkeypatch.setattr(main_window, "_load_universe", lambda game_path: universe_load_calls.append(str(game_path)))
    monkeypatch.setattr(main_window, "_load", lambda path: loaded_paths.append(str(path)))
    monkeypatch.setattr(main_window._parser, "parse", lambda path: [] if str(path) == str(uni_ini) else [])
    monkeypatch.setattr(main_window.browser, "highlight_current", lambda path: highlighted.append(str(path)))
    monkeypatch.setattr(
        main_window.browser,
        "set_game_path",
        lambda path, scan=True: set_game_path_calls.append((str(path), bool(scan))),
    )
    monkeypatch.setattr(main_window.browser, "set_system_name_map", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window.browser, "set_system_name_mode", lambda *_args, **_kwargs: None)

    main_window._create_system_at_pos(QPointF(100.0, 200.0))

    sys_file = universe_dir / "SYSTEMS" / "TE01" / "TE01.ini"

    assert universe_load_calls == []
    assert loaded_paths == [str(sys_file)]
    assert highlighted == [str(sys_file)]
    assert set_game_path_calls == [(str(tmp_path), True)]
    assert main_window._filepath == str(sys_file)
    assert sys_file.exists()


def test_place_connection_moves_to_destination_tab_with_pending_state(main_window, monkeypatch, tmp_path: Path):
    origin_path = tmp_path / "li01.ini"
    dest_path = tmp_path / "br01.ini"
    origin_path.write_text("", encoding="utf-8")
    dest_path.write_text("", encoding="utf-8")

    origin_key = main_window._system_tab_key(str(origin_path))
    origin_host = main_window._ensure_system_tab_host(origin_key)
    origin_idx = main_window._center_register_tab(origin_host.view, "LI01", origin_key, closable=True)
    main_window._center_tab_specs[origin_idx]["host_key"] = origin_host.key
    main_window._center_tab_specs[origin_idx]["path"] = str(origin_path)
    main_window._center_tab_specs[origin_idx]["document"] = main_window._system_document_factory(path=str(origin_path))
    main_window._center_current_tab_key = origin_key
    main_window._filepath = str(origin_path)
    main_window._scale = 1.0

    opened: list[tuple[str, bool]] = []
    writes: list[bool] = []

    def _fake_open(path: str, new_tab: bool = False):
        opened.append((path, new_tab))
        dest_key = main_window._system_tab_key(path)
        dest_idx = main_window._center_tab_index_for_key(dest_key)
        if dest_idx < 0:
            host = main_window._ensure_system_tab_host(dest_key)
            idx = main_window._center_register_tab(host.view, Path(path).stem.upper(), dest_key, closable=True)
            main_window._center_tab_specs[idx]["host_key"] = host.key
            main_window._center_tab_specs[idx]["path"] = str(path)
            main_window._center_tab_specs[idx]["document"] = main_window._system_document_factory(path=str(path))
        main_window._center_current_tab_key = dest_key
        main_window._filepath = str(path)

    monkeypatch.setattr(main_window, "_open_system_tab", _fake_open)
    monkeypatch.setattr(main_window, "_write_to_file", lambda reload=False: writes.append(bool(reload)) or main_window._set_dirty(False))
    monkeypatch.setattr(main_window, "_has_ids_resource_toolchain", lambda: False)
    monkeypatch.setattr(main_window.browser, "highlight_current", lambda _path: None)

    main_window._pending_conn = {
        "origin": str(origin_path),
        "origin_nick": "LI01",
        "dest": str(dest_path),
        "dest_nick": "BR01",
        "type": "Jump Hole",
        "phase": "origin",
        "gate_info": None,
        "ids_name_text": "",
    }

    main_window._place_connection(QPointF(100.0, 200.0))

    assert writes == [False]
    assert opened == [(str(dest_path), True)]
    assert main_window._filepath == str(dest_path)
    assert main_window._pending_conn is not None
    assert main_window._pending_conn["phase"] == "destination"
    dest_doc = main_window._center_system_tab_spec(main_window._system_tab_key(str(dest_path)))["document"]
    assert dest_doc.pending_conn["phase"] == "destination"


def test_place_connection_final_step_returns_to_origin_tab(main_window, monkeypatch, tmp_path: Path):
    origin_path = tmp_path / "li01.ini"
    dest_path = tmp_path / "br01.ini"
    origin_path.write_text("", encoding="utf-8")
    dest_path.write_text("", encoding="utf-8")

    for path in (origin_path, dest_path):
        key = main_window._system_tab_key(str(path))
        host = main_window._ensure_system_tab_host(key)
        idx = main_window._center_register_tab(host.view, Path(path).stem.upper(), key, closable=True)
        main_window._center_tab_specs[idx]["host_key"] = host.key
        main_window._center_tab_specs[idx]["path"] = str(path)
        main_window._center_tab_specs[idx]["document"] = main_window._system_document_factory(path=str(path))

    main_window._center_current_tab_key = main_window._system_tab_key(str(dest_path))
    main_window._filepath = str(dest_path)
    main_window._scale = 1.0

    opened: list[tuple[str, bool]] = []
    writes: list[bool] = []
    pathgen_calls: list[str] = []

    monkeypatch.setattr(main_window, "_write_to_file", lambda reload=False: writes.append(bool(reload)) or main_window._set_dirty(False))
    monkeypatch.setattr(main_window, "_has_ids_resource_toolchain", lambda: False)
    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_fallback_game_path", lambda: "")
    monkeypatch.setattr(main_window.browser, "highlight_current", lambda _path: None)

    def _fake_open(path: str, new_tab: bool = False):
        opened.append((path, new_tab))
        main_window._center_current_tab_key = main_window._system_tab_key(str(path))
        main_window._filepath = str(path)

    monkeypatch.setattr(main_window, "_open_system_tab", _fake_open)
    monkeypatch.setattr(
        "fl_editor.pathgen.regenerate_shortest_paths",
        lambda game_path, _parser, fallback_root=None: pathgen_calls.append(game_path) or "updated",
    )

    main_window._pending_conn = {
        "origin": str(origin_path),
        "origin_nick": "LI01",
        "dest": str(dest_path),
        "dest_nick": "BR01",
        "type": "Jump Hole",
        "phase": "destination",
        "gate_info": None,
        "ids_name_text": "",
    }

    main_window._place_connection(QPointF(300.0, 400.0))

    assert writes == [False]
    assert opened == [(str(origin_path), False)]
    assert main_window._filepath == str(origin_path)
    assert main_window._pending_conn is None
    assert pathgen_calls == [str(tmp_path)]


def test_create_base_at_pos_uses_loading_and_defers_3d_refresh(main_window, monkeypatch, tmp_path: Path):
    system_path = tmp_path / "li01.ini"
    system_path.write_text("", encoding="utf-8")
    main_window._filepath = str(system_path)
    main_window._scale = 1.0
    monkeypatch.setattr(main_window.view3d_switch, "isChecked", lambda: True)
    main_window._pending_base = {
        "game_path": str(tmp_path),
        "sys_nick": "LI01",
        "base_nickname": "Li01_Test_Base",
        "obj_nickname": "Li01_Test_Obj",
        "rooms": ["bar"],
        "start_room": "bar",
        "price_variance": 1.0,
        "ids_name_text": "",
        "ids_info_template_xml": "",
        "reputation": "li_n_grp",
        "archetype": "outpost",
        "bgcs_base_run_by": "",
        "loadout": "",
        "pilot": "",
        "voice": "",
        "space_costume": "",
    }

    loading_calls: list[tuple[bool, object]] = []
    add_calls: list[tuple[list[tuple[str, str]], str, bool]] = []
    refresh_calls: list[bool] = []
    write_calls: list[bool] = []
    message_calls: list[tuple[str, str]] = []
    universe_dir = tmp_path / "DATA" / "UNIVERSE"
    universe_dir.mkdir(parents=True)
    universe_ini = universe_dir / "universe.ini"
    universe_ini.write_text("", encoding="utf-8")

    monkeypatch.setattr(main_window, "_has_ids_resource_toolchain", lambda: False)
    monkeypatch.setattr(main_window, "_normalize_base_archetype", lambda _game_path, archetype: (archetype, False))
    monkeypatch.setattr(main_window, "_normalize_reputation_value", lambda value: value)
    monkeypatch.setattr(main_window, "_load_template_rooms", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(main_window, "_find_universe_ini_write", lambda _game_path: universe_ini)
    monkeypatch.setattr(main_window, "_ensure_mbase_entry_for_base", lambda **_kwargs: (False, ""))
    monkeypatch.setattr(main_window, "_room_customizations_have_npcs", lambda _cfg: False)
    monkeypatch.setattr(main_window, "_write_to_file", lambda reload=False: write_calls.append(bool(reload)))
    monkeypatch.setattr(main_window, "_refresh_3d_scene", lambda *args, **kwargs: refresh_calls.append(True))
    monkeypatch.setattr(main_window, "_set_loading_visible", lambda visible, message=None: loading_calls.append((bool(visible), message)))
    monkeypatch.setattr(
        main_window,
        "_add_object_from_entries",
        lambda entries, section_name, refresh_3d=True: add_calls.append((list(entries), section_name, bool(refresh_3d))),
    )
    monkeypatch.setattr("fl_editor.main_window.create_base_room_files", lambda **_kwargs: ["room created"])
    monkeypatch.setattr("fl_editor.main_window.write_base_ini", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "fl_editor.main_window.build_base_object_entries",
        lambda **_kwargs: [("nickname", "Li01_Test_Obj"), ("base", "Li01_Test_Base")],
    )
    monkeypatch.setattr(
        "fl_editor.main_window.build_universe_base_entries",
        lambda **_kwargs: [("nickname", "Li01_Test_Base")],
    )
    monkeypatch.setattr("fl_editor.main_window.append_ini_section_block", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(QMessageBox, "information", lambda _parent, title, text: message_calls.append((title, text)))

    main_window._create_base_at_pos(QPointF(100.0, 200.0))

    assert loading_calls[0][0] is True
    assert loading_calls[-1][0] is False
    assert add_calls == [([("nickname", "Li01_Test_Obj"), ("base", "Li01_Test_Base")], "Object", False)]
    assert write_calls == [False]
    assert refresh_calls == [True]
    assert message_calls


def test_base_builder_add_part_creates_parented_station_child_draft_only_until_save(main_window, monkeypatch, tmp_path: Path):
    scene = main_window.view._scene
    base_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_Obj"),
                ("archetype", "smallstation1"),
                ("base", "Li01_01_Base"),
                ("dock_with", "Li01_01_Base"),
                ("reputation", "li_p_grp"),
                ("pos", "10, 20, 30"),
                ("rotate", "0, -90, 0"),
            ],
            "nickname": "Li01_01_Base_Obj",
            "archetype": "smallstation1",
            "base": "Li01_01_Base",
            "dock_with": "Li01_01_Base",
            "reputation": "li_p_grp",
            "pos": "10, 20, 30",
            "rotate": "0, -90, 0",
        },
        main_window._scale,
    )
    scene.addItem(base_obj)
    main_window._objects = [base_obj]
    main_window._sections = []
    main_window._base_builder_active_base_nick = "Li01_01_Base"
    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_base_default_loadouts_from_solararch", lambda _path: {"smallstation1": "station_loadout"})
    monkeypatch.setattr(main_window, "_refresh_3d_scene", lambda: None)

    main_window._initialize_base_builder_draft("Li01_01_Base", base_obj)

    entry = ModelViewerEntry(
        category_key="stations",
        category_label="Stations",
        nickname="smallstation1",
        display_name="Small Station",
        archetype="smallstation1",
        da_archetype="solar\\smallstation1.cmp",
        model_path=tmp_path / "smallstation1.cmp",
        source_ini_path=tmp_path / "solararch.ini",
        source_section="Solar",
    )

    main_window._base_builder_add_part("Li01_01_Base", entry)

    assert len(main_window._objects) == 1
    assert len(main_window._base_builder_draft_parts) == 1
    child = main_window._base_builder_draft_parts[-1]
    assert child.data.get("parent") == "Li01_01_Base"
    assert child.data.get("reputation") == "li_p_grp"
    assert child.data.get("loadout") == "station_loadout"
    assert child.data.get("base", "") == ""
    assert child.data.get("dock_with", "") == ""
    assert child.data.get("pos") != base_obj.data.get("pos")
    assert main_window._base_builder_selected_object is child


def test_base_builder_save_commits_draft_parts_to_scene(main_window, monkeypatch, tmp_path: Path):
    scene = main_window.view._scene
    base_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_Obj"),
                ("archetype", "smallstation1"),
                ("base", "Li01_01_Base"),
                ("dock_with", "Li01_01_Base"),
                ("reputation", "li_p_grp"),
                ("pos", "10, 20, 30"),
                ("rotate", "0, -90, 0"),
            ],
            "nickname": "Li01_01_Base_Obj",
            "archetype": "smallstation1",
            "base": "Li01_01_Base",
            "dock_with": "Li01_01_Base",
            "reputation": "li_p_grp",
            "pos": "10, 20, 30",
            "rotate": "0, -90, 0",
        },
        main_window._scale,
    )
    scene.addItem(base_obj)
    main_window._objects = [base_obj]
    main_window._sections = [("Object", list(base_obj.data.get("_entries", [])))]
    main_window._filepath = str(tmp_path / "li01.ini")
    main_window._base_builder_active_base_nick = "Li01_01_Base"

    write_calls: list[bool] = []
    refresh_calls: list[tuple[bool, bool]] = []
    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_base_default_loadouts_from_solararch", lambda _path: {"smallstation1": "station_loadout"})
    monkeypatch.setattr(main_window, "_write_to_file", lambda reload=False: write_calls.append(bool(reload)))
    monkeypatch.setattr(
        main_window,
        "_refresh_3d_scene",
        lambda force=False, preserve_camera=False: refresh_calls.append((bool(force), bool(preserve_camera))),
    )

    main_window._initialize_base_builder_draft("Li01_01_Base", base_obj)

    entry = ModelViewerEntry(
        category_key="stations",
        category_label="Stations",
        nickname="smallstation1",
        display_name="Small Station",
        archetype="smallstation1",
        da_archetype="solar\\smallstation1.cmp",
        model_path=tmp_path / "smallstation1.cmp",
        source_ini_path=tmp_path / "solararch.ini",
        source_section="Solar",
    )

    main_window._base_builder_add_part("Li01_01_Base", entry)
    main_window._base_builder_save()

    assert len(main_window._objects) == 2
    child = main_window._objects[-1]
    assert child.data.get("parent") == "Li01_01_Base"
    assert child.data.get("loadout") == "station_loadout"
    assert write_calls == [False]
    assert refresh_calls == [(False, True)]
    assert main_window._base_builder_has_unsaved_changes() is False
    assert len(main_window._base_builder_history_rows()) == 2


def test_base_builder_undo_removes_last_added_draft_part(main_window, monkeypatch, tmp_path: Path):
    scene = main_window.view._scene
    base_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_Obj"),
                ("archetype", "smallstation1"),
                ("base", "Li01_01_Base"),
                ("dock_with", "Li01_01_Base"),
            ],
            "nickname": "Li01_01_Base_Obj",
            "archetype": "smallstation1",
            "base": "Li01_01_Base",
            "dock_with": "Li01_01_Base",
        },
        main_window._scale,
    )
    scene.addItem(base_obj)
    main_window._objects = [base_obj]
    main_window._sections = []
    main_window._base_builder_active_base_nick = "Li01_01_Base"

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_base_default_loadouts_from_solararch", lambda _path: {})

    main_window._initialize_base_builder_draft("Li01_01_Base", base_obj)

    entry = ModelViewerEntry(
        category_key="stations",
        category_label="Stations",
        nickname="smallstation1",
        display_name="Small Station",
        archetype="smallstation1",
        da_archetype="solar\\smallstation1.cmp",
        model_path=tmp_path / "smallstation1.cmp",
        source_ini_path=tmp_path / "solararch.ini",
        source_section="Solar",
    )

    main_window._base_builder_add_part("Li01_01_Base", entry)

    assert len(main_window._base_builder_draft_parts) == 1
    assert main_window._base_builder_has_unsaved_changes() is True
    assert len(main_window._base_builder_history_rows()) == 2

    assert main_window._base_builder_undo() is True

    assert len(main_window._base_builder_draft_parts) == 0
    assert main_window._base_builder_has_unsaved_changes() is False
    history_rows = main_window._base_builder_history_rows()
    assert len(history_rows) == 2
    assert history_rows[0]["is_current"] is True


def test_base_builder_undo_restores_previous_draft_transform(main_window, monkeypatch):
    scene = main_window.view._scene
    base_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_Obj"),
                ("archetype", "smallstation1"),
                ("base", "Li01_01_Base"),
                ("dock_with", "Li01_01_Base"),
            ],
            "nickname": "Li01_01_Base_Obj",
            "archetype": "smallstation1",
            "base": "Li01_01_Base",
            "dock_with": "Li01_01_Base",
        },
        main_window._scale,
    )
    child_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_part_001"),
                ("archetype", "smallstation1"),
                ("parent", "Li01_01_Base"),
                ("pos", "10, 20, 30"),
                ("rotate", "0, 0, 0"),
            ],
            "nickname": "Li01_01_Base_part_001",
            "archetype": "smallstation1",
            "parent": "Li01_01_Base",
            "pos": "10, 20, 30",
            "rotate": "0, 0, 0",
        },
        main_window._scale,
    )
    scene.addItem(base_obj)
    scene.addItem(child_obj)
    main_window._objects = [base_obj, child_obj]
    main_window._sections = [
        ("Object", list(base_obj.data["_entries"])),
        ("Object", list(child_obj.data["_entries"])),
    ]
    main_window._base_builder_active_base_nick = "Li01_01_Base"
    main_window._initialize_base_builder_draft("Li01_01_Base", child_obj)

    draft_child = main_window._base_builder_selected_part()
    assert draft_child is not None
    assert main_window._base_builder_begin_transform("move", "x")
    main_window._base_builder_apply_transform_delta(2.0)
    main_window._base_builder_end_transform(True)

    assert draft_child.data["pos"] == "22.00, 20.00, 30.00"
    assert main_window._base_builder_has_unsaved_changes() is True

    assert main_window._base_builder_undo() is True

    restored_child = main_window._base_builder_selected_part()
    assert restored_child is not None
    assert restored_child.data["pos"] == "10, 20, 30"
    assert main_window._base_builder_has_unsaved_changes() is False


def test_base_builder_add_part_skips_main_3d_refresh_when_builder_dialog_is_active(main_window, monkeypatch, tmp_path: Path):
    scene = main_window.view._scene
    base_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_Obj"),
                ("archetype", "smallstation1"),
                ("base", "Li01_01_Base"),
                ("dock_with", "Li01_01_Base"),
            ],
            "nickname": "Li01_01_Base_Obj",
            "archetype": "smallstation1",
            "base": "Li01_01_Base",
            "dock_with": "Li01_01_Base",
        },
        main_window._scale,
    )
    scene.addItem(base_obj)
    main_window._objects = [base_obj]
    main_window._sections = []
    main_window._base_builder_active_base_nick = "Li01_01_Base"

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_base_default_loadouts_from_solararch", lambda _path: {})

    refresh_calls: list[tuple[bool, bool]] = []
    monkeypatch.setattr(
        main_window,
        "_refresh_3d_scene",
        lambda force=False, preserve_camera=False: refresh_calls.append((bool(force), bool(preserve_camera))),
    )

    class _FakeDialog:
        def refresh_existing_parts(self):
            return None

        def set_selected_scene_object(self, **_kwargs):
            return None

    monkeypatch.setattr(main_window_module, "isValid", lambda _obj: True)
    main_window._base_builder_dialog = _FakeDialog()
    main_window._initialize_base_builder_draft("Li01_01_Base", base_obj)

    entry = ModelViewerEntry(
        category_key="stations",
        category_label="Stations",
        nickname="shipyard_component",
        display_name="Shipyard Component",
        archetype="shipyard_component",
        da_archetype="solar\\shipyard_component.cmp",
        model_path=tmp_path / "shipyard_component.cmp",
        source_ini_path=tmp_path / "solararch.ini",
        source_section="Solar",
    )

    main_window._base_builder_add_part("Li01_01_Base", entry)

    assert refresh_calls == []


def test_sync_view3d_selected_native_scene_data_skips_active_base_builder_selection(main_window, monkeypatch):
    base_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_Obj"),
                ("archetype", "smallstation1"),
                ("base", "Li01_01_Base"),
            ],
            "nickname": "Li01_01_Base_Obj",
            "archetype": "smallstation1",
            "base": "Li01_01_Base",
        },
        main_window._scale,
    )
    child_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_part_001"),
                ("archetype", "shipyard_component"),
                ("parent", "Li01_01_Base"),
            ],
            "nickname": "Li01_01_Base_part_001",
            "archetype": "shipyard_component",
            "parent": "Li01_01_Base",
        },
        main_window._scale,
    )
    main_window._objects = [base_obj, child_obj]
    main_window._selected = child_obj
    main_window._base_builder_active_base_nick = "Li01_01_Base"
    monkeypatch.setattr(main_window.view3d_switch, "isChecked", lambda: True)

    selected_calls: list[tuple[object, object]] = []
    refresh_calls: list[str] = []

    monkeypatch.setattr(main_window, "_native_model_path_for_object", lambda _obj: Path("/tmp/shipyard_component.cmp"))
    monkeypatch.setattr(main_window, "_on_native_scene_runtime_event", lambda event: refresh_calls.append(str(event.kind)))
    monkeypatch.setattr(main_window.view3d, "set_selected_native_scene_data", lambda obj, data: selected_calls.append((obj, data)))
    monkeypatch.setattr(main_window.view3d, "refresh_native_scene_previews", lambda: refresh_calls.append("refresh"))

    main_window._sync_view3d_selected_native_scene_data()

    assert selected_calls == [(child_obj, None)]
    assert "sync_skipped_base_builder_selection" in refresh_calls
    assert "refresh" not in refresh_calls


def test_refresh_base_builder_dialog_state_preserves_camera_on_scene_refresh(main_window, monkeypatch):
    base_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_Obj"),
                ("archetype", "smallstation1"),
                ("base", "Li01_01_Base"),
                ("dock_with", "Li01_01_Base"),
            ],
            "nickname": "Li01_01_Base_Obj",
            "archetype": "smallstation1",
            "base": "Li01_01_Base",
            "dock_with": "Li01_01_Base",
        },
        main_window._scale,
    )
    child_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_part_001"),
                ("archetype", "smallstation1"),
                ("parent", "Li01_01_Base"),
            ],
            "nickname": "Li01_01_Base_part_001",
            "archetype": "smallstation1",
            "parent": "Li01_01_Base",
        },
        main_window._scale,
    )
    main_window._objects = [base_obj, child_obj]
    main_window._selected = child_obj
    main_window._base_builder_active_base_nick = "Li01_01_Base"

    calls: list[tuple[str, object]] = []

    class _FakeDialog:
        def refresh_existing_parts(self):
            calls.append(("refresh", None))

        def set_selected_scene_object(self, **kwargs):
            calls.append(("selected", kwargs.get("scene_object")))

        def center_on_object(self, obj):
            calls.append(("center", obj))

    monkeypatch.setattr(main_window_module, "isValid", lambda _obj: True)
    main_window._base_builder_dialog = _FakeDialog()

    main_window._refresh_base_builder_dialog_state(refresh_parts=True)

    assert ("refresh", None) in calls
    assert ("selected", child_obj) in calls
    assert not any(name == "center" for name, _payload in calls)


def test_refresh_base_builder_dialog_state_does_not_recenter_on_selection(main_window, monkeypatch):
    child_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_part_001"),
                ("archetype", "smallstation1"),
                ("parent", "Li01_01_Base"),
            ],
            "nickname": "Li01_01_Base_part_001",
            "archetype": "smallstation1",
            "parent": "Li01_01_Base",
        },
        main_window._scale,
    )
    main_window._objects = [child_obj]
    main_window._selected = child_obj
    main_window._base_builder_active_base_nick = "Li01_01_Base"

    calls: list[tuple[str, object]] = []

    class _FakeDialog:
        def set_selected_scene_object(self, **kwargs):
            calls.append(("selected", kwargs.get("scene_object")))

        def center_on_object(self, obj):
            calls.append(("center", obj))

    monkeypatch.setattr(main_window_module, "isValid", lambda _obj: True)
    main_window._base_builder_dialog = _FakeDialog()

    main_window._refresh_base_builder_dialog_state(refresh_parts=False)

    assert ("selected", child_obj) in calls
    assert not any(name == "center" for name, _payload in calls)


def test_apply_group_visibility_keeps_base_builder_children_visible_without_active_builder(main_window):
    scene = main_window.view._scene
    base_obj = SolarObject(
        {
            "_entries": [("nickname", "Li01_01_Base_Obj"), ("archetype", "smallstation1"), ("base", "Li01_01_Base")],
            "nickname": "Li01_01_Base_Obj",
            "archetype": "smallstation1",
            "base": "Li01_01_Base",
        },
        main_window._scale,
    )
    child_obj = SolarObject(
        {
            "_entries": [("nickname", "Li01_01_Base_part_001"), ("archetype", "smallstation1"), ("parent", "Li01_01_Base")],
            "nickname": "Li01_01_Base_part_001",
            "archetype": "smallstation1",
            "parent": "Li01_01_Base",
        },
        main_window._scale,
    )
    other_base_obj = SolarObject(
        {
            "_entries": [("nickname", "Li01_02_Base_Obj"), ("archetype", "smallstation1"), ("base", "Li01_02_Base")],
            "nickname": "Li01_02_Base_Obj",
            "archetype": "smallstation1",
            "base": "Li01_02_Base",
        },
        main_window._scale,
    )
    scene.addItem(base_obj)
    scene.addItem(child_obj)
    scene.addItem(other_base_obj)
    main_window._objects = [base_obj, child_obj, other_base_obj]

    main_window._base_builder_active_base_nick = None
    main_window._apply_group_visibility()

    assert base_obj.isVisible()
    assert child_obj.isVisible()
    assert other_base_obj.isVisible()

    main_window._base_builder_active_base_nick = "Li01_01_Base"
    main_window._apply_group_visibility()

    assert base_obj.isVisible()
    assert child_obj.isVisible()
    assert not other_base_obj.isVisible()


def test_object_combo_groups_base_builder_children_under_root(main_window):
    base_obj = SolarObject(
        {
            "_entries": [("nickname", "Li01_01_Base_Obj"), ("archetype", "smallstation1"), ("base", "Li01_01_Base")],
            "nickname": "Li01_01_Base_Obj",
            "archetype": "smallstation1",
            "base": "Li01_01_Base",
        },
        main_window._scale,
    )
    child_obj = SolarObject(
        {
            "_entries": [("nickname", "Li01_01_Base_part_001"), ("archetype", "smallstation1"), ("parent", "Li01_01_Base")],
            "nickname": "Li01_01_Base_part_001",
            "archetype": "smallstation1",
            "parent": "Li01_01_Base",
        },
        main_window._scale,
    )
    other_obj = SolarObject(
        {
            "_entries": [("nickname", "Li01_Tradelane_Ring"), ("archetype", "tradelane_ring")],
            "nickname": "Li01_Tradelane_Ring",
            "archetype": "tradelane_ring",
        },
        main_window._scale,
    )
    main_window._objects = [base_obj, child_obj, other_obj]
    main_window._zones = []

    main_window._rebuild_object_combo()

    labels = [main_window.obj_combo.itemText(index) for index in range(main_window.obj_combo.count())]
    assert any("Li01_01_Base_Obj" in label and "(+1 parts)" in label for label in labels)
    assert len(labels) == 2

    group_index = next(index for index, label in enumerate(labels) if "(+1 parts)" in label)
    tooltip = str(main_window.obj_combo.itemData(group_index, Qt.ToolTipRole) or "")
    assert "Multipart base: Li01_01_Base_Obj" in tooltip
    assert "Li01_01_Base_part_001" in tooltip

    main_window._selected = child_obj
    main_window._sync_obj_combo_to_selection()

    assert main_window.obj_combo.currentData() is base_obj


def test_apply_viewer_text_visibility_hides_2d_labels_for_child_objects(main_window):
    base_obj = SolarObject(
        {
            "_entries": [("nickname", "Li01_01_Base_Obj"), ("archetype", "smallstation1"), ("base", "Li01_01_Base")],
            "nickname": "Li01_01_Base_Obj",
            "archetype": "smallstation1",
            "base": "Li01_01_Base",
        },
        main_window._scale,
    )
    child_obj = SolarObject(
        {
            "_entries": [("nickname", "Li01_01_Base_part_001"), ("archetype", "smallstation1"), ("parent", "Li01_01_Base")],
            "nickname": "Li01_01_Base_part_001",
            "archetype": "smallstation1",
            "parent": "Li01_01_Base",
        },
        main_window._scale,
    )
    main_window._filepath = "C:/tmp/li01.ini"
    main_window._objects = [base_obj, child_obj]
    main_window._viewer_text_visible = True

    main_window._apply_viewer_text_visibility()

    assert base_obj.label is not None and base_obj.label.isVisible() is True
    assert child_obj.label is not None and child_obj.label.isVisible() is False


def test_on_2d_object_selected_redirects_child_object_to_parent_root(main_window, monkeypatch):
    base_obj = SolarObject(
        {
            "_entries": [("nickname", "Br04_02"), ("archetype", "space_factory01"), ("base", "Br04_02_Base")],
            "nickname": "Br04_02",
            "archetype": "space_factory01",
            "base": "Br04_02_Base",
        },
        main_window._scale,
    )
    child_obj = SolarObject(
        {
            "_entries": [("nickname", "Br04_space_tankl4_2"), ("archetype", "space_tankl4"), ("parent", "Br04_02")],
            "nickname": "Br04_space_tankl4_2",
            "archetype": "space_tankl4",
            "parent": "Br04_02",
        },
        main_window._scale,
    )
    main_window._objects = [base_obj, child_obj]
    calls: list[object] = []
    monkeypatch.setattr(main_window, "_select", lambda obj: calls.append(obj))

    main_window._on_2d_object_selected(child_obj)

    assert calls == [base_obj]


def test_resolve_system_view_native_scene_data_for_object_combines_base_and_child_geometry(main_window, monkeypatch):
    base_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_Obj"),
                ("archetype", "smallstation1"),
                ("base", "Li01_01_Base"),
                ("pos", "0, 0, 0"),
            ],
            "nickname": "Li01_01_Base_Obj",
            "archetype": "smallstation1",
            "base": "Li01_01_Base",
            "pos": "0, 0, 0",
        },
        main_window._scale,
    )
    child_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_part_001"),
                ("archetype", "smallstation1"),
                ("parent", "Li01_01_Base"),
                ("pos", "10, 0, 0"),
            ],
            "nickname": "Li01_01_Base_part_001",
            "archetype": "smallstation1",
            "parent": "Li01_01_Base",
            "pos": "10, 0, 0",
        },
        main_window._scale,
    )
    main_window._objects = [base_obj, child_obj]

    def _scene_data(tag: str) -> NativePreviewSceneData:
        geometry = NativePreviewGeometry(
            model_name=tag,
            level_name=None,
            part_name=tag,
            group_start=0,
            group_count=1,
            positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
            indices=(0, 1, 2),
            vertex_stride=12,
            index_size=2,
            confidence="exact",
            bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(1.0, 1.0, 0.0), radius=1.0),
        )
        return NativePreviewSceneData(
            geometries=(geometry,),
            primary_geometry=geometry,
            bounds=geometry.bounds,
            part_names=(tag,),
            texture_path=None,
            geometry_texture_paths=(None,),
            all_geometries=(geometry,),
            all_geometry_texture_paths=(None,),
        )

    monkeypatch.setattr(
        main_window,
        "_resolve_native_scene_data_for_object",
        lambda obj: _scene_data("base") if obj is base_obj else (_scene_data("child") if obj is child_obj else None),
    )

    scene_data = main_window._resolve_system_view_native_scene_data_for_object(base_obj)

    assert scene_data is not None
    assert len(scene_data.geometries) == 2
    assert (10.0, 0.0, 0.0) in scene_data.geometries[1].positions
    assert scene_data.part_names == ("Li01_01_Base_Obj", "Li01_01_Base_part_001")


def test_resolve_system_view_native_scene_data_for_child_object_keeps_single_object_geometry(main_window, monkeypatch):
    base_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_Obj"),
                ("archetype", "smallstation1"),
                ("base", "Li01_01_Base"),
            ],
            "nickname": "Li01_01_Base_Obj",
            "archetype": "smallstation1",
            "base": "Li01_01_Base",
        },
        main_window._scale,
    )
    child_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_part_001"),
                ("archetype", "smallstation1"),
                ("parent", "Li01_01_Base"),
            ],
            "nickname": "Li01_01_Base_part_001",
            "archetype": "smallstation1",
            "parent": "Li01_01_Base",
        },
        main_window._scale,
    )
    main_window._objects = [base_obj, child_obj]

    child_scene_data = NativePreviewSceneData(
        geometries=(),
        primary_geometry=None,
        bounds=None,
        part_names=("child",),
        texture_path=None,
        geometry_texture_paths=(),
        all_geometries=(),
        all_geometry_texture_paths=(),
    )

    monkeypatch.setattr(
        main_window,
        "_resolve_native_scene_data_for_object",
        lambda obj: child_scene_data if obj is child_obj else None,
    )

    assert main_window._resolve_system_view_native_scene_data_for_object(child_obj) is child_scene_data


def test_base_builder_move_transform_updates_selected_child_and_commits(main_window, monkeypatch):
    scene = main_window.view._scene
    child_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_part_001"),
                ("archetype", "smallstation1"),
                ("parent", "Li01_01_Base"),
                ("pos", "10, 20, 30"),
                ("rotate", "0, 0, 0"),
            ],
            "nickname": "Li01_01_Base_part_001",
            "archetype": "smallstation1",
            "parent": "Li01_01_Base",
            "pos": "10, 20, 30",
            "rotate": "0, 0, 0",
        },
        main_window._scale,
    )
    scene.addItem(child_obj)
    main_window._objects = [child_obj]
    main_window._sections = [("Object", list(child_obj.data["_entries"]))]
    main_window._base_builder_active_base_nick = "Li01_01_Base"
    main_window._selected = child_obj

    undo_actions: list[dict] = []
    write_calls: list[bool] = []
    monkeypatch.setattr(main_window, "_push_undo_action", lambda action: undo_actions.append(action))
    monkeypatch.setattr(main_window, "_write_to_file", lambda reload=False: write_calls.append(bool(reload)))
    monkeypatch.setattr(main_window, "_append_change_log", lambda _line: None)
    monkeypatch.setattr(main_window.view3d, "update_object_position", lambda *_args, **_kwargs: None)

    assert main_window._base_builder_begin_transform("move", "x")
    main_window._base_builder_apply_transform_delta(2.0)
    main_window._base_builder_end_transform(True)

    assert child_obj.data["pos"] == "22.00, 20.00, 30.00"
    assert undo_actions and undo_actions[0]["type"] == "edit_object"
    assert write_calls == [False]


def test_base_builder_rotate_transform_updates_selected_child(main_window, monkeypatch):
    scene = main_window.view._scene
    child_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_part_001"),
                ("archetype", "smallstation1"),
                ("parent", "Li01_01_Base"),
                ("pos", "10, 20, 30"),
                ("rotate", "0, 0, 0"),
            ],
            "nickname": "Li01_01_Base_part_001",
            "archetype": "smallstation1",
            "parent": "Li01_01_Base",
            "pos": "10, 20, 30",
            "rotate": "0, 0, 0",
        },
        main_window._scale,
    )
    scene.addItem(child_obj)
    main_window._objects = [child_obj]
    main_window._sections = [("Object", list(child_obj.data["_entries"]))]
    main_window._base_builder_active_base_nick = "Li01_01_Base"
    main_window._selected = child_obj

    monkeypatch.setattr(main_window, "_push_undo_action", lambda _action: None)
    monkeypatch.setattr(main_window, "_write_to_file", lambda reload=False: None)
    monkeypatch.setattr(main_window, "_append_change_log", lambda _line: None)
    monkeypatch.setattr(main_window.view3d, "update_object_rotation", lambda *_args, **_kwargs: None)

    assert main_window._base_builder_begin_transform("rotate", "y")
    main_window._base_builder_apply_transform_delta(10.0)
    main_window._base_builder_end_transform(True)

    assert child_obj.data["rotate"] == "0, 2, 0"


def test_base_builder_move_transform_shift_modifier_enables_fine_control(main_window, monkeypatch):
    scene = main_window.view._scene
    child_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_part_001"),
                ("archetype", "smallstation1"),
                ("parent", "Li01_01_Base"),
                ("pos", "10, 20, 30"),
                ("rotate", "0, 0, 0"),
            ],
            "nickname": "Li01_01_Base_part_001",
            "archetype": "smallstation1",
            "parent": "Li01_01_Base",
            "pos": "10, 20, 30",
            "rotate": "0, 0, 0",
        },
        main_window._scale,
    )
    scene.addItem(child_obj)
    main_window._objects = [child_obj]
    main_window._sections = [("Object", list(child_obj.data["_entries"]))]
    main_window._base_builder_active_base_nick = "Li01_01_Base"
    main_window._selected = child_obj

    monkeypatch.setattr(main_window_module.QApplication, "keyboardModifiers", staticmethod(lambda: Qt.ShiftModifier))
    monkeypatch.setattr(main_window.view3d, "update_object_position", lambda *_args, **_kwargs: None)

    assert main_window._base_builder_begin_transform("move", "x")
    main_window._base_builder_apply_transform_delta(2.0)

    assert child_obj.data["pos"] == "13.00, 20.00, 30.00"


def test_base_builder_rotate_transform_ctrl_modifier_snaps_to_five_degrees(main_window, monkeypatch):
    scene = main_window.view._scene
    child_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_part_001"),
                ("archetype", "smallstation1"),
                ("parent", "Li01_01_Base"),
                ("pos", "10, 20, 30"),
                ("rotate", "0, 0, 0"),
            ],
            "nickname": "Li01_01_Base_part_001",
            "archetype": "smallstation1",
            "parent": "Li01_01_Base",
            "pos": "10, 20, 30",
            "rotate": "0, 0, 0",
        },
        main_window._scale,
    )
    scene.addItem(child_obj)
    main_window._objects = [child_obj]
    main_window._sections = [("Object", list(child_obj.data["_entries"]))]
    main_window._base_builder_active_base_nick = "Li01_01_Base"
    main_window._selected = child_obj

    monkeypatch.setattr(main_window_module.QApplication, "keyboardModifiers", staticmethod(lambda: Qt.ControlModifier))
    monkeypatch.setattr(main_window.view3d, "update_object_rotation", lambda *_args, **_kwargs: None)

    assert main_window._base_builder_begin_transform("rotate", "y")
    main_window._base_builder_apply_transform_delta(10.0)

    assert child_obj.data["rotate"] == "0, 5, 0"


def test_open_base_builder_wires_dedicated_3d_scene_provider(main_window, monkeypatch, tmp_path: Path):
    scene = main_window.view._scene
    base_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_Obj"),
                ("archetype", "smallstation1"),
                ("base", "Li01_01_Base"),
                ("dock_with", "Li01_01_Base"),
            ],
            "nickname": "Li01_01_Base_Obj",
            "archetype": "smallstation1",
            "base": "Li01_01_Base",
            "dock_with": "Li01_01_Base",
        },
        main_window._scale,
    )
    child_obj = SolarObject(
        {
            "_entries": [
                ("nickname", "Li01_01_Base_part_001"),
                ("archetype", "smallstation1"),
                ("parent", "Li01_01_Base"),
            ],
            "nickname": "Li01_01_Base_part_001",
            "archetype": "smallstation1",
            "parent": "Li01_01_Base",
        },
        main_window._scale,
    )
    scene.addItem(base_obj)
    scene.addItem(child_obj)
    main_window._objects = [base_obj, child_obj]
    main_window._selected = base_obj

    entry = ModelViewerEntry(
        category_key="stations",
        category_label="Stations",
        nickname="smallstation1",
        display_name="Small Station",
        archetype="smallstation1",
        da_archetype="solar\\smallstation1.cmp",
        model_path=tmp_path / "smallstation1.cmp",
        source_ini_path=tmp_path / "solararch.ini",
        source_section="Solar",
    )
    monkeypatch.setattr(main_window, "_collect_base_builder_part_entries", lambda: [entry])
    monkeypatch.setattr(main_window, "_apply_group_visibility", lambda: None)
    monkeypatch.setattr(main_window, "_refresh_base_builder_dialog_state", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_select", lambda _obj: None)

    captured: dict[str, object] = {}

    class _FakeDialog:
        def __init__(self, *_args, **kwargs):
            captured.update(kwargs)

        def show(self):
            return None

        def raise_(self):
            return None

        def activateWindow(self):
            return None

    monkeypatch.setattr(main_window_module, "BaseBuilderDialog", _FakeDialog)

    main_window._open_base_builder_for_object(base_obj)

    assert callable(captured["scene_payload_provider"])
    objects, zones, scale = captured["scene_payload_provider"]()
    assert [obj.nickname for obj in objects] == [base_obj.nickname, child_obj.nickname]
    assert objects[0] is not base_obj
    assert objects[1] is not child_obj
    assert zones == []
    assert scale == main_window._scale
    assert callable(captured["existing_parts_provider"])
    existing_rows = captured["existing_parts_provider"]()
    assert existing_rows == [{"nickname": "Li01_01_Base_part_001", "label": child_obj.nickname, "archetype": "smallstation1"}]
    assert callable(captured["configure_3d_view_callback"])
    assert callable(captured["select_existing_part_callback"])

    calls: list[tuple[str, object]] = []

    class _FakeView3D:
        def set_native_scene_resolver(self, value):
            calls.append(("native_scene_resolver", value))

        def set_native_scene_prepared_payload_resolver(self, value):
            calls.append(("native_scene_prepared_payload_resolver", value))

        def set_preview_mesh_resolver(self, value):
            calls.append(("preview_mesh_resolver", value))

        def set_planet_texture_resolver(self, value):
            calls.append(("planet_texture_resolver", value))

        def set_planet_cloud_texture_resolver(self, value):
            calls.append(("planet_cloud_texture_resolver", value))

        def set_planet_ring_resolver(self, value):
            calls.append(("planet_ring_resolver", value))

        def set_native_preview_max_distance_fl(self, value):
            calls.append(("max_distance", value))

        def set_native_preview_high_quality_distance_fl(self, value):
            calls.append(("hq_distance", value))

        def set_native_wireframe_visible(self, value):
            calls.append(("wireframe", value))

        def set_reference_overlay_visible(self, value):
            calls.append(("reference_overlay", value))

        def set_label_visibility(self, value):
            calls.append(("labels", value))

        def set_max_orbit_distance_scene(self, value):
            calls.append(("max_orbit", value))

    captured["configure_3d_view_callback"](_FakeView3D())

    assert ("native_scene_resolver", main_window._resolve_native_scene_data_for_object) in calls
    assert (
        "native_scene_prepared_payload_resolver",
        main_window._resolve_native_scene_prepared_payload_for_object,
    ) in calls
    assert ("max_distance", -1.0) in calls
    assert ("hq_distance", 1000000.0) in calls
    assert ("wireframe", True) in calls
    assert ("reference_overlay", False) in calls
    assert ("labels", False) in calls
    assert ("max_orbit", 3500.0) in calls


def test_base_builder_sidebar_button_opens_for_child_selection(main_window, monkeypatch):
    base_obj = SolarObject(
        {
            "nickname": "Li01_01_Base_Obj",
            "archetype": "smallstation1",
            "base": "Li01_01_Base",
            "dock_with": "Li01_01_Base",
            "_entries": [
                ("nickname", "Li01_01_Base_Obj"),
                ("archetype", "smallstation1"),
                ("base", "Li01_01_Base"),
                ("dock_with", "Li01_01_Base"),
            ],
        },
        main_window._scale,
    )
    child_obj = SolarObject(
        {
            "nickname": "Li01_01_Base_part_001",
            "archetype": "smallstation1",
            "parent": "Li01_01_Base",
            "_entries": [
                ("nickname", "Li01_01_Base_part_001"),
                ("archetype", "smallstation1"),
                ("parent", "Li01_01_Base"),
            ],
        },
        main_window._scale,
    )
    main_window._objects = [base_obj, child_obj]
    main_window._selected = child_obj

    opened: list[SolarObject | None] = []
    monkeypatch.setattr(main_window, "_open_base_builder_for_object", lambda obj=None: opened.append(obj))

    main_window._refresh_editing_action_states()

    assert main_window.base_builder_btn.isEnabled()

    main_window.base_builder_btn.click()

    assert opened == [None]


def test_show_base_related_3d_preview_uses_dedicated_preview_view(main_window, monkeypatch):
    obj = SolarObject(
        {
            "nickname": "li01_01_base_obj",
            "archetype": "smallstation1",
            "base": "Li01_01_Base",
            "dock_with": "Li01_01_Base",
            "_entries": [
                ("nickname", "li01_01_base_obj"),
                ("archetype", "smallstation1"),
                ("base", "Li01_01_Base"),
                ("dock_with", "Li01_01_Base"),
            ],
        },
        1.0,
    )
    child = SolarObject(
        {
            "nickname": "li01_01_base_part_001",
            "archetype": "smallstation1",
            "parent": "Li01_01_Base",
            "_entries": [
                ("nickname", "li01_01_base_part_001"),
                ("archetype", "smallstation1"),
                ("parent", "Li01_01_Base"),
            ],
        },
        1.0,
    )
    main_window._objects = [obj, child]

    calls: list[tuple[str, object]] = []

    class _FakePreviewView(QWidget):
        def __init__(self):
            super().__init__()

        def set_native_scene_resolver(self, value):
            calls.append(("native_scene_resolver", value))

        def set_native_scene_prepared_payload_resolver(self, value):
            calls.append(("native_scene_prepared_payload_resolver", value))

        def set_preview_mesh_resolver(self, value):
            calls.append(("preview_mesh_resolver", value))

        def set_planet_texture_resolver(self, value):
            calls.append(("planet_texture_resolver", value))

        def set_planet_cloud_texture_resolver(self, value):
            calls.append(("planet_cloud_texture_resolver", value))

        def set_planet_ring_resolver(self, value):
            calls.append(("planet_ring_resolver", value))

        def set_native_preview_max_distance_fl(self, value):
            calls.append(("max_distance", value))

        def set_native_preview_high_quality_distance_fl(self, value):
            calls.append(("hq_distance", value))

        def set_native_wireframe_visible(self, value):
            calls.append(("wireframe", value))

        def set_reference_overlay_visible(self, value):
            calls.append(("reference_overlay", value))

        def set_label_visibility(self, value):
            calls.append(("labels", value))

        def set_max_orbit_distance_scene(self, value):
            calls.append(("max_orbit", value))

        def set_data(self, objects, zones, scale):
            calls.append(("set_data", (objects, zones, scale)))

        def set_selected(self, current_obj):
            calls.append(("set_selected", current_obj))

        def center_on_item(self, current_obj):
            calls.append(("center_on_item", current_obj))

        def clear_scene(self):
            calls.append(("clear_scene", True))

    monkeypatch.setattr(main_window_module, "BaseAssemblyPreviewView", _FakePreviewView)
    monkeypatch.setattr(QDialog, "exec", lambda _dialog: 0)

    assert main_window._show_base_related_3d_preview(obj, "Li01_01_Base") is True
    assert ("native_scene_resolver", main_window._resolve_native_scene_data_for_object) in calls
    assert ("set_data", ([obj, child], [], main_window._scale)) in calls
    assert ("set_selected", obj) in calls
    assert ("center_on_item", obj) in calls
    assert ("wireframe", True) in calls


def test_build_system_editor_host_uses_composite_system_view_resolvers(main_window, monkeypatch):
    calls: list[tuple[str, object]] = []

    class _Signal:
        def connect(self, _callback):
            return None

    class _FakeView3D:
        def __init__(self):
            self.zoom_factor_changed = _Signal()
            self.object_selected = _Signal()
            self.context_menu_requested = _Signal()
            self.object_height_delta = _Signal()
            self.object_axis_delta = _Signal()

        def set_native_scene_resolver(self, value):
            calls.append(("native_scene_resolver", value))

        def set_native_scene_prepared_payload_resolver(self, value):
            calls.append(("native_scene_prepared_payload_resolver", value))

        def set_preview_mesh_resolver(self, value):
            calls.append(("preview_mesh_resolver", value))

        def set_planet_texture_resolver(self, value):
            calls.append(("planet_texture_resolver", value))

        def set_planet_cloud_texture_resolver(self, value):
            calls.append(("planet_cloud_texture_resolver", value))

        def set_planet_ring_resolver(self, value):
            calls.append(("planet_ring_resolver", value))

        def set_native_preview_progress_callback(self, value):
            calls.append(("native_preview_progress_callback", value))

        def set_native_preview_max_distance_fl(self, value):
            calls.append(("max_distance", value))

        def set_native_preview_high_quality_distance_fl(self, value):
            calls.append(("hq_distance", value))

        def set_reference_overlay_visible(self, value):
            calls.append(("reference_overlay", value))

    monkeypatch.setattr(main_window_module, "System3DView", _FakeView3D)

    host = main_window._build_system_editor_host("test")

    assert host is not None
    assert ("native_scene_resolver", main_window._resolve_system_view_native_scene_data_for_object) in calls
    assert (
        "native_scene_prepared_payload_resolver",
        main_window._resolve_system_view_native_scene_prepared_payload_for_object,
    ) in calls


def test_apply_tl_reposition_reapplies_object_y_rotation(main_window, monkeypatch):
    class _Rect:
        def width(self):
            return 10.0

        def height(self):
            return 10.0

    class _Obj:
        def __init__(self):
            self.nickname = "li01_trade_lane_ring_01"
            self.data = {
                "rotate": "0, 0, 0",
                "_entries": [
                    ("nickname", "li01_trade_lane_ring_01"),
                    ("rotate", "0, 0, 0"),
                    ("pos", "0, 0, 0"),
                ],
            }
            self.applied_rotation = None
            self.pos_calls: list[tuple[float, float]] = []

        def _apply_rotation_from_data(self):
            self.applied_rotation = self.data.get("rotate")

        def setPos(self, x, y):
            self.pos_calls.append((float(x), float(y)))

        def rect(self):
            return _Rect()

    obj = _Obj()
    main_window._scale = 1.0
    main_window._objects = [obj]
    main_window._sections = [("Object", list(obj.data["_entries"]))]
    main_window._pending_tl_reposition = {
        "chain": [{"_obj": obj}],
        "new_start": QPointF(0.0, 0.0),
        "new_end": QPointF(100.0, 0.0),
    }

    write_calls: list[bool] = []
    refresh_calls: list[bool] = []

    monkeypatch.setattr(main_window, "_write_to_file", lambda reload=False: write_calls.append(bool(reload)))
    monkeypatch.setattr(main_window, "_refresh_3d_scene", lambda *args, **kwargs: refresh_calls.append(True))

    main_window._apply_tl_reposition()

    assert obj.data["rotate"] == "0, -90, 0"
    assert obj.applied_rotation == "0, -90, 0"
    assert main_window._sections[0][1][1] == ("rotate", "0, -90, 0")
    assert write_calls == [False]
    assert refresh_calls == [True]


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

    monkeypatch.setattr(main_window, "_is_overlay_mode", lambda: True)
    monkeypatch.setattr(main_window, "_ensure_writable_path", lambda _p: dst_file)

    main_window._ini_editor_copy_tree_item_to_mod(item)

    assert item.data(0, Qt.UserRole) == str(dst_file)
    assert item.data(0, Qt.UserRole + 2) == "primary"
    assert item.text(0).startswith("copy.ini")
    assert "[mod]" in item.text(0).lower()
    assert main_window._ini_editor_current_file == str(dst_file)


def test_ini_editor_tree_labels_show_mod_and_vanilla_sources(main_window, monkeypatch, tmp_path: Path):
    mod_root = tmp_path / "mod"
    vanilla_root = tmp_path / "vanilla"
    (mod_root / "DATA").mkdir(parents=True)
    (vanilla_root / "DATA").mkdir(parents=True)
    (mod_root / "DATA" / "common.ini").write_text("[mod]\n", encoding="utf-8")
    (vanilla_root / "DATA" / "common.ini").write_text("[vanilla]\n", encoding="utf-8")
    (vanilla_root / "DATA" / "fallback.ini").write_text("[fallback]\n", encoding="utf-8")

    monkeypatch.setattr(main_window, "_ini_editor_context_root", lambda: mod_root)
    monkeypatch.setattr(main_window, "_is_overlay_mode", lambda: True)
    monkeypatch.setattr(main_window, "_fallback_game_path", lambda: str(vanilla_root))

    main_window._open_ini_editor_view()

    top = main_window.ini_tree.topLevelItem(0)
    data_dir = top.child(0)
    main_window._ini_editor_on_tree_item_expanded(data_dir)
    labels = [data_dir.child(i).text(0) for i in range(data_dir.childCount())]

    assert any("common.ini [mod]" in label.lower() for label in labels)
    assert any("fallback.ini [vanilla]" in label.lower() for label in labels)


def test_ini_editor_can_open_counterpart_file(main_window, monkeypatch, tmp_path: Path):
    mod_root = tmp_path / "mod"
    vanilla_root = tmp_path / "vanilla"
    mod_file = mod_root / "DATA" / "example.ini"
    vanilla_file = vanilla_root / "DATA" / "example.ini"
    mod_file.parent.mkdir(parents=True)
    vanilla_file.parent.mkdir(parents=True)
    mod_file.write_text("[mod]\n", encoding="utf-8")
    vanilla_file.write_text("[vanilla]\n", encoding="utf-8")

    monkeypatch.setattr(main_window, "_is_overlay_mode", lambda: True)
    main_window._ini_editor_root = str(mod_root)
    main_window._ini_editor_fallback_root = str(vanilla_root)

    item = QTreeWidgetItem(["example.ini [mod]"])
    item.setData(0, Qt.UserRole, str(mod_file))
    item.setData(0, Qt.UserRole + 1, "file")
    item.setData(0, Qt.UserRole + 2, "primary")

    opened: list[tuple[str, str]] = []
    monkeypatch.setattr(main_window, "_ini_editor_open_file_in_tab", lambda path, source="primary", ensure_workspace=True: opened.append((path, source)))

    counterpart = main_window._ini_editor_counterpart_path(item)

    assert counterpart == vanilla_file

    main_window._ini_editor_open_counterpart(item)

    assert opened == [(str(vanilla_file), "fallback")]


def test_ini_editor_compare_dialog_uses_current_and_counterpart_files(main_window, monkeypatch, tmp_path: Path):
    mod_root = tmp_path / "mod"
    vanilla_root = tmp_path / "vanilla"
    mod_file = mod_root / "DATA" / "example.ini"
    vanilla_file = vanilla_root / "DATA" / "example.ini"
    mod_file.parent.mkdir(parents=True)
    vanilla_file.parent.mkdir(parents=True)
    mod_file.write_text("[x]\nvalue = 2\n", encoding="utf-8")
    vanilla_file.write_text("[x]\nvalue = 1\n", encoding="utf-8")

    monkeypatch.setattr(main_window, "_is_overlay_mode", lambda: True)
    main_window._ini_editor_root = str(mod_root)
    main_window._ini_editor_fallback_root = str(vanilla_root)

    item = QTreeWidgetItem(["example.ini [mod]"])
    item.setData(0, Qt.UserRole, str(mod_file))
    item.setData(0, Qt.UserRole + 1, "file")
    item.setData(0, Qt.UserRole + 2, "primary")
    main_window._ini_editor_current_tree_item = item
    main_window._ini_editor_current_file = str(mod_file)

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        main_window,
        "_ini_editor_show_compare_dialog",
        lambda **kwargs: captured.update(kwargs),
    )

    main_window._ini_editor_open_compare_dialog()

    assert captured["current_path"] == mod_file
    assert captured["counterpart_path"] == vanilla_file
    assert "-value = 1" in str(captured["diff_text"])
    assert "+value = 2" in str(captured["diff_text"])
    assert "Changed" in str(captured["summary_text"]) or "Geaendert" in str(captured["summary_text"])


def test_ini_editor_compare_dialog_warns_without_counterpart(main_window, monkeypatch, tmp_path: Path):
    mod_file = tmp_path / "mod" / "DATA" / "example.ini"
    mod_file.parent.mkdir(parents=True)
    mod_file.write_text("[x]\n", encoding="utf-8")

    main_window._ini_editor_root = str(tmp_path / "mod")
    main_window._ini_editor_fallback_root = str(tmp_path / "vanilla")

    item = QTreeWidgetItem(["example.ini [mod]"])
    item.setData(0, Qt.UserRole, str(mod_file))
    item.setData(0, Qt.UserRole + 1, "file")
    item.setData(0, Qt.UserRole + 2, "primary")
    main_window._ini_editor_current_tree_item = item
    main_window._ini_editor_current_file = str(mod_file)

    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "fl_editor.main_window.QMessageBox.information",
        lambda *_args: calls.append((_args[1], _args[2])),
    )

    main_window._ini_editor_open_compare_dialog()

    assert len(calls) == 1
    assert "counterpart" in calls[0][1].lower() or "gegenst" in calls[0][1].lower()


def test_ini_editor_status_summary_shows_overlay_write_target_and_counterpart(main_window, monkeypatch, tmp_path: Path):
    mod_root = tmp_path / "mod"
    vanilla_root = tmp_path / "vanilla"
    mod_file = mod_root / "DATA" / "example.ini"
    vanilla_file = vanilla_root / "DATA" / "example.ini"
    mod_file.parent.mkdir(parents=True)
    vanilla_file.parent.mkdir(parents=True)
    mod_file.write_text("[mod]\n", encoding="utf-8")
    vanilla_file.write_text("[vanilla]\n", encoding="utf-8")

    monkeypatch.setattr(main_window, "_is_overlay_mode", lambda: True)
    monkeypatch.setattr(main_window, "_ensure_writable_path", lambda p: Path(p))

    main_window._ini_editor_root = str(mod_root)
    main_window._ini_editor_fallback_root = str(vanilla_root)
    main_window._ini_editor_current_file = str(mod_file)
    item = QTreeWidgetItem(["example.ini [mod]"])
    item.setData(0, Qt.UserRole, str(mod_file))
    item.setData(0, Qt.UserRole + 1, "file")
    item.setData(0, Qt.UserRole + 2, "primary")
    main_window._ini_editor_current_tree_item = item

    main_window._ini_editor_refresh_status_summary()

    summary = main_window.ini_status_summary_val.text().lower()
    tooltip = main_window.ini_status_summary_val.toolTip().lower()
    assert "example.ini" in summary
    assert "mod" in summary
    assert "clean" in summary or "sauber" in summary
    assert str(mod_file).lower() in tooltip
    assert str(vanilla_file).lower() in tooltip


def test_ini_editor_status_summary_updates_to_dirty(main_window, monkeypatch, tmp_path: Path):
    ini_file = tmp_path / "test.ini"
    ini_file.write_text("[x]\n", encoding="utf-8")
    item = QTreeWidgetItem(["test.ini [install]"])
    item.setData(0, Qt.UserRole, str(ini_file))
    item.setData(0, Qt.UserRole + 1, "file")
    item.setData(0, Qt.UserRole + 2, "primary")
    main_window._ini_editor_current_tree_item = item
    main_window._ini_editor_current_file = str(ini_file)
    main_window._ini_editor_dirty = False
    main_window.ini_code_edit.setPlainText("[x]\n")

    main_window._ini_editor_on_text_changed()

    summary = main_window.ini_status_summary_val.text().lower()
    assert "dirty" in summary or "geaendert" in summary


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


def test_open_model_file_uses_selected_object_preview_when_available(main_window, monkeypatch):
    obj = SolarObject(
        {
            "nickname": "li01_station",
            "archetype": "space_police01",
            "_entries": [("nickname", "li01_station"), ("archetype", "space_police01")],
        },
        1.0,
    )
    main_window._selected = obj
    calls: list[str] = []

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: "/tmp/freelancer")
    monkeypatch.setattr(main_window, "_show_selected_3d_preview", lambda: calls.append("selected-preview"))
    monkeypatch.setattr(
        "fl_editor.main_window.QFileDialog.getOpenFileName",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("file dialog should not open")),
    )

    main_window._open_model_file()

    assert calls == ["selected-preview"]


def test_show_selected_3d_preview_passes_planet_fallback_layers_to_dialog(main_window, monkeypatch, tmp_path: Path):
    obj = SolarObject(
        {
            "nickname": "li02_01",
            "archetype": "planet_watgrncld_3000",
            "atmosphere_range": "3200",
            "burn_color": "255, 222, 160",
            "_entries": [("nickname", "li02_01"), ("archetype", "planet_watgrncld_3000")],
        },
        1.0,
    )
    main_window._selected = obj

    surface = tmp_path / "surface.dds"
    cloud = tmp_path / "cloud.dds"
    ring = tmp_path / "ring.dds"
    surface.write_text("surface", encoding="utf-8")
    cloud.write_text("cloud", encoding="utf-8")
    ring.write_text("ring", encoding="utf-8")

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_resolve_model_for_archetype", lambda archetype, game_path: (tmp_path / "planet.sph", "planet.sph"))
    monkeypatch.setattr("fl_editor.main_window.QT3D_AVAILABLE", True)
    monkeypatch.setattr(
        "fl_editor.main_window.resolve_preview_mesh_candidate",
        lambda model_path: SimpleNamespace(preview_path=None, is_freelancer_native=False, extension=model_path.suffix.lower()),
    )
    monkeypatch.setattr(main_window, "_resolve_material_library_paths", lambda archetype, game_path: ())
    monkeypatch.setattr(main_window, "_resolve_planet_texture_for_object", lambda current_obj: surface if current_obj is obj else None)
    monkeypatch.setattr(main_window, "_resolve_planet_cloud_texture_for_object", lambda current_obj: cloud if current_obj is obj else None)
    monkeypatch.setattr(
        main_window,
        "_resolve_planet_ring_render_info_for_object",
        lambda current_obj: {"texture_path": ring, "inner_ratio": 1.4, "outer_ratio": 2.3, "rotate_xyz": (10.0, 20.0, 30.0)} if current_obj is obj else None,
    )

    captured: dict[str, object] = {}

    class _FakeDialog:
        def __init__(self, *args, **kwargs):
            captured.update(kwargs)

        def exec(self):
            return 0

    monkeypatch.setattr("fl_editor.main_window.MeshPreviewDialog", _FakeDialog)

    main_window._show_selected_3d_preview()

    assert captured["primitive"] == "sphere"
    assert captured["planet_surface_texture_path"] == surface
    assert captured["planet_cloud_texture_path"] == cloud
    assert captured["planet_ring_texture_path"] == ring
    assert captured["planet_ring_inner_ratio"] == 1.4
    assert captured["planet_ring_outer_ratio"] == 2.3
    assert captured["planet_ring_rotate_xyz"] == (10.0, 20.0, 30.0)
    assert captured["planet_atmosphere_range"] == 3200.0
    assert captured["planet_burn_color"] == (255, 222, 160)
    assert captured["planet_radius"] == 3000.0


def test_show_selected_3d_preview_uses_multipart_base_preview_branch(main_window, monkeypatch):
    obj = SolarObject(
        {
            "nickname": "li01_01_base_obj",
            "archetype": "smallstation1",
            "base": "Li01_01_Base",
            "dock_with": "Li01_01_Base",
            "_entries": [
                ("nickname", "li01_01_base_obj"),
                ("archetype", "smallstation1"),
                ("base", "Li01_01_Base"),
                ("dock_with", "Li01_01_Base"),
            ],
        },
        1.0,
    )
    main_window._selected = obj

    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(main_window, "_show_base_related_3d_preview", lambda current_obj, base_nick: calls.append((current_obj.nickname, base_nick)) or True)
    monkeypatch.setattr(main_window, "_resolve_model_for_archetype", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("single-object preview should not run")))

    main_window._show_selected_3d_preview()

    assert calls == [("li01_01_base_obj", "Li01_01_Base")]


def test_base_nickname_for_object_uses_root_nickname_when_children_reference_parent(main_window):
    root_obj = SolarObject(
        {
            "nickname": "Br04_02",
            "base": "Br04_02_Base",
            "dock_with": "Br04_02_Base",
            "archetype": "space_police01",
            "_entries": [
                ("nickname", "Br04_02"),
                ("archetype", "space_police01"),
                ("base", "Br04_02_Base"),
                ("dock_with", "Br04_02_Base"),
            ],
        },
        1.0,
    )
    child_obj = SolarObject(
        {
            "nickname": "Br04_02_part_001",
            "archetype": "smallstation1",
            "parent": "Br04_02",
            "_entries": [
                ("nickname", "Br04_02_part_001"),
                ("archetype", "smallstation1"),
                ("parent", "Br04_02"),
            ],
        },
        1.0,
    )
    main_window._objects = [root_obj, child_obj]

    assert main_window._base_nickname_for_object(root_obj) == "Br04_02"
    assert main_window._related_base_objects("Br04_02") == [root_obj, child_obj]


def test_show_selected_3d_preview_uses_multipart_branch_for_legacy_parented_root(main_window, monkeypatch):
    root_obj = SolarObject(
        {
            "nickname": "Br04_02",
            "base": "Br04_02_Base",
            "dock_with": "Br04_02_Base",
            "archetype": "space_police01",
            "_entries": [
                ("nickname", "Br04_02"),
                ("archetype", "space_police01"),
                ("base", "Br04_02_Base"),
                ("dock_with", "Br04_02_Base"),
            ],
        },
        1.0,
    )
    child_obj = SolarObject(
        {
            "nickname": "Br04_02_part_001",
            "archetype": "smallstation1",
            "parent": "Br04_02",
            "_entries": [
                ("nickname", "Br04_02_part_001"),
                ("archetype", "smallstation1"),
                ("parent", "Br04_02"),
            ],
        },
        1.0,
    )
    main_window._objects = [root_obj, child_obj]
    main_window._selected = root_obj

    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        main_window,
        "_show_base_related_3d_preview",
        lambda current_obj, base_nick: calls.append((current_obj.nickname, base_nick)) or True,
    )
    monkeypatch.setattr(
        main_window,
        "_resolve_model_for_archetype",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("single-object preview should not run")),
    )

    main_window._show_selected_3d_preview()

    assert calls == [("Br04_02", "Br04_02")]


def test_base_builder_payload_uses_legacy_root_parent_group_when_children_target_root_nickname(main_window):
    root_obj = SolarObject(
        {
            "nickname": "Br04_02",
            "base": "Br04_02_Base",
            "dock_with": "Br04_02_Base",
            "archetype": "space_factory01",
            "_entries": [
                ("nickname", "Br04_02"),
                ("archetype", "space_factory01"),
                ("base", "Br04_02_Base"),
                ("dock_with", "Br04_02_Base"),
            ],
        },
        main_window._scale,
    )
    child_a = SolarObject(
        {
            "nickname": "Br04_stokes_mplatform_1",
            "archetype": "mplatform",
            "parent": "Br04_02",
            "_entries": [
                ("nickname", "Br04_stokes_mplatform_1"),
                ("archetype", "mplatform"),
                ("parent", "Br04_02"),
            ],
        },
        main_window._scale,
    )
    child_b = SolarObject(
        {
            "nickname": "Br04_space_tankl4_2",
            "archetype": "space_tankl4",
            "parent": "Br04_02",
            "_entries": [
                ("nickname", "Br04_space_tankl4_2"),
                ("archetype", "space_tankl4"),
                ("parent", "Br04_02"),
            ],
        },
        main_window._scale,
    )
    main_window._objects = [root_obj, child_a, child_b]
    main_window._base_builder_active_base_nick = main_window._base_nickname_for_object(root_obj)

    objects, zones, scale = main_window._base_builder_scene_payload()
    existing_rows = main_window._base_builder_existing_parts("Br04_02")

    assert main_window._base_builder_active_base_nick == "Br04_02"
    assert objects == [root_obj, child_a, child_b]
    assert zones == []
    assert scale == main_window._scale
    assert [row["nickname"] for row in existing_rows] == ["Br04_space_tankl4_2", "Br04_stokes_mplatform_1"]


def test_show_selected_3d_preview_passes_native_scene_data_for_native_model(main_window, monkeypatch, tmp_path: Path):
    obj = SolarObject(
        {
            "nickname": "cf29_to_rh04",
            "archetype": "jumphole",
            "_entries": [("nickname", "cf29_to_rh04"), ("archetype", "jumphole")],
        },
        1.0,
    )
    main_window._selected = obj

    model_path = tmp_path / "jump_hole.3db"
    model_path.write_text("native", encoding="utf-8")
    native_scene_data = SimpleNamespace(geometries=(object(),), texture_path=None, primary_geometry=object(), part_names=())

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_resolve_model_for_archetype", lambda archetype, game_path: (model_path, "solar\\dockable\\jump_hole.3db"))
    monkeypatch.setattr("fl_editor.main_window.QT3D_AVAILABLE", True)
    monkeypatch.setattr(
        "fl_editor.main_window.resolve_preview_mesh_candidate",
        lambda current_model_path: SimpleNamespace(preview_path=None, is_freelancer_native=True, extension=current_model_path.suffix.lower()),
    )
    monkeypatch.setattr(main_window, "_resolve_native_scene_data_for_object", lambda current_obj: native_scene_data if current_obj is obj else None)
    monkeypatch.setattr(main_window, "_resolve_material_library_paths", lambda archetype, game_path: ())

    captured: dict[str, object] = {}

    class _FakeDialog:
        def __init__(self, *args, **kwargs):
            captured["title"] = args[2]
            captured.update(kwargs)

        def exec(self):
            return 0

    monkeypatch.setattr("fl_editor.main_window.MeshPreviewDialog", _FakeDialog)

    main_window._show_selected_3d_preview()

    assert captured["scene_data"] is native_scene_data
    assert captured["native_model"] is None
    assert captured["title"] == "3D Preview - cf29_to_rh04"


def test_resolve_planet_ring_render_info_for_object_uses_ring_ini_and_mat(main_window, monkeypatch, tmp_path: Path):
    obj = SolarObject(
        {
            "nickname": "li01_saturn",
            "archetype": "planet_saturn_4000",
            "ring": "solar\\rings\\saturn_ring.ini",
            "_entries": [("nickname", "li01_saturn"), ("archetype", "planet_saturn_4000"), ("ring", "solar\\rings\\saturn_ring.ini")],
        },
        1.0,
    )
    ring_ini = tmp_path / "DATA" / "solar" / "rings" / "saturn_ring.ini"
    ring_mat = tmp_path / "DATA" / "solar" / "rings" / "saturn_ring.mat"
    ring_tex = tmp_path / "ring.dds"
    ring_ini.parent.mkdir(parents=True)
    ring_ini.write_text("dummy", encoding="utf-8")
    ring_mat.write_text("dummy", encoding="utf-8")
    ring_tex.write_text("ring", encoding="utf-8")

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(
        main_window,
        "_resolve_game_path_case_insensitive",
        lambda _game_path, rel: {
            "DATA/solar/rings/saturn_ring.ini": ring_ini,
            "DATA/solar/rings/saturn_ring.mat": ring_mat,
        }.get(str(rel).replace("\\", "/")),
    )
    monkeypatch.setattr(
        main_window._parser,
        "parse",
        lambda _path: [("Ring", [("material_library", "solar\\rings\\saturn_ring.mat"), ("inner_radius", "5600"), ("outer_radius", "9200")])],
    )
    monkeypatch.setattr("fl_editor.main_window.extract_all_mat_textures", lambda paths: {"saturn_ring": ring_tex})

    resolved = main_window._resolve_planet_ring_render_info_for_object(obj)

    assert resolved is not None
    assert resolved["texture_path"] == ring_tex
    assert round(float(resolved["inner_ratio"]), 2) == 1.4
    assert round(float(resolved["outer_ratio"]), 2) == 2.3


def test_resolve_planet_ring_render_info_for_object_supports_zone_and_ini_format(main_window, monkeypatch, tmp_path: Path):
    obj = SolarObject(
        {
            "nickname": "ku03_aso",
            "archetype": "planet_gaspurcld_5000",
            "ring": "Zone_Ku03_Aso_ring, solar\\rings\\Aso.ini",
            "_entries": [
                ("nickname", "ku03_aso"),
                ("archetype", "planet_gaspurcld_5000"),
                ("ring", "Zone_Ku03_Aso_ring, solar\\rings\\Aso.ini"),
            ],
        },
        1.0,
    )
    ring_ini = tmp_path / "DATA" / "solar" / "rings" / "Aso.ini"
    ring_ini.parent.mkdir(parents=True)
    ring_ini.write_text("dummy", encoding="utf-8")

    requested: list[str] = []
    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))

    def _resolve(_game_path, rel):
        requested.append(str(rel).replace("\\", "/"))
        if str(rel).replace("\\", "/") == "DATA/solar/rings/Aso.ini":
            return ring_ini
        return None

    monkeypatch.setattr(main_window, "_resolve_game_path_case_insensitive", _resolve)
    main_window._sections = [
        ("Zone", [("nickname", "Zone_Ku03_Aso_ring"), ("rotate", "0, 35, 12")]),
    ]
    monkeypatch.setattr(main_window._parser, "parse", lambda _path: [])

    resolved = main_window._resolve_planet_ring_render_info_for_object(obj)

    assert requested[0] == "DATA/solar/rings/Aso.ini"
    assert resolved is not None
    assert round(float(resolved["inner_ratio"]), 2) == 1.35
    assert round(float(resolved["outer_ratio"]), 2) == 2.2
    assert resolved["rotate_xyz"] == (0.0, 35.0, 12.0)


def test_create_object_at_pos_accepts_missing_primary_game_path(main_window, monkeypatch):
    main_window._filepath = "C:/tmp/li01.ini"
    main_window._pending_new_object = True
    main_window._scale = 1.0
    main_window._objects = []
    main_window.arch_cb.clear()
    main_window.arch_cb.addItems(["station_a", "station_b"])
    main_window.loadout_cb.clear()
    main_window.loadout_cb.addItems(["loadout_a"])
    main_window.faction_cb.clear()
    main_window.faction_cb.addItems(["li_n_grp"])

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: "")
    monkeypatch.setattr(main_window, "_fallback_game_path", lambda: "")
    monkeypatch.setattr(main_window, "_has_ids_resource_toolchain", lambda: False)
    monkeypatch.setattr(main_window, "_suggest_system_scoped_name", lambda _kind, _existing: "object_01")
    monkeypatch.setattr(main_window, "_faction_from_ui", lambda value: value)

    captured_dialog: dict[str, object] = {}
    captured_added: dict[str, object] = {}

    class _TextField:
        def __init__(self):
            self.value = ""

        def setText(self, value):
            self.value = value

    class _FakeDialog:
        def __init__(self, _parent, archetypes, loadouts, factions):
            captured_dialog["archetypes"] = list(archetypes)
            captured_dialog["loadouts"] = list(loadouts)
            captured_dialog["factions"] = list(factions)
            self.nick_edit = _TextField()

        def exec(self):
            return QDialog.Accepted

        def payload(self):
            return {
                "nickname": "placed_object",
                "ids_name_text": "",
                "archetype": "station_a",
                "loadout": "loadout_a",
                "faction": "",
                "rep": "",
            }

    monkeypatch.setattr("fl_editor.main_window.ObjectCreationDialog", _FakeDialog)
    monkeypatch.setattr(
        main_window,
        "_add_object_from_entries",
        lambda entries, section_name: captured_added.update({"entries": list(entries), "section_name": section_name}),
    )

    main_window._create_object_at_pos(QPointF(120.0, 240.0))

    assert captured_dialog["archetypes"] == ["station_a", "station_b"]
    assert captured_dialog["loadouts"] == ["loadout_a"]
    assert captured_dialog["factions"] == ["li_n_grp"]
    assert captured_added["section_name"] == "Object"
    assert ("nickname", "placed_object") in captured_added["entries"]
    assert ("archetype", "station_a") in captured_added["entries"]
    assert ("loadout", "loadout_a") in captured_added["entries"]
    assert main_window._pending_new_object is False


def test_resolve_planet_texture_for_object_uses_material_library(main_window, monkeypatch, tmp_path: Path):
    obj = SolarObject(
        {
            "nickname": "li01_planet",
            "archetype": "planet_earthgrncld_4000",
            "_entries": [("nickname", "li01_planet"), ("archetype", "planet_earthgrncld_4000")],
        },
        1.0,
    )
    mat_path = tmp_path / "planet.mat"
    tex_path = tmp_path / "planet_surface.dds"
    mat_path.write_text("dummy", encoding="utf-8")
    tex_path.write_text("dummy", encoding="utf-8")

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_resolve_material_library_paths", lambda archetype, game_path: (mat_path,))
    monkeypatch.setattr("fl_editor.main_window.extract_all_mat_textures", lambda paths: {"planet_surface": tex_path})
    monkeypatch.setattr("fl_editor.main_window.find_best_mat_texture", lambda textures: tex_path)

    resolved = main_window._resolve_planet_texture_for_object(obj)

    assert resolved == tex_path


def test_resolve_planet_texture_for_object_prefers_surface_over_cloud_layer(main_window, monkeypatch, tmp_path: Path):
    obj = SolarObject(
        {
            "nickname": "li01_planet",
            "archetype": "planet_earthgrncld_4000",
            "_entries": [("nickname", "li01_planet"), ("archetype", "planet_earthgrncld_4000")],
        },
        1.0,
    )
    mat_path = tmp_path / "planet.mat"
    surface_path = tmp_path / "planet_surface.dds"
    cloud_path = tmp_path / "planet_clouds.dds"
    mat_path.write_text("dummy", encoding="utf-8")
    surface_path.write_text("surface", encoding="utf-8")
    cloud_path.write_text("cloud", encoding="utf-8")

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_resolve_material_library_paths", lambda archetype, game_path: (mat_path,))
    monkeypatch.setattr(
        "fl_editor.main_window.extract_all_mat_textures",
        lambda paths: {
            "planet_clouds": cloud_path,
            "planet_surface": surface_path,
        },
    )

    resolved = main_window._resolve_planet_texture_for_object(obj)

    assert resolved == surface_path


def test_resolve_planet_texture_for_object_matches_archetype_specific_original_texture(main_window, monkeypatch, tmp_path: Path):
    obj = SolarObject(
        {
            "nickname": "li01_planet",
            "archetype": "planet_earthgrncld_4000",
            "_entries": [("nickname", "li01_planet"), ("archetype", "planet_earthgrncld_4000")],
        },
        1.0,
    )
    mat_path = tmp_path / "planet.mat"
    earth_surface_path = tmp_path / "earthgrn.dds"
    generic_surface_path = tmp_path / "planet_surface.dds"
    cloud_path = tmp_path / "earthgrncld_clouds.dds"
    mat_path.write_text("dummy", encoding="utf-8")
    earth_surface_path.write_text("earth", encoding="utf-8")
    generic_surface_path.write_text("generic", encoding="utf-8")
    cloud_path.write_text("cloud", encoding="utf-8")

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_resolve_material_library_paths", lambda archetype, game_path: (mat_path,))
    monkeypatch.setattr(
        "fl_editor.main_window.extract_all_mat_textures",
        lambda paths: {
            "earthgrn": earth_surface_path,
            "planet_surface": generic_surface_path,
            "earthgrncld_clouds": cloud_path,
        },
    )

    resolved = main_window._resolve_planet_texture_for_object(obj)

    assert resolved == earth_surface_path


def test_resolve_planet_texture_for_object_replaces_stale_cap_cache_entry(main_window, monkeypatch, tmp_path: Path):
    obj = SolarObject(
        {
            "nickname": "br04_01",
            "archetype": "planet_earthcity_3000",
            "_entries": [("nickname", "br04_01"), ("archetype", "planet_earthcity_3000")],
        },
        1.0,
    )
    mat_path = tmp_path / "planet.mat"
    surface_path = tmp_path / "earthcity02.dds"
    cap_path = tmp_path / "earthcitycap.dds"
    mat_path.write_text("dummy", encoding="utf-8")
    surface_path.write_text("surface", encoding="utf-8")
    cap_path.write_text("cap", encoding="utf-8")

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_resolve_material_library_paths", lambda archetype, game_path: (mat_path,))
    monkeypatch.setattr(
        "fl_editor.main_window.extract_all_mat_textures",
        lambda paths: {
            "earthcity02": surface_path,
            "earthcitycap": cap_path,
        },
    )
    main_window._planet_texture_cache = {f"{str(tmp_path).lower()}::planet_earthcity_3000": cap_path}

    resolved = main_window._resolve_planet_texture_for_object(obj)

    assert resolved == surface_path


def test_resolve_planet_cloud_texture_for_object_matches_original_cloud_layer(main_window, monkeypatch, tmp_path: Path):
    obj = SolarObject(
        {
            "nickname": "li02_01",
            "archetype": "planet_watgrncld_3000",
            "_entries": [("nickname", "li02_01"), ("archetype", "planet_watgrncld_3000")],
        },
        1.0,
    )
    mat_path = tmp_path / "planet.mat"
    surface_path = tmp_path / "watgrn.dds"
    cloud_path = tmp_path / "watgrncld_clouds.dds"
    mat_path.write_text("dummy", encoding="utf-8")
    surface_path.write_text("surface", encoding="utf-8")
    cloud_path.write_text("cloud", encoding="utf-8")

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_resolve_material_library_paths", lambda archetype, game_path: (mat_path,))
    monkeypatch.setattr(
        "fl_editor.main_window.extract_all_mat_textures",
        lambda paths: {
            "watgrn": surface_path,
            "watgrncld_clouds": cloud_path,
        },
    )

    resolved = main_window._resolve_planet_cloud_texture_for_object(obj)

    assert resolved == cloud_path


def test_resolve_planet_texture_for_object_matches_desorgrck_surface_family(main_window, monkeypatch, tmp_path: Path):
    obj = SolarObject(
        {
            "nickname": "li02_planet_mojave",
            "archetype": "planet_desorgrck_2000",
            "_entries": [("nickname", "li02_planet_mojave"), ("archetype", "planet_desorgrck_2000")],
        },
        1.0,
    )
    mat_path = tmp_path / "planet.mat"
    desor_path = tmp_path / "desor.dds"
    generic_surface_path = tmp_path / "planet_surface.dds"
    ring_path = tmp_path / "desorgrck_ring.dds"
    mat_path.write_text("dummy", encoding="utf-8")
    desor_path.write_text("desor", encoding="utf-8")
    generic_surface_path.write_text("generic", encoding="utf-8")
    ring_path.write_text("ring", encoding="utf-8")

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_resolve_material_library_paths", lambda archetype, game_path: (mat_path,))
    monkeypatch.setattr(
        "fl_editor.main_window.extract_all_mat_textures",
        lambda paths: {
            "desor": desor_path,
            "planet_surface": generic_surface_path,
            "desorgrck_ring": ring_path,
        },
    )

    resolved = main_window._resolve_planet_texture_for_object(obj)

    assert resolved == desor_path


def test_resolve_planet_texture_for_object_matches_desored_surface_family(main_window, monkeypatch, tmp_path: Path):
    obj = SolarObject(
        {
            "nickname": "li01_02",
            "archetype": "planet_desored_1500",
            "_entries": [("nickname", "li01_02"), ("archetype", "planet_desored_1500")],
        },
        1.0,
    )

    desor_path = tmp_path / "desor.dds"
    desor_path.write_text("desor", encoding="utf-8")

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_resolve_material_library_paths", lambda archetype, game_path: (tmp_path / "planet.mat",))
    monkeypatch.setattr(
        "fl_editor.main_window.extract_all_mat_textures",
        lambda _mat_paths: {
            "desor": desor_path,
        },
    )

    resolved = main_window._resolve_planet_texture_for_object(obj)

    assert resolved == desor_path


def test_native_preview_distance_slider_updates_active_view3d(main_window):
    calls: list[float] = []

    class _FakeView3D:
        def set_native_preview_max_distance_fl(self, value: float):
            calls.append(float(value))

    main_window.view3d = _FakeView3D()

    main_window._on_native_preview_distance_changed(125)

    assert calls == [12500.0]
    assert main_window._native_preview_dist_value_lbl.text() == "12.5k"


def test_native_preview_distance_slider_supports_all_objects_mode(main_window):
    calls: list[float] = []

    class _FakeView3D:
        def set_native_preview_max_distance_fl(self, value: float):
            calls.append(float(value))

    main_window.view3d = _FakeView3D()

    main_window._on_native_preview_distance_changed(1001)

    assert calls == [-1.0]
    assert main_window._native_preview_dist_value_lbl.text() == "Alle"


def test_native_preview_status_label_formats_counts(main_window):
    main_window._update_native_preview_status_label({"active_3d_count": 12, "placeholder_count": 34})

    assert main_window._native_preview_dist_lbl.text() == "3D Render Distance"
    assert main_window._native_preview_hq_lbl.text() == "3D High-Quality Radius"
    assert main_window._zoom_lbl.text() == "Camera Zoom"
    assert main_window._native_preview_status_lbl.text() == "3D Models 12 | Placeholders 34"
    assert main_window._native_preview_dist_value_lbl.minimumWidth() == 56
    assert main_window._native_preview_hq_value_lbl.minimumWidth() == 56


def test_native_preview_high_quality_distance_slider_updates_active_view3d(main_window):
    calls: list[float] = []

    class _FakeView3D:
        def set_native_preview_high_quality_distance_fl(self, value: float):
            calls.append(float(value))

    main_window.view3d = _FakeView3D()

    main_window._on_native_preview_high_quality_distance_changed(200)

    assert calls == [20000.0]
    assert main_window._native_preview_hq_value_lbl.text() == "20.0k"


def test_legacy_main_toolbar_stays_hidden(main_window):
    assert main_window._main_toolbar.isHidden() is True
    assert main_window._main_toolbar.minimumHeight() == 0
    assert main_window._main_toolbar.maximumHeight() == 0


def test_resolve_preview_mesh_for_object_uses_renderable_preview_candidate(main_window, monkeypatch, tmp_path: Path):
    obj = SolarObject(
        {
            "nickname": "li01_station",
            "archetype": "station_preview",
            "_entries": [("nickname", "li01_station"), ("archetype", "station_preview")],
        },
        1.0,
    )
    model_path = tmp_path / "station.cmp"
    preview_path = tmp_path / "station.obj"
    model_path.write_text("cmp", encoding="utf-8")
    preview_path.write_text("obj", encoding="utf-8")

    monkeypatch.setattr(main_window, "_primary_game_path", lambda: str(tmp_path))
    monkeypatch.setattr(main_window, "_native_model_path_for_archetype_cached", lambda archetype, game_path: model_path)
    monkeypatch.setattr(main_window, "_find_preview_mesh_candidate", lambda current_model_path: preview_path if current_model_path == model_path else None)

    resolved = main_window._resolve_preview_mesh_for_object(obj)

    assert resolved == preview_path


def test_primitive_for_model_uses_jumpgate_fallback():
    class _Obj:
        data = {"archetype": "jumpgate_li01"}

    assert MainWindow._primitive_for_model(_Obj(), Path("C:/tmp/jumpgate.cmp")) == "jumpgate"


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


def test_apply_universe_payload_preserves_active_sector_on_reload(main_window, monkeypatch):
    main_window._uni_active_sector = "sector02"

    monkeypatch.setattr(main_window, "_apply_scene_wallpaper", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_apply_group_visibility", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_apply_system_name_mode_to_ui", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_refresh_3d_scene", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_build_standard_menu_bar", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_populate_quick_editor_options", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_sync_zoom_slider_from_view", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_refresh_viewer_move_border", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_clear_selection_ui", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_hide_zone_extra_editors", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_set_placement_mode", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_apply_workspace_layout", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_set_global_nav_active", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_sync_flight_button_visibility", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_ensure_primary_editor_host_alive", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_center_set_current_widget", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_fit", lambda *args, **kwargs: None)

    payload = {
        "game_path": "C:/tmp/game",
        "uni_ini_path": None,
        "uni_sections": [],
        "systems": [
            {
                "nickname": "li01",
                "path": "C:/tmp/game/DATA/UNIVERSE/SYSTEMS/LI01/li01.ini",
                "pos": (0.0, 0.0),
                "universe_pos": (0.0, 0.0),
                "ids_name": "",
                "map_positions": [{"map": "sector01", "pos": (0.0, 0.0), "label_ids": []}],
            },
            {
                "nickname": "cf80",
                "path": "C:/tmp/game/DATA/UNIVERSE/SYSTEMS/CF80/cf80.ini",
                "pos": (12.0, 3.0),
                "universe_pos": (5.0, 5.0),
                "ids_name": "",
                "map_positions": [{"map": "sector02", "pos": (12.0, 3.0), "label_ids": []}],
            },
        ],
        "sector_positions": {
            "LI01": {"universe": (0.0, 0.0), "sector01": (0.0, 0.0)},
            "CF80": {"universe": (5.0, 5.0), "sector02": (12.0, 3.0)},
        },
        "multiverse_detected": True,
        "scale": 1.0,
        "coord_map": {"LI01": (0.0, 0.0), "CF80": (5.0, 5.0)},
        "edges": {},
    }

    main_window._apply_universe_payload(payload)

    assert main_window._uni_active_sector == "sector02"
    sector02 = next(obj for obj in main_window._objects if str(obj.nickname).lower() == "cf80")
    sector01 = next(obj for obj in main_window._objects if str(obj.nickname).lower() == "li01")
    assert sector02.isVisible() is True
    assert sector01.isVisible() is False


def test_apply_group_visibility_preserves_universe_sector_filter(main_window, monkeypatch):
    main_window._uni_active_sector = "sector02"

    monkeypatch.setattr(main_window, "_apply_scene_wallpaper", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_apply_system_name_mode_to_ui", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_refresh_3d_scene", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_build_standard_menu_bar", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_populate_quick_editor_options", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_sync_zoom_slider_from_view", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_refresh_viewer_move_border", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_clear_selection_ui", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_hide_zone_extra_editors", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_set_placement_mode", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_apply_workspace_layout", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_set_global_nav_active", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_sync_flight_button_visibility", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_ensure_primary_editor_host_alive", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_center_set_current_widget", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_fit", lambda *args, **kwargs: None)

    payload = {
        "game_path": "C:/tmp/game",
        "uni_ini_path": None,
        "uni_sections": [],
        "systems": [
            {
                "nickname": "li01",
                "path": "C:/tmp/game/DATA/UNIVERSE/SYSTEMS/LI01/li01.ini",
                "pos": (0.0, 0.0),
                "universe_pos": (0.0, 0.0),
                "ids_name": "",
                "map_positions": [{"map": "sector01", "pos": (0.0, 0.0), "label_ids": []}],
            },
            {
                "nickname": "cf80",
                "path": "C:/tmp/game/DATA/UNIVERSE/SYSTEMS/CF80/cf80.ini",
                "pos": (12.0, 3.0),
                "universe_pos": (5.0, 5.0),
                "ids_name": "",
                "map_positions": [{"map": "sector02", "pos": (12.0, 3.0), "label_ids": []}],
            },
        ],
        "sector_positions": {
            "LI01": {"universe": (0.0, 0.0), "sector01": (0.0, 0.0)},
            "CF80": {"universe": (5.0, 5.0), "sector02": (12.0, 3.0)},
        },
        "multiverse_detected": True,
        "scale": 1.0,
        "coord_map": {"LI01": (0.0, 0.0), "CF80": (5.0, 5.0)},
        "edges": {},
    }

    main_window._apply_universe_payload(payload)
    main_window._apply_group_visibility()

    sector02 = next(obj for obj in main_window._objects if str(obj.nickname).lower() == "cf80")
    sector01 = next(obj for obj in main_window._objects if str(obj.nickname).lower() == "li01")
    assert sector02.isVisible() is True
    assert sector01.isVisible() is False


def test_apply_universe_payload_ignores_base_focus_for_universe_systems(main_window, monkeypatch):
    main_window._base_builder_active_base_nick = "Li01_01_Base"

    monkeypatch.setattr(main_window, "_apply_scene_wallpaper", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_apply_system_name_mode_to_ui", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_refresh_3d_scene", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_build_standard_menu_bar", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_populate_quick_editor_options", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_sync_zoom_slider_from_view", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_refresh_viewer_move_border", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_clear_selection_ui", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_hide_zone_extra_editors", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_set_placement_mode", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_apply_workspace_layout", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_set_global_nav_active", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_sync_flight_button_visibility", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_ensure_primary_editor_host_alive", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_center_set_current_widget", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window, "_fit", lambda *args, **kwargs: None)

    payload = {
        "game_path": "C:/tmp/game",
        "uni_ini_path": None,
        "uni_sections": [],
        "systems": [
            {
                "nickname": "li01",
                "path": "C:/tmp/game/DATA/UNIVERSE/SYSTEMS/LI01/li01.ini",
                "pos": (0.0, 0.0),
                "universe_pos": (0.0, 0.0),
                "ids_name": "",
                "map_positions": [],
            },
        ],
        "sector_positions": {
            "LI01": {"universe": (0.0, 0.0)},
        },
        "multiverse_detected": False,
        "scale": 1.0,
        "coord_map": {"LI01": (0.0, 0.0)},
        "edges": {},
    }

    main_window._apply_universe_payload(payload)

    system = next(obj for obj in main_window._objects if str(obj.nickname).lower() == "li01")
    assert system.isVisible() is True


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


def test_solar_object_uses_world_sized_radius_for_planets(qapp):
    obj = SolarObject(
        {
            "nickname": "li01_02",
            "archetype": "planet_desored_1500",
            "pos": "0,0,0",
            "_entries": [("nickname", "li01_02"), ("archetype", "planet_desored_1500"), ("pos", "0,0,0")],
        },
        0.01,
    )

    rect_before = obj.rect()
    obj.set_view_zoom(3.0)
    rect_after = obj.rect()

    assert round(rect_before.width(), 3) == 30.0
    assert rect_after == rect_before


def test_solar_object_uses_world_sized_radius_for_suns(qapp):
    obj = SolarObject(
        {
            "nickname": "li01_sun",
            "archetype": "sun_1000",
            "pos": "0,0,0",
            "_entries": [("nickname", "li01_sun"), ("archetype", "sun_1000"), ("pos", "0,0,0")],
        },
        0.01,
    )

    rect_before = obj.rect()
    obj.set_view_zoom(2.5)
    rect_after = obj.rect()

    assert round(rect_before.width(), 3) == 20.0
    assert rect_after == rect_before


def test_solar_object_updates_2d_radius_from_native_scene_bounds(qapp):
    obj = SolarObject(
        {
            "nickname": "station_a",
            "archetype": "space_police01",
            "pos": "0,0,0",
            "_entries": [("nickname", "station_a"), ("archetype", "space_police01"), ("pos", "0,0,0")],
        },
        0.01,
    )

    rect_before = obj.rect()
    obj.set_model_world_radius(18.0)
    rect_after = obj.rect()

    assert rect_after.width() > rect_before.width()
    assert round(rect_after.width(), 3) == 36.0


def test_solar_object_keeps_small_objects_clickable_in_2d(qapp):
    obj = SolarObject(
        {
            "nickname": "tiny_ring",
            "archetype": "trade_lane_ring",
            "pos": "0,0,0",
            "_entries": [("nickname", "tiny_ring"), ("archetype", "trade_lane_ring"), ("pos", "0,0,0")],
        },
        0.01,
    )

    obj.set_view_zoom(3.0)

    assert round(obj.rect().width(), 3) == 3.2


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
    assert snapshot["view3d_detail_state"]["has_scene_data"] is False
    assert snapshot["view3d_detail_state"]["geometry_count"] == 0
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
    main_window.view3d = type(
        "_FakeView3DState",
        (),
        {
            "get_selected_native_detail_debug_state": lambda self: {
                "has_scene_data": True,
                "geometry_count": 2,
                "geometry_confidences": ("structured-family-split", "structured-single-block"),
            }
        },
    )()

    snapshot = main_window._native_scene_debug_state_snapshot()

    assert snapshot["runtime_initialized"] is True
    assert snapshot["selected_object_nickname"] == "li01_station"
    assert snapshot["selected_model_path"] == model_path
    assert snapshot["view3d_detail_state"]["geometry_count"] == 2
    assert snapshot["view3d_detail_state"]["geometry_confidences"] == (
        "structured-family-split",
        "structured-single-block",
    )
    assert snapshot["stats"] == runtime.get_debug_state()["stats"]
    assert any(event.kind == "load_queued" for event in snapshot["events"])


def test_native_scene_runtime_event_refreshes_view3d_previews_for_completed_loads(main_window):
    calls: list[str] = []

    class _FakeView3D:
        def _schedule_native_scene_preview_refresh(self, delay_ms):
            calls.append(f"schedule:{delay_ms}")

        def refresh_native_scene_previews(self):
            calls.append("refresh")

    main_window.view3d = _FakeView3D()

    main_window._on_native_scene_runtime_event(
        NativeSceneRuntimeEvent(kind="load_succeeded", model_path=Path("/tmp/preview.cmp"), detail="")
    )
    main_window._on_native_scene_runtime_event(
        NativeSceneRuntimeEvent(kind="load_failed", model_path=Path("/tmp/preview_fail.cmp"), detail="")
    )
    main_window._on_native_scene_runtime_event(
        NativeSceneRuntimeEvent(kind="cache_pruned", model_path=Path("/tmp/old_preview.cmp"), detail="")
    )
    main_window._on_native_scene_runtime_event(
        NativeSceneRuntimeEvent(kind="load_queued", model_path=Path("/tmp/queued_preview.cmp"), detail="")
    )

    assert calls == ["schedule:30", "schedule:30", "schedule:30"]


def test_native_scene_runtime_event_appends_activity_messages(main_window):
    main_window._on_native_scene_runtime_event(
        NativeSceneRuntimeEvent(kind="load_queued", model_path=Path("/tmp/queued_preview.cmp"), detail="")
    )
    main_window._on_native_scene_runtime_event(
        NativeSceneRuntimeEvent(kind="pending_discarded", model_path=Path("/tmp/stale_preview.cmp"), detail="reprioritized")
    )
    main_window._on_native_scene_runtime_event(
        NativeSceneRuntimeEvent(kind="load_succeeded", model_path=Path("/tmp/ready_preview.cmp"), detail="")
    )

    messages = [str(entry.get("message", "")) for entry in main_window._activity_log_entries[-3:]]

    assert "3D queue: scheduled (queued_preview.cmp)" in messages
    assert "3D queue: canceled stale job (stale_preview.cmp)" in messages
    assert "3D decode: prepared in worker (ready_preview.cmp)" in messages


def test_sync_view3d_selected_native_scene_data_skips_selection_detail_when_3d_is_enabled(main_window, monkeypatch):
    selected = SolarObject(
        {
            "nickname": "first_obj",
            "archetype": "space_police01",
            "_entries": [("nickname", "first_obj"), ("archetype", "space_police01")],
        },
        1.0,
    )
    main_window._selected = selected

    calls: list[tuple[object, object]] = []

    class _FakeView3D:
        def set_selected_native_scene_data(self, obj, scene_data):
            calls.append((obj, scene_data))

        def refresh_native_scene_previews(self):
            calls.append(("refresh", None))

    class _FakeSwitch:
        def isChecked(self):
            return True

    class _FakeRuntime:
        def __init__(self):
            self.reasons: list[str] = []

        def discard_pending_requests(self, *, reason: str = "", protected_paths=()):
            self.reasons.append(reason)
            return ()

        def get_debug_state(self):
            return {"stats": {}, "pending_paths": (), "cached_paths": (), "failed_paths": (), "recent_events": ()}

    main_window.view3d = _FakeView3D()
    main_window.view3d_switch = _FakeSwitch()
    main_window._native_scene_runtime_store = _FakeRuntime()
    monkeypatch.setattr(
        main_window,
        "_native_model_path_for_object",
        lambda obj: Path(f"/tmp/{getattr(obj, 'nickname', 'none')}.cmp") if obj is not None else None,
    )

    main_window._sync_view3d_selected_native_scene_data()

    assert calls == [(selected, None), ("refresh", None)]
    assert main_window._native_scene_runtime_store.reasons == []
    snapshot = main_window._native_scene_debug_state_snapshot()
    assert snapshot["selected_object_nickname"] == "first_obj"
    assert any(event.kind == "sync_skipped_selection_detail_disabled" for event in snapshot["events"])


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


def test_sync_view3d_selected_native_scene_data_discards_pending_requests_without_selection(main_window):
    calls: list[tuple[object, object]] = []

    class _FakeView3D:
        def set_selected_native_scene_data(self, obj, scene_data):
            calls.append((obj, scene_data))

    class _FakeRuntime:
        def __init__(self):
            self.reasons: list[str] = []

        def discard_pending_requests(self, *, reason: str = "", protected_paths=()):
            self.reasons.append(reason)
            return ()

        def get_debug_state(self):
            return {"stats": {}, "pending_paths": (), "cached_paths": (), "failed_paths": (), "recent_events": ()}

    main_window.view3d = _FakeView3D()
    main_window._selected = None
    main_window._native_scene_runtime_store = _FakeRuntime()

    main_window._sync_view3d_selected_native_scene_data()

    assert calls == [(None, None)]
    assert main_window._native_scene_runtime_store.reasons == ["no-selection"]


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


def test_sync_view3d_selected_native_scene_data_discards_pending_requests_when_3d_is_disabled(main_window, monkeypatch):
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

    class _FakeRuntime:
        def __init__(self):
            self.reasons: list[str] = []

        def discard_pending_requests(self, *, reason: str = "", protected_paths=()):
            self.reasons.append(reason)
            return ()

        def get_debug_state(self):
            return {"stats": {}, "pending_paths": (), "cached_paths": (), "failed_paths": (), "recent_events": ()}

    main_window.view3d = _FakeView3D()
    main_window.view3d_switch = _FakeSwitch()
    main_window._native_scene_runtime_store = _FakeRuntime()
    monkeypatch.setattr(main_window, "_native_model_path_for_object", lambda _obj: Path("/tmp/disabled_obj.cmp"))

    main_window._sync_view3d_selected_native_scene_data()

    assert calls == [(obj, None)]
    assert main_window._native_scene_runtime_store.reasons == ["3d-disabled"]


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
