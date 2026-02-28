"""3D-Systemansicht auf Basis von Qt3D.

Enthält die komplette 3D-Rendering-Logik:
- Kamera-Steuerung (Orbit, Pan, Zoom)
- Objekt- und Zonenentitäten
- Auswahl (Sphere↔Cube Swap via setEnabled)
- Gizmo-System (Klick-Lock auf Achse, Mausrad-Bewegung)
- App-Level Event-Filter für Mausrad-Abfangen
"""

from __future__ import annotations

import math
from typing import Any

from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QEvent, Signal
from PySide6.QtGui import QColor, QFont, QVector3D, QQuaternion

from .qt3d_compat import (
    QT3D_AVAILABLE,
    QConeMesh3D,
    QCuboidMesh3D,
    QCylinderMesh3D,
    QDirectionalLight3D,
    QEntity3D,
    QExtrudedTextMesh3D,
    QObjectPicker3D,
    QPhongAlphaMaterial3D,
    QPhongMaterial3D,
    QSphereMesh3D,
    QTransform3D,
    Qt3DWindow3D,
)
from .flight_mode import FlightModeController


class System3DView(QWidget):
    """Qt3D-basierte 3D-Ansicht eines Freelancer-Systems."""

    object_selected = Signal(object)
    object_height_delta = Signal(object, float)
    object_axis_delta = Signal(object, float, float, float)

    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)
        # Objekt-Entity-Verwaltung
        self._obj_map: dict[Any, tuple[Any, Any]] = {}
        self._zone_map: dict[Any, tuple[Any, Any]] = {}
        self._zone_entities: list[Any] = []
        self._obj_component_refs: dict[Any, list[Any]] = {}
        self._zone_component_refs: dict[Any, list[Any]] = {}
        self._obj_label_ent: dict[Any, Any] = {}
        self._labels_visible = True

        # Sphere/Cube-Toggle (pre-created, via setEnabled gesteuert)
        self._obj_sphere_ent: dict[Any, Any] = {}
        self._obj_cube_ent: dict[Any, Any] = {}
        self._obj_cube_refs: dict[Any, list[Any]] = {}

        self._selected_obj: Any = None

        # Gizmo
        self._axis_gizmo_entities: list[Any] = []
        self._axis_gizmo_refs: list[Any] = []
        self._axis_gizmo_mats: dict[str, Any] = {}
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

        # Flight-Mode
        self._flight = FlightModeController(self)

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
            "W/S: accelerate / brake\n"
            "Shift+W: cruise\n"
            "F2: autopilot to selected\n"
            "F3: trade lane\n"
            "ESC: exit flight mode"
        )
        self._flight_help_overlay.adjustSize()
        self._flight_help_overlay.setVisible(False)
        self._flight_help_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        if not QT3D_AVAILABLE:
            layout.addWidget(QLabel("Qt3D ist nicht verfügbar."))
            return

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
        layout.addWidget(self._container)

        self._root = QEntity3D()
        self._window.setRootEntity(self._root)

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
        self._update_camera()

    # ==================================================================
    #  Kamera
    # ==================================================================
    def center_on_item(self, item):
        entry = self._obj_map.get(item) or self._zone_map.get(item)
        if entry is None:
            return
        _ent, tr = entry
        self._cam_target = tr.translation()
        self._cam_pitch = 1.42
        self._cam_yaw = 0.0
        is_zone = item in self._zone_map
        self._cam_distance = max(
            180.0 if is_zone else 120.0,
            self._system_radius * (0.6 if is_zone else 0.45),
        )
        self._update_camera()

    def _update_camera(self):
        cp = math.cos(self._cam_pitch)
        dir_vec = QVector3D(
            cp * math.sin(self._cam_yaw),
            math.sin(self._cam_pitch),
            cp * math.cos(self._cam_yaw),
        )
        pos = self._cam_target + dir_vec * self._cam_distance
        self._camera.setPosition(pos)
        self._camera.setViewCenter(self._cam_target)

    def _pan_camera(self, dx: float, dy: float):
        pos = self._camera.position()
        fwd = self._cam_target - pos
        if fwd.length() < 1e-6:
            return
        fwd = fwd.normalized()
        right = QVector3D.crossProduct(fwd, QVector3D(0.0, 1.0, 0.0))
        if right.length() < 1e-6:
            return
        right = right.normalized()
        up = QVector3D.crossProduct(right, fwd).normalized()
        factor = self._cam_distance * 0.0015
        shift = (-right * dx + up * dy) * factor
        self._cam_target += shift
        self._update_camera()

    # ==================================================================
    #  Event-Filter  (Orbit, Pan, Zoom, Gizmo-Scroll)
    # ==================================================================
    def eventFilter(self, obj, event):
        if self._flight.active:
            et = event.type()
            if et == QEvent.KeyPress:
                return bool(self._flight.on_key_press(event))
            if et == QEvent.KeyRelease:
                return bool(self._flight.on_key_release(event))
            if et == QEvent.MouseButtonPress:
                self._flight.on_mouse_press(event)
                return False
            if et == QEvent.MouseButtonRelease:
                self._flight.on_mouse_release(event)
                return False
            if et == QEvent.MouseMove:
                self._flight.on_mouse_move(event)
                return True
            if et == QEvent.Wheel:
                self._flight.on_wheel(event)
                return True

        # Globale Mausrad-Abfangung wenn eine Gizmo-Achse gesperrt ist
        if event.type() == QEvent.Wheel and self._locked_axis and self._selected_obj:
            self._emit_axis_scroll(event.angleDelta().y())
            return True

        container = getattr(self, "_container", None)
        window = getattr(self, "_window", None)
        if not QT3D_AVAILABLE or obj not in (container, window):
            return super().eventFilter(obj, event)

        et = event.type()

        if et == QEvent.MouseButtonPress:
            self._last_mouse_pos = event.position()
            if event.button() == Qt.LeftButton:
                # Wenn eine Achse gesperrt ist → Linksklick hebt die Sperre auf
                if self._locked_axis is not None:
                    self._locked_axis = None
                    self._reset_gizmo_colors()
                    app = QApplication.instance()
                    if app:
                        app.removeEventFilter(self)
                    return True
                self._drag_mode = "orbit"
                return True
            if event.button() == Qt.RightButton:
                self._drag_mode = "pan"
                return True

        elif et == QEvent.MouseMove and self._last_mouse_pos and self._drag_mode:
            pos = event.position()
            d = pos - self._last_mouse_pos
            self._last_mouse_pos = pos
            dx, dy = float(d.x()), float(d.y())
            if self._drag_mode == "orbit":
                self._cam_yaw -= dx * 0.008
                self._cam_pitch = max(-1.45, min(1.45, self._cam_pitch + dy * 0.008))
                self._update_camera()
                return True
            if self._drag_mode == "pan":
                self._pan_camera(dx, dy)
                return True

        elif et == QEvent.MouseButtonRelease:
            if event.button() in (Qt.LeftButton, Qt.RightButton):
                self._drag_mode = None
                self._last_mouse_pos = None
                return True

        elif et == QEvent.Wheel:
            delta = event.angleDelta().y()
            if self._locked_axis and self._selected_obj:
                self._emit_axis_scroll(delta)
                return True
            if event.modifiers() & Qt.ControlModifier and self._selected_obj is not None:
                self.object_height_delta.emit(self._selected_obj, delta / 120.0 * 100.0)
                return True
            zoom = 0.9 if delta > 0 else 1.1
            self._cam_distance = max(20.0, min(15000.0, self._cam_distance * zoom))
            self._update_camera()
            return True

        return super().eventFilter(obj, event)

    def _emit_axis_scroll(self, delta: int):
        """Sendet ein Achsen-Delta-Signal basierend auf Mausrad."""
        step = self._axis_step_world * (1.0 if delta > 0 else -1.0)
        ax = self._locked_axis
        self.object_axis_delta.emit(
            self._selected_obj,
            step if ax == "x" else 0.0,
            step if ax == "y" else 0.0,
            step if ax == "z" else 0.0,
        )

    # ==================================================================
    #  Szene verwalten
    # ==================================================================
    def clear_scene(self):
        if not QT3D_AVAILABLE:
            return
        for ent, _tr in self._obj_map.values():
            ent.setParent(None)
        self._obj_map.clear()
        self._obj_component_refs.clear()
        self._obj_label_ent.clear()
        for ent, _tr in self._zone_map.values():
            ent.setParent(None)
        self._zone_map.clear()
        self._zone_component_refs.clear()
        for ent in self._zone_entities:
            ent.setParent(None)
        self._zone_entities.clear()
        self._selected_obj = None
        self._locked_axis = None
        self._obj_sphere_ent.clear()
        self._obj_cube_ent.clear()
        self._obj_cube_refs.clear()
        self._clear_axis_gizmo()

    def set_data(self, objects, zones, scale: float):
        """Baut die 3D-Szene aus Objekt- und Zonenlisten auf."""
        if not QT3D_AVAILABLE:
            return
        self._scene_scale = float(scale)
        self.clear_scene()

        min_x = min_y = min_z = float("inf")
        max_x = max_y = max_z = float("-inf")

        for obj in objects:
            ent, tr, refs = self._create_object_entity(obj, scale)
            if ent is None:
                continue
            self._obj_map[obj] = (ent, tr)
            self._obj_component_refs[obj] = refs
            p = tr.translation()
            min_x, max_x = min(min_x, p.x()), max(max_x, p.x())
            min_y, max_y = min(min_y, p.y()), max(max_y, p.y())
            min_z, max_z = min(min_z, p.z()), max(max_z, p.z())

        for zone in zones:
            ent, tr, refs = self._create_zone_entity(zone, scale)
            if ent is not None and tr is not None:
                self._zone_map[zone] = (ent, tr)
                self._zone_component_refs[zone] = refs
                self._zone_entities.append(ent)

        if self._obj_map:
            cx = (min_x + max_x) * 0.5
            cy = (min_y + max_y) * 0.5
            cz = (min_z + max_z) * 0.5
            radius = max(max_x - min_x, max_z - min_z, (max_y - min_y) * 0.5, 120.0)
            self._cam_target = QVector3D(cx, cy, cz)
            self._cam_distance = max(240.0, radius * 1.3)
            self._system_center = QVector3D(cx, cy, cz)
            self._system_radius = radius
        else:
            self._cam_target = QVector3D(0.0, 0.0, 0.0)
            self._cam_distance = 500.0
            self._system_center = QVector3D(0.0, 0.0, 0.0)
            self._system_radius = 500.0

        self._cam_yaw = 0.0
        self._cam_pitch = 1.42
        self._update_camera()

    # ==================================================================
    #  Objekt-Entitäten
    # ==================================================================
    @staticmethod
    def _obj_color(obj) -> QColor:
        arch = obj.data.get("archetype", "").lower()
        name = obj.nickname.lower()
        if any(tag in name or tag in arch for tag in ("trade_lane_ring", "tradelane_ring")):
            return QColor(70, 140, 255)
        if arch == "nav_buoy":
            return QColor(255, 230, 80)
        if "surprise" in name:
            return QColor(230, 60, 60)
        if any(x in arch for x in ("sun", "star")):
            return QColor(255, 215, 40)
        if "planet" in arch:
            return QColor(60, 130, 220)
        if any(x in arch for x in ("base", "station")):
            return QColor(80, 210, 100)
        if any(x in arch for x in ("jump", "gate")):
            return QColor(210, 90, 210)
        return QColor(190, 190, 190)

    def _create_object_entity(self, obj, scale: float):
        arch = obj.data.get("archetype", "").lower()
        name = obj.nickname.lower()
        is_trade_lane = any(
            tag in name or tag in arch for tag in ("trade_lane_ring", "tradelane_ring")
        )

        ent = QEntity3D(self._root)
        tr = QTransform3D()
        sun_radius = 0.0

        # Mesh-Typ und -Größe bestimmen
        mesh = QSphereMesh3D()
        if is_trade_lane:
            mesh.setRadius(1.2)
        elif arch.strip() == "dock_ring":
            mesh.setRadius(0.9)
        elif "surprise" in name:
            mesh.setRadius(3.5)
        elif any(x in arch for x in ("sun", "star")):
            sun_radius = 11.0
            mesh.setRadius(sun_radius)
        elif "planet" in arch:
            mesh.setRadius(7.5)
        elif any(x in arch for x in ("base", "station")):
            mesh.setRadius(3.5)
        else:
            mesh.setRadius(2.8)

        # Material
        color = self._obj_color(obj)
        mat = QPhongMaterial3D(self._root)
        mat.setDiffuse(color)
        try:
            mat.setAmbient(
                QColor(255, 245, 170) if sun_radius > 0 else color.lighter(175)
            )
        except Exception:
            pass

        # Position
        pparts = [float(c.strip()) for c in obj.data.get("pos", "0,0,0").split(",")]
        fx = pparts[0] if len(pparts) > 0 else 0.0
        fy = pparts[1] if len(pparts) > 1 else 0.0
        fz = pparts[2] if len(pparts) > 2 else (pparts[1] if len(pparts) > 1 else 0.0)
        tr.setTranslation(QVector3D(fx * scale, fy * scale, fz * scale))

        # Picker
        picker = QObjectPicker3D(ent)
        picker.setHoverEnabled(False)
        picker.clicked.connect(lambda *_a, o=obj: self.object_selected.emit(o))

        # -- Sphere Entity (default sichtbar) --
        sphere_ent = QEntity3D(ent)
        sphere_ent.addComponent(mesh)
        sphere_ent.addComponent(mat)
        self._obj_sphere_ent[obj] = sphere_ent

        # -- Cube Entity (default unsichtbar) --
        cube_wrapper = QEntity3D(ent)
        cube_wrapper.setEnabled(False)
        cube_refs = self._create_orientation_cube(cube_wrapper, obj, cube_size=4.6)
        self._obj_cube_ent[obj] = cube_wrapper
        self._obj_cube_refs[obj] = cube_refs

        component_refs: list[Any] = [tr, picker, mesh, mat, sphere_ent, cube_wrapper]
        ent.addComponent(tr)
        ent.addComponent(picker)

        # Sonnenglow
        if sun_radius > 0:
            glow_ent = QEntity3D(sphere_ent)
            glow_mesh = QSphereMesh3D()
            glow_mesh.setRadius(sun_radius * 1.35)
            glow_tr = QTransform3D()
            glow_mat = QPhongAlphaMaterial3D(self._root)
            glow_mat.setAlpha(0.40)
            glow_mat.setDiffuse(QColor(255, 220, 90, 120))
            glow_ent.addComponent(glow_mesh)
            glow_ent.addComponent(glow_mat)
            glow_ent.addComponent(glow_tr)
            component_refs.extend([glow_ent, glow_mesh, glow_mat, glow_tr])

        lbl_ent, lbl_refs = self._attach_object_label(ent, obj.nickname)
        if lbl_ent is not None:
            self._obj_label_ent[obj] = lbl_ent
            lbl_ent.setEnabled(self._labels_visible)
        component_refs.extend(lbl_refs)
        return ent, tr, component_refs

    def _create_orientation_cube(self, parent_ent, obj, cube_size: float):
        """Erzeugt einen Orientierungswürfel aus 6 farbigen Flächen."""
        half = cube_size * 0.5
        thick = max(0.35, cube_size * 0.09)
        face_specs = [
            (QColor(255, 40, 40),  QVector3D(0, 0, half),  QVector3D(cube_size, cube_size, thick)),
            (QColor(80, 220, 220), QVector3D(0, 0, -half), QVector3D(cube_size, cube_size, thick)),
            (QColor(80, 220, 80),  QVector3D(half, 0, 0),  QVector3D(thick, cube_size, cube_size)),
            (QColor(70, 130, 255), QVector3D(-half, 0, 0), QVector3D(thick, cube_size, cube_size)),
            (QColor(245, 235, 80), QVector3D(0, half, 0),  QVector3D(cube_size, thick, cube_size)),
            (QColor(220, 80, 220), QVector3D(0, -half, 0), QVector3D(cube_size, thick, cube_size)),
        ]
        refs: list[Any] = []
        for color, trans, ext in face_specs:
            face_ent = QEntity3D(parent_ent)
            face_mesh = QCuboidMesh3D()
            face_mesh.setXExtent(ext.x())
            face_mesh.setYExtent(ext.y())
            face_mesh.setZExtent(ext.z())
            face_mat = QPhongMaterial3D(self._root)
            face_mat.setDiffuse(color)
            try:
                face_mat.setAmbient(color.lighter(150))
            except Exception:
                pass
            face_tr = QTransform3D()
            face_tr.setTranslation(trans)
            face_picker = QObjectPicker3D(face_ent)
            face_picker.setHoverEnabled(False)
            face_picker.clicked.connect(lambda *_a, o=obj: self.object_selected.emit(o))
            face_ent.addComponent(face_mesh)
            face_ent.addComponent(face_mat)
            face_ent.addComponent(face_tr)
            face_ent.addComponent(face_picker)
            refs.extend([face_ent, face_mesh, face_mat, face_tr, face_picker])
        return refs

    def _attach_object_label(self, parent_ent, text: str):
        if not QExtrudedTextMesh3D:
            return None, []
        label_text = text if len(text) <= 28 else (text[:25] + "...")
        lbl_ent = QEntity3D(parent_ent)
        txt_mesh = QExtrudedTextMesh3D()
        txt_mesh.setText(label_text)
        txt_mesh.setDepth(0.25)
        txt_mesh.setFont(QFont("Sans", 12))
        txt_tr = QTransform3D()
        txt_tr.setTranslation(QVector3D(16.0, 36.0, 16.0))
        txt_tr.setScale(2.1)
        txt_mat = QPhongMaterial3D(self._root)
        txt_mat.setDiffuse(QColor(245, 245, 245))
        try:
            txt_mat.setAmbient(QColor(250, 250, 250))
        except Exception:
            pass
        lbl_ent.addComponent(txt_mesh)
        lbl_ent.addComponent(txt_tr)
        lbl_ent.addComponent(txt_mat)
        return lbl_ent, [lbl_ent, txt_mesh, txt_tr, txt_mat]

    # ==================================================================
    #  Zonen-Entitäten
    # ==================================================================
    @staticmethod
    def _zone_color(zone) -> QColor:
        n = zone.nickname.lower()
        d = zone.data
        if "death" in n or "damage" in d:
            return QColor(220, 50, 50, 50)
        if "nebula" in n or "badlands" in n:
            return QColor(150, 80, 220, 50)
        if "debris" in n or "asteroid" in n:
            return QColor(180, 130, 60, 50)
        if "tradelane" in n:
            return QColor(70, 140, 255, 180)
        return QColor(80, 160, 200, 50)

    def _create_zone_entity(self, zone, scale: float):
        zone_name = zone.nickname.lower()
        is_tradelane = "tradelane" in zone_name
        if "destroy_vignette" in zone_name:
            return None, None, []
        if "path" in zone_name and not is_tradelane:
            return None, None, []

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
            else:
                mesh = QSphereMesh3D()
                mesh.setRadius(1.0)
                tr.setScale3D(QVector3D(sx, sy, sz))

        mat = QPhongAlphaMaterial3D(self._root)
        mat.setAlpha(0.58 if is_tradelane else 0.14)
        mat.setDiffuse(self._zone_color(zone))
        try:
            mat.setAmbient(self._zone_color(zone).lighter(120))
        except Exception:
            pass

        pparts = [float(c.strip()) for c in zone.data.get("pos", "0,0,0").split(",")]
        fx = pparts[0] if len(pparts) > 0 else 0.0
        fy = pparts[1] if len(pparts) > 1 else 0.0
        fz = pparts[2] if len(pparts) > 2 else (pparts[1] if len(pparts) > 1 else 0.0)
        tr.setTranslation(QVector3D(fx * scale, fy * scale, fz * scale))

        ent.addComponent(mesh)
        ent.addComponent(mat)
        ent.addComponent(tr)
        return ent, tr, [mesh, mat, tr]

    # ==================================================================
    #  Auswahl  (Sphere↔Cube Toggle)
    # ==================================================================
    def _show_cube_hide_sphere(self, obj):
        sphere_ent = self._obj_sphere_ent.get(obj)
        cube_ent = self._obj_cube_ent.get(obj)
        if sphere_ent is not None:
            sphere_ent.setEnabled(False)
        if cube_ent is not None:
            cube_ent.setEnabled(True)

    def _show_sphere_hide_cube(self, obj):
        cube_ent = self._obj_cube_ent.get(obj)
        sphere_ent = self._obj_sphere_ent.get(obj)
        if cube_ent is not None:
            cube_ent.setEnabled(False)
        if sphere_ent is not None:
            sphere_ent.setEnabled(True)

    def set_selected(self, obj):
        if not QT3D_AVAILABLE:
            return
        new_obj = obj if obj in self._obj_map else None
        if new_obj is not None and new_obj is self._selected_obj:
            return
        flight_active = bool(getattr(self, "_flight", None) and self._flight.active)
        # Vorherige Auswahl zurücksetzen
        prev = self._selected_obj
        if prev is not None and prev in self._obj_map:
            self._show_sphere_hide_cube(prev)
        self._selected_obj = new_obj
        self._locked_axis = None
        if self._selected_obj is None:
            self._clear_axis_gizmo()
            return
        # Im Flight Mode keine Cube-Darstellung erzwingen.
        if flight_active:
            self._show_sphere_hide_cube(self._selected_obj)
        else:
            self._show_cube_hide_sphere(self._selected_obj)
        _ent, tr = self._obj_map[self._selected_obj]
        if self._move_mode and not flight_active:
            self._show_axis_gizmo(tr.translation())
        else:
            self._clear_axis_gizmo()

    def set_label_visibility(self, enabled: bool):
        self._labels_visible = bool(enabled)
        for ent in self._obj_label_ent.values():
            try:
                ent.setEnabled(self._labels_visible)
            except Exception:
                pass

    def update_object_position(self, obj, scale: float):
        if not QT3D_AVAILABLE or obj not in self._obj_map:
            return
        _ent, tr = self._obj_map[obj]
        pparts = [float(c.strip()) for c in obj.data.get("pos", "0,0,0").split(",")]
        fx = pparts[0] if len(pparts) > 0 else 0.0
        fy = pparts[1] if len(pparts) > 1 else 0.0
        fz = pparts[2] if len(pparts) > 2 else (pparts[1] if len(pparts) > 1 else 0.0)
        tr.setTranslation(QVector3D(fx * scale, fy * scale, fz * scale))
        if self._selected_obj is obj and self._move_mode:
            # Preserve locked axis state across gizmo rebuild
            saved_axis = self._locked_axis
            self._show_axis_gizmo(tr.translation())
            if saved_axis:
                self._locked_axis = saved_axis
                self._highlight_gizmo_axis(saved_axis)
                app = QApplication.instance()
                if app:
                    app.installEventFilter(self)

    # ==================================================================
    #  Move-Modus  &  Achsen-Gizmo
    # ==================================================================
    def set_move_mode(self, enabled: bool):
        """Wird vom MainWindow aufgerufen wenn die Move-Checkbox getoggled wird."""
        self._move_mode = enabled
        if self._locked_axis is not None:
            self._locked_axis = None
            app = QApplication.instance()
            if app:
                app.removeEventFilter(self)
        if self._selected_obj is not None:
            if enabled:
                ent, tr = self._obj_map.get(self._selected_obj, (None, None))
                if tr:
                    self._show_axis_gizmo(tr.translation())
            else:
                self._clear_axis_gizmo()

    def _clear_axis_gizmo(self):
        for ent in self._axis_gizmo_entities:
            ent.setParent(None)
        self._axis_gizmo_entities.clear()
        self._axis_gizmo_refs.clear()
        self._axis_gizmo_mats.clear()
        if self._locked_axis is not None:
            self._locked_axis = None
            app = QApplication.instance()
            if app:
                app.removeEventFilter(self)

    def _show_axis_gizmo(self, center: QVector3D):
        self._clear_axis_gizmo()
        if self._selected_obj is None:
            return

        configs = [
            ("x", QColor(255, 80, 80),  QVector3D(20, 0, 0),  QQuaternion.fromAxisAndAngle(0, 0, 1, -90)),
            ("y", QColor(80, 220, 80),  QVector3D(0, 20, 0),  QQuaternion()),
            ("z", QColor(80, 140, 255), QVector3D(0, 0, 20),  QQuaternion.fromAxisAndAngle(1, 0, 0, -90)),
        ]

        for axis_name, color, offset, rotation in configs:
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

            arrow_tr = QTransform3D()
            arrow_tr.setTranslation(center + offset)
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
            self._axis_gizmo_refs.extend([arrow_mesh, arrow_mat, arrow_tr, arrow_pick])
            self._axis_gizmo_mats[axis_name] = arrow_mat

    def _on_axis_gizmo_clicked(self, axis: str):
        if self._selected_obj is None:
            return
        app = QApplication.instance()
        if self._locked_axis == axis:
            self._locked_axis = None
            self._reset_gizmo_colors()
            if app:
                app.removeEventFilter(self)
        else:
            self._locked_axis = axis
            self._highlight_gizmo_axis(axis)
            if app:
                app.installEventFilter(self)
        container = getattr(self, "_container", None)
        if container is not None:
            container.setFocus(Qt.OtherFocusReason)

    def _highlight_gizmo_axis(self, axis: str):
        bright = {"x": QColor(255, 180, 180), "y": QColor(180, 255, 180), "z": QColor(180, 200, 255)}
        dim = {"x": QColor(100, 40, 40), "y": QColor(40, 90, 40), "z": QColor(40, 60, 100)}
        for ax, mat in self._axis_gizmo_mats.items():
            try:
                if ax == axis:
                    mat.setDiffuse(bright[ax])
                    mat.setAmbient(bright[ax])
                else:
                    mat.setDiffuse(dim[ax])
                    mat.setAmbient(dim[ax])
            except Exception:
                pass

    def _reset_gizmo_colors(self):
        defaults = {"x": QColor(255, 80, 80), "y": QColor(80, 220, 80), "z": QColor(80, 140, 255)}
        for ax, mat in self._axis_gizmo_mats.items():
            try:
                mat.setDiffuse(defaults[ax])
                mat.setAmbient(defaults[ax].lighter(140))
            except Exception:
                pass

    # ==================================================================
    #  Flight-Mode
    # ==================================================================
    def is_flight_mode_active(self) -> bool:
        return bool(self._flight.active)

    def set_flight_mode_active(self, enabled: bool, editor=None):
        if not QT3D_AVAILABLE:
            return
        if enabled:
            if hasattr(self, "_container"):
                self._container.setFocus(Qt.OtherFocusReason)
            self._flight.start(self, editor)
            if self._selected_obj is not None:
                self._show_sphere_hide_cube(self._selected_obj)
            self._flight_help_overlay.adjustSize()
            self._flight_help_overlay.setVisible(True)
            self._flight_help_overlay.raise_()
            self._reposition_flight_overlays()
        else:
            self._flight.stop()
            self._sync_orbit_state_from_camera()
            if self._selected_obj is not None:
                self._show_cube_hide_sphere(self._selected_obj)
            self._flight_help_overlay.setVisible(False)

    def set_flight_hud_callback(self, callback):
        self._flight.hud_callback = callback

    def _sync_orbit_state_from_camera(self):
        cam = getattr(self, "_camera", None)
        if cam is None:
            return
        pos = cam.position()
        target = cam.viewCenter()
        vec = pos - target
        dist = float(vec.length())
        if dist < 1e-6:
            return
        dir_n = vec / dist
        self._cam_target = QVector3D(target)
        # Keep exact orbit distance so leaving Flight Mode does not "snap" the view.
        self._cam_distance = max(0.001, dist)
        self._cam_yaw = math.atan2(float(dir_n.x()), float(dir_n.z()))
        self._cam_pitch = math.asin(max(-1.0, min(1.0, float(dir_n.y()))))

    def set_flight_overlay_text(self, text: str):
        if not text:
            self._flight_overlay.clear()
            self._flight_overlay.setVisible(False)
            return
        self._flight_overlay.setText(text)
        self._flight_overlay.adjustSize()
        self._reposition_flight_overlays()
        self._flight_overlay.setVisible(True)
        self._flight_overlay.raise_()

    def _reposition_flight_overlays(self):
        y = self._controls_hint.height() + 8
        self._flight_overlay.move(8, y)
        if self._flight_help_overlay.isVisible():
            x = max(8, self.width() - self._flight_help_overlay.width() - 8)
            self._flight_help_overlay.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._flight_overlay.isVisible() or self._flight_help_overlay.isVisible():
            self._reposition_flight_overlays()

    def keyPressEvent(self, event):
        if self._flight.active and self._flight.on_key_press(event):
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if self._flight.active and self._flight.on_key_release(event):
            event.accept()
            return
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        if self._flight.active:
            self._flight.on_mouse_press(event)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._flight.active:
            self._flight.on_mouse_release(event)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self._flight.active:
            self._flight.on_mouse_move(event)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        if self._flight.active:
            self._flight.on_wheel(event)
            event.accept()
            return
        super().wheelEvent(event)
