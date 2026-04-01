"""3D-Systemansicht auf Basis von Qt3D.

Enthält die komplette 3D-Rendering-Logik:
- Kamera-Steuerung (Orbit, Pan, Zoom)
- Objekt- und Zonenentitäten
- Gizmo-System (Klick-Lock auf Achse, Mausrad-Bewegung)
- App-Level Event-Filter für Mausrad-Abfangen
"""

from __future__ import annotations

import math
import random
import time
from pathlib import Path
from typing import Any, Callable

from PySide6.QtWidgets import QApplication, QLabel, QProgressBar, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QEvent, Signal, QTimer, QUrl, QPointF
from PySide6.QtGui import QColor, QCursor, QFont, QVector3D, QQuaternion, QImage, QPainter

from .qt3d_compat import (
    QT3D_AVAILABLE,
    Qt3DExtras,
    Qt3DRender,
    QConeMesh3D,
    QCuboidMesh3D,
    QCylinderMesh3D,
    QDirectionalLight3D,
    QEntity3D,
    QExtrudedTextMesh3D,
    QMesh3D,
    QObjectPicker3D,
    QPhongAlphaMaterial3D,
    QPhongMaterial3D,
    QSphereMesh3D,
    QTransform3D,
    Qt3DWindow3D,
)
from .flight_mode import FlightModeController
from .view_3d_camera import (
    MIN_ORBIT_CAMERA_DISTANCE,
    build_camera_state_dict,
    centered_item_camera_state,
    normalize_camera_state,
    panned_camera_target,
    zoomed_camera_distance,
)
from .view_3d_camera_apply import apply_camera_update_effects, apply_label_scales, apply_sky_translation
from .view_3d_camera_effects import camera_update_effects_state, synced_orbit_camera_state
from .view_3d_object_logic import (
    extract_arch_size,
    is_trade_lane_object,
    object_rotation_quaternion,
    parse_pos,
    parse_rotate,
    rotation_quaternion_from_fl,
    scaled_radius_from_arch,
    tradelane_direction_quaternion,
)
from .view_3d_object_updates import object_position_update_state
from .view_3d_object_kinds import classify_object_kind
from .view_3d_materials import (
    build_torus_mesh,
    make_alpha_material,
    make_phong_material,
    material_always_on_top_refs,
    material_no_cull_refs,
    material_no_depth_write_refs,
)
from .view_3d_gizmo import (
    gizmo_click_state,
    gizmo_default_colors,
    gizmo_highlight_colors,
    gizmo_transform_state,
    toggled_locked_axis,
)
from .view_3d_flight_visuals import dust_update_state, flight_ship_render_pose, initial_dust_positions
from .view_3d_flight_overlay import cruise_charge_bar_state, flight_overlay_layout, flight_overlay_text_state
from .view_3d_overlay_apply import apply_cruise_charge_bar, apply_flight_overlay_layout, apply_flight_overlay_text
from .view_3d_orbit_apply import apply_synced_orbit_camera_state
from .view_3d_flight_apply import flight_camera_context_from_camera, flight_dust_apply_state
from .view_3d_flight_ui import flight_mode_toggle_state, flight_visual_entity_state
from .view_3d_flight_entities_apply import apply_flight_entity_state
from .view_3d_event_routing import (
    dispatch_widget_flight_event,
    filter_flight_event_state,
    should_capture_locked_axis_wheel,
    should_process_qt3d_interaction,
)
from .view_3d_interaction import (
    axis_scroll_delta,
    mouse_move_interaction,
    mouse_press_interaction,
    mouse_release_interaction,
    wheel_interaction,
)
from .view_3d_runtime_state import label_scale_for_distance, orbit_state_from_camera
from .view_3d_reset_state import gizmo_clear_state, scene_clear_state
from .view_3d_selection_state import (
    item_visibility_state,
    label_visibility_state,
    move_mode_state,
    position_update_state,
    selection_state,
)
from .view_3d_scene_state import object_nick_index, scene_camera_state_from_points
from .view_3d_sky import ensure_darkened_sky_texture
from .view_3d_palette import object_color, planet_palette, sun_palette, zone_color
from .native_preview_qt3d import (
    apply_native_geometry_material,
    build_annulus_renderer,
    build_native_geometry_material,
    build_native_geometry_renderer,
    build_native_wireframe_entity,
    build_qt3d_texture_material,
)
from .native_preview_scene_data import scene_data_with_lod_mode, texture_path_for_geometry
from .view_3d_native_detail_state import (
    centered_native_detail_camera_state,
    native_detail_transform_cache_key,
    native_detail_transform_state,
    selected_native_detail_state,
)


