from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtGui import QTransform

from fl_editor.system_tab_document_runtime import (
    capture_system_tab_document,
    capture_system_tab_state,
    center_update_current_system_tab_title,
    preserve_active_system_tab_document,
    restore_system_tab_state,
)


class _Doc:
    def __init__(self, path: str = ""):
        self.path = path
        self.sections = []
        self.dirty = False
        self.change_snapshots = []
        self.last_snapshot_fp = ""
        self.history_restore_in_progress = False
        self.undo_actions = []
        self.change_log_entries = []
        self.pending_zone = None
        self.pending_simple_zone = None
        self.pending_exclusion_zone = None
        self.pending_light_source = None
        self.pending_template_object = None
        self.pending_buoy = None
        self.pending_create = None
        self.pending_new_object = False
        self.pending_conn = None
        self.pending_snapshots = []
        self.pending_new_system = None
        self.pending_tradelane = None
        self.pending_tl_reposition = None
        self.pending_base = None
        self.pending_dock_ring = None
        self.pending_mode_text = ""
        self.left_panel_mode = ""
        self.left_sidebar_visible = True
        self.right_panel_visible = True
        self.legend_visible = True
        self.zoom_controls_visible = True
        self.view3d_toggle_visible = True
        self.view3d_toggle_enabled = True
        self.sidebar_3d_enabled = True
        self.editor_text = ""
        self.editor_cursor_pos = 0
        self.editor_visible = True
        self.apply_visible = True
        self.zone_link_text = ""
        self.zone_link_visible = False
        self.zone_file_text = ""
        self.zone_file_visible = False
        self.object_label_text = ""
        self.quick_arch = ""
        self.quick_loadout = ""
        self.quick_faction = ""
        self.quick_rep = ""
        self.view_transform = None
        self.use_3d = False
        self.camera_state = None
        self.selected_kind = ""
        self.selected_nickname = ""


class _TextCursor:
    def __init__(self, position: int = 0):
        self._position = int(position)

    def position(self):
        return self._position

    def setPosition(self, value: int):
        self._position = int(value)


class _Editor:
    def __init__(self, text: str = "", visible: bool = True):
        self._text = text
        self._visible = visible
        self._cursor = _TextCursor()

    def toPlainText(self):
        return self._text

    def setPlainText(self, text: str):
        self._text = str(text)

    def isVisible(self):
        return self._visible

    def setVisible(self, visible: bool):
        self._visible = bool(visible)

    def textCursor(self):
        return self._cursor

    def setTextCursor(self, cursor):
        self._cursor = cursor


class _VisibleWidget:
    def __init__(self, visible: bool = True, enabled: bool = True):
        self._visible = bool(visible)
        self._enabled = bool(enabled)

    def isVisible(self):
        return self._visible

    def setVisible(self, visible: bool):
        self._visible = bool(visible)

    def isEnabled(self):
        return self._enabled

    def setEnabled(self, enabled: bool):
        self._enabled = bool(enabled)


class _LineEdit:
    def __init__(self, text: str = ""):
        self._text = text

    def text(self):
        return self._text

    def setText(self, text: str):
        self._text = str(text)


class _Combo:
    def __init__(self, text: str = ""):
        self._text = text

    def currentText(self):
        return self._text

    def setCurrentText(self, text: str):
        self._text = str(text)


class _Switch:
    def __init__(self, checked: bool = False, visible: bool = True, enabled: bool = True):
        self.checked = bool(checked)
        self.visible = bool(visible)
        self.enabled = bool(enabled)
        self.blocked = []

    def isChecked(self):
        return self.checked

    def setChecked(self, value: bool):
        self.checked = bool(value)

    def blockSignals(self, value: bool):
        self.blocked.append(bool(value))

    def isVisible(self):
        return self.visible

    def isEnabled(self):
        return self.enabled


class _View:
    def __init__(self):
        self._transform = QTransform()

    def transform(self):
        return self._transform

    def setTransform(self, transform):
        self._transform = QTransform(transform)

    def current_zoom_factor(self):
        return 1.0


