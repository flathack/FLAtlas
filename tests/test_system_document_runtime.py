from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtGui import QTransform

from fl_editor import system_document_runtime as runtime


class _Scene:
    def __init__(self):
        self.items = []
        self.cleared = 0
        self.scene_rects = []

    def clear(self):
        self.cleared += 1
        self.items.clear()

    def setSceneRect(self, *rect):
        self.scene_rects.append(rect)

    def addItem(self, item):
        self.items.append(item)


class _View:
    def __init__(self):
        self._scene = _Scene()
        self.world_scale = None
        self.zoom_out_limit = None
        self.zoom_out_reference_rect = None
        self.zoom_in_limit_multiplier = None
        self.unbounded_pan = None
        self.left_drag_pan = None
        self.transform_value = None

    def set_world_scale(self, scale):
        self.world_scale = scale

    def set_zoom_out_limit_to_scene(self, value):
        self.zoom_out_limit = bool(value)

    def set_zoom_out_reference_rect(self, rect):
        self.zoom_out_reference_rect = rect

    def set_zoom_in_limit_multiplier(self, value):
        self.zoom_in_limit_multiplier = float(value)

    def set_unbounded_pan(self, value):
        self.unbounded_pan = bool(value)

    def set_left_drag_pan_enabled(self, value):
        self.left_drag_pan = bool(value)

    def setTransform(self, transform):
        self.transform_value = transform

    def current_zoom_factor(self):
        return 1.5


class _Toggle:
    def __init__(self, checked=False):
        self._checked = bool(checked)

    def isChecked(self):
        return self._checked


class _Parser:
    def __init__(self, objects=None, zones=None, parsed=None):
        self._objects = list(objects or [])
        self._zones = list(zones or [])
        self._parsed = list(parsed or [])
        self.parse_calls = []

    def get_objects(self, _sections):
        return list(self._objects)

    def get_zones(self, _sections):
        return list(self._zones)

    def parse(self, path):
        self.parse_calls.append(path)
        return list(self._parsed)


class _Label:
    def __init__(self):
        self.text = ""

    def setPlainText(self, text):
        self.text = str(text)


class _FakeSolarObject:
    _top_view_icon_auto_refresh_enabled = True
    auto_refresh_history: list[bool] = []

    def __init__(self, data, scale):
        self.data = dict(data)
        self.scale = scale
        self.nickname = str(data.get("nickname", ""))
        self.label = _Label()
        self.flags = []
        self.visible_labels = []
        self.refresh_calls = 0
        self.auto_refresh_used = bool(type(self)._top_view_icon_auto_refresh_enabled)
        type(self).auto_refresh_history.append(self.auto_refresh_used)

    def set_label_visibility(self, visible):
        self.visible_labels.append(bool(visible))

    def setFlag(self, flag, enabled):
        self.flags.append((flag, bool(enabled)))

    @classmethod
    def set_top_view_icon_auto_refresh_enabled(cls, enabled):
        cls._top_view_icon_auto_refresh_enabled = bool(enabled)

    def refresh_top_view_icon(self):
        self.refresh_calls += 1


class _FakeZoneItem:
    def __init__(self, data, scale):
        self.data = dict(data)
        self.scale = scale
        self.visible_labels = []

    def set_label_visibility(self, visible):
        self.visible_labels.append(bool(visible))


class _Action:
    def __init__(self):
        self.visible = None
        self.enabled = None

    def setVisible(self, value):
        self.visible = bool(value)

    def setEnabled(self, value):
        self.enabled = bool(value)


class _TextHolder:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = str(text)


class _StatusBar:
    def __init__(self):
        self.message = ""

    def showMessage(self, message):
        self.message = str(message)


class _Doc:
    def __init__(self):
        self.change_snapshots = [{"x": 1}]
        self.last_snapshot_fp = "snap.json"
        self.history_restore_in_progress = True
        self.undo_actions = ["undo"]
        self.change_log_entries = ["log"]
        self.pending_zone = {"kind": "zone"}


