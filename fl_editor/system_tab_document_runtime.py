"""Runtime helpers for system-tab document and editor state."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from typing import Any

from PySide6.QtGui import QTransform

from .system_tabs import apply_dirty_system_tab_title
from .models import ZoneItem
from .system_editor_persistence import build_saved_system_sections


def _left_panel_mode(window: Any) -> str:
    if not hasattr(window, "left_stack"):
        return "ini"
    current = window.left_stack.currentWidget()
    mapping = (
        ("browser", getattr(window, "browser", None)),
        ("ini", getattr(window, "left_ini_panel", None)),
        ("universe", getattr(window, "left_uni_panel", None)),
        ("trade", getattr(window, "left_trade_panel", None)),
        ("name", getattr(window, "left_name_panel", None)),
    )
    for key, widget in mapping:
        if widget is not None and current is widget:
            return key
    return "ini"


def _left_widget_for_mode(window: Any, mode: str) -> object | None:
    mapping = {
        "browser": getattr(window, "browser", None),
        "ini": getattr(window, "left_ini_panel", None),
        "universe": getattr(window, "left_uni_panel", None),
        "trade": getattr(window, "left_trade_panel", None),
        "name": getattr(window, "left_name_panel", None),
    }
    return mapping.get(str(mode or "").strip().lower(), getattr(window, "left_ini_panel", None))


def capture_system_tab_state(window: Any, key: str | None = None) -> None:
    spec = window._center_system_tab_spec(key)
    if spec is None or not window._filepath:
        return
    doc = spec.get("document")
    if doc is None or not hasattr(doc, "path"):
        factory = getattr(window, "_system_document_factory", None)
        if factory is None:
            return
        doc = factory(path=str(window._filepath))
        spec["document"] = doc
    try:
        doc.view_transform = QTransform(window.view.transform())
    except Exception:
        pass
    try:
        doc.use_3d = bool(window.view3d_switch.isChecked())
    except Exception:
        doc.use_3d = False
    try:
        if hasattr(window.view3d, "get_camera_state"):
            cam_state = window.view3d.get_camera_state()
            if isinstance(cam_state, dict):
                doc.camera_state = dict(cam_state)
    except Exception:
        pass
    if window._selected is None:
        doc.selected_kind = ""
        doc.selected_nickname = ""
    else:
        doc.selected_kind = "zone" if isinstance(window._selected, ZoneItem) else "object"
        doc.selected_nickname = str(getattr(window._selected, "nickname", "") or "").strip()


def _restore_system_tab_pending_state(window: Any, doc: object | None) -> None:
    is_doc = doc is not None and hasattr(doc, "pending_zone")
    window._pending_zone = deepcopy(doc.pending_zone) if is_doc else None
    window._pending_simple_zone = deepcopy(doc.pending_simple_zone) if is_doc else None
    window._pending_exclusion_zone = deepcopy(doc.pending_exclusion_zone) if is_doc else None
    window._pending_light_source = deepcopy(doc.pending_light_source) if is_doc else None
    window._pending_template_object = deepcopy(doc.pending_template_object) if is_doc else None
    window._pending_buoy = deepcopy(doc.pending_buoy) if is_doc else None
    window._pending_create = deepcopy(doc.pending_create) if is_doc else None
    window._pending_new_object = bool(doc.pending_new_object) if is_doc else False
    window._pending_conn = deepcopy(doc.pending_conn) if is_doc else None
    window._pending_snapshots = deepcopy(doc.pending_snapshots) if is_doc else []
    window._pending_new_system = deepcopy(doc.pending_new_system) if is_doc else None
    window._pending_tradelane = deepcopy(doc.pending_tradelane) if is_doc else None
    window._pending_tl_reposition = deepcopy(doc.pending_tl_reposition) if is_doc else None
    window._pending_base = deepcopy(doc.pending_base) if is_doc else None
    window._pending_dock_ring = deepcopy(doc.pending_dock_ring) if is_doc else None
    window._pending_ring_attach = deepcopy(doc.pending_ring_attach) if is_doc else None
    window._clear_pending_visual_helpers()
    if hasattr(window, "save_conn_btn"):
        window.save_conn_btn.setVisible(bool(window._pending_snapshots))
    if hasattr(window, "create_conn_btn"):
        window.create_conn_btn.setEnabled(not bool(window._pending_snapshots))
    if window._has_pending_placement():
        mode_text = str(getattr(doc, "pending_mode_text", "") or "").strip() if is_doc else ""
        window._set_placement_mode(True, "")
        if mode_text:
            window.mode_lbl.setText(mode_text)
    else:
        window._set_placement_mode(False)


def restore_system_tab_editor_state(window: Any, doc: object | None) -> None:
    if doc is None or not hasattr(doc, "editor_text"):
        return
    if hasattr(window, "left_stack") and hasattr(window, "left_ini_panel"):
        window.left_stack.setCurrentWidget(window.left_ini_panel)
    if hasattr(window, "editor"):
        window.editor.setPlainText(str(doc.editor_text or ""))
        window.editor.setVisible(bool(doc.editor_visible))
        try:
            tc = window.editor.textCursor()
            tc.setPosition(max(0, min(int(doc.editor_cursor_pos), len(window.editor.toPlainText()))))
            window.editor.setTextCursor(tc)
        except Exception:
            pass
    if hasattr(window, "apply_btn"):
        window.apply_btn.setVisible(bool(doc.apply_visible))
    if hasattr(window, "zone_link_editor"):
        window.zone_link_editor.setPlainText(str(doc.zone_link_text or ""))
        window.zone_link_editor.setVisible(bool(doc.zone_link_visible))
    if hasattr(window, "zone_link_lbl"):
        window.zone_link_lbl.setVisible(bool(doc.zone_link_visible))
    if hasattr(window, "zone_file_editor"):
        window.zone_file_editor.setPlainText(str(doc.zone_file_text or ""))
        window.zone_file_editor.setVisible(bool(doc.zone_file_visible))
    if hasattr(window, "zone_file_lbl"):
        window.zone_file_lbl.setVisible(bool(doc.zone_file_visible))
    if hasattr(window, "name_lbl") and getattr(doc, "object_label_text", ""):
        window.name_lbl.setText(str(doc.object_label_text))
    if hasattr(window, "arch_cb"):
        window.arch_cb.setCurrentText(str(doc.quick_arch or ""))
    if hasattr(window, "loadout_cb"):
        window.loadout_cb.setCurrentText(str(doc.quick_loadout or ""))
    if hasattr(window, "faction_cb"):
        window.faction_cb.setCurrentText(str(doc.quick_faction or ""))
    if hasattr(window, "rep_edit"):
        window.rep_edit.setText(str(doc.quick_rep or ""))


def restore_system_tab_state(window: Any, key: str | None = None) -> None:
    spec = window._center_system_tab_spec(key)
    if spec is None:
        return
    doc = spec.get("document")
    apply_layout = getattr(window, "_apply_workspace_layout", None)
    if callable(apply_layout):
        apply_layout(
            SimpleNamespace(
                left_widget=_left_widget_for_mode(window, getattr(doc, "left_panel_mode", "ini")),
                left_sidebar_visible=bool(getattr(doc, "left_sidebar_visible", True)),
                right_panel_visible=bool(getattr(doc, "right_panel_visible", True)),
                legend_visible=bool(getattr(doc, "legend_visible", True)),
                zoom_controls_visible=bool(getattr(doc, "zoom_controls_visible", True)),
                view3d_toggle_visible=bool(getattr(doc, "view3d_toggle_visible", True)),
                view3d_toggle_enabled=bool(getattr(doc, "view3d_toggle_enabled", True)),
                view3d_toggle_checked=bool(getattr(doc, "use_3d", False)),
                sidebar_3d_enabled=bool(getattr(doc, "sidebar_3d_enabled", True)),
            )
        )
    transform = getattr(doc, "view_transform", None)
    if isinstance(transform, QTransform):
        try:
            window.view.setTransform(QTransform(transform))
            if hasattr(window.view, "set_zoom_factor") and hasattr(window.view, "current_zoom_factor"):
                window.view.set_zoom_factor(window.view.current_zoom_factor())
            window._sync_zoom_slider_from_view(window.view.current_zoom_factor())
        except Exception:
            pass
    selected_item = None
    want_nick = str(getattr(doc, "selected_nickname", "") or "").strip().lower()
    want_kind = str(getattr(doc, "selected_kind", "") or "").strip().lower()
    if want_nick:
        if want_kind == "zone":
            selected_item = next((z for z in window._zones if z.nickname.strip().lower() == want_nick), None)
            if selected_item is not None:
                window._select_zone(selected_item)
        else:
            selected_item = next(
                (o for o in window._objects if o.nickname.strip().lower() == want_nick and not hasattr(o, "sys_path")),
                None,
            )
            if selected_item is not None:
                window._select(selected_item)
    use_3d = bool(getattr(doc, "use_3d", False))
    window.view3d_switch.blockSignals(True)
    window.view3d_switch.setChecked(use_3d)
    window.view3d_switch.blockSignals(False)
    window._toggle_3d_view(use_3d)
    cam_state = getattr(doc, "camera_state", None)
    if use_3d and isinstance(cam_state, dict) and hasattr(window.view3d, "set_camera_state"):
        try:
            window.view3d.set_camera_state(cam_state)
        except Exception:
            pass
    if use_3d and selected_item is not None:
        try:
            window.view3d.set_selected(selected_item)
        except Exception:
            pass
    _restore_system_tab_pending_state(window, doc)
    restore_system_tab_editor_state(window, doc)


def capture_system_tab_document(window: Any, key: str | None = None) -> None:
    spec = window._center_system_tab_spec(key)
    if spec is None or not window._filepath:
        return
    try:
        doc = spec.get("document")
        if doc is None or not hasattr(doc, "path"):
            factory = getattr(window, "_system_document_factory", None)
            if factory is None:
                return
            doc = factory(path=str(window._filepath))
        doc.path = str(window._filepath)
        saved_sections = build_saved_system_sections(
            list(getattr(window, "_sections", []) or []),
            list(getattr(window, "_objects", []) or []),
            list(getattr(window, "_zones", []) or []),
            extract_nickname_from_entries=window._extract_nickname_from_entries,
        )
        doc.sections = deepcopy(saved_sections)
        doc.dirty = bool(window._dirty)
        doc.change_snapshots = deepcopy(window._change_snapshots)
        doc.last_snapshot_fp = str(window._last_snapshot_fp or "")
        doc.history_restore_in_progress = bool(window._history_restore_in_progress)
        doc.undo_actions = deepcopy(window._undo_actions)
        doc.change_log_entries = list(window._change_log_entries)
        doc.pending_zone = deepcopy(window._pending_zone)
        doc.pending_simple_zone = deepcopy(window._pending_simple_zone)
        doc.pending_exclusion_zone = deepcopy(window._pending_exclusion_zone)
        doc.pending_light_source = deepcopy(window._pending_light_source)
        doc.pending_template_object = deepcopy(window._pending_template_object)
        doc.pending_buoy = deepcopy(window._pending_buoy)
        doc.pending_create = deepcopy(window._pending_create)
        doc.pending_new_object = bool(window._pending_new_object)
        doc.pending_conn = deepcopy(window._pending_conn)
        doc.pending_snapshots = deepcopy(window._pending_snapshots)
        doc.pending_new_system = deepcopy(window._pending_new_system)
        doc.pending_tradelane = deepcopy(window._pending_tradelane)
        doc.pending_tl_reposition = deepcopy(window._pending_tl_reposition)
        doc.pending_base = deepcopy(window._pending_base)
        doc.pending_dock_ring = deepcopy(window._pending_dock_ring)
        doc.pending_ring_attach = deepcopy(window._pending_ring_attach)
        doc.pending_mode_text = str(window.mode_lbl.text() or "")
        doc.left_panel_mode = _left_panel_mode(window)
        doc.left_sidebar_visible = bool(window.left_stack.isVisible()) if hasattr(window, "left_stack") else True
        doc.right_panel_visible = bool(window.right_panel.isVisible()) if hasattr(window, "right_panel") else True
        doc.legend_visible = bool(window.legend_box.isVisible()) if hasattr(window, "legend_box") else True
        doc.zoom_controls_visible = bool(window._menu_zoom_host.isVisible()) if hasattr(window, "_menu_zoom_host") else True
        doc.view3d_toggle_visible = bool(window.view3d_switch.isVisible()) if hasattr(window, "view3d_switch") else True
        doc.view3d_toggle_enabled = bool(window.view3d_switch.isEnabled()) if hasattr(window, "view3d_switch") else True
        doc.sidebar_3d_enabled = bool(window._sidebar_3d_btn.isEnabled()) if hasattr(window, "_sidebar_3d_btn") else True
        doc.editor_text = window.editor.toPlainText() if hasattr(window, "editor") else ""
        doc.editor_cursor_pos = int(window.editor.textCursor().position()) if hasattr(window, "editor") else 0
        doc.editor_visible = bool(window.editor.isVisible()) if hasattr(window, "editor") else True
        doc.apply_visible = bool(window.apply_btn.isVisible()) if hasattr(window, "apply_btn") else True
        doc.zone_link_text = window.zone_link_editor.toPlainText() if hasattr(window, "zone_link_editor") else ""
        doc.zone_link_visible = bool(window.zone_link_editor.isVisible()) if hasattr(window, "zone_link_editor") else False
        doc.zone_file_text = window.zone_file_editor.toPlainText() if hasattr(window, "zone_file_editor") else ""
        doc.zone_file_visible = bool(window.zone_file_editor.isVisible()) if hasattr(window, "zone_file_editor") else False
        doc.object_label_text = window.name_lbl.text() if hasattr(window, "name_lbl") else ""
        doc.quick_arch = window.arch_cb.currentText() if hasattr(window, "arch_cb") else ""
        doc.quick_loadout = window.loadout_cb.currentText() if hasattr(window, "loadout_cb") else ""
        doc.quick_faction = window.faction_cb.currentText() if hasattr(window, "faction_cb") else ""
        doc.quick_rep = window.rep_edit.text() if hasattr(window, "rep_edit") else ""
        spec["document"] = doc
    except Exception:
        pass


def center_update_current_system_tab_title(window: Any) -> None:
    key = str(window._center_current_tab_key or "").strip()
    if not key.startswith("system:") or not window._filepath:
        return
    idx = window._center_tab_index_for_key(key)
    if idx < 0:
        return
    base_title = window._system_tab_title(window._filepath)
    window._center_tab_specs[idx]["title"] = apply_dirty_system_tab_title(base_title, window._dirty)
    window._center_sync_tab_bar()


def preserve_active_system_tab_document(window: Any) -> None:
    key = str(window._center_current_tab_key or "").strip()
    if not key.startswith("system:"):
        return
    capture_system_tab_state(window, key)
    capture_system_tab_document(window, key)
