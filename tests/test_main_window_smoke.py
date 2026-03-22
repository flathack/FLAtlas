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
    monkeypatch.setattr(main_window.view3d, "center_on_item", lambda obj: centered_3d.append(obj.nickname))

    assert main_window._trade_route_select_base_object("li01_01_base")
    assert selected == ["planet_manhattan"]
    assert centered_2d == ["planet_manhattan"]
    assert centered_3d == ["planet_manhattan"]


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