class _LeftStack:
    def __init__(self, current=None, visible: bool = True):
        self._current = current
        self._visible = bool(visible)

    def currentWidget(self):
        return self._current

    def setCurrentWidget(self, widget):
        self._current = widget

    def isVisible(self):
        return self._visible

    def setVisible(self, visible: bool):
        self._visible = bool(visible)


def _build_window():
    spec = {"key": "system:li01", "document": None}
    selected = SimpleNamespace(nickname="Li01", __class__=SimpleNamespace)
    window = SimpleNamespace()
    window._filepath = "C:/mods/DATA/UNIVERSE/li01.ini"
    window._sections = [("system", [("nickname", "li01")])]
    window._dirty = True
    window._change_snapshots = [{"a": 1}]
    window._last_snapshot_fp = "snap.json"
    window._history_restore_in_progress = False
    window._undo_actions = ["undo"]
    window._change_log_entries = ["changed"]
    window._pending_zone = {"zone": 1}
    window._pending_simple_zone = None
    window._pending_exclusion_zone = None
    window._pending_light_source = None
    window._pending_template_object = None
    window._pending_buoy = None
    window._pending_create = None
    window._pending_new_object = True
    window._pending_conn = {"conn": 1}
    window._pending_snapshots = [1]
    window._pending_new_system = {"sys": 1}
    window._pending_tradelane = {"tl": 1}
    window._pending_tl_reposition = {"move": 1}
    window._pending_base = {"base": 1}
    window._pending_dock_ring = {"dock": 1}
    window.mode_lbl = SimpleNamespace(_text="place", text=lambda: "place", setText=lambda text: setattr(window.mode_lbl, "_text", text))
    window.editor = _Editor("editor text", True)
    window.editor.textCursor().setPosition(4)
    window.apply_btn = SimpleNamespace(isVisible=lambda: True, setVisible=lambda value: setattr(window, "apply_visible", bool(value)))
    window.zone_link_editor = _Editor("zone link", True)
    window.zone_link_lbl = SimpleNamespace(setVisible=lambda value: setattr(window, "zone_link_lbl_visible", bool(value)))
    window.zone_file_editor = _Editor("zone file", False)
    window.zone_file_lbl = SimpleNamespace(setVisible=lambda value: setattr(window, "zone_file_lbl_visible", bool(value)))
    window.name_lbl = SimpleNamespace(text=lambda: "Object", setText=lambda text: setattr(window, "name_label", text))
    window.arch_cb = _Combo("arch")
    window.loadout_cb = _Combo("loadout")
    window.faction_cb = _Combo("faction")
    window.rep_edit = _LineEdit("0.9")
    window._system_document_factory = _Doc
    window._center_current_tab_key = "system:li01"
    window._center_tab_specs = [spec]
    window._center_system_tab_spec = lambda key=None: spec
    window.view = _View()
    window.view3d_switch = _Switch(True)
    window.view3d = SimpleNamespace(
        get_camera_state=lambda: {"cam": 1},
        set_camera_state=lambda state: setattr(window, "restored_camera_state", state),
        set_selected=lambda item: setattr(window, "view3d_selected", item),
    )
    window._selected = selected
    window._objects = [selected]
    window._zones = []
    window._sync_zoom_slider_from_view = lambda zoom: setattr(window, "synced_zoom", zoom)
    window._select = lambda item: setattr(window, "selected_object", item)
    window._select_zone = lambda item: setattr(window, "selected_zone", item)
    window._toggle_3d_view = lambda enabled: setattr(window, "toggle_3d", bool(enabled))
    window._clear_pending_visual_helpers = lambda: setattr(window, "pending_visuals_cleared", True)
    window.save_conn_btn = SimpleNamespace(setVisible=lambda value: setattr(window, "save_conn_visible", bool(value)))
    window.create_conn_btn = SimpleNamespace(setEnabled=lambda value: setattr(window, "create_conn_enabled", bool(value)))
    window._has_pending_placement = lambda: True
    window._set_placement_mode = lambda enabled, _text="": setattr(window, "placement_mode", bool(enabled))
    window.browser = object()
    window.left_ini_panel = object()
    window.left_uni_panel = object()
    window.left_trade_panel = object()
    window.left_name_panel = object()
    window.left_stack = _LeftStack(window.left_ini_panel, True)
    window.right_panel = _VisibleWidget(True)
    window.legend_box = _VisibleWidget(True)
    window._menu_zoom_host = _VisibleWidget(True)
    window._sidebar_3d_btn = _VisibleWidget(True, True)
    window._apply_workspace_layout = lambda state: setattr(window, "applied_layout", state)
    window._center_tab_index_for_key = lambda key: 0
    window._system_tab_title = lambda path: f"System::{path}"
    window._center_sync_tab_bar = lambda: setattr(window, "tab_bar_synced", True)
    return window


