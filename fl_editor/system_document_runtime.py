"""Runtime helpers for applying and loading system editor documents."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QTransform
from PySide6.QtWidgets import QGraphicsItem

from .async_ui_runtime import start_async_view_load
from .i18n import tr
from .models import SolarObject, ZoneItem


def _reset_change_tracking(window: Any, doc: object | None) -> None:
    if doc is not None and hasattr(doc, "change_snapshots"):
        window._change_snapshots = deepcopy(getattr(doc, "change_snapshots", []))
        window._last_snapshot_fp = str(getattr(doc, "last_snapshot_fp", "") or "")
        window._history_restore_in_progress = bool(getattr(doc, "history_restore_in_progress", False))
        window._undo_actions = deepcopy(getattr(doc, "undo_actions", []))
        window._change_log_entries = list(getattr(doc, "change_log_entries", []))
        return
    window._change_snapshots = []
    window._last_snapshot_fp = ""
    window._history_restore_in_progress = False
    window._undo_actions = []
    window._change_log_entries = []


def _system_boundary_radius(raw_objects: list[dict[str, Any]]) -> float:
    rmax = 0.0
    for data in raw_objects:
        pp = [float(c.strip()) for c in str(data.get("pos", "0,0,0")).split(",")]
        fx = pp[0] if len(pp) > 0 else 0.0
        fz = pp[2] if len(pp) > 2 else (pp[1] if len(pp) > 1 else 0.0)
        dist = (fx * fx + fz * fz) ** 0.5
        size = 0.0
        if "size" in data:
            try:
                size = float(str(data["size"]).split(",")[0])
            except Exception:
                pass
        rmax = max(rmax, dist + size)
    return rmax


def _build_workspace_state(window: Any) -> Any:
    factory = getattr(window, "_workspace_layout_state_factory", None)
    kwargs = {
        "left_widget": getattr(window, "left_ini_panel", None),
        "left_sidebar_visible": True,
        "right_panel_visible": True,
        "legend_visible": True,
        "zoom_controls_visible": True,
        "view3d_toggle_visible": True,
        "view3d_toggle_enabled": True,
        "view3d_toggle_checked": bool(window.view3d_switch.isChecked()),
        "sidebar_3d_enabled": True,
    }
    if callable(factory):
        return factory(**kwargs)
    return SimpleNamespace(**kwargs)


def _rebuild_system_scene(window: Any, raw_zones: list[dict[str, Any]], raw_objects: list[dict[str, Any]]) -> None:
    window.view._scene.clear()
    window.view._scene.setSceneRect(0, 0, 0, 0)
    window._apply_scene_wallpaper()
    window._objects, window._zones = [], []
    window._selected = None
    window._clear_selection_ui()
    window._hide_zone_extra_editors()

    for zone_data in raw_zones:
        try:
            zone = ZoneItem(zone_data, window._scale)
            if hasattr(zone, "set_label_visibility"):
                zone.set_label_visibility(window._viewer_text_visible)
            window.view._scene.addItem(zone)
            window._zones.append(zone)
        except Exception:
            pass

    movable = window.move_cb.isChecked()
    for object_data in raw_objects:
        try:
            obj = SolarObject(object_data, window._scale)
            if getattr(obj, "label", None):
                obj.label.setPlainText(window._object_display_label(obj))
            if hasattr(obj, "set_label_visibility"):
                obj.set_label_visibility(window._viewer_text_visible)
            obj.setFlag(QGraphicsItem.ItemIsMovable, movable)
            window.view._scene.addItem(obj)
            window._objects.append(obj)
        except Exception:
            pass


def _apply_system_document_data(
    window: Any,
    path: str,
    sections: list[tuple[str, list[tuple[str, str]]]],
    raw_zones: list[dict[str, Any]],
    raw_objects: list[dict[str, Any]],
    boundary_radius: float,
    restore: QTransform | None = None,
    dirty: bool = False,
    doc: object | None = None,
) -> None:
    window._filepath = path
    window._sections = deepcopy(sections)
    _reset_change_tracking(window, doc)
    window._restore_system_tab_pending_state(doc if doc is not None and hasattr(doc, "pending_zone") else None)
    window._reload_dll_name_cache()

    extent_world = max(float(boundary_radius or 0.0), 10000.0)
    window._scale = 500.0 / extent_world
    window.view.set_world_scale(window._scale)
    window.view.set_zoom_out_limit_to_scene(False)
    window.view.set_unbounded_pan(False)
    window.view.set_left_drag_pan_enabled(False)
    window._set_system_zoom_controls_visible(True)
    window._clear_move_delta_indicator()

    _rebuild_system_scene(window, raw_zones, raw_objects)
    window._draw_system_reference_overlay(float(boundary_radius or 0.0))
    window._apply_group_visibility()
    if window._avoid_label_overlap:
        window._reflow_2d_labels()
    else:
        window._reset_2d_label_positions()

    sys_nick = window._system_nickname_for_path(path)
    name = window._system_display_name(sys_nick)
    if hasattr(window, "_sys_header_lbl"):
        window._sys_header_lbl.setText(window._format_system_header_text(sys_nick))
    window.info_lbl.setText(
        tr("info.system").format(filename=Path(path).name, obj_count=len(window._objects), zone_count=len(window._zones))
    )
    window._rebuild_object_combo()
    window.setWindowTitle(window._title_with_version(tr("app.title_system").format(name=name)))
    window.statusBar().showMessage(
        tr("status.system_loaded").format(name=name, obj_count=len(window._objects), zone_count=len(window._zones))
    )
    window._apply_workspace_layout(_build_workspace_state(window))
    if hasattr(window, "_status_grp"):
        window._status_grp.setVisible(False)
    window._set_global_nav_active("universe")
    window._new_system_action.setVisible(False)
    window._uni_save_action.setVisible(False)
    window._uni_undo_action.setVisible(False)
    window._uni_delete_action.setVisible(False)
    window.uni_delete_btn.setEnabled(False)
    window._ids_scan_action.setVisible(False)
    window._ids_import_action.setVisible(False)
    window._set_dirty(False)
    if restore:
        window.view.setTransform(restore)
        window._sync_zoom_slider_from_view(window.view.current_zoom_factor())
    else:
        window._fit()
    QTimer.singleShot(0, window._refresh_3d_scene)
    window._refresh_viewer_move_border()
    window._populate_system_options()
    if callable(getattr(window, "_apply_system_name_mode_to_ui", None)):
        window._apply_system_name_mode_to_ui()
    if hasattr(window, "_sys_header_lbl"):
        window._sys_header_lbl.setText(window._format_system_header_text(sys_nick))
    window.setWindowTitle(window._title_with_version(tr("app.title_system").format(name=window._system_display_name(sys_nick))))
    window._build_standard_menu_bar()
    window._refresh_system_fields()
    if hasattr(window, "_change_undo_btn"):
        window._change_undo_btn.setEnabled(bool(window._change_snapshots) or bool(window._undo_actions))
    if hasattr(window, "change_log_view"):
        try:
            window.change_log_view.setPlainText("\n".join(window._collect_change_log_lines()))
        except Exception:
            pass
    if dirty:
        window._set_dirty(True)
    if callable(getattr(window, "_primary_game_path", None)) and callable(getattr(window, "_populate_quick_editor_options", None)):
        QTimer.singleShot(0, lambda gp=window._primary_game_path(): window._populate_quick_editor_options(gp))


def collect_system_document_payload(window: Any, path: str, restore: QTransform | None = None) -> dict[str, Any]:
    sections = window._parser.parse(path)
    raw_objects = window._parser.get_objects(sections)
    raw_zones = window._parser.get_zones(sections)
    return {
        "path": str(path),
        "sections": sections,
        "raw_objects": raw_objects,
        "raw_zones": raw_zones,
        "boundary_radius": _system_boundary_radius(raw_objects),
        "restore": restore,
    }


def apply_system_document_payload(window: Any, payload: dict[str, Any], *, dirty: bool = False, doc: object | None = None) -> None:
    _apply_system_document_data(
        window,
        str(payload.get("path", "") or ""),
        list(payload.get("sections", []) or []),
        list(payload.get("raw_zones", []) or []),
        list(payload.get("raw_objects", []) or []),
        float(payload.get("boundary_radius", 0.0) or 0.0),
        restore=payload.get("restore"),
        dirty=dirty,
        doc=doc,
    )


def apply_system_document(
    window: Any,
    path: str,
    sections: list[tuple[str, list[tuple[str, str]]]],
    restore: QTransform | None = None,
    dirty: bool = False,
    doc: object | None = None,
) -> None:
    raw_objects = window._parser.get_objects(sections)
    raw_zones = window._parser.get_zones(sections)
    _apply_system_document_data(
        window,
        path,
        sections,
        raw_zones,
        raw_objects,
        _system_boundary_radius(raw_objects),
        restore=restore,
        dirty=dirty,
        doc=doc,
    )


def load_system(window: Any, path: str, restore: QTransform | None = None) -> None:
    if window._flight_lock_active:
        window._set_flight_mode(False)
    window._pending_conn = None
    window._pending_create = None
    window._pending_light_source = None
    window._pending_new_object = False
    window._pending_tradelane = None
    window._pending_tl_reposition = None
    window._set_placement_mode(False)
    if not isinstance(window, QObject):
        if callable(getattr(window, "_set_loading_visible", None)):
            window._set_loading_visible(True, tr("status.loading"))
        try:
            sections = window._parser.parse(path)
            if callable(getattr(window, "_apply_system_document", None)):
                window._apply_system_document(path, sections, restore=restore, dirty=False)
            else:
                apply_system_document(window, path, sections, restore=restore, dirty=False)
        finally:
            if callable(getattr(window, "_set_loading_visible", None)):
                window._set_loading_visible(False)
        return

    start_async_view_load(
        window,
        key="system-load",
        worker=lambda: collect_system_document_payload(window, path, restore=restore),
        apply_result=lambda payload: apply_system_document_payload(window, payload, dirty=False),
        loading_message=tr("status.loading"),
        error_title=tr("msg.load_error"),
    )
