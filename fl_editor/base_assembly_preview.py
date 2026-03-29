from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEvent, QPointF, Qt, Signal
from PySide6.QtGui import QCursor, QColor, QVector3D
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from .freelancer_mesh_data import FreelancerBounds
from .native_preview_qt3d import (
    apply_native_geometry_material,
    build_native_geometry_material,
    build_native_geometry_renderer,
    build_native_wireframe_renderer,
)
from .native_preview_scene_data import NativePreviewSceneData, texture_path_for_geometry
from .qt3d_compat import (
    QCylinderMesh3D,
    QDirectionalLight3D,
    QEntity3D,
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
        self._wireframe_entities: list[object] = []
        self._material_pairs: list[tuple[object, object, object]] = []
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
        self._camera_yaw_deg -= float(delta_x) * 0.35
        self._camera_pitch_deg = max(-89.0, min(89.0, self._camera_pitch_deg - (float(delta_y) * 0.25)))
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
        selected_obj = self._selected_object()
        self._clear_item_entities()
        self._preview_bounds = None
        self._items_by_key.clear()
        self._wireframe_entities = []
        self._material_pairs = []
        self._texture_refs = []
        self._picker_refs = []
        for obj in self._objects:
            item = self._build_object_entity(obj)
            if item is None:
                continue
            key = self._obj_key(obj)
            self._items_by_key[key] = item
        self._preview_bounds = self._aggregate_preview_bounds()
        if self._preview_bounds is not None:
            self._apply_native_preview_bounds(self._camera, self._preview_bounds)
        self._selected_key = None
        self.set_selected(selected_obj)

    def _clear_item_entities(self) -> None:
        for item in self._items_by_key.values():
            try:
                item.root_entity.setParent(None)
            except Exception:
                pass
            try:
                item.root_entity.deleteLater()
            except Exception:
                pass

    def _build_object_entity(self, obj) -> _AssemblyPreviewItem | None:
        scene_data = self._scene_data_for_object(obj)
        mesh_path = self._mesh_path_for_object(obj)
        root_entity = QEntity3D(self._root)
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
                entity = QEntity3D(root_entity)
                renderer = build_native_geometry_renderer(geometry, owner=entity)
                material = build_native_geometry_material(
                    owner=entity,
                    native_geometry=geometry,
                    texture_refs=self._texture_refs,
                    texture_resolver=texture_resolver,
                )
                apply_native_geometry_material(material, geometry)
                colored_material = QPhongMaterial3D(entity)
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
                self._wireframe_entities.append(wire_entity)

                selection_entity = self._build_wireframe_entity(root_entity, geometry, QColor(255, 210, 64), False)
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
        show_gizmo = self._selected_key is not None and self._interaction_mode in {"move", "rotate"}
        base_colors = {
            "x": QColor(224, 92, 92),
            "y": QColor(88, 208, 118),
            "z": QColor(96, 156, 236),
        }
        for key, item in self._items_by_key.items():
            visible = show_gizmo and key == self._selected_key
            for axis in ("x", "y", "z"):
                entity = item.gizmo_entities.get(axis)
                material = item.gizmo_entities.get(f"{axis}_material")
                if entity is not None:
                    try:
                        entity.setEnabled(bool(visible))
                    except Exception:
                        pass
                if material is not None:
                    color = base_colors[axis]
                    if visible and axis == self._transform_axis:
                        color = color.lighter(165)
                    try:
                        material.setDiffuse(color)
                    except Exception:
                        pass
                    try:
                        material.setAmbient(color.lighter(120))
                    except Exception:
                        pass

    def _build_wireframe_entity(self, parent_entity, geometry, color: QColor, enabled: bool) -> object:
        entity = QEntity3D(parent_entity)
        renderer = build_native_wireframe_renderer(geometry, owner=entity)
        material = QPhongMaterial3D(entity)
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

    @staticmethod
    def _obj_key(obj) -> int:
        return int(id(obj))