class System3DView(QWidget):
    """Qt3D-basierte 3D-Ansicht eines Freelancer-Systems."""

    zoom_factor_changed = Signal(float)
    object_selected = Signal(object)
    context_menu_requested = Signal(object, object)
    object_height_delta = Signal(object, float)
    object_axis_delta = Signal(object, float, float, float)

    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)
        # Objekt-Entity-Verwaltung
        self._obj_map: dict[Any, tuple[Any, Any]] = {}
        self._obj_by_nick: dict[str, Any] = {}
        self._zone_map: dict[Any, tuple[Any, Any]] = {}
        self._zone_entities: list[Any] = []
        self._obj_component_refs: dict[Any, list[Any]] = {}
        self._zone_component_refs: dict[Any, list[Any]] = {}
        self._obj_label_ent: dict[Any, Any] = {}
        self._obj_label_tr: dict[Any, Any] = {}
        self._obj_label_yoff: dict[Any, float] = {}
        self._obj_selection_ent: dict[Any, Any] = {}
        self._labels_visible = True
        # Keep 3D text roughly constant in screen size across zoom levels.
        self._label_scale_factor = 0.00125
        self._label_scale_min = 0.24
        self._label_scale_max = 3.4

        # Primärdarstellung pro Objekt
        self._obj_sphere_ent: dict[Any, Any] = {}

        self._selected_obj: Any = None
        self._selected_native_scene_data: Any = None
        self._selected_native_detail_obj: Any = None
        self._selected_native_detail_entity: Any = None
        self._selected_native_detail_refs: list[Any] = []
        self._selected_native_detail_cache_key: Any = None
        self._native_detail_entity_cache: dict[Any, tuple[Any, list[Any]]] = {}
        self._native_scene_resolver: Callable[[Any], Any | None] | None = None
        self._native_scene_prepared_payload_resolver: Callable[[Any], Any | None] | None = None
        self._preview_mesh_resolver: Callable[[Any], Path | None] | None = None
        self._planet_texture_resolver: Callable[[Any], Path | None] | None = None
        self._planet_cloud_texture_resolver: Callable[[Any], Path | None] | None = None
        self._planet_ring_resolver: Callable[[Any], dict[str, object] | None] | None = None
        self._native_preview_max_distance_fl = -1.0
        self._native_preview_force_coarsest_lod = True
        self._native_preview_high_quality_distance_fl = 20000.0
        self._native_wireframe_visible = False
        self._native_preview_entity_by_obj: dict[Any, Any] = {}
        self._native_preview_refs_by_obj: dict[Any, list[Any]] = {}
        self._native_preview_cache_key_by_obj: dict[Any, Any] = {}
        self._native_preview_entity_cache: dict[Any, tuple[Any, list[Any]]] = {}
        self._native_preview_lod_scene_cache: dict[tuple[object, int], object] = {}
        self._native_preview_refresh_timer: QTimer | None = None
        self._native_preview_batch_timer: QTimer | None = None
        self._native_preview_progress_callback: Callable[[dict[str, object]], None] | None = None
        self._native_preview_pending_builds: list[dict[str, object]] = []
        self._native_preview_batch_size = 2
        self._native_preview_geometry_batch_size = 8
        self._native_preview_progress_total = 0
        self._native_preview_progress_done = 0
        self._native_preview_refresh_suppression_count = 0
        self._native_preview_refresh_pending = False
        self._native_preview_refresh_after_batch = False
        self._native_preview_last_reported_counts: tuple[int, int] = (0, 0)
        self._native_preview_entity_cache_limit = 48
        self._native_preview_build_generation = 0
        self._native_preview_large_jump_threshold_fl = 12000.0
        self._native_preview_tradelane_near_keep = 10
        self._native_preview_tradelane_stride = 4
        self._native_preview_view_half_angle_deg = 55.0
        self._native_preview_active_view_half_angle_deg = 68.0
        self._native_preview_camera_idle_delay_ms = 180
        self._native_preview_free_camera_idle_delay_ms = 240
        self._native_preview_visibility_stable_ms = 260
        self._native_preview_motion_deadline_monotonic = 0.0
        self._native_preview_visible_since_monotonic: dict[Any, float] = {}
        self._native_preview_finalize_budget_per_tick = 1
        self._native_preview_batch_time_budget_ms = 7
        self._native_preview_max_active_count = 18
        self._native_preview_cheap_geometry_limit = 10
        self._native_preview_duplicate_cache_key_cooldown_ms = 220
        self._native_preview_recent_builds_by_key: dict[Any, float] = {}

        # Gizmo
        self._axis_gizmo_entities: list[Any] = []
        self._axis_gizmo_refs: list[Any] = []
        self._axis_gizmo_mats: dict[str, Any] = {}
        self._axis_gizmo_nodes: dict[str, tuple[Any, QVector3D, QQuaternion]] = {}
        self._axis_gizmo_center: QVector3D | None = None
        self._axis_step_world = 120.0
        self._move_mode = False
        self._locked_axis: str | None = None

        # Kamera
        self._drag_mode: str | None = None
        self._last_mouse_pos = None
        self._cam_target = QVector3D(0.0, 0.0, 0.0)
        self._cam_distance = 450.0
        self._cam_yaw = 0.0
        self._cam_pitch = 1.42
        self._system_center = QVector3D(0.0, 0.0, 0.0)
        self._system_radius = 500.0
        self._scene_scale = 1.0
        self._orbit_target_plane_y = 0.0
        self._reference_radius_scene = 0.0
        self._max_orbit_distance_scene = 15000.0
        self._reference_overlay_visible = True
        self._reference_overlay_entities: list[Any] = []
        self._reference_overlay_refs: list[Any] = []
        self._sky_entity = None
        self._sky_transform = None
        self._sky_refs: list[Any] = []

        # Flight-Mode
        self._flight = FlightModeController(self)
        self._flight_ship_entity = None
        self._flight_ship_tr = None
        self._flight_ship_refs: list[Any] = []
        self._dust_entities: list[Any] = []
        self._dust_transforms: list[Any] = []
        self._dust_local_positions: list[QVector3D] = []
        self._dust_refs: list[Any] = []
        self._flight_snapshot: dict[str, Any] | None = None
        self._free_camera_active = False
        self._free_camera_timer: QTimer | None = None
        self._free_camera_elapsed = QTimer(self)
        self._free_camera_keys_down: set[int] = set()
        self._free_camera_pos = QVector3D(0.0, 0.0, 0.0)
        self._free_camera_yaw = 0.0
        self._free_camera_pitch = 0.0
        self._free_camera_speed = 180.0
        self._free_camera_look_active = False
        self._free_camera_last_mouse: QPointF | None = None
        self._free_camera_look_sensitivity = 0.006
        self._free_camera_view_distance = 220.0

        self._build_ui()

    # ==================================================================
    #  UI-Aufbau
    # ==================================================================
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._controls_hint = QLabel(
            "3D: Linke Maus = Orbit · Rechte Maus = Pan · Mausrad = Zoom "
            "· Move-Modus: Pfeil klicken → Mausrad = Verschieben"
        )
        self._controls_hint.setWordWrap(False)
        self._controls_hint.setFixedHeight(22)
        self._controls_hint.setStyleSheet(
            "QLabel { background: rgba(0, 0, 0, 120); color: #E6E6E6;"
            " padding: 1px 8px; font-size: 11px; }"
        )
        layout.addWidget(self._controls_hint)

        self._flight_overlay = QLabel(self)
        self._flight_overlay.setStyleSheet(
            "QLabel { background: rgba(0, 0, 0, 155); color: #d8ffd8;"
            " border: 1px solid rgba(100, 180, 120, 150);"
            " padding: 4px 6px; font-size: 11px; }"
        )
        self._flight_overlay.setVisible(False)
        self._flight_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._flight_help_overlay = QLabel(self)
        self._flight_help_overlay.setStyleSheet(
            "QLabel { background: rgba(0, 0, 0, 150); color: #e7f0ff;"
            " border: 1px solid rgba(120, 150, 220, 140);"
            " padding: 4px 6px; font-size: 10px; }"
        )
        self._flight_help_overlay.setText(
            "Controls\n"
            "LMB hold + Mouse: steer\n"
            "Freiflug: W beschleunigt, S bremst\n"
            "Shift+W: cruise\n"
            "F2: autopilot to selected\n"
            "F3: trade lane\n"
            "H: orbit camera toggle\n"
            "Sidebar: Free/Approach/Dock\n"
            "ESC: exit flight mode"
        )
        self._flight_help_overlay.adjustSize()
        self._flight_help_overlay.setVisible(False)
        self._flight_help_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._flight_charge_bar = QProgressBar(self)
        self._flight_charge_bar.setRange(0, 100)
        self._flight_charge_bar.setValue(0)
        self._flight_charge_bar.setFormat("Cruise Charge %p%")
        self._flight_charge_bar.setStyleSheet(
            "QProgressBar { background: rgba(0,0,0,165); color: #d8ffd8; border: 1px solid rgba(100,180,120,150);"
            " border-radius: 3px; text-align: center; padding: 1px; }"
            "QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #45b36b, stop:1 #9cf7b5); }"
        )
        self._flight_charge_bar.setVisible(False)
        self._flight_charge_bar.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        if not QT3D_AVAILABLE:
            layout.addWidget(QLabel("Qt3D ist nicht verfügbar."))
            return

        self._native_preview_refresh_timer = QTimer(self)
        self._native_preview_refresh_timer.setSingleShot(True)
        self._native_preview_refresh_timer.setInterval(90)
        self._native_preview_refresh_timer.timeout.connect(self.refresh_native_scene_previews)
        self._native_preview_batch_timer = QTimer(self)
        self._native_preview_batch_timer.setSingleShot(True)
        self._native_preview_batch_timer.setInterval(0)
        self._native_preview_batch_timer.timeout.connect(self._process_native_preview_build_batch)
        self._free_camera_timer = QTimer(self)
        self._free_camera_timer.setInterval(16)
        self._free_camera_timer.timeout.connect(self._on_free_camera_tick)

        self._window = Qt3DWindow3D()
        try:
            self._window.defaultFrameGraph().setClearColor(QColor(0, 0, 0))
        except Exception:
            pass
        self._container = QWidget.createWindowContainer(self._window)
        self._container.setFocusPolicy(Qt.StrongFocus)
        self._container.setMouseTracking(True)
        self._container.installEventFilter(self)
        self._window.installEventFilter(self)
        # Overlays must live on the window container, otherwise they can be hidden behind it.
        self._flight_overlay.setParent(self._container)
        self._flight_help_overlay.setParent(self._container)
        self._flight_charge_bar.setParent(self._container)
        layout.addWidget(self._container)

        self._root = QEntity3D()
        self._window.setRootEntity(self._root)
        self._init_sky_background()

        # Zwei Richtungslichter
        self._light_entity = QEntity3D(self._root)
        self._light = QDirectionalLight3D(self._light_entity)
        self._light.setWorldDirection(QVector3D(-0.6, -1.0, -0.4))
        self._light_entity.addComponent(self._light)

        self._light_entity_2 = QEntity3D(self._root)
        self._light_2 = QDirectionalLight3D(self._light_entity_2)
        self._light_2.setWorldDirection(QVector3D(0.2, -0.8, 0.7))
        self._light_entity_2.addComponent(self._light_2)

        self._camera = self._window.camera()
        self._camera.lens().setPerspectiveProjection(45.0, 16.0 / 9.0, 0.1, 50000.0)
        self._init_flight_visual_entities()
        self._update_camera()

    def shutdown_for_app_exit(self):
        """Best-effort teardown to avoid late OpenGL cleanup warnings on app exit."""
        if not QT3D_AVAILABLE:
            return
        try:
            self.set_flight_mode_active(False)
        except Exception:
            pass
        try:
            self._flight.stop()
        except Exception:
            pass
        app = QApplication.instance()
        if app is not None:
            try:
                app.removeEventFilter(self)
            except Exception:
                pass
        try:
            self.clear_scene()
        except Exception:
            pass
        try:
            for ent in self._dust_entities:
                ent.setParent(None)
            self._dust_entities.clear()
            self._dust_transforms.clear()
            self._dust_local_positions.clear()
            self._dust_refs.clear()
        except Exception:
            pass
        try:
            if self._flight_ship_entity is not None:
                self._flight_ship_entity.setParent(None)
        except Exception:
            pass
        self._flight_ship_entity = None
        self._flight_ship_tr = None
        self._flight_ship_refs.clear()
        try:
            if self._sky_entity is not None:
                self._sky_entity.setParent(None)
        except Exception:
            pass
        self._sky_entity = None
        self._sky_transform = None
        self._sky_refs.clear()
        container = getattr(self, "_container", None)
        window = getattr(self, "_window", None)
        if container is not None:
            try:
                container.removeEventFilter(self)
            except Exception:
                pass
        if window is not None:
            try:
                window.removeEventFilter(self)
            except Exception:
                pass
            try:
                window.setRootEntity(None)
            except Exception:
                pass

    def _init_flight_visual_entities(self):
        if not QT3D_AVAILABLE:
            return
        # Spieler-Schiff (einfaches 3D-Proxy-Modell)
        ship_root = QEntity3D(self._root)
        ship_tr = QTransform3D()
        ship_tr.setScale(0.22)
        ship_root.addComponent(ship_tr)
        ship_root.setEnabled(False)
        self._flight_ship_entity = ship_root
        self._flight_ship_tr = ship_tr
        self._flight_ship_refs = [ship_root, ship_tr]

        def add_ship_part(mesh, mat, tr):
            ent = QEntity3D(ship_root)
            ent.addComponent(mesh)
            ent.addComponent(mat)
            ent.addComponent(tr)
            self._flight_ship_refs.extend([ent, mesh, mat, tr])

        # Haupt-Rumpf
        hull_mesh = QCylinderMesh3D()
        hull_mesh.setLength(5.8)
        hull_mesh.setRadius(0.86)
        hull_mat = QPhongMaterial3D(self._root)
        hull_mat.setDiffuse(QColor(150, 172, 205))
        hull_tr = QTransform3D()
        hull_tr.setRotation(QQuaternion.fromAxisAndAngle(1.0, 0.0, 0.0, -90.0))
        add_ship_part(hull_mesh, hull_mat, hull_tr)

        # Nase
        nose_mesh = QConeMesh3D() if QConeMesh3D is not None else QCylinderMesh3D()
        if QConeMesh3D is not None:
            nose_mesh.setLength(2.5)
            nose_mesh.setBottomRadius(0.9)
            try:
                nose_mesh.setTopRadius(0.0)
            except Exception:
                pass
        else:
            nose_mesh.setLength(2.0)
            nose_mesh.setRadius(0.62)
        nose_mat = QPhongMaterial3D(self._root)
        nose_mat.setDiffuse(QColor(176, 198, 225))
        nose_tr = QTransform3D()
        nose_tr.setTranslation(QVector3D(0.0, 0.0, 3.65))
        nose_tr.setRotation(QQuaternion.fromAxisAndAngle(1.0, 0.0, 0.0, -90.0))
        add_ship_part(nose_mesh, nose_mat, nose_tr)

        # Cockpit
        cockpit_mesh = QSphereMesh3D()
        cockpit_mesh.setRadius(0.52)
        cockpit_mat = QPhongAlphaMaterial3D(self._root)
        cockpit_mat.setAlpha(0.55)
        cockpit_mat.setDiffuse(QColor(92, 170, 255, 180))
        cockpit_tr = QTransform3D()
        cockpit_tr.setTranslation(QVector3D(0.0, 0.38, 1.55))
        add_ship_part(cockpit_mesh, cockpit_mat, cockpit_tr)

        # Rückenmodul
        spine_mesh = QCuboidMesh3D()
        spine_mesh.setXExtent(0.66)
        spine_mesh.setYExtent(0.48)
        spine_mesh.setZExtent(2.6)
        spine_mat = QPhongMaterial3D(self._root)
        spine_mat.setDiffuse(QColor(118, 138, 172))
        spine_tr = QTransform3D()
        spine_tr.setTranslation(QVector3D(0.0, 0.42, -0.35))
        add_ship_part(spine_mesh, spine_mat, spine_tr)

        # Flügel + Winglets
        wing_mesh = QCuboidMesh3D()
        wing_mesh.setXExtent(5.0)
        wing_mesh.setYExtent(0.22)
        wing_mesh.setZExtent(1.7)
        wing_mat = QPhongMaterial3D(self._root)
        wing_mat.setDiffuse(QColor(90, 116, 165))
        wing_tr = QTransform3D()
        wing_tr.setTranslation(QVector3D(0.0, -0.04, -0.35))
        add_ship_part(wing_mesh, wing_mat, wing_tr)

        for sx in (-2.15, 2.15):
            tip_mesh = QCuboidMesh3D()
            tip_mesh.setXExtent(0.56)
            tip_mesh.setYExtent(0.74)
            tip_mesh.setZExtent(0.82)
            tip_mat = QPhongMaterial3D(self._root)
            tip_mat.setDiffuse(QColor(86, 104, 148))
            tip_tr = QTransform3D()
            tip_tr.setTranslation(QVector3D(float(sx), 0.32, -0.32))
            add_ship_part(tip_mesh, tip_mat, tip_tr)

        # Triebwerksgondeln
        for sx in (-1.42, 1.42):
            eng_mesh = QCylinderMesh3D()
            eng_mesh.setLength(2.4)
            eng_mesh.setRadius(0.36)
            eng_mat = QPhongMaterial3D(self._root)
            eng_mat.setDiffuse(QColor(112, 128, 164))
            eng_tr = QTransform3D()
            eng_tr.setTranslation(QVector3D(float(sx), -0.14, -2.05))
            eng_tr.setRotation(QQuaternion.fromAxisAndAngle(1.0, 0.0, 0.0, -90.0))
            add_ship_part(eng_mesh, eng_mat, eng_tr)

            nozzle_mesh = QSphereMesh3D()
            nozzle_mesh.setRadius(0.28)
            nozzle_mat = QPhongAlphaMaterial3D(self._root)
            nozzle_mat.setAlpha(0.68)
            nozzle_mat.setDiffuse(QColor(116, 188, 255, 205))
            nozzle_tr = QTransform3D()
            nozzle_tr.setTranslation(QVector3D(float(sx), -0.14, -3.25))
            add_ship_part(nozzle_mesh, nozzle_mat, nozzle_tr)

        # Heckflosse
        tail_mesh = QCuboidMesh3D()
        tail_mesh.setXExtent(0.5)
        tail_mesh.setYExtent(1.05)
        tail_mesh.setZExtent(1.1)
        tail_mat = QPhongMaterial3D(self._root)
        tail_mat.setDiffuse(QColor(84, 100, 138))
        tail_tr = QTransform3D()
        tail_tr.setTranslation(QVector3D(0.0, 0.52, -2.68))
        add_ship_part(tail_mesh, tail_mat, tail_tr)

        # Space-Dust: kleine helle Partikel im Schiffsraum
        dust_count = 32
        for _i in range(dust_count):
            d_ent = QEntity3D(self._root)
            d_mesh = QSphereMesh3D()
            d_mesh.setRadius(0.08)
            d_mat = QPhongMaterial3D(self._root)
            d_mat.setDiffuse(QColor(196, 208, 232))
            d_tr = QTransform3D()
            d_ent.addComponent(d_mesh)
            d_ent.addComponent(d_mat)
            d_ent.addComponent(d_tr)
            d_ent.setEnabled(False)
            self._dust_entities.append(d_ent)
            self._dust_transforms.append(d_tr)
            self._dust_refs.extend([d_ent, d_mesh, d_mat, d_tr])
        self._reset_dust_distribution()

    def _reset_dust_distribution(self):
        self._dust_local_positions = [QVector3D(*pos) for pos in initial_dust_positions(len(self._dust_entities), random)]

    # ==================================================================
    #  Kamera
    # ==================================================================
    def center_on_item(self, item):
        entry = self._obj_map.get(item) or self._zone_map.get(item)
        if entry is None:
            return
        _ent, tr = entry
        is_zone = item in self._zone_map
        native_scene_data = self._selected_native_scene_data if item is self._selected_native_detail_obj else None
        if (not is_zone) and native_scene_data is not None and getattr(native_scene_data, "bounds", None) is not None:
            state = centered_native_detail_camera_state(
                object_translation_xyz=(tr.translation().x(), tr.translation().y(), tr.translation().z()),
                bounds=native_scene_data.bounds,
                scene_scale=float(getattr(self, "_scene_scale", 1.0) or 1.0),
            )
        else:
            state = centered_item_camera_state(
                target_xyz=(tr.translation().x(), tr.translation().y(), tr.translation().z()),
                system_radius=self._system_radius,
                is_zone=is_zone,
            )
        tx, _ty, tz = state["target_xyz"]
        self._cam_target = QVector3D(float(tx), float(self._orbit_target_plane_y), float(tz))
        self._cam_pitch = float(state["pitch"])
        self._cam_yaw = float(state["yaw"])
        self._cam_distance = max(float(MIN_ORBIT_CAMERA_DISTANCE), min(self._effective_max_orbit_distance_scene(), float(state["distance"])))
        self._update_camera()

    def jump_to_item_preserving_view(self, item) -> None:
        entry = self._obj_map.get(item) or self._zone_map.get(item)
        if entry is None:
            return
        _ent, tr = entry
        jump_distance_fl = 0.0
        try:
            scene_scale = max(1e-6, float(getattr(self, "_scene_scale", 1.0) or 1.0))
            jump_distance_scene = math.sqrt(
                float(tr.translation().x() - self._cam_target.x()) ** 2
                + float(tr.translation().y() - self._cam_target.y()) ** 2
                + float(tr.translation().z() - self._cam_target.z()) ** 2
            )
            jump_distance_fl = float(jump_distance_scene) / scene_scale
        except Exception:
            jump_distance_fl = 0.0
        if jump_distance_fl >= float(self._native_preview_large_jump_threshold_fl):
            self._prepare_for_large_camera_jump()
        state = self.get_camera_state()
        if not isinstance(state, dict):
            state = {}
        state["target_x"] = float(tr.translation().x())
        state["target_y"] = float(self._orbit_target_plane_y)
        state["target_z"] = float(tr.translation().z())
        self.set_camera_state(state)
        if jump_distance_fl >= float(self._native_preview_large_jump_threshold_fl):
            self._schedule_native_scene_preview_refresh(180)

    def set_orbit_target_plane_y(self, value: float) -> None:
        self._orbit_target_plane_y = float(value)
        self._cam_target = QVector3D(float(self._cam_target.x()), float(self._orbit_target_plane_y), float(self._cam_target.z()))

    def set_reference_radius_scene(self, radius_scene: float) -> None:
        self._reference_radius_scene = max(0.0, float(radius_scene))
        self._max_orbit_distance_scene = max(self._default_zoom_distance(), self._reference_radius_scene * 2.35)
        self._rebuild_reference_overlay()

    def set_reference_overlay_visible(self, visible: bool) -> None:
        self._reference_overlay_visible = bool(visible)
        self._rebuild_reference_overlay()

    def set_max_orbit_distance_scene(self, value: float) -> None:
        self._max_orbit_distance_scene = max(float(MIN_ORBIT_CAMERA_DISTANCE), float(value))

    def _effective_max_orbit_distance_scene(self) -> float:
        return max(float(MIN_ORBIT_CAMERA_DISTANCE), float(getattr(self, "_max_orbit_distance_scene", 15000.0) or 15000.0))

    def get_camera_state(self) -> dict[str, float]:
        return build_camera_state_dict(
            target_xyz=(self._cam_target.x(), self._cam_target.y(), self._cam_target.z()),
            distance=self._cam_distance,
            yaw=self._cam_yaw,
            pitch=self._cam_pitch,
        )

    def set_camera_state(self, state: dict[str, float] | None):
        normalized = normalize_camera_state(
            state,
            fallback_target_xyz=(self._cam_target.x(), self._cam_target.y(), self._cam_target.z()),
            fallback_distance=self._cam_distance,
            fallback_yaw=self._cam_yaw,
            fallback_pitch=self._cam_pitch,
        )
        if not normalized:
            return
        tx, _ty, tz = normalized["target_xyz"]
        self._cam_target = QVector3D(float(tx), float(self._orbit_target_plane_y), float(tz))
        self._cam_distance = max(
            float(MIN_ORBIT_CAMERA_DISTANCE),
            min(self._effective_max_orbit_distance_scene(), float(normalized["distance"])),
        )
        self._cam_yaw = float(normalized["yaw"])
        self._cam_pitch = float(normalized["pitch"])
        self._update_camera()

    def _default_zoom_distance(self) -> float:
        return max(240.0, float(self._system_radius) * 1.3, float(self._reference_radius_scene) * 1.12)

    def minimum_zoom_factor(self) -> float:
        return max(0.01, self._default_zoom_distance() / max(self._effective_max_orbit_distance_scene(), 1e-6))

    def maximum_zoom_factor(self) -> float:
        return max(self.minimum_zoom_factor(), min(100.0, self._default_zoom_distance() / float(MIN_ORBIT_CAMERA_DISTANCE)))

    def get_zoom_factor(self) -> float:
        return max(self.minimum_zoom_factor(), min(self.maximum_zoom_factor(), self._default_zoom_distance() / max(1e-6, float(self._cam_distance))))

    def set_zoom_factor(self, target: float) -> None:
        target = max(self.minimum_zoom_factor(), min(self.maximum_zoom_factor(), float(target)))
        next_distance = self._default_zoom_distance() / target
        next_distance = max(
            float(MIN_ORBIT_CAMERA_DISTANCE),
            min(self._effective_max_orbit_distance_scene(), float(next_distance)),
        )
        if abs(float(self._cam_distance) - next_distance) <= 1e-6:
            return
        self._cam_distance = float(next_distance)
        self._update_camera()

    def _make_reference_line(
        self,
        *,
        x_extent: float,
        z_extent: float,
        y_extent: float,
        translation_xyz: tuple[float, float, float],
        color: QColor,
        alpha: float,
    ) -> None:
        line_ent = QEntity3D(self._root)
        line_mesh = QCuboidMesh3D()
        line_mesh.setXExtent(max(0.01, float(x_extent)))
        line_mesh.setYExtent(max(0.01, float(y_extent)))
        line_mesh.setZExtent(max(0.01, float(z_extent)))
        line_mat = self._make_alpha(color, alpha)
        line_depth_refs = material_always_on_top_refs(line_mat, Qt3DRender)
        line_tr = QTransform3D()
        line_tr.setTranslation(QVector3D(*translation_xyz))
        line_ent.addComponent(line_mesh)
        line_ent.addComponent(line_mat)
        line_ent.addComponent(line_tr)
        self._reference_overlay_entities.append(line_ent)
        self._reference_overlay_refs.extend([line_ent, line_mesh, line_mat, line_tr, *line_depth_refs])

    def _clear_reference_overlay(self) -> None:
        for ent in self._reference_overlay_entities:
            try:
                ent.setParent(None)
            except Exception:
                pass
        self._reference_overlay_entities.clear()
        self._reference_overlay_refs.clear()

    def _rebuild_reference_overlay(self) -> None:
        self._clear_reference_overlay()
        if not QT3D_AVAILABLE or self._root is None:
            return
        if not bool(getattr(self, "_reference_overlay_visible", True)):
            return
        radius = max(0.0, float(self._reference_radius_scene))
        if radius <= 0.0:
            return
        plane_y = float(self._orbit_target_plane_y)
        plane_height = max(0.02, radius * 0.0012)
        line_thickness = max(0.05, radius * 0.0022)
        grid_size = radius * 2.0
        cell = grid_size / 8.0

        for index in range(9):
            offset = -radius + cell * float(index)
            is_border = index in (0, 8)
            is_center = index == 4
            color = QColor(92, 164, 255) if is_border else QColor(88, 132, 198)
            alpha = 0.30 if is_border else 0.18
            thickness = line_thickness * (1.35 if is_border else (1.15 if is_center else 1.0))
            self._make_reference_line(
                x_extent=grid_size,
                z_extent=thickness,
                y_extent=plane_height * 1.15,
                translation_xyz=(0.0, plane_y, offset),
                color=color,
                alpha=alpha,
            )
            self._make_reference_line(
                x_extent=thickness,
                z_extent=grid_size,
                y_extent=plane_height * 1.15,
                translation_xyz=(offset, plane_y, 0.0),
                color=color,
                alpha=alpha,
            )

    @staticmethod
    def _button_value(button: object) -> object:
        try:
            return getattr(button, "value")
        except Exception:
            return button

    def _picker_button_from_args(self, *args) -> object | None:
        for arg in args:
            try:
                button = arg.button()
            except Exception:
                continue
            if button is not None:
                return button
        return None

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

    def _update_camera(self):
        if self._free_camera_active:
            self._sync_free_camera_from_orbit_camera()
            self._apply_free_camera_pose()
            return
        state = camera_update_effects_state(
            target_xyz=(self._cam_target.x(), self._cam_target.y(), self._cam_target.z()),
            distance=self._cam_distance,
            yaw=self._cam_yaw,
            pitch=self._cam_pitch,
            label_positions_xyz=[
                (
                    tr.translation().x(),
                    tr.translation().y(),
                    tr.translation().z(),
                )
                for tr in self._obj_label_tr.values()
            ],
            scale_factor=self._label_scale_factor,
            scale_min=self._label_scale_min,
            scale_max=self._label_scale_max,
        )
        apply_camera_update_effects(
            camera=self._camera,
            cam_target_xyz=(self._cam_target.x(), self._cam_target.y(), self._cam_target.z()),
            sky_transform=self._sky_transform,
            label_transforms=self._obj_label_tr.values(),
            state=state,
            update_axis_gizmo=self._update_axis_gizmo_transforms,
        )
        try:
            self.zoom_factor_changed.emit(self.get_zoom_factor())
        except Exception:
            pass
        self._schedule_native_scene_preview_refresh_for_camera_motion()

    def _sync_free_camera_from_orbit_camera(self) -> None:
        try:
            cam_pos = self._camera.position()
            view_center = self._camera.viewCenter()
        except Exception:
            return
        self._free_camera_pos = QVector3D(float(cam_pos.x()), float(cam_pos.y()), float(cam_pos.z()))
        fx = float(view_center.x()) - float(cam_pos.x())
        fy = float(view_center.y()) - float(cam_pos.y())
        fz = float(view_center.z()) - float(cam_pos.z())
        flen = math.sqrt(fx * fx + fy * fy + fz * fz)
        if flen <= 1e-6:
            return
        fx /= flen
        fy /= flen
        fz /= flen
        self._free_camera_yaw = math.atan2(fx, fz)
        self._free_camera_pitch = max(math.radians(-85.0), min(math.radians(85.0), math.asin(max(-1.0, min(1.0, fy)))))

    def _forward_vector(self) -> QVector3D:
        cp = math.cos(float(self._free_camera_pitch))
        return QVector3D(
            float(cp * math.sin(float(self._free_camera_yaw))),
            float(math.sin(float(self._free_camera_pitch))),
            float(cp * math.cos(float(self._free_camera_yaw))),
        )

    def _right_vector(self) -> QVector3D:
        forward = self._forward_vector()
        right = QVector3D(float(forward.z()), 0.0, float(-forward.x()))
        if right.lengthSquared() <= 1e-9:
            return QVector3D(1.0, 0.0, 0.0)
        return right.normalized()

    def _apply_free_camera_pose(self) -> None:
        if not QT3D_AVAILABLE:
            return
        forward = self._forward_vector()
        if forward.lengthSquared() <= 1e-9:
            forward = QVector3D(0.0, 0.0, 1.0)
        view_center = self._free_camera_pos + (forward.normalized() * float(self._free_camera_view_distance))
        try:
            self._camera.setPosition(self._free_camera_pos)
            self._camera.setViewCenter(view_center)
        except Exception:
            return
        self._sync_sky_to_camera((self._free_camera_pos.x(), self._free_camera_pos.y(), self._free_camera_pos.z()))
        self._update_label_scales()
        self._schedule_native_scene_preview_refresh_for_camera_motion(free_camera=True)

    def _on_free_camera_tick(self) -> None:
        if not self._free_camera_active:
            return
        dt = 0.016
        move = QVector3D(0.0, 0.0, 0.0)
        forward = self._forward_vector()
        right = self._right_vector()
        if Qt.Key_W in self._free_camera_keys_down:
            move += forward
        if Qt.Key_S in self._free_camera_keys_down:
            move -= forward
        if Qt.Key_D in self._free_camera_keys_down:
            move += right
        if Qt.Key_A in self._free_camera_keys_down:
            move -= right
        if move.lengthSquared() > 1e-9:
            self._free_camera_pos += move.normalized() * (float(self._free_camera_speed) * dt)
            self._apply_free_camera_pose()

    def is_free_camera_active(self) -> bool:
        return bool(self._free_camera_active)

    def set_free_camera_active(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._free_camera_active:
            return
        if enabled:
            self._free_camera_keys_down.clear()
            self._free_camera_look_active = False
            self._free_camera_last_mouse = None
            self._sync_free_camera_from_orbit_camera()
            self._free_camera_speed = max(30.0, min(4000.0, float(self._default_zoom_distance()) * 0.18))
            self._free_camera_active = True
            if self._free_camera_timer is not None:
                self._free_camera_timer.start()
            self._apply_free_camera_pose()
            return
        self._free_camera_active = False
        self._free_camera_keys_down.clear()
        self._free_camera_look_active = False
        self._free_camera_last_mouse = None
        if self._free_camera_timer is not None:
            self._free_camera_timer.stop()
        forward = self._forward_vector()
        next_target = self._free_camera_pos + (forward.normalized() * max(20.0, float(self._cam_distance)))
        self._cam_target = QVector3D(float(next_target.x()), float(next_target.y()), float(next_target.z()))
        self._cam_yaw = float(self._free_camera_yaw)
        self._cam_pitch = float(self._free_camera_pitch)
        self._update_camera()

    def _init_sky_background(self):
        if not QT3D_AVAILABLE:
            return
        self._sky_entity = QEntity3D(self._root)
        self._sky_transform = QTransform3D()
        self._sky_transform.setTranslation(QVector3D(0.0, 0.0, 0.0))
        # Inverted scale -> innere Fläche sichtbar.
        self._sky_transform.setScale3D(QVector3D(-1.0, 1.0, 1.0))

        sky_mesh = QSphereMesh3D()
        sky_mesh.setRadius(42000.0)

        sky_mat = None
        try:
            extras_ns = getattr(Qt3DExtras, "Qt3DExtras", Qt3DExtras)
            render_ns = getattr(Qt3DRender, "Qt3DRender", Qt3DRender)
            texture_mat_cls = getattr(extras_ns, "QTextureMaterial", None)
            diffuse_map_mat_cls = getattr(extras_ns, "QDiffuseMapMaterial", None)
            texture_loader_cls = getattr(render_ns, "QTextureLoader", None)
            if texture_loader_cls is not None:
                tex_path = Path(__file__).resolve().parent / "images" / "star-background.png"
                if tex_path.exists():
                    tex_source = self._ensure_darkened_sky_texture(tex_path)
                    tex_owner = self._root
                    tex = texture_loader_cls(tex_owner)
                    tex.setSource(QUrl.fromLocalFile(str(tex_source)))
                    # Prefer unlit texture material (keeps stars dark, unaffected by scene lights).
                    if texture_mat_cls is not None:
                        sky_mat = texture_mat_cls(self._root)
                        if hasattr(sky_mat, "setTexture"):
                            sky_mat.setTexture(tex)
                    elif diffuse_map_mat_cls is not None:
                        sky_mat = diffuse_map_mat_cls(self._root)
                        if hasattr(sky_mat, "setDiffuse"):
                            sky_mat.setDiffuse(tex)
                        if hasattr(sky_mat, "setAmbient"):
                            # Keep ambient low to avoid brightening a dark starfield.
                            sky_mat.setAmbient(QColor(28, 28, 28))
                    self._sky_refs.extend([tex])
        except Exception:
            sky_mat = None

        if sky_mat is None:
            sky_mat = QPhongMaterial3D(self._root)
            sky_mat.setDiffuse(QColor(7, 9, 18))
            try:
                sky_mat.setAmbient(QColor(8, 10, 20))
            except Exception:
                pass

        self._sky_entity.addComponent(sky_mesh)
        self._sky_entity.addComponent(sky_mat)
        self._sky_entity.addComponent(self._sky_transform)
        self._sky_refs.extend([self._sky_entity, sky_mesh, sky_mat, self._sky_transform])

    def _ensure_darkened_sky_texture(self, src_path: Path) -> Path:
        return ensure_darkened_sky_texture(src_path)

    def _sync_sky_to_camera(self, sky_translation_xyz: tuple[float, float, float] | None = None):
        if self._sky_transform is None:
            return
        try:
            if sky_translation_xyz is None:
                cam_pos = self._camera.position()
                sky_translation_xyz = (cam_pos.x(), cam_pos.y(), cam_pos.z())
            apply_sky_translation(sky_transform=self._sky_transform, sky_translation_xyz=sky_translation_xyz)
        except Exception:
            pass

    def _update_label_scales(self, label_scales: list[float] | None = None):
        if not QT3D_AVAILABLE:
            return
        if label_scales is None:
            state = camera_update_effects_state(
                target_xyz=(self._cam_target.x(), self._cam_target.y(), self._cam_target.z()),
                distance=self._cam_distance,
                yaw=self._cam_yaw,
                pitch=self._cam_pitch,
                label_positions_xyz=[
                    (
                        tr.translation().x(),
                        tr.translation().y(),
                        tr.translation().z(),
                    )
                    for tr in self._obj_label_tr.values()
                ],
                scale_factor=self._label_scale_factor,
                scale_min=self._label_scale_min,
                scale_max=self._label_scale_max,
            )
            label_scales = list(state["label_scales"])
        try:
            apply_label_scales(label_transforms=self._obj_label_tr.values(), label_scales=label_scales)
        except Exception:
            pass

    def _pan_camera(self, dx: float, dy: float):
        pos = self._camera.position()
        next_target = panned_camera_target(
            camera_pos_xyz=(pos.x(), pos.y(), pos.z()),
            target_xyz=(self._cam_target.x(), self._cam_target.y(), self._cam_target.z()),
            cam_distance=self._cam_distance,
            dx=dx,
            dy=dy,
        )
        if next_target is None:
            return
        self._cam_target = QVector3D(float(next_target[0]), float(self._orbit_target_plane_y), float(next_target[2]))
        self._update_camera()

    # ==================================================================
    #  Event-Filter  (Orbit, Pan, Zoom, Gizmo-Scroll)
    # ==================================================================
    def eventFilter(self, obj, event):
        try:
            if self._free_camera_active:
                et = event.type()
                if et == QEvent.KeyPress:
                    key = int(event.key())
                    if key == int(Qt.Key_Escape):
                        self.set_free_camera_active(False)
                        return True
                    if key in {int(Qt.Key_W), int(Qt.Key_A), int(Qt.Key_S), int(Qt.Key_D)}:
                        self._free_camera_keys_down.add(key)
                        return True
                elif et == QEvent.KeyRelease:
                    key = int(event.key())
                    if key in {int(Qt.Key_W), int(Qt.Key_A), int(Qt.Key_S), int(Qt.Key_D)}:
                        self._free_camera_keys_down.discard(key)
                        return True
                elif et == QEvent.MouseButtonPress and event.button() == Qt.RightButton:
                    self._free_camera_look_active = True
                    self._free_camera_last_mouse = event.position()
                    return True
                elif et == QEvent.MouseButtonRelease and event.button() == Qt.RightButton:
                    self._free_camera_look_active = False
                    self._free_camera_last_mouse = None
                    return True
                elif et == QEvent.MouseMove:
                    if self._free_camera_look_active and self._free_camera_last_mouse is not None:
                        pos = event.position()
                        delta = pos - self._free_camera_last_mouse
                        self._free_camera_last_mouse = pos
                        self._free_camera_yaw -= float(delta.x()) * float(self._free_camera_look_sensitivity)
                        self._free_camera_pitch = max(
                            math.radians(-85.0),
                            min(
                                math.radians(85.0),
                                float(self._free_camera_pitch) - float(delta.y()) * float(self._free_camera_look_sensitivity),
                            ),
                        )
                        self._apply_free_camera_pose()
                    return True
                elif et == QEvent.Wheel:
                    delta_y = float(event.angleDelta().y())
                    speed_mul = 1.14 if delta_y > 0.0 else 0.88
                    self._free_camera_speed = max(2.0, min(12000.0, float(self._free_camera_speed) * speed_mul))
                    return True
            event_type_map = {
                QEvent.KeyPress: "key_press",
                QEvent.KeyRelease: "key_release",
                QEvent.MouseButtonPress: "mouse_press",
                QEvent.MouseButtonRelease: "mouse_release",
                QEvent.MouseMove: "mouse_move",
                QEvent.Wheel: "wheel",
            }
            event_type_name = event_type_map.get(event.type())
            flight_state = filter_flight_event_state(active=self._flight.active, event_type=event_type_name or "")
            if flight_state is not None:
                handler = getattr(self._flight, str(flight_state["handler_name"]))
                result = handler(event)
                consume_mode = str(flight_state["consume_mode"])
                if consume_mode == "handler_result":
                    return bool(result)
                if consume_mode == "always_consume":
                    return True
                return False

            # Globale Mausrad-Abfangung wenn eine Gizmo-Achse gesperrt ist
            if should_capture_locked_axis_wheel(
                event_type=event_type_name or "",
                locked_axis=self._locked_axis,
                has_selected_obj=self._selected_obj is not None,
            ):
                self._emit_axis_scroll(event.angleDelta().y())
                return True

            container = getattr(self, "_container", None)
            window = getattr(self, "_window", None)
            if not should_process_qt3d_interaction(
                qt3d_available=QT3D_AVAILABLE,
                target_matches=obj in (container, window),
            ):
                return super().eventFilter(obj, event)

            et = event.type()

            if et == QEvent.MouseButtonPress:
                self._last_mouse_pos = event.position()
                button = "left" if event.button() == Qt.LeftButton else ("right" if event.button() == Qt.RightButton else "")
                state = mouse_press_interaction(button=button, locked_axis=self._locked_axis)
                if state.get("clear_locked_axis"):
                    self._locked_axis = None
                    self._reset_gizmo_colors()
                    app = QApplication.instance()
                    if app:
                        app.removeEventFilter(self)
                    return True
                if state.get("drag_mode") is not None:
                    self._drag_mode = str(state["drag_mode"])
                    return True

            elif et == QEvent.MouseMove and self._last_mouse_pos and self._drag_mode:
                pos = event.position()
                d = pos - self._last_mouse_pos
                self._last_mouse_pos = pos
                state = mouse_move_interaction(
                    drag_mode=self._drag_mode,
                    delta_x=float(d.x()),
                    delta_y=float(d.y()),
                    cam_yaw=self._cam_yaw,
                    cam_pitch=self._cam_pitch,
                )
                if state.get("update_camera"):
                    self._cam_yaw = float(state["cam_yaw"])
                    self._cam_pitch = float(state["cam_pitch"])
                    self._update_camera()
                    return True
                if state.get("pan_dx") is not None:
                    self._pan_camera(float(state["pan_dx"]), float(state["pan_dy"]))
                    return True

            elif et == QEvent.MouseButtonRelease:
                button = "left" if event.button() == Qt.LeftButton else ("right" if event.button() == Qt.RightButton else "")
                state = mouse_release_interaction(button=button)
                if state.get("clear_drag_state"):
                    self._drag_mode = None
                    self._last_mouse_pos = None
                    return True

            elif et == QEvent.Wheel:
                delta = event.angleDelta().y()
                state = wheel_interaction(
                    delta=delta,
                    locked_axis=self._locked_axis,
                    has_selected_obj=self._selected_obj is not None,
                    control_modifier_active=bool(event.modifiers() & Qt.ControlModifier),
                    cam_distance=self._cam_distance,
                    axis_step_world=self._axis_step_world,
                    max_camera_distance=self._effective_max_orbit_distance_scene(),
                )
                if state.get("axis_delta") is not None:
                    dx, dy, dz = state["axis_delta"]
                    self.object_axis_delta.emit(self._selected_obj, dx, dy, dz)
                    return True
                if state.get("height_delta") is not None:
                    self.object_height_delta.emit(self._selected_obj, float(state["height_delta"]))
                    return True
                if state.get("update_camera"):
                    self._cam_distance = float(state["cam_distance"])
                    self._update_camera()
                    return True
                return True

            return super().eventFilter(obj, event)
        except KeyboardInterrupt:
            app = QApplication.instance()
            if app is not None:
                app.quit()
            return True

    def _emit_axis_scroll(self, delta: int):
        """Sendet ein Achsen-Delta-Signal basierend auf Mausrad."""
        dx, dy, dz = axis_scroll_delta(delta=delta, axis_step_world=self._axis_step_world, locked_axis=self._locked_axis)
        self.object_axis_delta.emit(self._selected_obj, dx, dy, dz)

    # ==================================================================
    #  Szene verwalten
    # ==================================================================
    def clear_scene(self):
        if not QT3D_AVAILABLE:
            return
        if self._free_camera_timer is not None:
            self._free_camera_timer.stop()
        self._free_camera_active = False
        self._free_camera_keys_down.clear()
        self._free_camera_look_active = False
        self._free_camera_last_mouse = None
        state = scene_clear_state()
        for ent, _tr in self._obj_map.values():
            ent.setParent(None)
        if state["clear_obj_map"]:
            self._obj_map.clear()
        if state["clear_obj_by_nick"]:
            self._obj_by_nick.clear()
        if state["clear_obj_component_refs"]:
            self._obj_component_refs.clear()
        if state["clear_obj_label_ent"]:
            self._obj_label_ent.clear()
        if state["clear_obj_label_tr"]:
            self._obj_label_tr.clear()
        if state["clear_obj_label_yoff"]:
            self._obj_label_yoff.clear()
        self._obj_selection_ent.clear()
        for ent, _tr in self._zone_map.values():
            ent.setParent(None)
        if state["clear_zone_map"]:
            self._zone_map.clear()
        if state["clear_zone_component_refs"]:
            self._zone_component_refs.clear()
        for ent in self._zone_entities:
            ent.setParent(None)
        if state["clear_zone_entities"]:
            self._zone_entities.clear()
        self._selected_obj = state["selected_obj"]
        self._locked_axis = state["locked_axis"]
        if state["clear_obj_sphere_ent"]:
            self._obj_sphere_ent.clear()
        for cached_ent, _cached_refs in self._native_detail_entity_cache.values():
            try:
                cached_ent.setParent(None)
            except Exception:
                pass
        self._native_detail_entity_cache.clear()
        for obj in tuple(self._native_preview_entity_by_obj.keys()):
            self._clear_native_preview_entity_for_object(obj)
        self._native_preview_entity_cache.clear()
        self._clear_selected_native_scene_data()
        if self._native_preview_refresh_timer is not None:
            self._native_preview_refresh_timer.stop()
        if self._native_preview_batch_timer is not None:
            self._native_preview_batch_timer.stop()
        self._discard_native_preview_pending_builds()
        self._native_preview_progress_total = 0
        self._native_preview_progress_done = 0
        self._native_preview_refresh_pending = False
        self._native_preview_refresh_after_batch = False
        if state["clear_axis_gizmo"]:
            self._clear_axis_gizmo()
        self._clear_reference_overlay()

    def set_data(self, objects, zones, scale: float):
        """Baut die 3D-Szene aus Objekt- und Zonenlisten auf."""
        if not QT3D_AVAILABLE:
            return
        self._scene_scale = float(scale)
        self.clear_scene()
        self._obj_by_nick = object_nick_index(list(objects))
        object_points_xyz: list[tuple[float, float, float]] = []

        for obj in objects:
            ent, tr, refs = self._create_object_entity(obj, scale)
            if ent is None:
                continue
            self._obj_map[obj] = (ent, tr)
            self._obj_component_refs[obj] = refs
            p = tr.translation()
            object_points_xyz.append((p.x(), p.y(), p.z()))

        for zone in zones:
            ent, tr, refs = self._create_zone_entity(zone, scale)
            if ent is not None and tr is not None:
                self._zone_map[zone] = (ent, tr)
                self._zone_component_refs[zone] = refs
                self._zone_entities.append(ent)

        state = scene_camera_state_from_points(object_points_xyz)
        tx, _ty, tz = state["cam_target_xyz"]
        self._cam_target = QVector3D(float(tx), float(self._orbit_target_plane_y), float(tz))
        self._cam_distance = float(state["cam_distance"])
        cx, _cy, cz = state["system_center_xyz"]
        self._system_center = QVector3D(float(cx), float(self._orbit_target_plane_y), float(cz))
        self._system_radius = float(state["system_radius"])
        self._cam_yaw = float(state["cam_yaw"])
        self._cam_pitch = float(state["cam_pitch"])
        self._update_camera()

    # ==================================================================
    #  Objekt-Entitäten
    # ==================================================================
    def _make_torus_mesh(self, radius: float, minor: float, rings: int = 52, slices: int = 24):
        extras_ns = getattr(Qt3DExtras, "Qt3DExtras", Qt3DExtras)
        torus_cls = getattr(extras_ns, "QTorusMesh", None)
        return build_torus_mesh(torus_cls, radius=radius, minor=minor, rings=rings, slices=slices)

    def _make_phong(self, color: QColor, ambient_lighter: int = 155):
        return make_phong_material(lambda: QPhongMaterial3D(self._root), color, ambient_lighter=ambient_lighter)

    def _make_alpha(self, color: QColor, alpha: float):
        return make_alpha_material(lambda: QPhongAlphaMaterial3D(self._root), color, alpha=alpha)

    def _resolve_planet_texture_path(self, obj) -> Path | None:
        resolver = self._planet_texture_resolver
        if resolver is None:
            return None
        try:
            return resolver(obj)
        except Exception:
            return None

    def _resolve_planet_cloud_texture_path(self, obj) -> Path | None:
        resolver = self._planet_cloud_texture_resolver
        if resolver is None:
            return None
        try:
            return resolver(obj)
        except Exception:
            return None

    def _build_planet_material(self, obj, fallback_color: QColor, refs: list[Any]):
        texture_path = self._resolve_planet_texture_path(obj)
        material = build_qt3d_texture_material(
            owner=self._root,
            texture_path=texture_path,
            texture_refs=refs,
        )
        if material is not None:
            return material
        return self._make_phong(fallback_color, ambient_lighter=132)

    def _build_planet_cloud_material(self, obj, fallback_color: QColor, refs: list[Any]):
        texture_path = self._resolve_planet_cloud_texture_path(obj)
        if texture_path is None and not self._planet_has_cloud_layer(obj):
            return None
        material = build_qt3d_texture_material(
            owner=self._root,
            texture_path=texture_path,
            texture_refs=refs,
        )
        if material is not None:
            return material
        return self._make_alpha(fallback_color, 0.16)

    def _resolve_planet_ring_info(self, obj) -> dict[str, object] | None:
        resolver = self._planet_ring_resolver
        if resolver is None:
            return None
        try:
            return resolver(obj)
        except Exception:
            return None

    @staticmethod
    def _planet_has_cloud_layer(obj) -> bool:
        archetype = str(getattr(obj, "data", {}).get("archetype", "") or "").strip().lower()
        return "cloud" in archetype or "cld" in archetype

    @staticmethod
    def _configure_planet_sphere_mesh(mesh, *, radius: float, shell: str = "surface") -> None:
        try:
            mesh.setRadius(float(radius))
        except Exception:
            pass
        shell_key = str(shell or "surface").strip().lower()
        rings = 48
        slices = 72
        if shell_key in {"cloud", "atmosphere", "glow"}:
            rings = 56
            slices = 84
        if shell_key == "surface":
            rings = 64
            slices = 96
        if hasattr(mesh, "setRings"):
            try:
                mesh.setRings(int(rings))
            except Exception:
                pass
        if hasattr(mesh, "setSlices"):
            try:
                mesh.setSlices(int(slices))
            except Exception:
                pass

    @staticmethod
    def _planet_atmosphere_radius_ratio(obj, planet_size_fl: float) -> float:
        try:
            atmosphere_range = float(str(getattr(obj, "data", {}).get("atmosphere_range", "") or "0").strip() or "0")
        except Exception:
            atmosphere_range = 0.0
        if atmosphere_range <= 0.0 or planet_size_fl <= 1e-6:
            return 0.0
        return max(1.01, min(1.65, atmosphere_range / max(planet_size_fl, 1e-6)))

    @staticmethod
    def _planet_burn_color(obj, fallback: QColor) -> QColor:
        raw = str(getattr(obj, "data", {}).get("burn_color", "") or "").strip()
        parts = [part.strip() for part in raw.split(",") if part.strip()]
        if len(parts) < 3:
            return fallback
        try:
            red = max(0, min(255, int(float(parts[0]))))
            green = max(0, min(255, int(float(parts[1]))))
            blue = max(0, min(255, int(float(parts[2]))))
        except Exception:
            return fallback
        return QColor(red, green, blue, 170)

    def _tradelane_direction_quaternion(self, obj) -> QQuaternion | None:
        prev_nick = str(obj.data.get("prev_ring", "")).strip().lower()
        next_nick = str(obj.data.get("next_ring", "")).strip().lower()
        prev_obj = self._obj_by_nick.get(prev_nick)
        next_obj = self._obj_by_nick.get(next_nick)
        return tradelane_direction_quaternion(
            current_pos_raw=obj.data.get("pos", "0,0,0"),
            prev_pos_raw=prev_obj.data.get("pos", "0,0,0") if prev_obj is not None else None,
            next_pos_raw=next_obj.data.get("pos", "0,0,0") if next_obj is not None else None,
        )

    def _rotation_quaternion_for_object(self, obj) -> QQuaternion:
        prev_nick = str(obj.data.get("prev_ring", "")).strip().lower()
        next_nick = str(obj.data.get("next_ring", "")).strip().lower()
        prev_obj = self._obj_by_nick.get(prev_nick)
        next_obj = self._obj_by_nick.get(next_nick)
        return object_rotation_quaternion(
            nickname=obj.nickname,
            archetype=obj.data.get("archetype", ""),
            rotate_raw=obj.data.get("rotate", "0,0,0"),
            current_pos_raw=obj.data.get("pos", "0,0,0"),
            prev_pos_raw=prev_obj.data.get("pos", "0,0,0") if prev_obj is not None else None,
            next_pos_raw=next_obj.data.get("pos", "0,0,0") if next_obj is not None else None,
        )

    def _placeholder_model_radius(self, obj) -> float | None:
        try:
            radius = getattr(obj, "_model_world_radius", None)
            if radius is not None:
                return max(0.1, float(radius))
        except Exception:
            pass
        return None

    def _placeholder_size_factor(self, obj, *, default_radius: float) -> float:
        model_radius = self._placeholder_model_radius(obj)
        if model_radius is None:
            return 1.0
        baseline = max(0.25, float(default_radius))
        return max(0.5, min(1.45, float(model_radius) / baseline))

    def _create_object_entity(self, obj, scale: float):
        arch = obj.data.get("archetype", "").lower()
        name = obj.nickname.lower()
        kind = classify_object_kind(nickname=name, archetype=arch)
        is_trade_lane = kind["is_trade_lane"]
        is_dock_ring = kind["is_dock_ring"]
        is_sun = kind["is_sun"]
        is_planet = kind["is_planet"]
        is_jump_gate = kind["is_jump_gate"]
        is_jump_hole = kind["is_jump_hole"]
        is_platform = kind["is_platform"]
        is_buoy_like = kind["is_buoy_like"]
        is_asteroid_like = kind["is_asteroid_like"]
        is_debris_like = kind["is_debris_like"]
        is_miner_like = kind["is_miner_like"]
        is_nomad_structure = kind["is_nomad_structure"]
        is_station_like = kind["is_station_like"]
        is_prison = kind["is_prison"]
        is_tank_like = kind["is_tank_like"]
        is_depot_like = kind["is_depot_like"]
        is_capship = kind["is_capship"]
        is_transport = kind["is_transport"]
        is_surprise_ship = kind["is_surprise_ship"]
        is_hazard = kind["is_hazard"]
        generic_size_factor = self._placeholder_size_factor(obj, default_radius=2.6)

        ent = QEntity3D(self._root)
        tr = QTransform3D()

        # Position
        fx, fy, fz = parse_pos(obj.data.get("pos", "0,0,0"))
        tr.setTranslation(QVector3D(fx * scale, fy * scale, fz * scale))
        tr.setRotation(self._rotation_quaternion_for_object(obj))

        # Picker
        picker = QObjectPicker3D(ent)
        picker.setHoverEnabled(False)
        picker.clicked.connect(lambda *args, o=obj: self._handle_object_picker_clicked(o, *args))

        # -- Visual Wrapper (default sichtbar; kann mehrere Meshes enthalten) --
        sphere_ent = QEntity3D(ent)
        self._obj_sphere_ent[obj] = sphere_ent

        component_refs: list[Any] = [tr, picker, sphere_ent]
        label_y_offset = 3.8

        def add_part(mesh, mat, sub_tr: QTransform3D | None = None):
            part_ent = QEntity3D(sphere_ent)
            part_ent.addComponent(mesh)
            part_ent.addComponent(mat)
            refs = [part_ent, mesh, mat]
            if sub_tr is not None:
                part_ent.addComponent(sub_tr)
                refs.append(sub_tr)
            component_refs.extend(refs)

        def add_selection_halo(radius: float):
            halo_mesh = QSphereMesh3D()
            halo_mesh.setRadius(max(1.2, float(radius) * 1.18))
            halo_mat = self._make_alpha(QColor(88, 214, 255, 220), 0.16)
            halo_ent = QEntity3D(sphere_ent)
            halo_ent.addComponent(halo_mesh)
            halo_ent.addComponent(halo_mat)
            halo_ent.setEnabled(False)
            self._obj_selection_ent[obj] = halo_ent
            component_refs.extend([halo_ent, halo_mesh, halo_mat])

        def add_forward_markers(z_front: float, z_back: float, size: float):
            if QConeMesh3D is not None:
                f_mesh = QConeMesh3D()
                f_mesh.setLength(size * 1.7)
                f_mesh.setBottomRadius(size * 0.55)
                try:
                    f_mesh.setTopRadius(0.0)
                except Exception:
                    pass
            else:
                f_mesh = QCylinderMesh3D()
                f_mesh.setLength(size * 1.5)
                f_mesh.setRadius(size * 0.38)
            f_mat = self._make_phong(QColor(92, 230, 130), ambient_lighter=126)
            f_tr = QTransform3D()
            f_tr.setTranslation(QVector3D(0.0, 0.0, z_front))
            # Cone points +Y by default -> rotate so tip points +Z (forward).
            f_tr.setRotation(QQuaternion.fromAxisAndAngle(1.0, 0.0, 0.0, -90.0))
            add_part(f_mesh, f_mat, f_tr)

            b_mesh = QSphereMesh3D()
            b_mesh.setRadius(size * 0.55)
            b_mat = self._make_phong(QColor(236, 108, 98), ambient_lighter=122)
            b_tr = QTransform3D()
            b_tr.setTranslation(QVector3D(0.0, 0.0, z_back))
            add_part(b_mesh, b_mat, b_tr)

        def add_trade_lane_placeholder(radius: float, tube: float):
            inner_ring_radius = max(0.9, radius * 0.78)
            inner_ring_tube = max(0.16, tube * 0.24)
            ring_mesh = self._make_torus_mesh(inner_ring_radius, inner_ring_tube, rings=14, slices=8)
            if ring_mesh is None:
                add_portal_ring(inner_ring_radius, inner_ring_tube, QColor(92, 122, 156), segments=8)
            else:
                ring_mat = self._make_phong(QColor(92, 122, 156), ambient_lighter=126)
                add_part(ring_mesh, ring_mat)

            module_count = 8
            module_radius = max(inner_ring_radius + (tube * 0.8), radius * 0.92)
            blade_len = max(1.6, radius * 0.92)
            blade_width = max(0.20, tube * 0.34)
            blade_depth = max(0.12, tube * 0.16)
            fin_len = max(1.15, radius * 0.56)
            fin_width = max(0.14, tube * 0.22)
            fin_depth = max(0.10, tube * 0.14)

            for i in range(module_count):
                ang = (2.0 * math.pi * i) / module_count
                angle_deg = float(math.degrees(ang))
                tangent_deg = angle_deg + 90.0
                radial_dir = QVector3D(math.cos(ang), math.sin(ang), 0.0)
                tangent_dir = QVector3D(-math.sin(ang), math.cos(ang), 0.0)
                sweep_sign = -1.0 if (math.cos(ang) * math.sin(ang)) >= 0.0 else 1.0
                blade_center = radial_dir * module_radius + tangent_dir * (blade_len * 0.05 * sweep_sign)

                blade_mesh = QCuboidMesh3D()
                blade_mesh.setXExtent(blade_len)
                blade_mesh.setYExtent(blade_width)
                blade_mesh.setZExtent(blade_depth)
                blade_mat = self._make_phong(QColor(116, 168, 214), ambient_lighter=134)
                blade_tr = QTransform3D()
                blade_tr.setTranslation(blade_center)
                blade_tr.setRotation(
                    QQuaternion.fromAxisAndAngle(0.0, 0.0, 1.0, tangent_deg + (sweep_sign * 24.0))
                )
                add_part(blade_mesh, blade_mat, blade_tr)

                fin_mesh = QCuboidMesh3D()
                fin_mesh.setXExtent(fin_len)
                fin_mesh.setYExtent(fin_width)
                fin_mesh.setZExtent(fin_depth)
                fin_mat = self._make_phong(QColor(86, 118, 152), ambient_lighter=126)
                fin_tr = QTransform3D()
                fin_tr.setTranslation(
                    blade_center
                    - radial_dir * (blade_len * 0.20)
                    + tangent_dir * (blade_len * 0.12 * sweep_sign)
                )
                fin_tr.setRotation(
                    QQuaternion.fromAxisAndAngle(0.0, 0.0, 1.0, tangent_deg - (sweep_sign * 52.0))
                )
                add_part(fin_mesh, fin_mat, fin_tr)

            brace_len = max(1.2, radius * 1.20)
            brace_width = max(0.12, tube * 0.18)
            brace_depth = max(0.08, tube * 0.12)
            for angle_deg in (-45.0, 45.0):
                brace_mesh = QCuboidMesh3D()
                brace_mesh.setXExtent(brace_len)
                brace_mesh.setYExtent(brace_width)
                brace_mesh.setZExtent(brace_depth)
                brace_mat = self._make_phong(QColor(54, 70, 94), ambient_lighter=118)
                brace_tr = QTransform3D()
                brace_tr.setRotation(QQuaternion.fromAxisAndAngle(0.0, 0.0, 1.0, angle_deg))
                add_part(brace_mesh, brace_mat, brace_tr)

        def add_portal_ring(radius: float, thickness: float, color: QColor, segments: int = 12):
            # Build a guaranteed upright, fly-through ring in XY plane (hole axis = Z).
            arc_len = max(0.35, (2.0 * math.pi * radius) / segments * 0.92)
            for i in range(segments):
                ang = (2.0 * math.pi * i) / segments
                seg_mesh = QCuboidMesh3D()
                seg_mesh.setXExtent(max(0.14, thickness * 0.55))
                seg_mesh.setYExtent(max(0.16, thickness * 0.62))
                seg_mesh.setZExtent(arc_len)
                seg_mat = self._make_phong(color, ambient_lighter=128)
                seg_tr = QTransform3D()
                seg_tr.setTranslation(
                    QVector3D(
                        math.cos(ang) * radius,
                        math.sin(ang) * radius,
                        0.0,
                    )
                )
                seg_tr.setRotation(QQuaternion.fromAxisAndAngle(0.0, 0.0, 1.0, float(math.degrees(ang))))
                add_part(seg_mesh, seg_mat, seg_tr)

        # Primitive-basierte Visuals pro Objekttyp.
        if is_sun:
            sun_r = scaled_radius_from_arch(arch, default_size=2000.0, base_size=2000.0, base_radius=10.5, min_r=7.5, max_r=17.0)
            label_y_offset = max(label_y_offset, sun_r * 1.75)
            sun_core, sun_glow_in, sun_glow_out = sun_palette(arch, name)
            core = QSphereMesh3D()
            core.setRadius(sun_r)
            core_mat = self._make_phong(sun_core, ambient_lighter=120)
            add_part(core, core_mat)

            for radius, alpha, col in (
                (sun_r * 1.28, 0.30, sun_glow_in),
                (sun_r * 1.62, 0.14, sun_glow_out),
            ):
                glow_mesh = QSphereMesh3D()
                glow_mesh.setRadius(radius)
                glow_tr = QTransform3D()
                glow_mat = self._make_alpha(col, alpha)
                add_part(glow_mesh, glow_mat, glow_tr)
        elif is_planet:
            # Planet archetypes (e.g. planet_earthgrncld_4000) encode the in-game size.
            # Map that size directly into scene units so relative planet scale matches Freelancer better.
            p_size = extract_arch_size(arch, 1800.0)
            p_r = max(2.5, min(160.0, float(p_size) * float(scale)))
            label_y_offset = max(label_y_offset, p_r * 1.45)
            p_color, cloud_color = planet_palette(arch, name)
            planet = QSphereMesh3D()
            self._configure_planet_sphere_mesh(planet, radius=p_r, shell="surface")
            planet_mat = self._build_planet_material(obj, p_color, component_refs)
            add_part(planet, planet_mat)

            cloud_mat = self._build_planet_cloud_material(obj, cloud_color, component_refs)
            if cloud_mat is not None:
                cloud = QSphereMesh3D()
                self._configure_planet_sphere_mesh(cloud, radius=(p_r * 1.018), shell="cloud")
                add_part(cloud, cloud_mat)

            atmosphere_ratio = self._planet_atmosphere_radius_ratio(obj, float(p_size))
            if atmosphere_ratio > 0.0:
                atmosphere_color = self._planet_burn_color(obj, cloud_color)
                atmosphere = QSphereMesh3D()
                self._configure_planet_sphere_mesh(atmosphere, radius=(p_r * atmosphere_ratio), shell="atmosphere")
                atmosphere_mat = self._make_alpha(atmosphere_color, 0.10)
                add_part(atmosphere, atmosphere_mat)

                glow = QSphereMesh3D()
                self._configure_planet_sphere_mesh(glow, radius=(p_r * min(atmosphere_ratio + 0.03, 1.72)), shell="glow")
                glow_mat = self._make_alpha(atmosphere_color, 0.05)
                add_part(glow, glow_mat)
        elif is_jump_gate:
            label_y_offset = max(label_y_offset, 5.2)
            gate_scale = min(1.1, self._placeholder_size_factor(obj, default_radius=4.2))
            gate_radius = 4.2 * gate_scale
            add_portal_ring(gate_radius, 0.86, QColor(154, 164, 186), segments=14)
            add_portal_ring(gate_radius * 1.18, 0.42, QColor(116, 126, 152), segments=16)

            for i in range(6):
                spoke_mesh = QCuboidMesh3D()
                spoke_mesh.setXExtent(0.36 * gate_scale)
                spoke_mesh.setYExtent(0.30 * gate_scale)
                spoke_mesh.setZExtent(gate_radius * 0.95)
                spoke_mat = self._make_phong(QColor(108, 116, 142), ambient_lighter=132)
                spoke_tr = QTransform3D()
                spoke_tr.setTranslation(QVector3D(0.0, 0.0, gate_radius * 0.58))
                spoke_tr.setRotation(QQuaternion.fromAxisAndAngle(1.0, 0.0, 0.0, float(i * 60)))
                add_part(spoke_mesh, spoke_mat, spoke_tr)

            for i in range(4):
                strut_mesh = QCylinderMesh3D()
                strut_mesh.setRadius(max(0.14, 0.18 * gate_scale))
                strut_mesh.setLength(gate_radius * 0.96)
                strut_mat = self._make_phong(QColor(132, 142, 170), ambient_lighter=134)
                strut_tr = QTransform3D()
                angle_deg = float(i * 90.0 + 45.0)
                angle_rad = math.radians(angle_deg)
                strut_tr.setTranslation(
                    QVector3D(
                        math.cos(angle_rad) * gate_radius * 0.46,
                        math.sin(angle_rad) * gate_radius * 0.46,
                        0.0,
                    )
                )
                strut_tr.setRotation(QQuaternion.fromEulerAngles(0.0, 0.0, angle_deg))
                add_part(strut_mesh, strut_mat, strut_tr)

            core_mesh = QSphereMesh3D()
            core_mesh.setRadius(max(1.55, gate_radius * 0.27))
            core_mat = self._make_alpha(QColor(132, 186, 255, 150), 0.32)
            add_part(core_mesh, core_mat)
            add_forward_markers(z_front=gate_radius + 1.7, z_back=-(gate_radius + 1.7), size=0.62)
        elif is_jump_hole:
            label_y_offset = max(label_y_offset, 4.6)
            ring_mesh = self._make_torus_mesh(4.2, 0.58)
            if ring_mesh is None:
                ring_mesh = QSphereMesh3D()
                ring_mesh.setRadius(3.2)
            ring_mat = self._make_phong(QColor(92, 72, 156), ambient_lighter=140)
            add_part(ring_mesh, ring_mat)

            vortex_mesh = QSphereMesh3D()
            vortex_mesh.setRadius(2.3)
            vortex_mat = self._make_alpha(QColor(108, 156, 255, 170), 0.44)
            add_part(vortex_mesh, vortex_mat)
        elif is_trade_lane or is_dock_ring:
            label_y_offset = max(label_y_offset, 2.8)
            default_radius = 3.0 if is_trade_lane else 3.4
            ring_radius = default_radius * self._placeholder_size_factor(obj, default_radius=default_radius)
            ring_radius = max(default_radius, min(9.5 if is_trade_lane else 11.0, ring_radius))
            ring_tube = max(0.48, min(1.35, ring_radius * (0.18 if is_trade_lane else 0.19)))
            if is_trade_lane:
                add_trade_lane_placeholder(ring_radius, ring_tube)
            else:
                # Explicit portal ring geometry, always upright/fly-through.
                add_portal_ring(ring_radius, ring_tube, QColor(74, 162, 255), segments=12)

                pylon_count = 6
                pylon_radius = ring_radius * 0.78
                pylon_len = max(0.9, ring_radius * 0.44)
                pylon_width = max(0.18, ring_tube * 0.62)
                pylon_col = QColor(156, 170, 196)
                for i in range(pylon_count):
                    ang = (2.0 * math.pi * i) / pylon_count
                    arm_mesh = QCuboidMesh3D()
                    arm_mesh.setXExtent(pylon_width)
                    arm_mesh.setYExtent(max(0.18, pylon_width * 1.1))
                    arm_mesh.setZExtent(pylon_len)
                    arm_mat = self._make_phong(pylon_col, ambient_lighter=132)
                    arm_tr = QTransform3D()
                    arm_tr.setTranslation(
                        QVector3D(
                            math.cos(ang) * pylon_radius,
                            math.sin(ang) * pylon_radius,
                            0.0,
                        )
                    )
                    arm_tr.setRotation(QQuaternion.fromAxisAndAngle(0.0, 0.0, 1.0, float(math.degrees(ang))))
                    add_part(arm_mesh, arm_mat, arm_tr)

            if not is_trade_lane:
                # Dock ring can keep a center hub; trade lanes skip this for performance.
                hub_mesh = QSphereMesh3D()
                hub_mesh.setRadius(max(0.8, ring_radius * 0.24))
                hub_mat = self._make_phong(QColor(150, 170, 198), ambient_lighter=140)
                add_part(hub_mesh, hub_mat)
                add_forward_markers(z_front=ring_radius + 0.95, z_back=-(ring_radius + 0.95), size=0.5)
        elif is_buoy_like:
            label_y_offset = max(label_y_offset, 2.2)
            buoy_scale = min(1.45, self._placeholder_size_factor(obj, default_radius=1.6))
            post_mesh = QCylinderMesh3D()
            post_mesh.setRadius((0.18 if "nav" in arch else 0.22) * buoy_scale)
            post_mesh.setLength((2.2 if "m10" in arch else 2.8) * buoy_scale)
            post_mat = self._make_phong(QColor(190, 188, 138) if "nav" in arch else QColor(170, 170, 185), ambient_lighter=132)
            add_part(post_mesh, post_mat)

            top_mesh = QSphereMesh3D()
            top_mesh.setRadius((0.42 if "gravity" in arch else 0.36) * buoy_scale)
            top_col = QColor(115, 185, 255)
            if "hazard" in arch:
                top_col = QColor(255, 118, 88)
            elif "nav" in arch:
                top_col = QColor(240, 208, 112)
            top_mat = self._make_alpha(top_col, 0.35)
            top_tr = QTransform3D()
            top_tr.setTranslation(QVector3D(0.0, 1.35 * buoy_scale, 0.0))
            add_part(top_mesh, top_mat, top_tr)

            cross_width = max(0.12, 0.16 * buoy_scale)
            cross_len = max(0.9, 1.2 * buoy_scale)
            for axis, offset in (
                ("x", QVector3D(0.0, 0.4 * buoy_scale, 0.0)),
                ("z", QVector3D(0.0, -0.4 * buoy_scale, 0.0)),
            ):
                arm_mesh = QCuboidMesh3D()
                arm_mesh.setXExtent(cross_len if axis == "x" else cross_width)
                arm_mesh.setYExtent(cross_width)
                arm_mesh.setZExtent(cross_width if axis == "x" else cross_len)
                arm_mat = self._make_phong(QColor(156, 160, 170), ambient_lighter=130)
                arm_tr = QTransform3D()
                arm_tr.setTranslation(offset)
                add_part(arm_mesh, arm_mat, arm_tr)
        elif is_platform:
            label_y_offset = max(label_y_offset, 3.2)
            core_r = (0.88 if arch == "small_wplatform" else 1.12) * min(1.45, generic_size_factor)
            core_mesh = QCylinderMesh3D()
            core_mesh.setRadius(core_r)
            core_mesh.setLength((2.6 if arch == "small_wplatform" else 3.5) * min(1.65, generic_size_factor))
            core_mat = self._make_phong(QColor(122, 136, 160), ambient_lighter=136)
            add_part(core_mesh, core_mat)

            arms = 3 if arch == "small_wplatform" else 4
            arm_len = (3.6 if arch == "small_wplatform" else 4.5) * min(1.7, generic_size_factor)
            for i in range(arms):
                arm_mesh = QCuboidMesh3D()
                arm_mesh.setXExtent(0.28)
                arm_mesh.setYExtent(0.28)
                arm_mesh.setZExtent(arm_len)
                arm_mat = self._make_phong(QColor(102, 116, 142), ambient_lighter=132)
                arm_tr = QTransform3D()
                angle_deg = float(i * (360.0 / arms))
                angle_rad = math.radians(angle_deg)
                offset = core_r + arm_len / 2.0
                arm_tr.setTranslation(QVector3D(
                    math.sin(angle_rad) * offset,
                    0.0,
                    math.cos(angle_rad) * offset,
                ))
                arm_tr.setRotation(QQuaternion.fromAxisAndAngle(0.0, 1.0, 0.0, angle_deg))
                add_part(arm_mesh, arm_mat, arm_tr)

            turret_count = 3 if arch == "small_wplatform" else 4
            turret_offset = core_r + arm_len * 0.72
            for i in range(turret_count):
                angle_deg = float(i * (360.0 / turret_count))
                angle_rad = math.radians(angle_deg)
                turret_mesh = QCylinderMesh3D()
                turret_mesh.setRadius(max(0.18, core_r * 0.22))
                turret_mesh.setLength(max(0.8, core_r * 1.25))
                turret_mat = self._make_phong(QColor(148, 156, 182), ambient_lighter=136)
                turret_tr = QTransform3D()
                turret_tr.setTranslation(
                    QVector3D(
                        math.sin(angle_rad) * turret_offset,
                        0.0,
                        math.cos(angle_rad) * turret_offset,
                    )
                )
                turret_tr.setRotation(QQuaternion.fromAxisAndAngle(1.0, 0.0, 0.0, 90.0))
                add_part(turret_mesh, turret_mat, turret_tr)
        elif is_asteroid_like:
            label_y_offset = max(label_y_offset, 2.5)
            rock_r = 1.15
            if "large" in arch:
                rock_r = 2.1
            elif "small" in arch:
                rock_r = 0.8
            elif "60" in arch:
                rock_r = 0.95
            rock_mesh = QSphereMesh3D()
            rock_mesh.setRadius(rock_r)
            rock_col = QColor(114, 104, 92)
            if "ice" in arch:
                rock_col = QColor(164, 184, 206)
            elif "lava" in arch:
                rock_col = QColor(162, 92, 70)
            elif "nomad" in arch:
                rock_col = QColor(112, 90, 150)
            rock_mat = self._make_phong(rock_col, ambient_lighter=128)
            add_part(rock_mesh, rock_mat)
        elif is_debris_like:
            label_y_offset = max(label_y_offset, 2.3)
            deb_mesh = QCuboidMesh3D()
            deb_mesh.setXExtent(1.6 if "xlarge" in arch else 1.2)
            deb_mesh.setYExtent(0.8)
            deb_mesh.setZExtent(2.2 if "large" in arch else 1.5)
            deb_mat = self._make_phong(QColor(102, 106, 114), ambient_lighter=126)
            add_part(deb_mesh, deb_mat)

            fin_mesh = QCuboidMesh3D()
            fin_mesh.setXExtent(0.24)
            fin_mesh.setYExtent(0.95)
            fin_mesh.setZExtent(1.35)
            fin_mat = self._make_phong(QColor(92, 98, 106), ambient_lighter=122)
            for off in (QVector3D(0.75, 0.0, -0.55), QVector3D(-0.75, 0.0, 0.45)):
                fin_tr = QTransform3D()
                fin_tr.setTranslation(off)
                add_part(fin_mesh, fin_mat, fin_tr)
        elif is_miner_like:
            label_y_offset = max(label_y_offset, 3.0)
            hub = QSphereMesh3D()
            hub.setRadius(1.1 * min(2.8, generic_size_factor))
            hub_mat = self._make_phong(QColor(126, 136, 148), ambient_lighter=132)
            add_part(hub, hub_mat)

            for i in range(4):
                arm_mesh = QCylinderMesh3D()
                arm_mesh.setRadius(0.16)
                arm_mesh.setLength(2.3 * min(3.0, generic_size_factor))
                arm_mat = self._make_phong(QColor(104, 116, 136), ambient_lighter=128)
                arm_tr = QTransform3D()
                arm_tr.setTranslation(QVector3D(0.0, 0.0, 1.35 * min(3.0, generic_size_factor)))
                arm_tr.setRotation(QQuaternion.fromAxisAndAngle(0.0, 1.0, 0.0, float(i * 90.0)))
                add_part(arm_mesh, arm_mat, arm_tr)
        elif is_nomad_structure:
            label_y_offset = max(label_y_offset, 4.2)
            core = QSphereMesh3D()
            core.setRadius(2.3 if "dyson" in arch else 1.7)
            core_mat = self._make_phong(QColor(86, 102, 156), ambient_lighter=136)
            add_part(core, core_mat)
            aura = QSphereMesh3D()
            aura.setRadius(2.9 if "dyson" in arch else 2.25)
            aura_mat = self._make_alpha(QColor(118, 146, 235, 150), 0.24)
            add_part(aura, aura_mat)
        elif is_prison:
            label_y_offset = max(label_y_offset, 4.4)
            body_mesh = QCuboidMesh3D()
            body_mesh.setXExtent(4.4)
            body_mesh.setYExtent(4.4)
            body_mesh.setZExtent(4.4)
            body_mat = self._make_phong(QColor(118, 128, 152), ambient_lighter=134)
            add_part(body_mesh, body_mat)

            for off in (
                QVector3D(2.9, 0.0, 0.0),
                QVector3D(-2.9, 0.0, 0.0),
                QVector3D(0.0, 2.9, 0.0),
                QVector3D(0.0, -2.9, 0.0),
            ):
                n_mesh = QSphereMesh3D()
                n_mesh.setRadius(0.46)
                n_mat = self._make_phong(QColor(166, 176, 198), ambient_lighter=132)
                n_tr = QTransform3D()
                n_tr.setTranslation(off)
                add_part(n_mesh, n_mat, n_tr)
        elif is_station_like:
            label_y_offset = max(label_y_offset, 4.2)
            station_scale = min(1.2, generic_size_factor)
            body_mesh = QCuboidMesh3D()
            body_mesh.setXExtent(2.5 * station_scale)
            body_mesh.setYExtent(2.3 * station_scale)
            body_mesh.setZExtent(6.2 * station_scale)
            body_mat = self._make_phong(QColor(126, 138, 160), ambient_lighter=136)
            add_part(body_mesh, body_mat)

            side_offsets = (
                QVector3D(2.2 * station_scale, 0.0, 0.0),
                QVector3D(-2.2 * station_scale, 0.0, 0.0),
            )
            for off in side_offsets:
                mod_mesh = QCylinderMesh3D()
                mod_mesh.setRadius(0.86 * station_scale)
                mod_mesh.setLength(2.9 * station_scale)
                mod_mat = self._make_phong(QColor(104, 118, 145), ambient_lighter=132)
                mod_tr = QTransform3D()
                mod_tr.setTranslation(off)
                mod_tr.setRotation(QQuaternion.fromAxisAndAngle(0.0, 0.0, 1.0, 90.0))
                add_part(mod_mesh, mod_mat, mod_tr)
        elif is_tank_like:
            label_y_offset = max(label_y_offset, 3.4)
            tank_scale = min(1.55, generic_size_factor)
            tank_mesh = QCylinderMesh3D()
            tank_mesh.setRadius((1.35 if "dmg" not in arch else 1.2) * tank_scale)
            tank_mesh.setLength(4.2 * tank_scale)
            tank_mat = self._make_phong(QColor(112, 128, 145) if "dmg" not in arch else QColor(86, 94, 108), ambient_lighter=128)
            tank_tr = QTransform3D()
            tank_tr.setRotation(QQuaternion.fromAxisAndAngle(1.0, 0.0, 0.0, 90.0))
            add_part(tank_mesh, tank_mat, tank_tr)

            for off in (QVector3D(1.7 * tank_scale, 0.0, 0.0), QVector3D(-1.7 * tank_scale, 0.0, 0.0)):
                small_mesh = QSphereMesh3D()
                small_mesh.setRadius(0.62 * tank_scale)
                small_mat = self._make_phong(QColor(102, 116, 136), ambient_lighter=126)
                small_tr = QTransform3D()
                small_tr.setTranslation(off)
                add_part(small_mesh, small_mat, small_tr)
        elif is_depot_like:
            label_y_offset = max(label_y_offset, 2.7)
            depot_scale = min(1.5, self._placeholder_size_factor(obj, default_radius=1.5))
            # Kompakter Tank-/Container-Cluster.
            for off, rad in (
                (QVector3D(0.0, 0.0, 0.0), 0.9 * depot_scale),
                (QVector3D(1.45 * depot_scale, 0.0, 0.45 * depot_scale), 0.62 * depot_scale),
                (QVector3D(-1.35 * depot_scale, 0.2 * depot_scale, -0.35 * depot_scale), 0.56 * depot_scale),
                (QVector3D(0.35 * depot_scale, -0.15 * depot_scale, -1.25 * depot_scale), 0.48 * depot_scale),
            ):
                dep_mesh = QSphereMesh3D()
                dep_mesh.setRadius(rad)
                dep_mat = self._make_phong(QColor(138, 118, 96), ambient_lighter=132)
                dep_tr = QTransform3D()
                dep_tr.setTranslation(off)
                add_part(dep_mesh, dep_mat, dep_tr)

            frame_mesh = QCuboidMesh3D()
            frame_mesh.setXExtent(3.6 * depot_scale)
            frame_mesh.setYExtent(max(0.18, 0.22 * depot_scale))
            frame_mesh.setZExtent(0.22 * depot_scale)
            frame_mat = self._make_phong(QColor(164, 146, 124), ambient_lighter=132)
            for off in (
                QVector3D(0.0, 0.9 * depot_scale, 1.4 * depot_scale),
                QVector3D(0.0, -0.9 * depot_scale, 1.4 * depot_scale),
                QVector3D(0.0, 0.9 * depot_scale, -1.4 * depot_scale),
                QVector3D(0.0, -0.9 * depot_scale, -1.4 * depot_scale),
            ):
                frame_tr = QTransform3D()
                frame_tr.setTranslation(off)
                add_part(frame_mesh, frame_mat, frame_tr)
        elif is_capship or is_transport or is_surprise_ship:
            label_y_offset = max(label_y_offset, 3.4)
            ship_scale = 0.56 if is_surprise_ship else (0.72 if is_transport else 0.82)
            hull_mesh = QCylinderMesh3D()
            hull_mesh.setRadius((0.62 if is_surprise_ship else (0.95 if is_transport else 1.35)) * ship_scale)
            hull_mesh.setLength((6.8 if is_surprise_ship else (8.6 if is_transport else 12.4)) * ship_scale)
            hull_mat = self._make_phong(QColor(116, 130, 152), ambient_lighter=136)
            hull_tr = QTransform3D()
            hull_tr.setRotation(QQuaternion.fromAxisAndAngle(1.0, 0.0, 0.0, 90.0))
            add_part(hull_mesh, hull_mat, hull_tr)

            nose_mesh = QConeMesh3D() if QConeMesh3D is not None else QCylinderMesh3D()
            if QConeMesh3D is not None:
                nose_mesh.setLength((1.9 if is_surprise_ship else 2.5) * ship_scale)
                nose_mesh.setBottomRadius((0.55 if is_surprise_ship else 0.85) * ship_scale)
                try:
                    nose_mesh.setTopRadius(0.02)
                except Exception:
                    pass
            else:
                nose_mesh.setLength(1.6 * ship_scale)
                nose_mesh.setRadius(0.52 * ship_scale)
            nose_mat = self._make_phong(QColor(142, 154, 172), ambient_lighter=134)
            nose_tr = QTransform3D()
            nose_tr.setTranslation(QVector3D(0.0, 0.0, (3.9 if is_surprise_ship else (4.9 if is_transport else 6.8)) * ship_scale))
            add_part(nose_mesh, nose_mat, nose_tr)
        elif is_hazard:
            label_y_offset = max(label_y_offset, 3.2)
            hz_mesh = QSphereMesh3D()
            hz_mesh.setRadius(2.8 if "neutron" in arch else 2.4)
            hz_col = QColor(230, 80, 60, 180)
            if "baxter" in arch:
                hz_col = QColor(188, 108, 255, 176)
            elif "neutron" in arch:
                hz_col = QColor(166, 192, 255, 180)
            hz_mat = self._make_alpha(hz_col, 0.33)
            add_part(hz_mesh, hz_mat)

            hz_core = QSphereMesh3D()
            hz_core.setRadius(1.25 if "neutron" in arch else 1.1)
            hz_core_mat = self._make_alpha(QColor(255, 180, 90, 160) if "neutron" not in arch else QColor(214, 226, 255, 168), 0.45)
            add_part(hz_core, hz_core_mat)
        else:
            # Fallback für Stationen / sonstige Objekte.
            mesh = QSphereMesh3D()
            if "surprise" in name:
                mesh.setRadius(1.2)
            elif any(x in arch for x in ("base", "station")):
                mesh.setRadius(1.55)
            else:
                mesh.setRadius(1.85)
            mat = self._make_phong(object_color(nickname=obj.nickname, archetype=obj.data.get("archetype", "")), ambient_lighter=165)
            base_ent = QEntity3D(sphere_ent)
            base_ent.addComponent(mesh)
            base_ent.addComponent(mat)
            component_refs.extend([base_ent, mesh, mat])

        ring_info = self._resolve_planet_ring_info(obj)
        if ring_info:
            direct_inner_radius = ring_info.get("inner_radius")
            direct_outer_radius = ring_info.get("outer_radius")
            if direct_inner_radius is not None and direct_outer_radius is not None:
                inner_radius = max(0.1, float(direct_inner_radius) * float(scale))
                outer_radius = max(inner_radius + 0.1, float(direct_outer_radius) * float(scale))
            else:
                reference_radius = 1.85
                if is_planet:
                    reference_radius = p_r
                elif is_sun:
                    reference_radius = sun_r
                reference_radius = max(reference_radius, label_y_offset * 0.42)
                inner_radius = reference_radius * float(ring_info.get("inner_ratio", 1.35) or 1.35)
                outer_radius = reference_radius * float(ring_info.get("outer_ratio", 2.2) or 2.2)
            ring_renderer = build_annulus_renderer(
                owner=sphere_ent,
                inner_radius=inner_radius,
                outer_radius=outer_radius,
                segments=128,
            )
            ring_material = build_qt3d_texture_material(
                owner=self._root,
                texture_path=ring_info.get("texture_path"),
                texture_refs=component_refs,
            )
            if ring_material is None:
                ring_material = self._make_alpha(QColor(196, 184, 148), 0.26)
            ring_tr = QTransform3D()
            rotate_xyz = ring_info.get("rotate_xyz")
            if isinstance(rotate_xyz, (tuple, list)) and len(rotate_xyz) >= 3:
                try:
                    ring_tr.setRotation(
                        rotation_quaternion_from_fl(
                            float(rotate_xyz[0]),
                            float(rotate_xyz[1]),
                            float(rotate_xyz[2]),
                        )
                    )
                except Exception:
                    pass
            add_part(ring_renderer, ring_material, ring_tr)
            label_y_offset = max(label_y_offset, min(outer_radius * 0.35, 16.0))

        ent.addComponent(tr)
        ent.addComponent(picker)

        show_label = (not is_trade_lane) and (not is_buoy_like)
        add_selection_halo(max(1.8, label_y_offset * 0.42))
        world_pos = tr.translation()
        lbl_ent, lbl_tr, lbl_refs = self._attach_object_label(
            obj.nickname,
            world_pos,
            y_offset=label_y_offset,
            enabled=show_label,
        )
        if lbl_ent is not None and show_label:
            self._obj_label_ent[obj] = lbl_ent
            self._obj_label_tr[obj] = lbl_tr
            self._obj_label_yoff[obj] = float(label_y_offset)
            lbl_ent.setEnabled(self._labels_visible)
        component_refs.extend(lbl_refs)
        self._update_label_scales()
        return ent, tr, component_refs

    def _attach_object_label(self, text: str, world_pos: QVector3D, y_offset: float = 3.8, enabled: bool = True):
        if not enabled:
            return None, None, []
        if not QExtrudedTextMesh3D:
            return None, None, []
        label_text = text if len(text) <= 28 else (text[:25] + "...")
        lbl_ent = QEntity3D(self._root)
        txt_mesh = QExtrudedTextMesh3D()
        txt_mesh.setText(label_text)
        txt_mesh.setDepth(0.11)
        txt_mesh.setFont(QFont("Sans", 9))
        txt_tr = QTransform3D()
        txt_tr.setTranslation(
            QVector3D(
                float(world_pos.x()) + 1.0,
                float(world_pos.y()) + float(y_offset),
                float(world_pos.z()) + 1.0,
            )
        )
        txt_tr.setScale(0.58)
        txt_mat = QPhongMaterial3D(self._root)
        txt_mat.setDiffuse(QColor(228, 236, 246))
        try:
            txt_mat.setAmbient(QColor(180, 192, 208))
        except Exception:
            pass
        lbl_ent.addComponent(txt_mesh)
        lbl_ent.addComponent(txt_tr)
        lbl_ent.addComponent(txt_mat)
        return lbl_ent, txt_tr, [lbl_ent, txt_mesh, txt_tr, txt_mat]

    # ==================================================================
    #  Zonen-Entitäten
    # ==================================================================
    def _create_zone_entity(self, zone, scale: float):
        zone_name = zone.nickname.lower()
        is_tradelane = "tradelane" in zone_name
        uses_legacy_cylinder_yaw = (
            "path" in zone_name or "patrol" in zone_name or "exclusion" in zone_name
        )

        ent = QEntity3D(self._root)
        tr = QTransform3D()

        sp = [float(s.strip()) for s in zone.data.get("size", "1000").split(",")]
        s0 = sp[0] if len(sp) > 0 else 1000.0
        s1 = sp[1] if len(sp) > 1 else s0
        s2 = sp[2] if len(sp) > 2 else s0
        shape = str(zone.data.get("shape", "SPHERE")).upper()
        mesh = None
        if is_tradelane:
            mesh = QSphereMesh3D()
            mesh.setRadius(2.6)
            tr.setScale3D(QVector3D(1.0, 1.0, 1.0))
        else:
            sx = max(4.0, min(1400.0, s0 * scale))
            sy = max(4.0, min(1400.0, s1 * scale))
            sz = max(4.0, min(1400.0, s2 * scale))
            if shape == "BOX":
                mesh = QCuboidMesh3D()
                mesh.setXExtent(sx)
                mesh.setYExtent(sy)
                mesh.setZExtent(sz)
                tr.setScale3D(QVector3D(1.0, 1.0, 1.0))
            elif shape == "CYLINDER":
                mesh = QCylinderMesh3D()
                mesh.setRadius(sx)
                mesh.setLength(sy)
                tr.setScale3D(QVector3D(1.0, 1.0, 1.0))
            else:
                mesh = QSphereMesh3D()
                mesh.setRadius(1.0)
                tr.setScale3D(QVector3D(sx, sy, sz))

        zone_col = zone_color(nickname=zone.nickname, data=zone.data)
        mat = QPhongAlphaMaterial3D(self._root)
        mat.setAlpha(0.58 if is_tradelane else 0.14)
        mat.setDiffuse(zone_col)
        try:
            mat.setAmbient(zone_col.lighter(120))
        except Exception:
            pass
        # Zones are an editor overlay and should stay visible even when other models
        # sit in front of them from the current camera angle.
        always_on_top_refs = material_always_on_top_refs(mat, Qt3DRender)
        # Overlapping translucent zones should not occlude each other via depth writes.
        depth_state_refs = material_no_depth_write_refs(mat, Qt3DRender)
        # Zones should remain visible from inside and from both sides.
        cull_state_refs = material_no_cull_refs(mat, Qt3DRender)

        pparts = [float(c.strip()) for c in zone.data.get("pos", "0,0,0").split(",")]
        fx = pparts[0] if len(pparts) > 0 else 0.0
        fy = pparts[1] if len(pparts) > 1 else 0.0
        fz = pparts[2] if len(pparts) > 2 else (pparts[1] if len(pparts) > 1 else 0.0)
        tr.setTranslation(QVector3D(fx * scale, fy * scale, fz * scale))
        rx, ry, rz = parse_rotate(zone.data.get("rotate", "0,0,0"))
        if shape == "CYLINDER":
            if uses_legacy_cylinder_yaw:
                # Path/patrol/exclusion cylinders use the legacy yaw-only alignment that
                # matches the 2D editor and the expected in-game orientation.
                tol = 0.25
                yaw = float(ry)
                if abs(abs(float(rx)) - 90.0) <= tol and abs(abs(float(rz)) - 180.0) <= tol:
                    yaw = -yaw
                yaw_rad = math.radians(yaw)
                axis_dir = QVector3D(float(math.sin(yaw_rad)), 0.0, float(math.cos(yaw_rad)))
                if axis_dir.lengthSquared() <= 1e-9:
                    axis_dir = QVector3D(0.0, 0.0, 1.0)
                tr.setRotation(QQuaternion.rotationTo(QVector3D(0.0, 1.0, 0.0), axis_dir.normalized()))
            else:
                # Keep the full FL rotation for generic cylinders; only the legacy 180/180
                # normalization is handled inside the shared quaternion conversion helper.
                tr.setRotation(rotation_quaternion_from_fl(rx, ry, rz))
        else:
            tr.setRotation(rotation_quaternion_from_fl(rx, ry, rz))

        ent.addComponent(mesh)
        ent.addComponent(mat)
        ent.addComponent(tr)
        return ent, tr, [mesh, mat, tr, *always_on_top_refs, *depth_state_refs, *cull_state_refs]

    # ==================================================================
    #  Auswahl
    # ==================================================================
    def set_selected(self, obj):
        if not QT3D_AVAILABLE:
            return
        new_obj = obj if obj in self._obj_map else None
        previous_obj = self._selected_obj
        state = selection_state(
            has_object=new_obj is not None,
            is_same_selected=new_obj is not None and new_obj is self._selected_obj,
            move_mode=self._move_mode,
            flight_active=bool(getattr(self, "_flight", None) and self._flight.active),
        )
        if not state.get("selection_changed", True):
            return
        self._set_selection_halo_visible(previous_obj, False)
        self._selected_obj = new_obj
        if self._selected_native_detail_obj is not self._selected_obj:
            self._clear_selected_native_scene_data()
        if state.get("clear_locked_axis"):
            self._locked_axis = None
        if self._selected_obj is None:
            if state.get("clear_gizmo"):
                self._clear_axis_gizmo()
            self._schedule_native_scene_preview_refresh(30)
            return
        self._set_selection_halo_visible(self._selected_obj, True)
        _ent, tr = self._obj_map[self._selected_obj]
        if state.get("show_gizmo"):
            self._show_axis_gizmo(tr.translation())
        elif state.get("clear_gizmo"):
            self._clear_axis_gizmo()
        self._schedule_native_scene_preview_refresh(30)

    def _set_selection_halo_visible(self, obj, visible: bool) -> None:
        halo_ent = self._obj_selection_ent.get(obj)
        if halo_ent is None:
            return
        try:
            halo_ent.setEnabled(bool(visible))
        except Exception:
            pass

    def set_selected_native_scene_data(self, obj, scene_data) -> None:
        state = selected_native_detail_state(
            selected_obj=self._selected_obj,
            requested_obj=obj,
            has_scene_data=bool(scene_data is not None and getattr(scene_data, "geometries", ())),
        )
        if state["clear_detail"]:
            self._clear_selected_native_scene_data()
        if state["store_detail"]:
            self._selected_native_detail_obj = obj
            self._selected_native_scene_data = scene_data
            self._rebuild_selected_native_detail_entity()
        self._schedule_native_scene_preview_refresh(30)

    def get_selected_native_scene_data(self):
        return self._selected_native_scene_data

    def set_native_scene_resolver(self, resolver: Callable[[Any], Any | None] | None) -> None:
        self._native_scene_resolver = resolver
        self._schedule_native_scene_preview_refresh(30)

    def set_native_scene_prepared_payload_resolver(self, resolver: Callable[[Any], Any | None] | None) -> None:
        self._native_scene_prepared_payload_resolver = resolver
        self._schedule_native_scene_preview_refresh(30)

    def set_preview_mesh_resolver(self, resolver: Callable[[Any], Path | None] | None) -> None:
        self._preview_mesh_resolver = resolver
        self._schedule_native_scene_preview_refresh(30)

    def set_planet_texture_resolver(self, resolver: Callable[[Any], Path | None] | None) -> None:
        self._planet_texture_resolver = resolver

    def set_planet_cloud_texture_resolver(self, resolver: Callable[[Any], Path | None] | None) -> None:
        self._planet_cloud_texture_resolver = resolver

    def set_planet_ring_resolver(self, resolver: Callable[[Any], dict[str, object] | None] | None) -> None:
        self._planet_ring_resolver = resolver

    def set_native_preview_progress_callback(self, callback: Callable[[dict[str, object]], None] | None) -> None:
        self._native_preview_progress_callback = callback

    def set_native_preview_max_distance_fl(self, value: float) -> None:
        self._native_preview_max_distance_fl = float(value)
        self._schedule_native_scene_preview_refresh(30)

    def get_native_preview_max_distance_fl(self) -> float:
        return float(self._native_preview_max_distance_fl)

    def set_native_preview_high_quality_distance_fl(self, value: float) -> None:
        self._native_preview_high_quality_distance_fl = max(0.0, float(value))
        self._schedule_native_scene_preview_refresh(30)

    def get_native_preview_high_quality_distance_fl(self) -> float:
        return float(self._native_preview_high_quality_distance_fl)

    def set_native_preview_refresh_suppressed(self, suppressed: bool) -> None:
        if suppressed:
            self._native_preview_refresh_suppression_count += 1
            return
        self._native_preview_refresh_suppression_count = max(0, int(self._native_preview_refresh_suppression_count) - 1)
        if self._native_preview_refresh_suppression_count == 0 and self._native_preview_refresh_pending:
            self._native_preview_refresh_pending = False
            self._schedule_native_scene_preview_refresh(30)

    def _schedule_native_scene_preview_refresh_for_camera_motion(self, *, free_camera: bool = False) -> None:
        delay_ms = (
            int(self._native_preview_free_camera_idle_delay_ms)
            if free_camera
            else int(self._native_preview_camera_idle_delay_ms)
        )
        self._native_preview_motion_deadline_monotonic = max(
            float(self._native_preview_motion_deadline_monotonic),
            float(time.monotonic()) + (max(0, int(delay_ms)) / 1000.0),
        )
        self._schedule_native_scene_preview_refresh(delay_ms)

    def _schedule_native_scene_preview_refresh(self, delay_ms: int = 90) -> None:
        timer = self._native_preview_refresh_timer
        if not QT3D_AVAILABLE or timer is None:
            return
        if int(self._native_preview_refresh_suppression_count) > 0:
            self._native_preview_refresh_pending = True
            return
        batch_timer = self._native_preview_batch_timer
        if (batch_timer is not None and batch_timer.isActive()) or bool(self._native_preview_pending_builds):
            self._native_preview_refresh_after_batch = True
            return
        timer.start(max(30, int(delay_ms)))

    def _emit_native_preview_progress(self, *, active: bool) -> None:
        callback = self._native_preview_progress_callback
        if callback is None:
            return
        total = max(0, int(self._native_preview_progress_total))
        done = max(0, min(total, int(self._native_preview_progress_done)))
        active_3d_count, placeholder_count = self._native_preview_status_counts()
        self._native_preview_last_reported_counts = (active_3d_count, placeholder_count)
        try:
            callback(
                {
                    "active": bool(active),
                    "total": total,
                    "done": done,
                    "pending": max(0, total - done),
                    "active_3d_count": active_3d_count,
                    "placeholder_count": placeholder_count,
                }
            )
        except Exception:
            pass

    def _native_preview_status_counts(self) -> tuple[int, int]:
        renderable_total = 0
        for obj in self._obj_map.keys():
            archetype = str(getattr(obj, "data", {}).get("archetype", "") or "").strip()
            if archetype:
                renderable_total += 1
        active_3d_count = len(self._native_preview_entity_by_obj)
        if self._selected_native_detail_entity is not None and self._selected_native_detail_obj is not None:
            if self._selected_native_detail_obj not in self._native_preview_entity_by_obj:
                active_3d_count += 1
        placeholder_count = max(0, int(renderable_total) - int(active_3d_count))
        return int(active_3d_count), int(placeholder_count)

    def get_native_preview_status_counts(self) -> tuple[int, int]:
        return self._native_preview_status_counts()

    def _finish_native_preview_progress(self) -> None:
        timer = self._native_preview_batch_timer
        if timer is not None:
            timer.stop()
        self._native_preview_pending_builds = []
        self._native_preview_progress_done = self._native_preview_progress_total
        self._emit_native_preview_progress(active=False)
        if self._native_preview_refresh_after_batch:
            self._native_preview_refresh_after_batch = False
            self._schedule_native_scene_preview_refresh(30)

    def _discard_native_preview_pending_builds(self) -> None:
        self._native_preview_build_generation = int(getattr(self, "_native_preview_build_generation", 0) or 0) + 1
        for payload in self._native_preview_pending_builds:
            detail_root = payload.get("detail_root")
            if detail_root is None:
                continue
            try:
                detail_root.setParent(None)
            except Exception:
                pass
        self._native_preview_pending_builds = []

    def _create_native_preview_root(
        self,
        *,
        parent_ent: Any,
        transform_state: dict[str, object],
    ) -> tuple[Any, list[Any]]:
        detail_root = QEntity3D(parent_ent)
        refs: list[Any] = []
        detail_root_tr = QTransform3D(detail_root)
        detail_root_tr.setScale(float(transform_state["scale"]))
        extra_rx, extra_ry, extra_rz = tuple(transform_state["rotate_euler_deg"])
        if abs(extra_rx) > 1e-6 or abs(extra_ry) > 1e-6 or abs(extra_rz) > 1e-6:
            detail_root_tr.setRotation(
                QQuaternion.fromEulerAngles(float(extra_rx), float(extra_ry), float(extra_rz))
            )
        detail_root.addComponent(detail_root_tr)
        refs.append(detail_root_tr)
        return detail_root, refs

    def _finalize_native_preview_build(
        self,
        *,
        obj: Any,
        cache_key: Any,
        detail_root: Any,
        refs: list[Any],
    ) -> None:
        self._native_preview_entity_by_obj[obj] = detail_root
        self._native_preview_refs_by_obj[obj] = refs
        self._native_preview_cache_key_by_obj[obj] = cache_key
        if obj in self._obj_sphere_ent:
            try:
                self._obj_sphere_ent[obj].setEnabled(False)
            except Exception:
                pass

    def _build_native_preview_geometry_chunk(self, payload: dict[str, object]) -> bool:
        obj = payload.get("obj")
        preview_data = payload.get("scene_data")
        detail_root = payload.get("detail_root")
        refs = payload.get("refs")
        geometry_index = int(payload.get("geometry_index", 0) or 0)
        if (
            obj is None
            or preview_data is None
            or detail_root is None
            or not isinstance(refs, list)
        ):
            return True

        geometries = tuple(getattr(preview_data, "geometries", ()) or ())
        next_index = min(
            len(geometries),
            geometry_index + max(1, int(self._native_preview_geometry_batch_size)),
        )
        for geometry in geometries[geometry_index:next_index]:
            part_ent = QEntity3D(detail_root)
            renderer = build_native_geometry_renderer(geometry, owner=part_ent)
            transform = QTransform3D(part_ent)
            material = build_native_geometry_material(
                owner=part_ent,
                native_geometry=geometry,
                texture_refs=refs,
                texture_resolver=lambda current_geometry, data=preview_data: texture_path_for_geometry(data, current_geometry),
                allow_textures=False,
            )
            apply_native_geometry_material(material, geometry)
            part_ent.addComponent(renderer)
            part_ent.addComponent(transform)
            part_ent.addComponent(material)
            refs.extend([part_ent, renderer, transform, material])
            wireframe_ent = build_native_wireframe_entity(root=detail_root, native_geometry=geometry)
            try:
                wireframe_ent.setEnabled(bool(self._native_wireframe_visible))
            except Exception:
                pass
            refs.append(wireframe_ent)

        payload["geometry_index"] = next_index
        return next_index >= len(geometries)

    def _process_native_preview_build_batch(self) -> None:
        if not QT3D_AVAILABLE:
            self._finish_native_preview_progress()
            return
        batch_start = float(time.perf_counter())
        batch_time_budget_s = max(
            0.0,
            float(getattr(self, "_native_preview_batch_time_budget_ms", 7) or 0) / 1000.0,
        )
        processed = 0
        finalized = 0
        while self._native_preview_pending_builds and processed < max(1, int(self._native_preview_batch_size)):
            payload = self._native_preview_pending_builds.pop(0)
            payload_generation = int(payload.get("generation", 0) or 0)
            current_generation = int(getattr(self, "_native_preview_build_generation", 0) or 0)
            if payload_generation != current_generation:
                detail_root = payload.get("detail_root")
                if detail_root is not None:
                    try:
                        detail_root.setParent(None)
                    except Exception:
                        pass
                processed += 1
                continue
            obj = payload.get("obj")
            scene_data = payload.get("scene_data")
            obj_ent = payload.get("obj_ent")
            cache_key = payload.get("cache_key")
            transform_state = payload.get("transform_state")
            if obj is None or scene_data is None or obj_ent is None or not isinstance(transform_state, dict):
                self._native_preview_progress_done += 1
                processed += 1
                continue
            current_key = self._native_preview_cache_key_by_obj.get(obj)
            if obj in self._native_preview_entity_by_obj and current_key == cache_key:
                if obj in self._obj_sphere_ent:
                    try:
                        self._obj_sphere_ent[obj].setEnabled(False)
                    except Exception:
                        pass
                self._native_preview_progress_done += 1
                processed += 1
                continue
            try:
                if isinstance(scene_data, Path):
                    detail_root, refs = self._build_native_preview_entity(
                        parent_ent=obj_ent,
                        preview_data=scene_data,
                        cache_key=cache_key,
                        transform_state=transform_state,
                    )
                    self._finalize_native_preview_build(
                        obj=obj,
                        cache_key=cache_key,
                        detail_root=detail_root,
                        refs=refs,
                    )
                    self._native_preview_recent_builds_by_key[cache_key] = float(time.monotonic())
                    finalized += 1
                else:
                    cached = self._native_preview_entity_cache.pop(cache_key, None)
                    if cached is not None:
                        detail_root, refs = cached
                        try:
                            detail_root.setParent(obj_ent)
                        except Exception:
                            pass
                        self._finalize_native_preview_build(
                            obj=obj,
                            cache_key=cache_key,
                            detail_root=detail_root,
                            refs=list(refs),
                        )
                        self._native_preview_recent_builds_by_key[cache_key] = float(time.monotonic())
                        finalized += 1
                    else:
                        detail_root = payload.get("detail_root")
                        refs = payload.get("refs")
                        if detail_root is None or not isinstance(refs, list):
                            detail_root, refs = self._create_native_preview_root(
                                parent_ent=obj_ent,
                                transform_state=transform_state,
                            )
                            payload["detail_root"] = detail_root
                            payload["refs"] = refs
                            payload["geometry_index"] = 0
                        build_complete = self._build_native_preview_geometry_chunk(payload)
                        if build_complete:
                            if int(payload.get("generation", 0) or 0) != int(getattr(self, "_native_preview_build_generation", 0) or 0):
                                try:
                                    detail_root.setParent(None)
                                except Exception:
                                    pass
                                processed += 1
                                continue
                            self._finalize_native_preview_build(
                                obj=obj,
                                cache_key=cache_key,
                                detail_root=detail_root,
                                refs=refs,
                            )
                            self._native_preview_recent_builds_by_key[cache_key] = float(time.monotonic())
                            finalized += 1
                        else:
                            self._native_preview_pending_builds.insert(0, payload)
                            processed += 1
                            continue
            except Exception:
                detail_root = payload.get("detail_root")
                if detail_root is not None:
                    try:
                        detail_root.setParent(None)
                    except Exception:
                        pass
                if obj in self._obj_sphere_ent:
                    try:
                        self._obj_sphere_ent[obj].setEnabled(True)
                    except Exception:
                        pass
            self._native_preview_progress_done += 1
            processed += 1
            if finalized >= max(1, int(getattr(self, "_native_preview_finalize_budget_per_tick", 1) or 1)):
                break
            if batch_time_budget_s > 0.0 and (float(time.perf_counter()) - batch_start) >= batch_time_budget_s:
                break

        self._emit_native_preview_progress(active=bool(self._native_preview_pending_builds))
        if self._native_preview_pending_builds:
            timer = self._native_preview_batch_timer
            if timer is not None:
                timer.start()
            return
        self._finish_native_preview_progress()

    def _camera_reference_position(self) -> QVector3D:
        target = self._cam_target
        try:
            cam = getattr(self, "_camera", None)
            if cam is not None:
                cam_pos = cam.position()
                return QVector3D(float(cam_pos.x()), float(cam_pos.y()), float(cam_pos.z()))
        except Exception:
            pass
        return QVector3D(float(target.x()), float(target.y()), float(target.z()))

    def _distance_fl_to_object(self, obj: Any) -> float:
        target = self._camera_reference_position()
        entry = self._obj_map.get(obj)
        if entry is None:
            return 1e18
        _ent, tr = entry
        try:
            pos = tr.translation()
            distance_scene = math.sqrt(
                float(pos.x() - target.x()) ** 2
                + float(pos.y() - target.y()) ** 2
                + float(pos.z() - target.z()) ** 2
            )
        except Exception:
            return 1e18
        scene_scale = max(1e-6, float(getattr(self, "_scene_scale", 1.0) or 1.0))
        return float(distance_scene) / scene_scale

    def _camera_forward_vector(self) -> QVector3D:
        try:
            cam = getattr(self, "_camera", None)
            if cam is not None:
                cam_pos = cam.position()
                view_center = cam.viewCenter()
                forward = QVector3D(
                    float(view_center.x()) - float(cam_pos.x()),
                    float(view_center.y()) - float(cam_pos.y()),
                    float(view_center.z()) - float(cam_pos.z()),
                )
                if forward.lengthSquared() > 1e-9:
                    return forward.normalized()
        except Exception:
            pass
        target = self._cam_target
        try:
            return QVector3D(float(target.x()), float(target.y()), float(target.z())).normalized()
        except Exception:
            return QVector3D(0.0, 0.0, 1.0)

    def _is_object_within_native_preview_view(self, obj: Any, *, active: bool = False) -> bool:
        entry = self._obj_map.get(obj)
        if entry is None:
            return False
        cam_pos = self._camera_reference_position()
        forward = self._camera_forward_vector()
        try:
            pos = entry[1].translation()
            to_obj = QVector3D(
                float(pos.x()) - float(cam_pos.x()),
                float(pos.y()) - float(cam_pos.y()),
                float(pos.z()) - float(cam_pos.z()),
            )
        except Exception:
            return False
        if to_obj.lengthSquared() <= 1e-9:
            return True
        try:
            to_obj = to_obj.normalized()
            dot = (
                float(forward.x()) * float(to_obj.x())
                + float(forward.y()) * float(to_obj.y())
                + float(forward.z()) * float(to_obj.z())
            )
        except Exception:
            return True
        half_angle_deg = (
            float(self._native_preview_active_view_half_angle_deg)
            if active
            else float(self._native_preview_view_half_angle_deg)
        )
        min_dot = math.cos(math.radians(max(1.0, min(89.0, half_angle_deg))))
        return dot >= min_dot

    def _lod_mode_for_distance_fl(self, distance_fl: float) -> int:
        dist = max(0.0, float(distance_fl))
        coarse_distance = 8000.0
        coarsest_distance = 20000.0
        if dist >= coarsest_distance:
            return 2
        if dist >= coarse_distance:
            return 1
        return 0

    def _scene_data_for_preview_lod(self, scene_data: Any, obj: Any) -> Any:
        if scene_data is None or not getattr(scene_data, "all_geometries", ()):
            return scene_data
        distance_fl = self._distance_fl_to_object(obj)
        high_quality_distance_fl = max(0.0, float(getattr(self, "_native_preview_high_quality_distance_fl", 0.0) or 0.0))
        if high_quality_distance_fl > 0.0 and distance_fl <= high_quality_distance_fl:
            return scene_data
        if bool(getattr(self, "_native_preview_force_coarsest_lod", False)):
            lod_mode = 2
        else:
            lod_mode = self._lod_mode_for_distance_fl(distance_fl)
        if lod_mode <= 0:
            return scene_data
        cache_key = (scene_data, int(lod_mode))
        cached = self._native_preview_lod_scene_cache.get(cache_key)
        if cached is not None:
            return cached
        reduced = scene_data_with_lod_mode(scene_data, lod_mode)
        self._native_preview_lod_scene_cache[cache_key] = reduced
        return reduced

    def _native_preview_render_tier(self, obj: Any, *, prepared_geometry_count: int = 0) -> int:
        distance_fl = self._distance_fl_to_object(obj)
        high_quality_distance_fl = max(
            0.0,
            float(getattr(self, "_native_preview_high_quality_distance_fl", 0.0) or 0.0),
        )
        if high_quality_distance_fl > 0.0 and distance_fl <= high_quality_distance_fl:
            return 2
        geometry_count = max(0, int(prepared_geometry_count))
        if geometry_count <= max(1, int(getattr(self, "_native_preview_cheap_geometry_limit", 10) or 10)):
            return 1
        return 0

    def _native_preview_candidate_objects(self) -> tuple[Any, ...]:
        if not self._obj_map:
            return ()
        target = self._camera_reference_position()
        now_monotonic = float(time.monotonic())
        visibility_stable_seconds = max(
            0.0,
            float(getattr(self, "_native_preview_visibility_stable_ms", 0) or 0) / 1000.0,
        )
        scene_scale = max(1e-6, float(getattr(self, "_scene_scale", 1.0) or 1.0))
        max_distance_fl = float(self._native_preview_max_distance_fl)
        max_distance_scene = max(0.0, max_distance_fl) * scene_scale
        active_max_distance_scene = max_distance_scene * 1.12
        ranked: list[tuple[float, Any]] = []
        visible_now: set[Any] = set()
        for obj, (_ent, tr) in self._obj_map.items():
            if obj is self._selected_obj:
                continue
            archetype = str(getattr(obj, "data", {}).get("archetype", "") or "")
            nickname = str(getattr(obj, "nickname", "") or "")
            if is_trade_lane_object(nickname=nickname, archetype=archetype):
                continue
            try:
                pos = tr.translation()
                dist_sq = (
                    float(pos.x() - target.x()) ** 2
                    + float(pos.y() - target.y()) ** 2
                    + float(pos.z() - target.z()) ** 2
                )
            except Exception:
                dist_sq = 1e18
            archetype = str(getattr(obj, "data", {}).get("archetype", "") or "").strip()
            if not archetype:
                continue
            distance_scene = math.sqrt(dist_sq) if dist_sq < 1e17 else 1e18
            if max_distance_fl >= 0.0:
                if max_distance_scene <= 0.0:
                    continue
                cutoff = active_max_distance_scene if obj in self._native_preview_entity_by_obj else max_distance_scene
                if distance_scene > cutoff:
                    continue
            if not self._is_object_within_native_preview_view(
                obj,
                active=obj in self._native_preview_entity_by_obj,
            ):
                continue
            visible_now.add(obj)
            if obj in self._native_preview_entity_by_obj:
                self._native_preview_visible_since_monotonic[obj] = now_monotonic
            else:
                first_seen = self._native_preview_visible_since_monotonic.get(obj)
                if first_seen is None:
                    self._native_preview_visible_since_monotonic[obj] = now_monotonic
                    continue
                if (now_monotonic - float(first_seen)) < visibility_stable_seconds:
                    continue
            ranked.append((dist_sq, obj))
        for obj in tuple(self._native_preview_visible_since_monotonic.keys()):
            if obj not in visible_now and obj not in self._native_preview_entity_by_obj:
                self._native_preview_visible_since_monotonic.pop(obj, None)
        ranked.sort(key=lambda item: item[0])
        ordered = tuple(obj for _dist_sq, obj in ranked)
        return tuple(ordered)

    def _sparsify_tradelane_preview_candidates(self, candidates: tuple[Any, ...]) -> tuple[Any, ...]:
        if not candidates:
            return ()
        near_keep = max(0, int(getattr(self, "_native_preview_tradelane_near_keep", 10) or 0))
        stride = max(1, int(getattr(self, "_native_preview_tradelane_stride", 4) or 1))
        tradelane_seen = 0
        filtered: list[Any] = []
        for obj in candidates:
            archetype = str(getattr(obj, "data", {}).get("archetype", "") or "")
            nickname = str(getattr(obj, "nickname", "") or "")
            if not is_trade_lane_object(nickname=nickname, archetype=archetype):
                filtered.append(obj)
                continue
            tradelane_seen += 1
            if tradelane_seen <= near_keep or ((tradelane_seen - near_keep - 1) % stride) == 0:
                filtered.append(obj)
        return tuple(filtered)

    def _clear_native_preview_entity_for_object(self, obj: Any) -> None:
        if obj in self._obj_sphere_ent:
            try:
                self._obj_sphere_ent[obj].setEnabled(True)
            except Exception:
                pass
        ent = self._native_preview_entity_by_obj.pop(obj, None)
        refs = self._native_preview_refs_by_obj.pop(obj, [])
        cache_key = self._native_preview_cache_key_by_obj.pop(obj, None)
        if ent is None:
            return
        try:
            if cache_key is not None:
                self._native_preview_entity_cache[cache_key] = (ent, list(refs))
                self._prune_native_preview_entity_cache()
            ent.setParent(None)
        except Exception:
            pass

    def _clear_all_native_preview_entities(self) -> None:
        for obj in tuple(self._native_preview_entity_by_obj.keys()):
            self._clear_native_preview_entity_for_object(obj)

    def _prune_native_preview_entity_cache(self) -> None:
        limit = max(0, int(getattr(self, "_native_preview_entity_cache_limit", 48) or 0))
        if limit <= 0:
            self._native_preview_entity_cache.clear()
            return
        while len(self._native_preview_entity_cache) > limit:
            try:
                oldest_key = next(iter(self._native_preview_entity_cache.keys()))
            except StopIteration:
                break
            ent, _refs = self._native_preview_entity_cache.pop(oldest_key, (None, None))
            if ent is not None:
                try:
                    ent.setParent(None)
                except Exception:
                    pass

    def _prepare_for_large_camera_jump(self) -> None:
        refresh_timer = self._native_preview_refresh_timer
        if refresh_timer is not None:
            refresh_timer.stop()
        batch_timer = self._native_preview_batch_timer
        if batch_timer is not None:
            batch_timer.stop()
        self._discard_native_preview_pending_builds()
        self._native_preview_progress_total = 0
        self._native_preview_progress_done = 0
        self._clear_all_native_preview_entities()
        self._native_preview_entity_cache.clear()
        self._native_preview_lod_scene_cache.clear()
        self._emit_native_preview_progress(active=False)

    def _build_native_preview_entity(
        self,
        *,
        parent_ent: Any,
        preview_data: Any,
        cache_key: Any,
        transform_state: dict[str, object],
    ) -> tuple[Any, list[Any]]:
        cached = self._native_preview_entity_cache.pop(cache_key, None)
        if cached is not None:
            detail_root, refs = cached
            try:
                detail_root.setParent(parent_ent)
            except Exception:
                pass
            return detail_root, list(refs)

        detail_root, refs = self._create_native_preview_root(
            parent_ent=parent_ent,
            transform_state=transform_state,
        )
        if isinstance(preview_data, Path):
            mesh_ent = QEntity3D(detail_root)
            mesh = QMesh3D(mesh_ent)
            mesh.setSource(QUrl.fromLocalFile(str(preview_data)))
            material = self._make_phong(QColor(176, 196, 214), ambient_lighter=128)
            transform = QTransform3D(mesh_ent)
            mesh_ent.addComponent(mesh)
            mesh_ent.addComponent(material)
            mesh_ent.addComponent(transform)
            refs.extend([mesh_ent, mesh, material, transform])
            return detail_root, refs
        for geometry in getattr(preview_data, "geometries", ()):
            part_ent = QEntity3D(detail_root)
            renderer = build_native_geometry_renderer(geometry, owner=part_ent)
            transform = QTransform3D(part_ent)
            material = build_native_geometry_material(
                owner=part_ent,
                native_geometry=geometry,
                texture_refs=refs,
                texture_resolver=lambda current_geometry, data=preview_data: texture_path_for_geometry(data, current_geometry),
                allow_textures=False,
            )
            apply_native_geometry_material(material, geometry)
            part_ent.addComponent(renderer)
            part_ent.addComponent(transform)
            part_ent.addComponent(material)
            refs.extend([part_ent, renderer, transform, material])
            wireframe_ent = build_native_wireframe_entity(root=detail_root, native_geometry=geometry)
            try:
                wireframe_ent.setEnabled(bool(self._native_wireframe_visible))
            except Exception:
                pass
            refs.append(wireframe_ent)
        return detail_root, refs

    def _set_wireframe_visible_in_refs(self, refs: list[Any], visible: bool) -> None:
        for ref in refs:
            try:
                if callable(getattr(ref, "objectName", None)) and str(ref.objectName()) == "flatlas_native_wireframe":
                    ref.setEnabled(bool(visible))
            except Exception:
                pass

    def set_native_wireframe_visible(self, visible: bool) -> None:
        self._native_wireframe_visible = bool(visible)
        for refs in self._native_preview_refs_by_obj.values():
            if isinstance(refs, list):
                self._set_wireframe_visible_in_refs(refs, self._native_wireframe_visible)
        if isinstance(self._selected_native_detail_refs, list):
            self._set_wireframe_visible_in_refs(self._selected_native_detail_refs, self._native_wireframe_visible)
        for _ent, refs in self._native_preview_entity_cache.values():
            if isinstance(refs, list):
                self._set_wireframe_visible_in_refs(refs, self._native_wireframe_visible)
        for _ent, refs in self._native_detail_entity_cache.values():
            if isinstance(refs, list):
                self._set_wireframe_visible_in_refs(refs, self._native_wireframe_visible)

    def get_native_wireframe_visible(self) -> bool:
        return bool(self._native_wireframe_visible)

    def refresh_native_scene_previews(self) -> None:
        if not QT3D_AVAILABLE:
            return
        motion_deadline = float(getattr(self, "_native_preview_motion_deadline_monotonic", 0.0) or 0.0)
        now_monotonic = float(time.monotonic())
        if motion_deadline > now_monotonic:
            timer = self._native_preview_refresh_timer
            if timer is not None:
                timer.start(max(30, int(math.ceil((motion_deadline - now_monotonic) * 1000.0))))
            return
        self._native_preview_motion_deadline_monotonic = 0.0
        batch_timer = self._native_preview_batch_timer
        if batch_timer is not None:
            batch_timer.stop()
        self._discard_native_preview_pending_builds()
        resolver = self._native_scene_resolver
        if resolver is None:
            for obj in list(self._native_preview_entity_by_obj.keys()):
                self._clear_native_preview_entity_for_object(obj)
            self._native_preview_progress_total = 0
            self._native_preview_progress_done = 0
            self._emit_native_preview_progress(active=False)
            return

        mesh_resolver = self._preview_mesh_resolver
        prepared_payload_resolver = self._native_scene_prepared_payload_resolver
        desired: dict[Any, Any] = {}
        desired_meta: dict[Any, dict[str, object]] = {}
        scheduled_cache_keys: set[Any] = set()
        deferred_duplicate_builds = False
        deferred_delay_ms: int | None = None
        cooldown_ms = max(
            0,
            int(getattr(self, "_native_preview_duplicate_cache_key_cooldown_ms", 220) or 220),
        )
        now_monotonic = float(time.monotonic())
        if self._native_preview_recent_builds_by_key:
            prune_before = now_monotonic - (max(1000, cooldown_ms) / 1000.0) * 6.0
            stale_keys = [
                key
                for key, built_at in self._native_preview_recent_builds_by_key.items()
                if float(built_at) < prune_before
            ]
            for stale_key in stale_keys:
                self._native_preview_recent_builds_by_key.pop(stale_key, None)
        candidate_objects = self._native_preview_candidate_objects()
        native_slots_remaining = max(1, int(getattr(self, "_native_preview_max_active_count", 18) or 18))
        for priority_index, obj in enumerate(candidate_objects):
            preview_data = None
            prepared_payload = None
            if prepared_payload_resolver is not None:
                try:
                    prepared_payload = prepared_payload_resolver(obj)
                except Exception:
                    prepared_payload = None
            scene_data = getattr(prepared_payload, "scene_data", None)
            if scene_data is None:
                try:
                    scene_data = resolver(obj)
                except Exception:
                    scene_data = None
            if scene_data is not None and getattr(scene_data, "geometries", ()):
                preview_data = self._scene_data_for_preview_lod(scene_data, obj)
            elif mesh_resolver is not None:
                try:
                    preview_mesh = mesh_resolver(obj)
                except Exception:
                    preview_mesh = None
                if isinstance(preview_mesh, Path):
                    preview_data = preview_mesh
            if preview_data is None:
                existing_cache_key = self._native_preview_cache_key_by_obj.get(obj)
                if (
                    isinstance(existing_cache_key, tuple)
                    and existing_cache_key
                    and (isinstance(existing_cache_key[0], Path) or getattr(existing_cache_key[0], "geometries", ()))
                ):
                    preview_data = existing_cache_key[0]
            if preview_data is not None:
                prepared_geometry_count = int(
                    getattr(prepared_payload, "geometry_count", len(getattr(scene_data, "geometries", ()) or ())) or 0
                )
                render_tier = self._native_preview_render_tier(
                    obj,
                    prepared_geometry_count=prepared_geometry_count,
                )
                if render_tier <= 0:
                    continue
                if obj not in self._native_preview_entity_by_obj and native_slots_remaining <= 0:
                    continue
                desired[obj] = preview_data
                desired_meta[obj] = {
                    "priority_index": int(priority_index),
                    "geometry_count": prepared_geometry_count,
                    "render_tier": int(render_tier),
                }
                if obj not in self._native_preview_entity_by_obj:
                    native_slots_remaining -= 1

        selected_obj = self._selected_obj
        selected_has_detail = (
            selected_obj is not None
            and self._selected_native_detail_obj is selected_obj
            and self._selected_native_scene_data is not None
            and getattr(self._selected_native_scene_data, "geometries", ())
        )
        selected_is_trade_lane = bool(
            selected_obj is not None
            and is_trade_lane_object(
                nickname=str(getattr(selected_obj, "nickname", "") or ""),
                archetype=str(getattr(selected_obj, "data", {}).get("archetype", "") or ""),
            )
        )
        if selected_obj is not None and not selected_has_detail and not selected_is_trade_lane:
            selected_scene_data = None
            try:
                selected_scene_data = resolver(selected_obj)
            except Exception:
                selected_scene_data = None
            if selected_scene_data is None and mesh_resolver is not None:
                try:
                    selected_scene_data = mesh_resolver(selected_obj)
                except Exception:
                    selected_scene_data = None
            if selected_scene_data is None:
                selected_cache_key = self._native_preview_cache_key_by_obj.get(selected_obj)
                if (
                    isinstance(selected_cache_key, tuple)
                    and selected_cache_key
                    and (isinstance(selected_cache_key[0], Path) or getattr(selected_cache_key[0], "geometries", ()))
                ):
                    selected_scene_data = selected_cache_key[0]
            if selected_scene_data is not None and (
                isinstance(selected_scene_data, Path) or getattr(selected_scene_data, "geometries", ())
            ):
                desired[selected_obj] = selected_scene_data
                desired_meta[selected_obj] = {
                    "priority_index": -1,
                    "geometry_count": int(len(getattr(selected_scene_data, "geometries", ()) or ()) or 0),
                    "render_tier": 2,
                }

        for obj in tuple(self._native_preview_entity_by_obj.keys()):
            if obj not in desired:
                self._clear_native_preview_entity_for_object(obj)

        pending_builds: list[dict[str, object]] = []
        matched_count = 0
        for obj, scene_data in desired.items():
            entry = self._obj_map.get(obj)
            if entry is None:
                self._clear_native_preview_entity_for_object(obj)
                continue
            obj_ent, _obj_tr = entry
            transform_state = native_detail_transform_state(
                nickname=str(getattr(obj, "nickname", "") or ""),
                archetype=str(getattr(obj, "data", {}).get("archetype", "") or ""),
                bounds=getattr(scene_data, "bounds", None),
                label_y_offset=float(self._obj_label_yoff.get(obj, 3.8)),
                scene_scale=float(getattr(self, "_scene_scale", 1.0) or 1.0),
                cmp_up_correction_euler_deg=tuple(
                    getattr(scene_data, "cmp_up_correction_euler_deg", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)
                ),
            )
            cache_key = (
                scene_data,
                native_detail_transform_cache_key(
                    scale=float(transform_state["scale"]),
                    rotate_euler_deg=tuple(transform_state["rotate_euler_deg"]),
                ),
            )
            current_key = self._native_preview_cache_key_by_obj.get(obj)
            if obj in self._native_preview_entity_by_obj and current_key == cache_key:
                if obj in self._obj_sphere_ent:
                    try:
                        self._obj_sphere_ent[obj].setEnabled(False)
                    except Exception:
                        pass
                matched_count += 1
                continue
            if obj is not selected_obj:
                if cache_key in scheduled_cache_keys:
                    deferred_duplicate_builds = True
                    deferred_delay_ms = 30 if deferred_delay_ms is None else min(int(deferred_delay_ms), 30)
                    continue
                recent_build_at = self._native_preview_recent_builds_by_key.get(cache_key)
                if recent_build_at is not None and cooldown_ms > 0:
                    remaining_ms = int(
                        max(
                            0.0,
                            (
                                float(recent_build_at)
                                + (float(cooldown_ms) / 1000.0)
                                - now_monotonic
                            )
                            * 1000.0,
                        )
                    )
                    if remaining_ms > 0:
                        deferred_duplicate_builds = True
                        deferred_delay_ms = remaining_ms if deferred_delay_ms is None else min(int(deferred_delay_ms), remaining_ms)
                        continue
            cached_entity_available = cache_key in self._native_preview_entity_cache
            self._clear_native_preview_entity_for_object(obj)
            scheduled_cache_keys.add(cache_key)
            pending_builds.append(
                {
                    "obj": obj,
                    "scene_data": scene_data,
                    "obj_ent": obj_ent,
                    "cache_key": cache_key,
                    "transform_state": transform_state,
                    "generation": int(getattr(self, "_native_preview_build_generation", 0) or 0),
                    "priority_index": int(desired_meta.get(obj, {}).get("priority_index", 0) or 0),
                    "prepared_geometry_count": int(desired_meta.get(obj, {}).get("geometry_count", 0) or 0),
                    "cached_entity_available": bool(cached_entity_available),
                }
            )
        pending_builds.sort(
            key=lambda payload: (
                0 if payload.get("obj") is selected_obj else 1,
                -int(desired_meta.get(payload.get("obj"), {}).get("render_tier", 0) or 0),
                0 if bool(payload.get("cached_entity_available")) else 1,
                int(payload.get("prepared_geometry_count", 0) or 0),
                int(payload.get("priority_index", 0) or 0),
            )
        )
        self._native_preview_progress_total = len(desired)
        self._native_preview_progress_done = matched_count
        self._native_preview_pending_builds = pending_builds
        if deferred_duplicate_builds:
            self._native_preview_refresh_after_batch = True
        if not pending_builds:
            self._emit_native_preview_progress(active=False)
            if deferred_duplicate_builds:
                self._schedule_native_scene_preview_refresh(max(30, int(deferred_delay_ms or 30)))
            return
        self._emit_native_preview_progress(active=True)
        if batch_timer is not None:
            batch_timer.start()

    def get_selected_native_detail_debug_state(self) -> dict[str, object]:
        marker_visible = None
        if self._selected_native_detail_obj in self._obj_sphere_ent:
            try:
                marker_visible = bool(self._obj_sphere_ent[self._selected_native_detail_obj].isEnabled())
            except Exception:
                marker_visible = None
        return {
            "selected_object_nickname": getattr(self._selected_obj, "nickname", None),
            "detail_object_nickname": getattr(self._selected_native_detail_obj, "nickname", None),
            "has_scene_data": bool(
                self._selected_native_scene_data is not None
                and getattr(self._selected_native_scene_data, "geometries", ())
            ),
            "geometry_count": len(getattr(self._selected_native_scene_data, "geometries", ()) or ()),
            "geometry_confidences": tuple(
                str(getattr(geometry, "confidence", "") or "")
                for geometry in getattr(self._selected_native_scene_data, "geometries", ()) or ()
            ),
            "has_detail_entity": self._selected_native_detail_entity is not None,
            "selected_detail_marker_visible": marker_visible,
            "detail_cache_size": len(self._native_detail_entity_cache),
            "detail_cache_keys": tuple(self._native_detail_entity_cache.keys()),
            "selected_cache_key": self._selected_native_detail_cache_key,
            "cmp_orientation_debug_rows": tuple(
                getattr(self._selected_native_scene_data, "cmp_orientation_debug_rows", ()) or ()
            ),
        }

    def _clear_selected_native_scene_data(self) -> None:
        self._clear_selected_native_detail_entity()
        self._selected_native_detail_obj = None
        self._selected_native_scene_data = None
        self._schedule_native_scene_preview_refresh(30)

    def _clear_selected_native_detail_entity(self) -> None:
        if self._selected_native_detail_obj in self._obj_sphere_ent:
            try:
                self._obj_sphere_ent[self._selected_native_detail_obj].setEnabled(True)
            except Exception:
                pass
        if self._selected_native_detail_entity is not None:
            try:
                if self._selected_native_detail_cache_key is not None:
                    self._native_detail_entity_cache[self._selected_native_detail_cache_key] = (
                        self._selected_native_detail_entity,
                        list(self._selected_native_detail_refs),
                    )
                self._selected_native_detail_entity.setParent(None)
            except Exception:
                pass
        self._selected_native_detail_entity = None
        self._selected_native_detail_refs.clear()
        self._selected_native_detail_cache_key = None

    def _rebuild_selected_native_detail_entity(self) -> None:
        if self._selected_native_detail_obj is None or self._selected_native_scene_data is None:
            self._clear_selected_native_detail_entity()
            return
        entry = self._obj_map.get(self._selected_native_detail_obj)
        if entry is None:
            self._clear_selected_native_detail_entity()
            return
        scene_data = self._selected_native_scene_data
        detail_obj = self._selected_native_detail_obj
        transform_state = native_detail_transform_state(
            nickname=str(getattr(detail_obj, "nickname", "") or ""),
            archetype=str(getattr(detail_obj, "data", {}).get("archetype", "") or ""),
            bounds=getattr(scene_data, "bounds", None),
            label_y_offset=float(self._obj_label_yoff.get(detail_obj, 3.8)),
            scene_scale=float(getattr(self, "_scene_scale", 1.0) or 1.0),
            cmp_up_correction_euler_deg=tuple(
                getattr(scene_data, "cmp_up_correction_euler_deg", (0.0, 0.0, 0.0)) or (0.0, 0.0, 0.0)
            ),
        )
        transform_cache_key = native_detail_transform_cache_key(
            scale=float(transform_state["scale"]),
            rotate_euler_deg=tuple(transform_state["rotate_euler_deg"]),
        )
        cache_key = (scene_data, transform_cache_key)
        if (
            self._selected_native_detail_entity is not None
            and self._selected_native_detail_obj in self._obj_map
            and self._selected_native_detail_cache_key == cache_key
        ):
            sphere_ent = self._obj_sphere_ent.get(self._selected_native_detail_obj)
            if sphere_ent is not None:
                try:
                    sphere_ent.setEnabled(False)
                except Exception:
                    pass
            return
        self._clear_selected_native_detail_entity()
        obj_ent, _obj_tr = entry
        sphere_ent = self._obj_sphere_ent.get(self._selected_native_detail_obj)
        if sphere_ent is not None:
            try:
                sphere_ent.setEnabled(False)
            except Exception:
                pass
        cached = self._native_detail_entity_cache.pop(cache_key, None)
        if cached is not None:
            detail_root, refs = cached
            try:
                detail_root.setParent(obj_ent)
            except Exception:
                pass
        else:
            detail_root, refs = self._build_native_preview_entity(
                parent_ent=obj_ent,
                scene_data=scene_data,
                cache_key=cache_key,
                transform_state=transform_state,
            )
        self._selected_native_detail_entity = detail_root
        self._selected_native_detail_refs = refs
        self._selected_native_detail_cache_key = cache_key

    def set_label_visibility(self, enabled: bool):
        state = label_visibility_state(enabled=enabled)
        self._labels_visible = bool(state["labels_visible"])
        for ent in self._obj_label_ent.values():
            try:
                ent.setEnabled(bool(state["entity_enabled"]))
            except Exception:
                pass

    def set_item_visibility(self, item, visible: bool):
        """Einzelnes 2D-Item (Objekt oder Zone) in der 3D-Ansicht ein-/ausblenden."""
        if not QT3D_AVAILABLE:
            return
        entry_obj = self._obj_map.get(item)
        if entry_obj:
            state = item_visibility_state(is_object=True, visible=visible, labels_visible=self._labels_visible)
            ent, _tr = entry_obj
            try:
                ent.setEnabled(bool(state["entity_enabled"]))
            except Exception:
                pass
            lbl = self._obj_label_ent.get(item)
            if lbl is not None:
                try:
                    lbl.setEnabled(bool(state["label_enabled"]))
                except Exception:
                    pass
            return
        entry_zone = self._zone_map.get(item)
        if entry_zone:
            state = item_visibility_state(is_object=False, visible=visible, labels_visible=self._labels_visible)
            ent, _tr = entry_zone
            try:
                ent.setEnabled(bool(state["entity_enabled"]))
            except Exception:
                pass

    def update_object_position(self, obj, scale: float):
        if not QT3D_AVAILABLE or obj not in self._obj_map:
            return
        _ent, tr = self._obj_map[obj]
        yoff = float(self._obj_label_yoff.get(obj, 3.8))
        update_state = object_position_update_state(
            pos_raw=obj.data.get("pos", "0,0,0"),
            scale=scale,
            label_y_offset=yoff,
        )
        tr.setTranslation(QVector3D(*update_state["translation_xyz"]))
        lbl_tr = self._obj_label_tr.get(obj)
        state = position_update_state(
            is_selected=self._selected_obj is obj,
            move_mode=self._move_mode,
            has_label=lbl_tr is not None,
            locked_axis=self._locked_axis,
        )
        if state["update_label"] and lbl_tr is not None:
            lbl_tr.setTranslation(QVector3D(*update_state["label_translation_xyz"]))
            self._update_label_scales()
        if state["rebuild_gizmo"]:
            # Preserve locked axis state across gizmo rebuild
            saved_axis = self._locked_axis
            self._show_axis_gizmo(tr.translation())
            if state["restore_locked_axis"] and saved_axis:
                self._locked_axis = saved_axis
                self._highlight_gizmo_axis(saved_axis)
                app = QApplication.instance()
                if app:
                    app.installEventFilter(self)
        if obj in self._native_preview_entity_by_obj or obj is self._selected_native_detail_obj:
            self._schedule_native_scene_preview_refresh(30)

    def update_object_rotation(self, obj):
        if not QT3D_AVAILABLE or obj not in self._obj_map:
            return
        _ent, tr = self._obj_map[obj]
        tr.setRotation(self._rotation_quaternion_for_object(obj))
        if obj in self._native_preview_entity_by_obj or obj is self._selected_native_detail_obj:
            self._schedule_native_scene_preview_refresh(30)

    # ==================================================================
    #  Move-Modus  &  Achsen-Gizmo
    # ==================================================================
    def set_move_mode(self, enabled: bool):
        """Wird vom MainWindow aufgerufen wenn die Move-Checkbox getoggled wird."""
        state = move_mode_state(enabled=enabled, has_selected_obj=self._selected_obj is not None, has_locked_axis=self._locked_axis is not None)
        self._move_mode = bool(state["move_mode"])
        if state["clear_locked_axis"]:
            self._locked_axis = None
            app = QApplication.instance()
            if app:
                app.removeEventFilter(self)
        if state["show_gizmo"]:
            ent, tr = self._obj_map.get(self._selected_obj, (None, None))
            if tr:
                self._show_axis_gizmo(tr.translation())
        elif state["clear_gizmo"]:
            self._clear_axis_gizmo()

    def _clear_axis_gizmo(self):
        state = gizmo_clear_state(has_locked_axis=self._locked_axis is not None)
        for ent in self._axis_gizmo_entities:
            ent.setParent(None)
        if state["clear_entities"]:
            self._axis_gizmo_entities.clear()
        if state["clear_refs"]:
            self._axis_gizmo_refs.clear()
        if state["clear_mats"]:
            self._axis_gizmo_mats.clear()
        if state["clear_nodes"]:
            self._axis_gizmo_nodes.clear()
        self._axis_gizmo_center = state["axis_gizmo_center"]
        if state["clear_locked_axis"]:
            self._locked_axis = None
            app = QApplication.instance()
            if app:
                app.removeEventFilter(self)

    def _show_axis_gizmo(self, center: QVector3D):
        self._clear_axis_gizmo()
        if self._selected_obj is None:
            return
        self._axis_gizmo_center = QVector3D(center.x(), center.y(), center.z())

        configs = [
            ("x", QColor(255, 80, 80),  QVector3D(1, 0, 0),  QQuaternion.fromAxisAndAngle(0, 0, 1, -90)),
            ("y", QColor(80, 220, 80),  QVector3D(0, 1, 0),  QQuaternion()),
            ("z", QColor(80, 140, 255), QVector3D(0, 0, 1),  QQuaternion.fromAxisAndAngle(1, 0, 0, -90)),
        ]

        for axis_name, color, axis_dir, rotation in configs:
            arrow_ent = QEntity3D(self._root)
            if QConeMesh3D is not None:
                arrow_mesh = QConeMesh3D()
                arrow_mesh.setLength(8.0)
                arrow_mesh.setBottomRadius(2.2)
                try:
                    arrow_mesh.setTopRadius(0.0)
                except Exception:
                    pass
            else:
                arrow_mesh = QCylinderMesh3D()
                arrow_mesh.setLength(7.0)
                arrow_mesh.setRadius(1.6)

            arrow_mat = QPhongMaterial3D(self._root)
            arrow_mat.setDiffuse(color)
            try:
                arrow_mat.setAmbient(color.lighter(140))
            except Exception:
                pass
            always_on_top_refs = self._make_material_always_on_top(arrow_mat)

            arrow_tr = QTransform3D()
            arrow_tr.setRotation(rotation)

            arrow_pick = QObjectPicker3D(arrow_ent)
            arrow_pick.setHoverEnabled(False)
            arrow_pick.clicked.connect(
                lambda *_a, ax=axis_name: self._on_axis_gizmo_clicked(ax)
            )

            arrow_ent.addComponent(arrow_mesh)
            arrow_ent.addComponent(arrow_mat)
            arrow_ent.addComponent(arrow_tr)
            arrow_ent.addComponent(arrow_pick)

            self._axis_gizmo_entities.append(arrow_ent)
            self._axis_gizmo_refs.extend([arrow_mesh, arrow_mat, arrow_tr, arrow_pick, *always_on_top_refs])
            self._axis_gizmo_mats[axis_name] = arrow_mat
            self._axis_gizmo_nodes[axis_name] = (arrow_tr, axis_dir, rotation)
        self._update_axis_gizmo_transforms()

    def _make_material_always_on_top(self, material) -> list[Any]:
        """Versucht den Material-Depth-Test auf Always zu setzen (Gizmo bleibt sichtbar)."""
        return material_always_on_top_refs(material, Qt3DRender)

    def _update_axis_gizmo_transforms(self):
        """Hält den Gizmo sichtbar: leicht zur Kamera versetzt und mit Zoom skaliert."""
        if self._axis_gizmo_center is None or not self._axis_gizmo_nodes:
            return
        try:
            cam_pos = self._camera.position()
        except Exception:
            return
        center = self._axis_gizmo_center
        for _axis, (tr, axis_dir, rotation) in self._axis_gizmo_nodes.items():
            state = gizmo_transform_state(
                center_xyz=(center.x(), center.y(), center.z()),
                cam_pos_xyz=(cam_pos.x(), cam_pos.y(), cam_pos.z()),
                axis_dir_xyz=(axis_dir.x(), axis_dir.y(), axis_dir.z()),
            )
            if state is None:
                continue
            try:
                tx, ty, tz = state["translation_xyz"]
                tr.setTranslation(QVector3D(tx, ty, tz))
                tr.setRotation(rotation)
                tr.setScale(float(state["scale"]))
            except Exception:
                pass

    def _on_axis_gizmo_clicked(self, axis: str):
        state = gizmo_click_state(self._locked_axis, axis, has_selection=self._selected_obj is not None)
        if not state["has_selection"]:
            return
        app = QApplication.instance()
        self._locked_axis = state["next_axis"]
        if state["reset_colors"]:
            self._reset_gizmo_colors()
        if state["highlight_axis"] is not None:
            self._highlight_gizmo_axis(str(state["highlight_axis"]))
        if app and state["remove_event_filter"]:
            app.removeEventFilter(self)
        if app and state["install_event_filter"]:
            app.installEventFilter(self)
        container = getattr(self, "_container", None)
        if container is not None:
            container.setFocus(Qt.OtherFocusReason)

    def _highlight_gizmo_axis(self, axis: str):
        colors = gizmo_highlight_colors(axis)
        for ax, mat in self._axis_gizmo_mats.items():
            try:
                mat.setDiffuse(colors[ax])
                mat.setAmbient(colors[ax])
            except Exception:
                pass

    def _reset_gizmo_colors(self):
        defaults = gizmo_default_colors()
        for ax, mat in self._axis_gizmo_mats.items():
            try:
                diffuse, ambient = defaults[ax]
                mat.setDiffuse(diffuse)
                mat.setAmbient(ambient)
            except Exception:
                pass

    # ==================================================================
    #  Flight-Mode
    # ==================================================================
    def is_flight_mode_active(self) -> bool:
        return bool(self._flight.active)

    def get_free_camera_speed(self) -> float:
        return float(self._free_camera_speed)

    def set_flight_mode_active(self, enabled: bool, editor=None):
        if not QT3D_AVAILABLE:
            return
        state = flight_mode_toggle_state(enabled=enabled)
        if state["focus_container"] and hasattr(self, "_container"):
            self._container.setFocus(Qt.OtherFocusReason)
        if state["start_flight"]:
            self._flight.start(self, editor)
        if state["stop_flight"]:
            self._flight.stop()
        self._flight_help_overlay.setVisible(bool(state["help_overlay_visible"]))
        if state["reset_dust_distribution"]:
            self._reset_dust_distribution()
        if state["reposition_overlays"]:
            self._reposition_flight_overlays()
        if state["sync_orbit_from_camera"]:
            self._sync_orbit_state_from_camera()
        if state["clear_flight_visuals"]:
            self.update_flight_visuals(None)

    def set_flight_hud_callback(self, callback):
        self._flight.hud_callback = callback

    def flight_set_freeflight(self):
        self._flight.set_free_flight()

    def flight_start_autopilot_selected(self):
        self._flight.start_autopilot_to_selection()

    def flight_dock_selected_tradelane(self):
        self._flight.start_dock_to_selected_tradelane()

    def flight_set_chase_distance_ship_lengths(self, value: float):
        self._flight.set_chase_distance_ship_lengths(value)

    def flight_get_chase_distance_ship_lengths(self) -> float:
        return self._flight.get_chase_distance_ship_lengths()

    def update_flight_visuals(self, snapshot: dict[str, Any] | None):
        self._flight_snapshot = snapshot
        state = flight_visual_entity_state(
            has_snapshot=snapshot is not None,
            has_ship_entity=self._flight_ship_entity is not None,
            dust_count=len(self._dust_entities),
        )
        apply_flight_entity_state(
            ship_entity=self._flight_ship_entity,
            dust_entities=self._dust_entities,
            charge_bar=self._flight_charge_bar,
            state=state,
        )
        if snapshot is None:
            return
        if state["update_ship_pose"] and self._flight_ship_entity is not None:
            self._update_flight_ship_pose(snapshot)
        if state["update_space_dust"]:
            self._update_space_dust(snapshot)
        if state["update_charge_bar"]:
            self._update_cruise_charge_bar(snapshot)

    def _update_flight_ship_pose(self, snapshot: dict[str, Any]):
        if self._flight_ship_tr is None:
            return
        try:
            camera_state = flight_camera_context_from_camera(camera=getattr(self, "_camera", None))
            state = flight_ship_render_pose(
                snapshot=snapshot,
                scene_scale=float(getattr(self, "_scene_scale", 1.0) or 1.0),
                camera_pos_xyz=camera_state["camera_pos_xyz"],
                camera_view_center_xyz=camera_state["camera_view_center_xyz"],
            )
            self._flight_ship_tr.setTranslation(QVector3D(*state["pos_xyz"]))
            self._flight_ship_tr.setRotation(QQuaternion.fromEulerAngles(*state["rotation_euler_deg"]))
        except Exception:
            pass

    def _update_space_dust(self, snapshot: dict[str, Any]):
        if not self._dust_entities:
            return
        try:
            state = dust_update_state(
                snapshot=snapshot,
                local_positions_xyz=[(pos.x(), pos.y(), pos.z()) for pos in self._dust_local_positions],
                scene_scale=float(getattr(self, "_scene_scale", 1.0) or 1.0),
                rng=random,
            )
            apply_state = flight_dust_apply_state(dust_count=len(self._dust_entities), enabled=bool(state["enabled"]))
            self._dust_local_positions = [QVector3D(*pos) for pos in state["local_positions_xyz"]]
            for i, tr in enumerate(self._dust_transforms):
                tr.setTranslation(QVector3D(*state["world_positions_xyz"][i]))
                self._dust_entities[i].setEnabled(bool(apply_state["enabled_states"][i]))
        except Exception:
            apply_state = flight_dust_apply_state(dust_count=len(self._dust_entities), enabled=False)
            for ent, enabled in zip(self._dust_entities, list(apply_state["enabled_states"])):
                ent.setEnabled(bool(enabled))

    def _update_cruise_charge_bar(self, snapshot: dict[str, Any]):
        state = cruise_charge_bar_state(snapshot=snapshot)
        apply_cruise_charge_bar(charge_bar=self._flight_charge_bar, state=state)

    def _sync_orbit_state_from_camera(self):
        cam = getattr(self, "_camera", None)
        if cam is None:
            return
        pos = cam.position()
        target = cam.viewCenter()
        state = synced_orbit_camera_state(
            camera_pos_xyz=(pos.x(), pos.y(), pos.z()),
            view_center_xyz=(target.x(), target.y(), target.z()),
        )
        if not state:
            return
        # Keep exact orbit distance so leaving Flight Mode does not "snap" the view.
        apply_synced_orbit_camera_state(view=self, state=state)

    def set_flight_overlay_text(self, text: str):
        state = flight_overlay_text_state(text=text)
        apply_flight_overlay_text(overlay=self._flight_overlay, state=state)

    def _reposition_flight_overlays(self):
        host = self._container if hasattr(self, "_container") else self
        state = flight_overlay_layout(
            host_width=host.width(),
            overlay_height=self._flight_overlay.height(),
            help_overlay_visible=self._flight_help_overlay.isVisible(),
            help_overlay_width=self._flight_help_overlay.width(),
        )
        apply_flight_overlay_layout(
            overlay=self._flight_overlay,
            charge_bar=self._flight_charge_bar,
            help_overlay=self._flight_help_overlay,
            state=state,
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._flight_overlay.isVisible() or self._flight_help_overlay.isVisible():
            self._reposition_flight_overlays()

    def keyPressEvent(self, event):
        state = dispatch_widget_flight_event(flight=self._flight, active=self._flight.active, event_type="key_press", event=event)
        if bool(state["accepted"]):
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        state = dispatch_widget_flight_event(flight=self._flight, active=self._flight.active, event_type="key_release", event=event)
        if bool(state["accepted"]):
            event.accept()
            return
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        dispatch_widget_flight_event(flight=self._flight, active=self._flight.active, event_type="mouse_press", event=event)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        dispatch_widget_flight_event(flight=self._flight, active=self._flight.active, event_type="mouse_release", event=event)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        state = dispatch_widget_flight_event(flight=self._flight, active=self._flight.active, event_type="mouse_move", event=event)
        if bool(state["accepted"]):
            event.accept()
            return
        super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        state = dispatch_widget_flight_event(flight=self._flight, active=self._flight.active, event_type="wheel", event=event)
        if bool(state["accepted"]):
            event.accept()
            return
        super().wheelEvent(event)
