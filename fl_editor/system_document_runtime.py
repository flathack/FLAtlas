"""Runtime helpers for applying and loading system editor documents."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from PySide6.QtCore import QObject, QPointF, QRectF, QTimer
from PySide6.QtGui import QTransform
from PySide6.QtWidgets import QGraphicsItem

from .async_ui_runtime import start_async_view_load
from .i18n import tr
from .models import SolarObject, ZoneItem
from .path_utils import is_offmap_helper_object_data


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


def _effective_system_boundary_radius(
    window: Any,
    path: str,
    sections: list[tuple[str, list[tuple[str, str]]]],
    raw_objects: list[dict[str, Any]],
) -> float:
    resolver = getattr(window, "_resolve_system_boundary_radius_world", None)
    if callable(resolver):
        try:
            resolved = resolver(path, sections=sections, raw_objects=raw_objects)
        except TypeError:
            resolved = resolver(path, sections, raw_objects)
        try:
            return float(resolved)
        except Exception:
            pass
    return _system_boundary_radius(raw_objects)


def _restore_view_transform_and_center(window: Any, restore: object | None) -> bool:
    transform = None
    center_scene = None
    if isinstance(restore, dict):
        candidate_transform = restore.get("transform")
        if isinstance(candidate_transform, QTransform):
            transform = candidate_transform
        candidate_center = restore.get("center_scene")
        if isinstance(candidate_center, QPointF):
            center_scene = candidate_center
    elif isinstance(restore, QTransform):
        transform = restore
    if transform is None and center_scene is None:
        return False
    if transform is not None:
        window.view.setTransform(transform)
    if center_scene is not None and hasattr(window.view, "centerOn"):
        try:
            window.view.centerOn(center_scene)
        except Exception:
            pass
    window._sync_zoom_slider_from_view(window.view.current_zoom_factor())
    return True


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
    SolarObject.set_top_view_icon_auto_refresh_enabled(False)
    try:
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
    finally:
        SolarObject.set_top_view_icon_auto_refresh_enabled(True)


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
    if doc is not None and hasattr(doc, "pending_zone"):
        window._restore_system_tab_pending_state(doc)
    window._reload_dll_name_cache()

    grid_half_resolver = getattr(window, "_system_reference_half_extent_world", None)
    grid_half = float(grid_half_resolver(float(boundary_radius or 0.0))) if callable(grid_half_resolver) else 10000.0
    extent_world = max(float(boundary_radius or 0.0), grid_half, 10000.0)
    window._scale = 500.0 / extent_world
    window.view.set_world_scale(window._scale)
    window.view.set_zoom_out_limit_to_scene(True)
    zoom_reference_rect = QRectF()
    reference_rect_resolver = getattr(window, "_system_zoom_reference_rect", None)
    if callable(reference_rect_resolver):
        try:
            zoom_reference_rect = QRectF(reference_rect_resolver(float(boundary_radius or 0.0)))
        except Exception:
            zoom_reference_rect = QRectF()
    if hasattr(window.view, "set_zoom_out_reference_rect"):
        window.view.set_zoom_out_reference_rect(zoom_reference_rect if not zoom_reference_rect.isNull() else None)
    if hasattr(window.view, "set_zoom_in_limit_multiplier"):
        window.view.set_zoom_in_limit_multiplier(40.0)
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
    window._update_base_child_interactivity()
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
    if not _restore_view_transform_and_center(window, restore):
        window._fit()
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
    should_refresh_3d = bool(
        callable(getattr(window, "_refresh_3d_scene", None))
        and hasattr(window, "view3d_switch")
        and bool(window.view3d_switch.isChecked())
    )
    should_populate_quick_options = bool(
        callable(getattr(window, "_primary_game_path", None))
        and callable(getattr(window, "_populate_quick_editor_options", None))
    )

    if not (should_refresh_3d or should_populate_quick_options):
        queue_top_view_icons = getattr(window, "_queue_top_view_icon_refresh", None)
        if callable(queue_top_view_icons):
            queue_top_view_icons(getattr(window, "_objects", []) or [])
        return

    if callable(getattr(window, "_set_loading_visible", None)):
        window._set_loading_visible(True, tr("status.preparing_system_view"))

    def _run_deferred_post_load() -> None:
        try:
            queue_top_view_icons = getattr(window, "_queue_top_view_icon_refresh", None)
            if callable(queue_top_view_icons):
                queue_top_view_icons(getattr(window, "_objects", []) or [])
            if should_refresh_3d:
                # Preserve the restored per-tab camera so deferred scene rebuilds
                # do not snap the user back to the default system framing.
                window._refresh_3d_scene(preserve_camera=True)
            if should_populate_quick_options:
                window._populate_quick_editor_options(window._primary_game_path())
        finally:
            if callable(getattr(window, "_set_loading_visible", None)):
                window._set_loading_visible(False)

    QTimer.singleShot(0, _run_deferred_post_load)


def collect_system_document_payload(window: Any, path: str, restore: QTransform | None = None) -> dict[str, Any]:
    sections = window._parser.parse(path)
    raw_objects = [obj for obj in window._parser.get_objects(sections) if not is_offmap_helper_object_data(obj)]
    raw_zones = window._parser.get_zones(sections)
    return {
        "path": str(path),
        "sections": sections,
        "raw_objects": raw_objects,
        "raw_zones": raw_zones,
        "boundary_radius": _effective_system_boundary_radius(window, str(path), sections, raw_objects),
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
    raw_objects = [obj for obj in window._parser.get_objects(sections) if not is_offmap_helper_object_data(obj)]
    raw_zones = window._parser.get_zones(sections)
    _apply_system_document_data(
        window,
        path,
        sections,
        raw_zones,
        raw_objects,
        _effective_system_boundary_radius(window, str(path), sections, raw_objects),
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
            window._set_loading_visible(True, tr("status.loading_system"))
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
        loading_message=tr("status.loading_system"),
        error_title=tr("msg.load_error"),
    )