def test_capture_system_tab_document_and_state_store_values():
    window = _build_window()

    capture_system_tab_state(window)
    capture_system_tab_document(window)

    doc = window._center_tab_specs[0]["document"]
    assert isinstance(doc, _Doc)
    assert isinstance(doc.view_transform, QTransform)
    assert doc.use_3d is True
    assert doc.camera_state == {"cam": 1}
    assert doc.selected_nickname == "Li01"
    assert doc.editor_text == "editor text"
    assert doc.editor_cursor_pos == 4
    assert doc.quick_arch == "arch"
    assert doc.pending_new_object is True
    assert doc.left_panel_mode == "ini"
    assert doc.left_sidebar_visible is True


def test_restore_system_tab_state_applies_selection_camera_and_editor_state():
    window = _build_window()
    doc = _Doc(path=window._filepath)
    doc.view_transform = QTransform()
    doc.use_3d = True
    doc.camera_state = {"cam": 2}
    doc.selected_kind = "object"
    doc.selected_nickname = "li01"
    doc.pending_snapshots = [1]
    doc.pending_mode_text = "placing"
    doc.editor_text = "restored"
    doc.editor_cursor_pos = 3
    doc.editor_visible = True
    doc.apply_visible = True
    doc.zone_link_text = "zl"
    doc.zone_link_visible = True
    doc.zone_file_text = "zf"
    doc.zone_file_visible = True
    doc.object_label_text = "Label"
    doc.quick_arch = "arch2"
    doc.quick_loadout = "load2"
    doc.quick_faction = "fac2"
    doc.quick_rep = "1.0"
    doc.left_panel_mode = "browser"
    doc.left_sidebar_visible = True
    doc.right_panel_visible = False
    doc.legend_visible = False
    doc.zoom_controls_visible = True
    doc.view3d_toggle_visible = True
    doc.view3d_toggle_enabled = True
    doc.sidebar_3d_enabled = False
    window._center_tab_specs[0]["document"] = doc

    restore_system_tab_state(window)

    assert window.synced_zoom == 1.0
    assert window.selected_object.nickname == "Li01"
    assert window.toggle_3d is True
    assert window.restored_camera_state == {"cam": 2}
    assert window.view3d_selected.nickname == "Li01"
    assert window.pending_visuals_cleared is True
    assert window.save_conn_visible is True
    assert window.create_conn_enabled is False
    assert window.placement_mode is True
    assert window.applied_layout.left_widget is window.browser
    assert window.applied_layout.right_panel_visible is False
    assert window.applied_layout.legend_visible is False
    assert window.applied_layout.sidebar_3d_enabled is False
    assert window.editor.toPlainText() == "restored"
    assert window.arch_cb.currentText() == "arch2"
    assert window.rep_edit.text() == "1.0"


def test_title_and_preserve_helpers_use_active_system_key():
    window = _build_window()

    center_update_current_system_tab_title(window)
    preserve_active_system_tab_document(window)

    assert "System::" in window._center_tab_specs[0]["title"]
    assert window.tab_bar_synced is True
    doc = window._center_tab_specs[0]["document"]
    assert isinstance(doc, _Doc)
    assert doc.selected_nickname == "Li01"
    assert doc.editor_text == "editor text"
