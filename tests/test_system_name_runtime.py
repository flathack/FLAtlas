from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fl_editor import system_name_runtime as runtime


class _Cfg:
    def __init__(self):
        self.values = {}

    def set(self, key, value):
        self.values[key] = value


class _Action:
    def __init__(self):
        self.checked = None

    def setChecked(self, value):
        self.checked = bool(value)


class _Label:
    def __init__(self):
        self.text = ""

    def setPlainText(self, text):
        self.text = str(text)

    def setText(self, text):
        self.text = str(text)


class _Resolver:
    def __init__(self):
        self.values = {}
        self.loaded = []
        self.cleared = 0

    def resolve_name(self, key):
        return self.values.get(str(key), "")

    def load_from_resource_pairs(self, pairs):
        self.loaded.append(list(pairs))

    def clear(self):
        self.cleared += 1


def _build_window():
    window = SimpleNamespace()
    window._dll_html_cache = {}
    window._dll_lookup_cache_sig = None
    window._ids_display_cache = {}
    window._info_editor_cache_sig = "sig"
    window._info_editor_rows_cache = ["row"]
    window._dll_resolver = _Resolver()
    window._resource_dll_pairs_for_lookup = lambda: []
    window._load_dll_html_resources = lambda path: {1: "<RDL/>"}
    window._system_display_names_by_nick = {}
    window._system_nick_by_path = {}
    window._primary_game_path = lambda: "C:/mods"
    window._find_all_systems = lambda gp: []
    window._ids_name_resolution_enabled = True
    window._system_name_mode = "ingame"
    window._cfg = _Cfg()
    window._view_system_name_actions = {"ingame": _Action(), "nickname": _Action()}
    window._view_ids_name_resolution_action = _Action()
    window.browser = SimpleNamespace(
        set_system_name_map=lambda mapping, scan=False: setattr(window, "browser_map", (mapping, scan)),
        set_system_name_mode=lambda mode, scan=False: setattr(window, "browser_mode", (mode, scan)),
    )
    window._apply_system_name_mode_to_ui = lambda: setattr(window, "ui_applied", True)
    window._reload_dll_name_cache = lambda force=False: setattr(window, "reloaded", force)
    window._display_name_from_ids_name = lambda value: {"100": "New York"}.get(str(value), "")
    window._faction_label_to_nick = {}
    window._faction_nick_to_label = {}
    window._extract_ids_name_from_entries = runtime.extract_ids_name_from_entries
    window._faction_from_ui = lambda value: runtime.faction_from_ui(window, value)
    window._safe_int = lambda text: int(text or "0")
    window._resolve_infocard_xml_by_global_id = lambda gid: "<RDL>Info</RDL>" if gid == 200 else ""
    window._xml_to_plain_preview = lambda xml: f"preview:{xml}"
    window._qt_widget_alive = lambda obj: obj is not None and getattr(obj, "alive", True)
    window._objects = []
    window._avoid_label_overlap = False
    window._reflow_2d_labels = lambda: setattr(window, "labels_reflowed", True)
    window._reset_2d_label_positions = lambda: setattr(window, "labels_reset", True)
    window.obj_combo = object()
    window._rebuild_object_combo = lambda: setattr(window, "combo_rebuilt", True)
    window._sync_obj_combo_to_selection = lambda: setattr(window, "combo_synced", True)
    window._uni_selected_nick = ""
    window.uni_sys_lbl = _Label()
    window._filepath = ""
    window._system_nickname_for_path = lambda path: "LI01"
    window._system_display_name = lambda nickname: {"LI01": "New York"}.get(str(nickname).upper(), str(nickname).upper())
    window._title_with_version = lambda text: f"title::{text}"
    window.setWindowTitle = lambda text: setattr(window, "window_title", text)
    window._refresh_system_fields = lambda: setattr(window, "fields_refreshed", True)
    window._selected = None
    window.status = SimpleNamespace(showMessage=lambda text: setattr(window, "status_message", text))
    window.statusBar = lambda: window.status
    return window


def test_display_name_and_text_use_cache_and_infocard_fallback():
    window = _build_window()
    window._dll_resolver.values = {"100": "Planet Manhattan"}

    assert runtime.display_name_from_ids_name(window, "100") == "Planet Manhattan"
    assert runtime.display_name_from_ids_name(window, "100") == "Planet Manhattan"
    assert runtime.display_text_from_ids_value(window, "200") == "preview:<RDL>Info</RDL>"


def test_build_faction_cache_and_normalize_reputation_handle_labels():
    window = _build_window()
    window._display_name_from_ids_name = lambda value: {"10": "Liberty Police, Inc."}.get(str(value), "")

    runtime.build_faction_label_cache(window, [("li_p_grp", "10")])

    assert runtime.faction_ui_label(window, "li_p_grp") == "li_p_grp - Liberty Police, Inc."
    assert runtime.faction_from_ui(window, "li_p_grp - Liberty Police, Inc.") == "li_p_grp"
    assert runtime.normalize_reputation_value(window, "li_p_grp, 0.9") == "li_p_grp,0.9"


def test_set_system_name_mode_and_resolution_update_cfg_and_ui():
    window = _build_window()
    window._refresh_system_name_cache = lambda gp: setattr(window, "refresh_path", gp)

    runtime.set_system_name_mode(window, "nickname")
    runtime.set_ids_name_resolution_enabled(window, False)

    assert window._system_name_mode == "nickname"
    assert window._cfg.values["view.system_name_mode"] == "nickname"
    assert window._view_system_name_actions["nickname"].checked is True
    assert window._ids_name_resolution_enabled is False
    assert window._cfg.values["view.ids_name_resolution"] is False
    assert window.refresh_path == "C:/mods"


def test_refresh_system_name_cache_and_path_lookup_fill_browser_state():
    window = _build_window()
    window._reload_dll_name_cache = lambda force=False: setattr(window, "reload_called", True)
    window._find_all_systems = lambda gp: [{"nickname": "li01", "ids_name": "100", "path": "C:/mods/DATA/li01.ini"}]

    runtime.refresh_system_name_cache(window, "C:/mods")

    assert window.reload_called is True
    assert window._system_display_names_by_nick["LI01"] == "New York"
    assert runtime.system_nickname_for_path(window, "C:/mods/DATA/li01.ini") == "LI01"
    assert window.browser_map[0]["LI01"] == "New York"


def test_apply_system_name_mode_to_ui_updates_labels_and_title():
    window = _build_window()
    obj = SimpleNamespace(
        nickname="planet_1",
        data={"ids_name": "100"},
        label=_Label(),
        alive=True,
    )
    window._objects = [obj]
    window._object_display_label = lambda target: "Planet Manhattan"
    window._filepath = "C:/mods/DATA/li01.ini"

    runtime.apply_system_name_mode_to_ui(window)

    assert obj.label.text == "Planet Manhattan"
    assert window.labels_reset is True
    assert window.combo_rebuilt is True
    assert "New York" in window.window_title
    assert window.fields_refreshed is True


def test_default_name_helpers_return_expected_strings():
    window = _build_window()
    window._auto_name_language = lambda: "de"

    assert runtime.default_jump_ids_name(window, "jumpgate", "New York") == "New York-Sprungtor"
    assert runtime.default_gate_connection_name("New York", "Texas") == "New York -> Texas"