def _build_window(*, parser=None):
    window = SimpleNamespace()
    window._parser = parser or _Parser()
    window._viewer_text_visible = True
    window._avoid_label_overlap = False
    window._objects = []
    window._zones = []
    window._selected = None
    window._filepath = ""
    window._sections = []
    window._dirty = False
    window._change_snapshots = []
    window._last_snapshot_fp = ""
    window._history_restore_in_progress = False
    window._undo_actions = []
    window._change_log_entries = []
    window._flight_lock_active = False
    window._pending_conn = {"old": 1}
    window._pending_create = {"old": 1}
    window._pending_light_source = {"old": 1}
    window._pending_new_object = True
    window._pending_tradelane = {"old": 1}
    window._pending_tl_reposition = {"old": 1}
    window.view = _View()
    window.move_cb = _Toggle(True)
    window.view3d_switch = _Toggle(True)
    window.left_ini_panel = object()
    window._workspace_layout_state_factory = lambda **kwargs: SimpleNamespace(**kwargs)
    window.info_lbl = _TextHolder()
    window._sys_header_lbl = _TextHolder()
    window.status = _StatusBar()
    window.statusBar = lambda: window.status
    window._new_system_action = _Action()
    window._uni_save_action = _Action()
    window._uni_undo_action = _Action()
    window._uni_delete_action = _Action()
    window.uni_delete_btn = _Action()
    window._ids_scan_action = _Action()
    window._ids_import_action = _Action()
    window._change_undo_btn = _Action()
    window.change_log_view = SimpleNamespace(setPlainText=lambda text: setattr(window, "change_log_text", text))
    window._set_system_zoom_controls_visible = lambda value: setattr(window, "zoom_controls_visible", bool(value))
    window._clear_move_delta_indicator = lambda: setattr(window, "move_delta_cleared", True)
    window._apply_scene_wallpaper = lambda: setattr(window, "wallpaper_applied", True)
    window._clear_selection_ui = lambda: setattr(window, "selection_cleared", True)
    window._hide_zone_extra_editors = lambda: setattr(window, "zone_editors_hidden", True)
    window._object_display_label = lambda obj: f"label:{obj.nickname}"
    window._draw_system_reference_overlay = lambda radius: setattr(window, "overlay_radius", radius)
    window._apply_group_visibility = lambda: setattr(window, "group_visibility_applied", True)
    window._reflow_2d_labels = lambda: setattr(window, "labels_reflowed", True)
    window._reset_2d_label_positions = lambda: setattr(window, "labels_reset", True)
    window._system_nickname_for_path = lambda path: "li01"
    window._system_display_name = lambda nick: f"System {nick.upper()}"
    window._format_system_header_text = lambda nick: f"Header {nick}"
    window._rebuild_object_combo = lambda: setattr(window, "object_combo_rebuilt", True)
    window._title_with_version = lambda text: f"title::{text}"
    window.setWindowTitle = lambda text: setattr(window, "window_title", text)
    window._apply_workspace_layout = lambda state: setattr(window, "workspace_state", state)
    window._set_global_nav_active = lambda key: setattr(window, "nav_key", key)
    window._set_dirty = lambda value: setattr(window, "_dirty", bool(value))
    window._fit = lambda: setattr(window, "fit_called", True)
    window._sync_zoom_slider_from_view = lambda zoom: setattr(window, "synced_zoom", zoom)
    window._refresh_3d_scene = lambda: setattr(window, "scene_refreshed", True)
    window._refresh_viewer_move_border = lambda: setattr(window, "move_border_refreshed", True)
    window._populate_quick_editor_options = lambda: setattr(window, "quick_options_populated", True)
    window._populate_system_options = lambda: setattr(window, "system_options_populated", True)
    window._build_standard_menu_bar = lambda: setattr(window, "menu_built", True)
    window._refresh_system_fields = lambda: setattr(window, "system_fields_refreshed", True)
    window._collect_change_log_lines = lambda: ["one", "two"]
    window._reload_dll_name_cache = lambda: setattr(window, "dll_cache_reloaded", True)
    window._restore_system_tab_pending_state = lambda doc: setattr(window, "restored_pending_doc", doc)
    window._set_loading_visible = lambda visible, text=None: setattr(
        window,
        "loading_calls",
        getattr(window, "loading_calls", []) + [(bool(visible), text)],
    )
    window._set_flight_mode = lambda enabled: setattr(window, "flight_mode", bool(enabled))
    window._set_placement_mode = lambda enabled, text="": setattr(window, "placement_mode", (bool(enabled), text))
    window._apply_system_document = lambda path, sections, restore=None, dirty=False: setattr(
        window,
        "applied_document",
        {"path": path, "sections": sections, "restore": restore, "dirty": dirty},
    )
    return window


