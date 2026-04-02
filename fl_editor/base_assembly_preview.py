from __future__ import annotations

import logging
import math
import os
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from struct import pack as _pack
from typing import Callable

_log = logging.getLogger(__name__)

_CRASH_LOG_PATH = Path(os.environ.get(
    "FLATLAS_CRASH_LOG",
    str(Path.home() / "flatlas_base_builder_crash.log"),
))


def _write_crash_breadcrumb(message: str) -> None:
    """Append a timestamped line to the crash breadcrumb log.

    This is written *before* a Qt3D call so that if the app segfaults
    we know which part / geometry was being processed.
    """
    try:
        with open(_CRASH_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n")
    except Exception:
        pass

from PySide6.QtCore import QByteArray, QEvent, QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QCursor, QColor, QVector3D
from PySide6.QtWidgets import QApplication, QSizePolicy, QVBoxLayout, QWidget

from .freelancer_mesh_data import FreelancerBounds
from .native_preview_qt3d import (
    _disable_backface_culling,
    apply_native_geometry_material,
    build_native_geometry_material,
    build_native_geometry_renderer,
    build_native_wireframe_renderer,
)
from .native_preview_scene_data import NativePreviewSceneData, texture_path_for_geometry
from .orbit_drag import orbit_drag_angles
from .qt3d_compat import (
    QAttribute3D,
    QBuffer3D,
    QCylinderMesh3D,
    QDirectionalLight3D,
    QEntity3D,
    QExtrudedTextMesh3D,
    QGeometry3D,
    QGeometryRenderer3D,
    QObjectPicker3D,
    QOrbitCameraController3D,
    QPhongMaterial3D,
    QQuaternion,
    QT3D_AVAILABLE,
    Qt3DWindow3D,
    QTransform3D,
)
from .view_3d_object_logic import parse_pos, parse_rotate, rotation_quaternion_from_fl


@dataclass
class _AssemblyPreviewItem:
    obj: object
    root_entity: object
    transform: object
    bounds: FreelancerBounds | None
    base_color: QColor
    display_materials: list[object]
    selection_entities: list[object]
    selection_materials: list[object]
    gizmo_entities: dict[str, object]
    gizmo_materials: dict[str, object]


class BaseAssemblyPreviewView(QWidget):
    object_selected = Signal(object)
    context_menu_requested = Signal(object, object)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._native_scene_resolver: Callable[[object], NativePreviewSceneData | None] | None = None
        self._preview_mesh_resolver: Callable[[object], str | Path | None] | None = None
        self._native_scene_overrides: dict[int, NativePreviewSceneData | None] = {}
        self._items_by_key: dict[int, _AssemblyPreviewItem] = {}
        self._objects: list[object] = []
        self._selected_key: int | None = None
        self._anchor_pos = (0.0, 0.0, 0.0)
        self._preview_bounds: FreelancerBounds | None = None
        self._preview_zoom_factor = 1.0
        self._wireframe_visible = True
        self._materials_visible = False
        self._max_orbit_distance_scene = 3500.0
        self._texture_refs: list[object] = []
        self._picker_refs: list[object] = []
        self._suppress_next_pick: bool = False
        self._wireframe_entities: list[object] = []
        self._material_pairs: list[tuple[object, object, object]] = []
        self._pending_deletions: list[object] = []
        self._rebuild_timer: QTimer | None = None
        self._interaction_mode = "navigate"
        self._transform_axis = "x"
        self._transform_begin_handler: Callable[[str, str], bool] | None = None
        self._transform_update_handler: Callable[[float], None] | None = None
        self._transform_finish_handler: Callable[[bool], None] | None = None
        self._pending_drag_mode: str | None = None
        self._active_drag_mode: str | None = None
        self._press_pos = QPointF()
        self._last_drag_pos = QPointF()
        self._drag_accumulated_delta = 0.0
        self._camera_distance = 120.0
        self._camera_yaw_deg = 0.0
        self._camera_pitch_deg = 0.0
        self._ground_grid_entity: object | None = None
        self._axis_indicator_entity: object | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if not QT3D_AVAILABLE:
            return

        self._view3d = Qt3DWindow3D()
        self._frame_graph = getattr(self._view3d, "defaultFrameGraph", lambda: None)()
        self._is_dark_theme = self.palette().window().color().lightnessF() < 0.5
        self._preview_background_color = QColor(0, 0, 0) if self._is_dark_theme else QColor(255, 255, 255)
        self._apply_preview_background_color()

        self._container = QWidget.createWindowContainer(self._view3d, self)
        self._container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._container.setFocusPolicy(Qt.StrongFocus)
        self._container.setMouseTracking(True)
        self._container.installEventFilter(self)
        self._view3d.installEventFilter(self)
        layout.addWidget(self._container)

        self._root = QEntity3D()
        self._light_entity = QEntity3D(self._root)
        self._light = QDirectionalLight3D(self._light_entity)
        self._light.setWorldDirection(QVector3D(-0.7, -1.0, -0.5))
        self._light_entity.addComponent(self._light)

        self._camera = self._view3d.camera()
        self._camera.lens().setPerspectiveProjection(45.0, 16.0 / 9.0, 0.1, 50000.0)
        self._camera.setPosition(QVector3D(0.0, 0.0, 120.0))
        self._camera.setViewCenter(QVector3D(0.0, 0.0, 0.0))

        self._cam_controller = QOrbitCameraController3D(self._root)
        self._cam_controller.setLinearSpeed(100.0)
        self._cam_controller.setLookSpeed(180.0)
        self._cam_controller.setCamera(self._camera)
        if hasattr(self._cam_controller, "setEnabled"):
            self._cam_controller.setEnabled(False)

        self._view3d.setRootEntity(self._root)
        self._sync_camera_polar_state()

    def set_native_scene_resolver(self, resolver) -> None:
        self._native_scene_resolver = resolver if callable(resolver) else None

    def set_native_scene_prepared_payload_resolver(self, _resolver) -> None:
        return None

    def set_preview_mesh_resolver(self, resolver) -> None:
        self._preview_mesh_resolver = resolver if callable(resolver) else None

    def set_interaction_mode(self, mode: str) -> None:
        value = str(mode or "navigate").strip().lower()
        if value not in {"navigate", "move", "rotate"}:
            value = "navigate"
        self._interaction_mode = value
        self._refresh_gizmo_state()

    def set_transform_axis(self, axis: str) -> None:
        value = str(axis or "x").strip().lower()
        if value not in {"x", "y", "z"}:
            value = "x"
        self._transform_axis = value
        self._refresh_gizmo_state()

    def set_transform_handlers(self, begin_handler, update_handler, finish_handler) -> None:
        self._transform_begin_handler = begin_handler if callable(begin_handler) else None
        self._transform_update_handler = update_handler if callable(update_handler) else None
        self._transform_finish_handler = finish_handler if callable(finish_handler) else None

    def set_planet_texture_resolver(self, _resolver) -> None:
        return None

    def set_planet_cloud_texture_resolver(self, _resolver) -> None:
        return None

    def set_planet_ring_resolver(self, _resolver) -> None:
        return None

    def set_native_preview_max_distance_fl(self, _value: float) -> None:
        return None

    def set_native_preview_high_quality_distance_fl(self, _value: float) -> None:
        return None

    def set_reference_overlay_visible(self, _visible: bool) -> None:
        return None

    def set_label_visibility(self, _visible: bool) -> None:
        return None

    def set_max_orbit_distance_scene(self, value: float) -> None:
        try:
            self._max_orbit_distance_scene = max(100.0, float(value))
        except Exception:
            self._max_orbit_distance_scene = 3500.0

    def set_native_wireframe_visible(self, visible: bool) -> None:
        self._wireframe_visible = bool(visible)
        for entity in self._wireframe_entities:
            try:
                entity.setEnabled(self._wireframe_visible)
            except Exception:
                pass

    def set_selected_native_scene_data(self, obj, scene_data) -> None:
        if obj is None:
            return
        key = self._obj_key(obj)
        if scene_data is None:
            self._native_scene_overrides.pop(key, None)
            return
        self._native_scene_overrides[key] = scene_data

    def set_data(self, objects, _zones, _scale: float) -> None:
        self._objects = list(objects or [])
        self._anchor_pos = self._resolve_anchor_pos(self._objects)
        live_keys = {self._obj_key(obj) for obj in self._objects}
        stale_keys = [key for key in self._native_scene_overrides if key not in live_keys]
        for key in stale_keys:
            self._native_scene_overrides.pop(key, None)
        self._rebuild_scene()

    def refresh_native_scene_previews(self) -> None:
        return None

    def clear_scene(self) -> None:
        self._clear_item_entities()
        self._objects = []
        self._preview_bounds = None

    def set_selected(self, obj) -> None:
        next_key = self._obj_key(obj) if obj is not None else None
        if next_key == self._selected_key:
            self._refresh_gizmo_state()
            return
        self._selected_key = next_key
        for key, item in self._items_by_key.items():
            self._apply_item_selection_state(item, key == self._selected_key)
        self._refresh_gizmo_state()

    def center_on_item(self, obj) -> None:
        bounds = self._bounds_for_object(obj)
        if bounds is None:
            bounds = self._preview_bounds
        if bounds is None:
            return
        self._apply_native_preview_bounds(self._camera, bounds)

    def set_preview_zoom_factor(self, zoom_factor: float) -> None:
        try:
            value = float(zoom_factor)
        except Exception:
            return
        self._preview_zoom_factor = max(0.1, min(6.0, value))
        self._apply_camera_pose()

    def get_preview_zoom_factor(self) -> float:
        return float(self._preview_zoom_factor)

    def update_object_position(self, obj, _scale: float) -> None:
        item = self._items_by_key.get(self._obj_key(obj))
        if item is None:
            self._rebuild_scene()
            return
        self._apply_object_transform(item.transform, obj)
        self._preview_bounds = self._aggregate_preview_bounds()

    def update_object_rotation(self, obj) -> None:
        item = self._items_by_key.get(self._obj_key(obj))
        if item is None:
            self._rebuild_scene()
            return
        self._apply_object_transform(item.transform, obj)

    def get_camera_state(self) -> dict[str, object]:
        center = self._camera.viewCenter()
        position = self._camera.position()
        offset = position - center
        return {
            "center": (float(center.x()), float(center.y()), float(center.z())),
            "position": (float(position.x()), float(position.y()), float(position.z())),
            "distance": float(offset.length()),
            "orbit_distance": float(self._camera_distance),
        }

    def set_camera_state(self, state: dict[str, object]) -> None:
        if not isinstance(state, dict):
            return
        center_values = state.get("center")
        position_values = state.get("position")
        if isinstance(center_values, (tuple, list)) and len(center_values) >= 3:
            center = QVector3D(float(center_values[0]), float(center_values[1]), float(center_values[2]))
            self._camera.setViewCenter(center)
        else:
            center = self._camera.viewCenter()
        if isinstance(position_values, (tuple, list)) and len(position_values) >= 3:
            position = QVector3D(float(position_values[0]), float(position_values[1]), float(position_values[2]))
            offset = position - center
            requested_distance = state.get("orbit_distance", state.get("distance"))
            try:
                distance = float(requested_distance)
            except Exception:
                distance = float(offset.length()) * max(0.1, float(self._preview_zoom_factor))
            if distance > 1e-6 and offset.length() > 1e-6:
                position = center + (offset.normalized() * (distance / max(0.1, float(self._preview_zoom_factor))))
                offset = position - center
            distance = float(offset.length())
            max_distance = max(100.0, float(self._max_orbit_distance_scene))
            if distance > max_distance and distance > 1e-6:
                position = center + (offset.normalized() * max_distance)
            self._camera.setPosition(position)
            self._sync_camera_polar_state()

    def eventFilter(self, watched, event) -> bool:
        if watched in {getattr(self, "_container", None), getattr(self, "_view3d", None)} and QT3D_AVAILABLE:
            event_type = event.type()
            if event_type == QEvent.MouseButtonPress:
                return self._handle_mouse_press(event)
            if event_type == QEvent.MouseMove:
                return self._handle_mouse_move(event)
            if event_type == QEvent.MouseButtonRelease:
                return self._handle_mouse_release(event)
            if event_type == QEvent.Wheel:
                return self._handle_wheel(event)
        return super().eventFilter(watched, event)

    def _picker_button_from_args(self, *args) -> object | None:
        for arg in args:
            try:
                button = arg.button()
            except Exception:
                continue
            if button is not None:
                return button
        return None

    def _button_value(self, button: object) -> int:
        try:
            return int(button)
        except Exception:
            try:
                return int(button.value)
            except Exception:
                return -1

    def _is_right_mouse_button(self, button: object) -> bool:
        if button is None:
            return False
        if button == Qt.RightButton:
            return True
        return self._button_value(button) == self._button_value(Qt.RightButton)

    def _handle_object_picker_clicked(self, obj, *args) -> None:
        if self._suppress_next_pick:
            self._suppress_next_pick = False
            return
        button = self._picker_button_from_args(*args)
        self.object_selected.emit(obj)
        if self._is_right_mouse_button(button):
            self.context_menu_requested.emit(obj, QCursor.pos())

    def _apply_preview_background_color(self) -> None:
        if self._frame_graph is not None and hasattr(self._frame_graph, "setClearColor"):
            try:
                self._frame_graph.setClearColor(self._preview_background_color)
            except Exception:
                pass

    def _handle_mouse_press(self, event) -> bool:
        button = getattr(event, "button", lambda: None)()
        position = self._event_position(event)
        self._press_pos = position
        self._last_drag_pos = position
        if button == Qt.MiddleButton:
            self._pending_drag_mode = None
            self._active_drag_mode = "pan"
            return True
        if button != Qt.LeftButton:
            return False
        if self._interaction_mode in {"move", "rotate"} and self._selected_key is not None:
            self._pending_drag_mode = "transform"
            self._active_drag_mode = None
            return False
        self._pending_drag_mode = "orbit"
        self._active_drag_mode = None
        return False

    def _handle_mouse_move(self, event) -> bool:
        position = self._event_position(event)
        if self._active_drag_mode == "pan":
            self._pan_camera(position.x() - self._last_drag_pos.x(), position.y() - self._last_drag_pos.y())
            self._last_drag_pos = position
            return True
        if self._pending_drag_mode is not None and self._active_drag_mode is None:
            if (position - self._press_pos).manhattanLength() < 4.0:
                return False
            if self._pending_drag_mode == "transform":
                begin_handler = self._transform_begin_handler
                if callable(begin_handler) and begin_handler(self._interaction_mode, self._transform_axis):
                    self._active_drag_mode = "transform"
                    self._suppress_next_pick = True
                    self._drag_accumulated_delta = 0.0
                    self._last_drag_pos = position
                    self._pending_drag_mode = None
                    return True
                self._pending_drag_mode = None
                return False
            if self._pending_drag_mode == "orbit":
                self._active_drag_mode = "orbit"
                self._last_drag_pos = position
                self._pending_drag_mode = None
                return True
        if self._active_drag_mode == "orbit":
            delta_x = position.x() - self._last_drag_pos.x()
            delta_y = position.y() - self._last_drag_pos.y()
            self._orbit_camera(delta_x, delta_y)
            self._last_drag_pos = position
            return True
        if self._active_drag_mode == "transform":
            delta_x = position.x() - self._last_drag_pos.x()
            delta_y = position.y() - self._last_drag_pos.y()
            step_delta = delta_x if abs(delta_x) >= abs(delta_y) else -delta_y
            if abs(step_delta) >= 0.01 and callable(self._transform_update_handler):
                self._drag_accumulated_delta += float(step_delta)
                self._transform_update_handler(self._drag_accumulated_delta)
            self._last_drag_pos = position
            return True
        return False

    def _handle_mouse_release(self, event) -> bool:
        button = getattr(event, "button", lambda: None)()
        if button == Qt.MiddleButton and self._active_drag_mode == "pan":
            self._active_drag_mode = None
            return True
        if button != Qt.LeftButton:
            return False
        if self._active_drag_mode == "transform":
            if callable(self._transform_finish_handler):
                self._transform_finish_handler(True)
            self._active_drag_mode = None
            self._pending_drag_mode = None
            return True
        if self._active_drag_mode == "orbit":
            self._active_drag_mode = None
            self._pending_drag_mode = None
            return True
        self._pending_drag_mode = None
        return False

    def _handle_wheel(self, event) -> bool:
        try:
            delta = event.angleDelta().y()
        except Exception:
            return False
        if abs(int(delta)) <= 0:
            return False
        factor = 0.82 if delta > 0 else 1.22
        self._camera_distance = max(2.0, min(float(self._max_orbit_distance_scene), self._camera_distance * factor))
        self._apply_camera_pose()
        return True

    def _event_position(self, event) -> QPointF:
        position = getattr(event, "position", None)
        if callable(position):
            return position()
        local_pos = getattr(event, "localPos", None)
        if callable(local_pos):
            return local_pos()
        return QPointF()

    def _orbit_camera(self, delta_x: float, delta_y: float) -> None:
        self._camera_yaw_deg, self._camera_pitch_deg = orbit_drag_angles(
            self._camera_yaw_deg,
            self._camera_pitch_deg,
            delta_x=delta_x,
            delta_y=delta_y,
        )
        self._apply_camera_pose()

    def _pan_camera(self, delta_x: float, delta_y: float) -> None:
        center = self._camera.viewCenter()
        position = self._camera.position()
        forward = center - position
        distance = max(1.0, float(forward.length()))
        if forward.lengthSquared() <= 1e-9:
            return
        forward = forward.normalized()
        world_up = QVector3D(0.0, 1.0, 0.0)
        right = QVector3D.crossProduct(forward, world_up)
        if right.lengthSquared() <= 1e-9:
            right = QVector3D(1.0, 0.0, 0.0)
        else:
            right = right.normalized()
        up = QVector3D.crossProduct(right, forward)
        if up.lengthSquared() <= 1e-9:
            up = QVector3D(0.0, 1.0, 0.0)
        else:
            up = up.normalized()
        viewport_size = max(240.0, float(min(self.width(), self.height()) or 0.0))
        factor = (distance / viewport_size) * 1.65
        translation = (right * float(-delta_x) * factor) + (up * float(delta_y) * factor)
        self._camera.setViewCenter(center + translation)
        self._camera.setPosition(position + translation)
        self._sync_camera_polar_state()

    def _sync_camera_polar_state(self) -> None:
        center = self._camera.viewCenter()
        position = self._camera.position()
        offset = position - center
        distance = max(1.0, float(offset.length()))
        self._camera_distance = distance * max(0.1, float(self._preview_zoom_factor))
        if distance <= 1e-6:
            return
        self._camera_yaw_deg = math.degrees(math.atan2(float(offset.x()), float(offset.z())))
        ratio = max(-1.0, min(1.0, float(offset.y()) / distance))
        self._camera_pitch_deg = math.degrees(math.asin(ratio))

    def _apply_camera_pose(self) -> None:
        if not QT3D_AVAILABLE:
            return
        center = self._camera.viewCenter()
        distance = max(1.0, float(self._camera_distance)) / max(0.1, float(self._preview_zoom_factor))
        yaw_rad = math.radians(float(self._camera_yaw_deg))
        pitch_rad = math.radians(float(self._camera_pitch_deg))
        cos_pitch = math.cos(pitch_rad)
        offset = QVector3D(
            math.sin(yaw_rad) * cos_pitch * distance,
            math.sin(pitch_rad) * distance,
            math.cos(yaw_rad) * cos_pitch * distance,
        )
        self._camera.setPosition(center + offset)

    def _rebuild_scene(self) -> None:
        # Debounce: if a rebuild is already pending, restart the timer
        # instead of doing two rebuilds back-to-back (which causes
        # use-after-free in the Qt3D render thread).
        if self._rebuild_timer is not None:
            self._rebuild_timer.stop()
            self._rebuild_timer = None
        self._rebuild_timer = QTimer()
        self._rebuild_timer.setSingleShot(True)
        self._rebuild_timer.timeout.connect(self._rebuild_scene_now)
        self._rebuild_timer.start(50)

    def _rebuild_scene_now(self) -> None:
        self._rebuild_timer = None
        _write_crash_breadcrumb("REBUILD_SCENE START")
        selected_obj = self._selected_object()
        self._clear_item_entities()
        self._preview_bounds = None
        self._items_by_key.clear()
        self._wireframe_entities = []
        self._material_pairs = []
        self._texture_refs = []
        self._picker_refs = []
        for obj in self._objects:
            try:
                item = self._build_object_entity(obj)
            except Exception:
                nickname = getattr(obj, "nickname", None) or "<unknown>"
                archetype = ""
                try:
                    archetype = (getattr(obj, "data", {}) or {}).get("archetype", "")
                except Exception:
                    pass
                _log.error(
                    "Base builder: failed to build 3D entity for part "
                    "nickname=%r archetype=%r:\n%s",
                    nickname,
                    archetype,
                    traceback.format_exc(),
                )
                continue
            if item is None:
                continue
            key = self._obj_key(obj)
            self._items_by_key[key] = item
        self._preview_bounds = self._aggregate_preview_bounds()
        if self._preview_bounds is not None:
            self._apply_native_preview_bounds(self._camera, self._preview_bounds)
            self._rebuild_ground_grid(self._preview_bounds)
            self._rebuild_axis_indicator(self._preview_bounds)
        self._selected_key = None
        self.set_selected(selected_obj)
        _write_crash_breadcrumb(
            f"REBUILD_SCENE DONE items={len(self._items_by_key)} "
            f"wireframes={len(self._wireframe_entities)} "
            f"pending_deletes={len(self._pending_deletions)}"
        )

    def _clear_item_entities(self) -> None:
        self._remove_ground_grid()
        self._remove_axis_indicator()
        # Step 1: Immediately disable all entities so Qt3D's render thread
        # stops accessing their geometry buffers in the next frame.
        stale_roots: list[object] = []
        for item in self._items_by_key.values():
            try:
                item.root_entity.setEnabled(False)
            except Exception:
                pass
            stale_roots.append(item.root_entity)
        # Also disable stray wireframe / selection entities
        for entity in self._wireframe_entities:
            try:
                entity.setEnabled(False)
            except Exception:
                pass
        # Step 2: Let Qt3D process the disable before we detach.
        try:
            QApplication.processEvents()
        except Exception:
            pass
        # Step 3: Detach from scene graph and schedule deletion.
        for root in stale_roots:
            try:
                root.setParent(None)
            except Exception:
                pass
        # Keep a strong reference so Python doesn't GC while Qt3D might
        # still be holding a pointer in the render thread.
        self._pending_deletions.extend(stale_roots)
        # Actually delete after a generous delay so the render thread
        # has completed any in-flight frame that referenced these.
        QTimer.singleShot(200, self._flush_pending_deletions)

    def _flush_pending_deletions(self) -> None:
        """Delete old Qt3D entities after a delay so the render thread is done with them."""
        batch = self._pending_deletions[:]
        self._pending_deletions.clear()
        for entity in batch:
            try:
                entity.deleteLater()
            except Exception:
                pass

    def _build_object_entity(self, obj) -> _AssemblyPreviewItem | None:
        scene_data = self._scene_data_for_object(obj)
        mesh_path = self._mesh_path_for_object(obj)
        nickname = getattr(obj, "nickname", None) or "<unknown>"
        archetype = ""
        try:
            archetype = (getattr(obj, "data", {}) or {}).get("archetype", "")
        except Exception:
            pass
        num_geoms = len(scene_data.geometries) if scene_data is not None and scene_data.geometries else 0
        _write_crash_breadcrumb(
            f"BUILD_ENTITY START nickname={nickname!r} archetype={archetype!r} "
            f"geometries={num_geoms} mesh_path={mesh_path!r}"
        )
        root_entity = QEntity3D(self._root)
        try:
            result = self._build_object_entity_inner(obj, scene_data, mesh_path, root_entity)
            _write_crash_breadcrumb(f"BUILD_ENTITY OK nickname={nickname!r}")
            return result
        except Exception:
            _log.error(
                "Base builder: crash building entity for %r: %s",
                nickname,
                traceback.format_exc(),
            )
            _write_crash_breadcrumb(f"BUILD_ENTITY PYTHON_ERROR nickname={nickname!r}: {traceback.format_exc(limit=2)}")
            try:
                root_entity.setParent(None)
                root_entity.deleteLater()
            except Exception:
                pass
            return None

    def _build_object_entity_inner(self, obj, scene_data, mesh_path, root_entity) -> _AssemblyPreviewItem | None:
        transform = QTransform3D(root_entity)
        root_entity.addComponent(transform)
        self._apply_object_transform(transform, obj)

        bounds = scene_data.bounds if scene_data is not None else None
        base_color = QColor(180, 190, 210)
        display_materials: list[object] = []
        selection_entities: list[object] = []
        selection_materials: list[object] = []
        picker_targets: list[object] = []
        texture_resolver = None
        if scene_data is not None:
            texture_resolver = lambda geometry, data=scene_data: texture_path_for_geometry(data, geometry)
        if scene_data is not None and scene_data.geometries:
            for index, geometry in enumerate(scene_data.geometries):
                # --- Validate geometry before sending to Qt3D ---
                positions = getattr(geometry, "positions", None) or ()
                indices = getattr(geometry, "indices", None) or ()
                if not positions or not indices:
                    _write_crash_breadcrumb(
                        f"  SKIP geometry #{index}: empty positions={len(positions)} indices={len(indices)}"
                    )
                    continue
                max_index = max(indices) if indices else 0
                if max_index >= len(positions):
                    _write_crash_breadcrumb(
                        f"  SKIP geometry #{index}: out-of-range max_index={max_index} positions={len(positions)}"
                    )
                    continue
                index_size = getattr(geometry, "index_size", 4) or 4
                if index_size == 2 and max_index > 65535:
                    _write_crash_breadcrumb(
                        f"  SKIP geometry #{index}: index_size=2 but max_index={max_index} > 65535"
                    )
                    continue
                _write_crash_breadcrumb(
                    f"  geometry #{index}: positions={len(positions)} indices={len(indices)} "
                    f"max_idx={max_index} idx_size={index_size}"
                )
                entity = QEntity3D(root_entity)
                renderer = build_native_geometry_renderer(geometry, owner=entity)
                if renderer is None:
                    try:
                        entity.setParent(None)
                        entity.deleteLater()
                    except Exception:
                        pass
                    continue
                material = build_native_geometry_material(
                    owner=entity,
                    native_geometry=geometry,
                    texture_refs=self._texture_refs,
                    texture_resolver=texture_resolver,
                )
                apply_native_geometry_material(material, geometry)
                colored_material = QPhongMaterial3D(entity)
                _disable_backface_culling(colored_material)
                apply_native_geometry_material(colored_material, geometry)
                colored_material.setDiffuse(base_color)
                try:
                    colored_material.setAmbient(base_color.lighter(120))
                except Exception:
                    pass
                entity.addComponent(renderer)
                entity.addComponent(material if self._materials_visible else colored_material)
                self._material_pairs.append((entity, material, colored_material))
                display_materials.append(colored_material)
                picker_targets.append(entity)

                wire_entity = self._build_wireframe_entity(root_entity, geometry, QColor(240, 240, 240), self._wireframe_visible)
                if wire_entity is not None:
                    self._wireframe_entities.append(wire_entity)

                selection_entity = self._build_wireframe_entity(root_entity, geometry, QColor(255, 210, 64), False)
                if selection_entity is not None:
                    selection_entities.append(selection_entity)
                    selection_materials.append(selection_entity)
                if index == 0 and bounds is None:
                    bounds = geometry.bounds
        elif mesh_path is not None:
            from PySide6.QtCore import QUrl
            from .qt3d_compat import QMesh3D

            entity = QEntity3D(root_entity)
            mesh = QMesh3D(entity)
            mesh.setSource(QUrl.fromLocalFile(str(mesh_path)))
            material = QPhongMaterial3D(entity)
            _disable_backface_culling(material)
            base_color = QColor(180, 190, 210)
            material.setDiffuse(base_color)
            try:
                material.setAmbient(base_color.lighter(120))
            except Exception:
                pass
            entity.addComponent(mesh)
            entity.addComponent(material)
            display_materials.append(material)
            picker_targets.append(entity)
            bounds = FreelancerBounds(min_xyz=(-40.0, -40.0, -40.0), max_xyz=(40.0, 40.0, 40.0), radius=60.0)
        else:
            from .qt3d_compat import QCuboidMesh3D

            entity = QEntity3D(root_entity)
            mesh = QCuboidMesh3D(entity)
            material = QPhongMaterial3D(entity)
            _disable_backface_culling(material)
            base_color = QColor(120, 160, 220)
            material.setDiffuse(base_color)
            try:
                material.setAmbient(base_color.lighter(120))
            except Exception:
                pass
            entity.addComponent(mesh)
            entity.addComponent(material)
            display_materials.append(material)
            picker_targets.append(entity)
            bounds = FreelancerBounds(min_xyz=(-25.0, -25.0, -25.0), max_xyz=(25.0, 25.0, 25.0), radius=40.0)

        self._attach_picker(root_entity, obj)
        return _AssemblyPreviewItem(
            obj=obj,
            root_entity=root_entity,
            transform=transform,
            bounds=bounds,
            base_color=base_color,
            display_materials=display_materials,
            selection_entities=selection_entities,
            selection_materials=selection_materials,
            gizmo_entities=self._build_axis_gizmo(root_entity, bounds),
            gizmo_materials={},
        )

    def _apply_item_selection_state(self, item: _AssemblyPreviewItem, selected: bool) -> None:
        for entity in item.selection_entities:
            try:
                entity.setEnabled(bool(selected))
            except Exception:
                pass
        color = QColor(255, 168, 64) if selected else QColor(item.base_color)
        for material in item.display_materials:
            try:
                material.setDiffuse(color)
            except Exception:
                pass
            try:
                material.setAmbient(color.lighter(125 if selected else 120))
            except Exception:
                pass

    def _build_axis_gizmo(self, parent_entity, bounds: FreelancerBounds | None) -> dict[str, object]:
        gizmo_entities: dict[str, object] = {}
        if QCylinderMesh3D is None:
            return gizmo_entities
        radius = float(getattr(bounds, "radius", 0.0) or 0.0)
        axis_length = max(18.0, min(70.0, radius * 0.9 if radius > 0.0 else 28.0))
        axis_thickness = max(0.35, min(1.8, axis_length * 0.035))
        axis_specs = {
            "x": (QColor(224, 92, 92), QVector3D(0.0, 0.0, 1.0), 90.0),
            "y": (QColor(88, 208, 118), QVector3D(0.0, 1.0, 0.0), 0.0),
            "z": (QColor(96, 156, 236), QVector3D(1.0, 0.0, 0.0), 90.0),
        }
        for axis, (color, rot_axis, angle_deg) in axis_specs.items():
            entity = QEntity3D(parent_entity)
            mesh = QCylinderMesh3D(entity)
            mesh.setLength(axis_length)
            mesh.setRadius(axis_thickness)
            transform = QTransform3D(entity)
            if angle_deg != 0.0:
                transform.setRotation(QQuaternion.fromAxisAndAngle(rot_axis, angle_deg))
            material = QPhongMaterial3D(entity)
            _disable_backface_culling(material)
            material.setDiffuse(color)
            try:
                material.setAmbient(color.lighter(120))
            except Exception:
                pass
            entity.addComponent(mesh)
            entity.addComponent(transform)
            entity.addComponent(material)
            entity.setEnabled(False)
            gizmo_entities[axis] = entity
            gizmo_entities[f"{axis}_material"] = material
        return gizmo_entities

    def _refresh_gizmo_state(self) -> None:
        for _key, item in self._items_by_key.items():
            for axis in ("x", "y", "z"):
                entity = item.gizmo_entities.get(axis)
                if entity is not None:
                    try:
                        entity.setEnabled(False)
                    except Exception:
                        pass

    def _build_wireframe_entity(self, parent_entity, geometry, color: QColor, enabled: bool) -> object | None:
        entity = QEntity3D(parent_entity)
        renderer = build_native_wireframe_renderer(geometry, owner=entity)
        if renderer is None:
            try:
                entity.setParent(None)
                entity.deleteLater()
            except Exception:
                pass
            return None
        material = QPhongMaterial3D(entity)
        _disable_backface_culling(material)
        material.setDiffuse(color)
        entity.addComponent(renderer)
        entity.addComponent(material)
        entity.setEnabled(bool(enabled))
        return entity

    def _attach_picker(self, entity, obj) -> None:
        if QObjectPicker3D is None:
            return
        try:
            picker = QObjectPicker3D(entity)
            if hasattr(picker, "setHoverEnabled"):
                picker.setHoverEnabled(False)
            picker.clicked.connect(lambda *args, selected=obj: self._handle_object_picker_clicked(selected, *args))
            entity.addComponent(picker)
            self._picker_refs.append(picker)
        except Exception:
            pass

    def _apply_object_transform(self, transform, obj) -> None:
        px, py, pz = parse_pos(getattr(obj, "data", {}).get("pos", "0,0,0"))
        ax, ay, az = self._anchor_pos
        transform.setTranslation(QVector3D(float(px - ax), float(py - ay), float(pz - az)))
        rx, ry, rz = parse_rotate(getattr(obj, "data", {}).get("rotate", "0,0,0"))
        transform.setRotation(rotation_quaternion_from_fl(float(rx), float(ry), float(rz)))

    def _aggregate_preview_bounds(self) -> FreelancerBounds | None:
        min_x = min_y = min_z = None
        max_x = max_y = max_z = None
        max_radius = 0.0
        for item in self._items_by_key.values():
            bounds = self._transformed_bounds(item)
            if bounds is None:
                continue
            if min_x is None:
                min_x, min_y, min_z = bounds.min_xyz
                max_x, max_y, max_z = bounds.max_xyz
            else:
                min_x = min(min_x, bounds.min_xyz[0])
                min_y = min(min_y, bounds.min_xyz[1])
                min_z = min(min_z, bounds.min_xyz[2])
                max_x = max(max_x, bounds.max_xyz[0])
                max_y = max(max_y, bounds.max_xyz[1])
                max_z = max(max_z, bounds.max_xyz[2])
            max_radius = max(max_radius, float(bounds.radius or 0.0))
        if min_x is None or max_x is None:
            return None
        center_x = (min_x + max_x) * 0.5
        center_y = (min_y + max_y) * 0.5
        center_z = (min_z + max_z) * 0.5
        dx = max(max_x - center_x, center_x - min_x)
        dy = max(max_y - center_y, center_y - min_y)
        dz = max(max_z - center_z, center_z - min_z)
        radius = max(max_radius, (dx * dx + dy * dy + dz * dz) ** 0.5)
        return FreelancerBounds(
            min_xyz=(float(min_x), float(min_y), float(min_z)),
            max_xyz=(float(max_x), float(max_y), float(max_z)),
            radius=float(max(radius, 1.0)),
        )

    def _transformed_bounds(self, item: _AssemblyPreviewItem) -> FreelancerBounds | None:
        if item.bounds is None:
            return None
        px, py, pz = parse_pos(getattr(item.obj, "data", {}).get("pos", "0,0,0"))
        ax, ay, az = self._anchor_pos
        tx = float(px - ax)
        ty = float(py - ay)
        tz = float(pz - az)
        return FreelancerBounds(
            min_xyz=(item.bounds.min_xyz[0] + tx, item.bounds.min_xyz[1] + ty, item.bounds.min_xyz[2] + tz),
            max_xyz=(item.bounds.max_xyz[0] + tx, item.bounds.max_xyz[1] + ty, item.bounds.max_xyz[2] + tz),
            radius=float(item.bounds.radius or 0.0),
        )

    def _bounds_for_object(self, obj) -> FreelancerBounds | None:
        item = self._items_by_key.get(self._obj_key(obj))
        if item is None:
            return None
        return self._transformed_bounds(item)

    def _selected_object(self):
        if self._selected_key is None:
            return None
        item = self._items_by_key.get(self._selected_key)
        return item.obj if item is not None else None

    def _scene_data_for_object(self, obj) -> NativePreviewSceneData | None:
        key = self._obj_key(obj)
        if key in self._native_scene_overrides:
            return self._native_scene_overrides.get(key)
        if callable(self._native_scene_resolver):
            try:
                result = self._native_scene_resolver(obj)
            except Exception:
                result = None
            if result is not None:
                self._native_scene_overrides[key] = result
            return result
        return None

    def _mesh_path_for_object(self, obj) -> str | Path | None:
        if not callable(self._preview_mesh_resolver):
            return None
        try:
            return self._preview_mesh_resolver(obj)
        except Exception:
            return None

    def _resolve_anchor_pos(self, objects: list[object]) -> tuple[float, float, float]:
        if not objects:
            return (0.0, 0.0, 0.0)
        anchor = objects[0]
        return parse_pos(getattr(anchor, "data", {}).get("pos", "0,0,0"))

    def _apply_native_preview_bounds(self, camera, bounds) -> None:
        min_x, min_y, min_z = bounds.min_xyz
        max_x, max_y, max_z = bounds.max_xyz
        center = QVector3D(
            (min_x + max_x) * 0.5,
            (min_y + max_y) * 0.5,
            (min_z + max_z) * 0.5,
        )
        radius = max(float(bounds.radius or 0.0), 1.0)
        camera.setViewCenter(center)
        offset = QVector3D(radius * 1.05, radius * 0.7, radius * 2.45)
        self._camera_distance = max(1.0, float(offset.length()))
        self._camera_yaw_deg = math.degrees(math.atan2(float(offset.x()), float(offset.z())))
        ratio = max(-1.0, min(1.0, float(offset.y()) / max(1.0, float(offset.length()))))
        self._camera_pitch_deg = math.degrees(math.asin(ratio))
        self._apply_camera_pose()

    # ------------------------------------------------------------------
    # Wireframe ground grid
    # ------------------------------------------------------------------

    def _remove_ground_grid(self) -> None:
        if self._ground_grid_entity is not None:
            try:
                self._ground_grid_entity.setParent(None)
            except Exception:
                pass
            try:
                self._ground_grid_entity.deleteLater()
            except Exception:
                pass
            self._ground_grid_entity = None

    def _rebuild_ground_grid(self, bounds: FreelancerBounds) -> None:
        self._remove_ground_grid()
        if not QT3D_AVAILABLE:
            return
        min_x, min_y, min_z = bounds.min_xyz
        max_x, _max_y, max_z = bounds.max_xyz

        cx = (min_x + max_x) * 0.5
        cz = (min_z + max_z) * 0.5
        span_x = max(max_x - min_x, 1.0)
        span_z = max(max_z - min_z, 1.0)
        span = max(span_x, span_z) * 1.6
        divisions = 10
        cell = span / divisions
        half = span * 0.5

        # Build line vertices: (divisions+1) lines in each direction
        positions: list[tuple[float, float, float]] = []
        indices: list[int] = []
        idx = 0
        y = float(min_y)
        for i in range(divisions + 1):
            t = -half + cell * i
            # Line along X at z = t
            positions.append((cx - half, y, cz + t))
            positions.append((cx + half, y, cz + t))
            indices.extend((idx, idx + 1))
            idx += 2
            # Line along Z at x = t
            positions.append((cx + t, y, cz - half))
            positions.append((cx + t, y, cz + half))
            indices.extend((idx, idx + 1))
            idx += 2

        vertex_blob = QByteArray()
        for x, vy, z in positions:
            vertex_blob.append(_pack("<3f", x, vy, z))

        index_blob = QByteArray()
        for i in indices:
            index_blob.append(_pack("<I", i))

        entity = QEntity3D(self._root)

        geometry = QGeometry3D(entity)
        vbuf = QBuffer3D(geometry)
        vbuf.setData(vertex_blob)
        pos_attr = QAttribute3D(geometry)
        pos_attr.setName(QAttribute3D.defaultPositionAttributeName())
        pos_attr.setAttributeType(QAttribute3D.VertexAttribute)
        pos_attr.setVertexBaseType(QAttribute3D.Float)
        pos_attr.setVertexSize(3)
        pos_attr.setByteStride(12)
        pos_attr.setCount(len(positions))
        pos_attr.setBuffer(vbuf)
        geometry.addAttribute(pos_attr)

        ibuf = QBuffer3D(geometry)
        ibuf.setData(index_blob)
        idx_attr = QAttribute3D(geometry)
        idx_attr.setAttributeType(QAttribute3D.IndexAttribute)
        idx_attr.setVertexBaseType(QAttribute3D.UnsignedInt)
        idx_attr.setCount(len(indices))
        idx_attr.setBuffer(ibuf)
        geometry.addAttribute(idx_attr)

        renderer = QGeometryRenderer3D(entity)
        renderer.setGeometry(geometry)
        renderer.setPrimitiveType(QGeometryRenderer3D.Lines)
        renderer.setVertexCount(len(indices))
        entity.addComponent(renderer)

        material = QPhongMaterial3D(entity)
        grid_color = QColor(90, 130, 180) if self._is_dark_theme else QColor(140, 160, 190)
        material.setAmbient(grid_color)
        material.setDiffuse(QColor(0, 0, 0, 0))
        material.setSpecular(QColor(0, 0, 0, 0))
        entity.addComponent(material)

        self._ground_grid_entity = entity

    # ------------------------------------------------------------------
    # Origin axis indicator + North marker
    # ------------------------------------------------------------------

    def _remove_axis_indicator(self) -> None:
        if self._axis_indicator_entity is not None:
            try:
                self._axis_indicator_entity.setParent(None)
            except Exception:
                pass
            try:
                self._axis_indicator_entity.deleteLater()
            except Exception:
                pass
            self._axis_indicator_entity = None

    def _rebuild_axis_indicator(self, bounds: FreelancerBounds) -> None:
        self._remove_axis_indicator()
        if not QT3D_AVAILABLE:
            return

        min_x, min_y, min_z = bounds.min_xyz
        max_x, _max_y, max_z = bounds.max_xyz
        span = max(max_x - min_x, max_z - min_z, 1.0)
        axis_length = max(12.0, span * 0.25)
        axis_thickness = max(0.3, axis_length * 0.025)
        label_scale = max(0.08, axis_length * 0.008)

        # Place origin at grid corner (min_x, min_y, max_z)
        ox = float(min_x + max_x) * 0.5 - span * 0.8 * 0.5
        oy = float(min_y)
        oz = float(min_z + max_z) * 0.5 + span * 0.8 * 0.5

        root = QEntity3D(self._root)

        axis_specs = [
            # (axis_label, color, rotation_axis, angle, translation for label)
            ("X", QColor(224, 92, 92), QVector3D(0.0, 0.0, 1.0), -90.0,
             QVector3D(axis_length * 1.1, 0.0, 0.0)),
            ("Y", QColor(88, 208, 118), None, 0.0,
             QVector3D(0.0, axis_length * 1.1, 0.0)),
            ("Z", QColor(96, 156, 236), QVector3D(1.0, 0.0, 0.0), 90.0,
             QVector3D(0.0, 0.0, axis_length * 1.1)),
        ]

        for label_text, color, rot_axis, angle_deg, label_offset in axis_specs:
            # Cylinder for axis line
            cyl_entity = QEntity3D(root)
            mesh = QCylinderMesh3D(cyl_entity)
            mesh.setLength(axis_length)
            mesh.setRadius(axis_thickness)
            mesh.setSlices(8)
            cyl_transform = QTransform3D(cyl_entity)
            cyl_transform.setTranslation(QVector3D(ox, oy, oz))
            if rot_axis is not None:
                q = QQuaternion.fromAxisAndAngle(rot_axis, angle_deg)
                # Shift cylinder center along its axis direction
                if label_text == "X":
                    cyl_transform.setTranslation(QVector3D(ox + axis_length * 0.5, oy, oz))
                elif label_text == "Z":
                    cyl_transform.setTranslation(QVector3D(ox, oy, oz - axis_length * 0.5))
                cyl_transform.setRotation(q)
            else:
                cyl_transform.setTranslation(QVector3D(ox, oy + axis_length * 0.5, oz))
            mat = QPhongMaterial3D(cyl_entity)
            mat.setDiffuse(color)
            cyl_entity.addComponent(mesh)
            cyl_entity.addComponent(cyl_transform)
            cyl_entity.addComponent(mat)

            # Text label
            if QExtrudedTextMesh3D is not None:
                txt_entity = QEntity3D(root)
                txt_mesh = QExtrudedTextMesh3D(txt_entity)
                txt_mesh.setText(label_text)
                txt_mesh.setDepth(0.3)
                txt_transform = QTransform3D(txt_entity)
                txt_transform.setTranslation(QVector3D(
                    ox + label_offset.x(),
                    oy + label_offset.y(),
                    oz + label_offset.z(),
                ))
                txt_transform.setScale(label_scale)
                txt_mat = QPhongMaterial3D(txt_entity)
                txt_mat.setDiffuse(color)
                txt_entity.addComponent(txt_mesh)
                txt_entity.addComponent(txt_transform)
                txt_entity.addComponent(txt_mat)

        # North marker: "N" placed well outside the grid at -Z (north in Freelancer)
        grid_half = span * 0.8
        north_z = float(min_z + max_z) * 0.5 - grid_half - axis_length * 1.5
        north_x = float(min_x + max_x) * 0.5
        north_color = QColor(255, 220, 80) if self._is_dark_theme else QColor(180, 140, 20)
        north_scale = label_scale * 8.0

        if QExtrudedTextMesh3D is not None:
            n_entity = QEntity3D(root)
            n_mesh = QExtrudedTextMesh3D(n_entity)
            n_mesh.setText("N")
            n_mesh.setDepth(0.8)
            n_transform = QTransform3D(n_entity)
            n_transform.setTranslation(QVector3D(north_x - north_scale * 0.35, oy, north_z))
            n_transform.setScale(north_scale)
            n_mat = QPhongMaterial3D(n_entity)
            n_mat.setDiffuse(north_color)
            n_mat.setAmbient(north_color)
            n_entity.addComponent(n_mesh)
            n_entity.addComponent(n_transform)
            n_entity.addComponent(n_mat)

        self._axis_indicator_entity = root

    @staticmethod
    def _obj_key(obj) -> int:
        return int(id(obj))