def test_apply_system_document_rebuilds_scene_and_restores_runtime_state(monkeypatch):
    parser = _Parser(
        objects=[{"nickname": "sun", "pos": "1000,0,2000", "size": "50"}],
        zones=[{"nickname": "zone_a"}],
    )
    window = _build_window(parser=parser)
    doc = _Doc()
    restore = QTransform()
    single_shot_calls: list[int] = []

    def _fake_single_shot(delay: int, callback):
        single_shot_calls.append(int(delay))
        callback()

    _FakeSolarObject.auto_refresh_history = []
    _FakeSolarObject._top_view_icon_auto_refresh_enabled = True
    monkeypatch.setattr(runtime, "SolarObject", _FakeSolarObject)
    monkeypatch.setattr(runtime, "ZoneItem", _FakeZoneItem)
    monkeypatch.setattr(runtime.QTimer, "singleShot", staticmethod(_fake_single_shot))

    runtime.apply_system_document(
        window,
        "C:/mods/DATA/UNIVERSE/li01.ini",
        [("system", [("nickname", "li01")])],
        restore=restore,
        dirty=True,
        doc=doc,
    )

    assert window._filepath.endswith("li01.ini")
    assert window._change_snapshots == [{"x": 1}]
    assert window._undo_actions == ["undo"]
    assert window.restored_pending_doc is doc
    assert window.view.world_scale == 0.05
    assert window.view.zoom_out_limit is True
    assert window.view.zoom_in_limit_multiplier == 40.0
    assert len(window._zones) == 1
    assert len(window._objects) == 1
    assert window._objects[0].label.text == "label:sun"
    assert window.overlay_radius == 2286.06797749979
    assert window.workspace_state.right_panel_visible is True
    assert window.object_combo_rebuilt is True
    assert window.scene_refreshed is True
    assert window.change_log_text == "one\ntwo"
    assert window._dirty is True
    assert window.synced_zoom == 1.5
    assert window.loading_calls == [(True, runtime.tr("status.preparing_system_view")), (False, None)]
    assert single_shot_calls == [0]
    assert _FakeSolarObject.auto_refresh_history == [False]


def test_apply_system_document_queues_top_view_icon_refresh_after_scene_rebuild(monkeypatch):
    parser = _Parser(
        objects=[
            {"nickname": "sun", "pos": "1000,0,2000", "size": "50"},
            {"nickname": "planet", "pos": "0,0,0", "size": "500"},
        ],
        zones=[{"nickname": "zone_a"}],
    )
    window = _build_window(parser=parser)
    queued_objects: list[list[object]] = []
    window._queue_top_view_icon_refresh = lambda objs: queued_objects.append(list(objs))

    def _fake_single_shot(delay: int, callback):
        callback()

    _FakeSolarObject.auto_refresh_history = []
    _FakeSolarObject._top_view_icon_auto_refresh_enabled = True
    monkeypatch.setattr(runtime, "SolarObject", _FakeSolarObject)
    monkeypatch.setattr(runtime, "ZoneItem", _FakeZoneItem)
    monkeypatch.setattr(runtime.QTimer, "singleShot", staticmethod(_fake_single_shot))

    runtime.apply_system_document(
        window,
        "C:/mods/DATA/UNIVERSE/li01.ini",
        [("system", [("nickname", "li01")])],
        restore=None,
        dirty=False,
        doc=None,
    )

    assert len(window._objects) == 2
    assert queued_objects == [window._objects]
    assert all(obj.refresh_calls == 0 for obj in window._objects)
    assert _FakeSolarObject.auto_refresh_history == [False, False]


def test_apply_system_document_does_not_clear_pending_connection_without_tab_document(monkeypatch):
    parser = _Parser(
        objects=[{"nickname": "sun", "pos": "1000,0,2000", "size": "50"}],
        zones=[],
    )
    window = _build_window(parser=parser)
    window._pending_conn = {"step": 2, "origin": "li01"}

    def _unexpected_restore(_doc):
        raise AssertionError("pending placement state should not be restored from a missing document")

    monkeypatch.setattr(runtime, "SolarObject", _FakeSolarObject)
    monkeypatch.setattr(runtime, "ZoneItem", _FakeZoneItem)
    monkeypatch.setattr(runtime.QTimer, "singleShot", staticmethod(lambda _delay, callback: callback()))
    window._restore_system_tab_pending_state = _unexpected_restore

    runtime.apply_system_document(
        window,
        "C:/mods/DATA/UNIVERSE/br01.ini",
        [("system", [("nickname", "br01")])],
        restore=None,
        dirty=False,
        doc=None,
    )

    assert window._pending_conn == {"step": 2, "origin": "li01"}


def test_apply_system_document_keeps_loading_visible_until_deferred_post_load_finishes(monkeypatch):
    parser = _Parser(
        objects=[{"nickname": "sun", "pos": "1000,0,2000", "size": "50"}],
        zones=[{"nickname": "zone_a"}],
    )
    window = _build_window(parser=parser)
    window.view3d_switch = _Toggle(False)
    window._primary_game_path = lambda: "C:/Freelancer"
    quick_calls: list[str] = []
    window._populate_quick_editor_options = lambda game_path: quick_calls.append(str(game_path))

    single_shot_calls: list[int] = []

    def _fake_single_shot(delay: int, callback):
        single_shot_calls.append(int(delay))
        callback()

    monkeypatch.setattr(runtime, "SolarObject", _FakeSolarObject)
    monkeypatch.setattr(runtime, "ZoneItem", _FakeZoneItem)
    monkeypatch.setattr(runtime.QTimer, "singleShot", staticmethod(_fake_single_shot))

    runtime.apply_system_document(
        window,
        "C:/mods/DATA/UNIVERSE/li01.ini",
        [("system", [("nickname", "li01")])],
        restore=None,
        dirty=False,
        doc=None,
    )

    assert single_shot_calls == [0]
    assert quick_calls == ["C:/Freelancer"]
    assert window.loading_calls == [(True, runtime.tr("status.preparing_system_view")), (False, None)]


def test_load_system_resets_pending_state_and_delegates_to_apply():
    parser = _Parser(parsed=[("system", [("nickname", "li01")])])
    window = _build_window(parser=parser)
    window._flight_lock_active = True
    restore = QTransform()

    runtime.load_system(window, "C:/mods/DATA/UNIVERSE/li01.ini", restore=restore)

    assert window.flight_mode is False
    assert window._pending_conn is None
    assert window._pending_create is None
    assert window._pending_light_source is None
    assert window._pending_new_object is False
    assert window._pending_tradelane is None
    assert window._pending_tl_reposition is None
    assert window.placement_mode == (False, "")
    assert parser.parse_calls == ["C:/mods/DATA/UNIVERSE/li01.ini"]
    assert window.applied_document == {
        "path": "C:/mods/DATA/UNIVERSE/li01.ini",
        "sections": [("system", [("nickname", "li01")])],
        "restore": restore,
        "dirty": False,
    }
    assert window.loading_calls == [(True, runtime.tr("status.loading_system")), (False, None)]


def test_collect_system_document_payload_uses_window_boundary_resolver():
    parser = _Parser(
        objects=[],
        zones=[],
        parsed=[("LightSource", [("nickname", "li01_system_light"), ("range", "120000"), ("type", "DIRECTIONAL")])],
    )
    window = _build_window(parser=parser)
    window._resolve_system_boundary_radius_world = lambda path, sections=None, raw_objects=None: 44117.64705882353

    payload = runtime.collect_system_document_payload(window, "C:/mods/DATA/UNIVERSE/li01.ini")

    assert payload["boundary_radius"] == pytest.approx(44117.64705882353)
