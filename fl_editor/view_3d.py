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
from pathlib import Path
import tempfile
import re
from typing import Any

from PySide6.QtWidgets import QApplication, QLabel, QProgressBar, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QEvent, Signal, QUrl
from PySide6.QtGui import QColor, QFont, QVector3D, QQuaternion, QImage, QPainter

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
        self._obj_by_nick: dict[str, Any] = {}
        self._zone_map: dict[Any, tuple[Any, Any]] = {}
        self._zone_entities: list[Any] = []
        self._obj_component_refs: dict[Any, list[Any]] = {}
        self._zone_component_refs: dict[Any, list[Any]] = {}
        self._obj_label_ent: dict[Any, Any] = {}
        self._obj_label_tr: dict[Any, Any] = {}
        self._obj_label_yoff: dict[Any, float] = {}
        self._labels_visible = True
        # Keep 3D text roughly constant in screen size across zoom levels.
        self._label_scale_factor = 0.00125
        self._label_scale_min = 0.24
        self._label_scale_max = 3.4

        # Primärdarstellung pro Objekt
        self._obj_sphere_ent: dict[Any, Any] = {}

        self._selected_obj: Any = None

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
        self._dust_local_positions = []
        for _ent in self._dust_entities:
            self._dust_local_positions.append(
                QVector3D(
                    random.uniform(-26.0, 26.0),
                    random.uniform(-14.0, 12.0),
                    random.uniform(8.0, 180.0),
                )
            )

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

    def get_camera_state(self) -> dict[str, float]:
        return {
            "target_x": float(self._cam_target.x()),
            "target_y": float(self._cam_target.y()),
            "target_z": float(self._cam_target.z()),
            "distance": float(self._cam_distance),
            "yaw": float(self._cam_yaw),
            "pitch": float(self._cam_pitch),
        }

    def set_camera_state(self, state: dict[str, float] | None):
        if not state:
            return
        try:
            self._cam_target = QVector3D(
                float(state.get("target_x", 0.0)),
                float(state.get("target_y", 0.0)),
                float(state.get("target_z", 0.0)),
            )
            self._cam_distance = max(0.001, float(state.get("distance", self._cam_distance)))
            self._cam_yaw = float(state.get("yaw", self._cam_yaw))
            self._cam_pitch = float(state.get("pitch", self._cam_pitch))
            self._update_camera()
        except Exception:
            pass

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
        self._sync_sky_to_camera()
        self._update_label_scales()
        self._update_axis_gizmo_transforms()

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
        try:
            darken_alpha = 150
            tmp_dir = Path(tempfile.gettempdir()) / "fl_atlas"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            dst_path = tmp_dir / f"star-background-dark-a{darken_alpha}.png"
            if dst_path.exists() and dst_path.stat().st_mtime >= src_path.stat().st_mtime:
                return dst_path
            img = QImage(str(src_path))
            if img.isNull():
                return src_path
            out = img.convertToFormat(QImage.Format_ARGB32)
            p = QPainter(out)
            p.fillRect(out.rect(), QColor(0, 0, 0, darken_alpha))
            p.end()
            if out.save(str(dst_path), "PNG"):
                return dst_path
        except Exception:
            pass
        return src_path

    def _sync_sky_to_camera(self):
        if self._sky_transform is None:
            return
        try:
            cam_pos = self._camera.position()
            self._sky_transform.setTranslation(QVector3D(cam_pos.x(), cam_pos.y(), cam_pos.z()))
        except Exception:
            pass

    def _update_label_scales(self):
        if not QT3D_AVAILABLE:
            return
        cam = getattr(self, "_camera", None)
        if cam is None:
            return
        cam_pos = cam.position()
        for tr in self._obj_label_tr.values():
            try:
                lp = tr.translation()
                dist = float((lp - cam_pos).length())
                s = max(self._label_scale_min, min(self._label_scale_max, dist * self._label_scale_factor))
                tr.setScale(float(s))
            except Exception:
                pass

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
        try:
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
        except KeyboardInterrupt:
            app = QApplication.instance()
            if app is not None:
                app.quit()
            return True

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
        self._obj_by_nick.clear()
        self._obj_component_refs.clear()
        self._obj_label_ent.clear()
        self._obj_label_tr.clear()
        self._obj_label_yoff.clear()
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
        self._clear_axis_gizmo()

    def set_data(self, objects, zones, scale: float):
        """Baut die 3D-Szene aus Objekt- und Zonenlisten auf."""
        if not QT3D_AVAILABLE:
            return
        self._scene_scale = float(scale)
        self.clear_scene()
        self._obj_by_nick = {
            str(getattr(o, "nickname", "")).strip().lower(): o
            for o in objects
            if str(getattr(o, "nickname", "")).strip()
        }

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

    @staticmethod
    def _sun_palette(arch: str, name: str) -> tuple[QColor, QColor, QColor]:
        s = f"{arch} {name}".lower()
        # core, inner glow, outer glow
        if any(k in s for k in ("blue", "blu", "aqua")):
            return QColor(168, 214, 255), QColor(130, 190, 255, 170), QColor(86, 150, 255, 120)
        if any(k in s for k in ("red", "rdd", "orange")):
            return QColor(255, 168, 96), QColor(255, 140, 82, 170), QColor(255, 108, 58, 120)
        if any(k in s for k in ("white", "wht")):
            return QColor(255, 244, 214), QColor(255, 220, 170, 170), QColor(255, 188, 126, 120)
        return QColor(255, 202, 102), QColor(255, 178, 82, 170), QColor(255, 148, 56, 120)

    @staticmethod
    def _planet_palette(arch: str, name: str) -> tuple[QColor, QColor]:
        s = f"{arch} {name}".lower()
        # base color, cloud/atmosphere color
        if "earthgrncld" in s or "earth" in s:
            return QColor(76, 146, 118), QColor(228, 238, 246, 100)
        if any(k in s for k in ("desored", "desert", "rock", "lava")):
            return QColor(176, 108, 74), QColor(220, 176, 142, 72)
        if any(k in s for k in ("icemoon", "ice", "frozen")):
            return QColor(164, 194, 226), QColor(230, 240, 252, 88)
        if any(k in s for k in ("gas", "jupiter", "storm")):
            return QColor(196, 154, 118), QColor(226, 208, 180, 70)
        if any(k in s for k in ("volcan", "molten")):
            return QColor(178, 90, 70), QColor(232, 150, 110, 64)
        return QColor(92, 138, 212), QColor(220, 232, 252, 86)

    def _make_torus_mesh(self, radius: float, minor: float, rings: int = 52, slices: int = 24):
        extras_ns = getattr(Qt3DExtras, "Qt3DExtras", Qt3DExtras)
        torus_cls = getattr(extras_ns, "QTorusMesh", None)
        if torus_cls is None:
            return None
        mesh = torus_cls()
        try:
            mesh.setRadius(float(radius))
            mesh.setMinorRadius(float(minor))
            mesh.setRings(int(rings))
            mesh.setSlices(int(slices))
        except Exception:
            return None
        return mesh

    def _make_phong(self, color: QColor, ambient_lighter: int = 155):
        mat = QPhongMaterial3D(self._root)
        mat.setDiffuse(color)
        try:
            mat.setAmbient(color.lighter(ambient_lighter))
        except Exception:
            pass
        return mat

    def _make_alpha(self, color: QColor, alpha: float):
        mat = QPhongAlphaMaterial3D(self._root)
        mat.setAlpha(float(alpha))
        mat.setDiffuse(color)
        try:
            mat.setAmbient(color)
        except Exception:
            pass
        return mat

    @staticmethod
    def _extract_arch_size(arch: str, default: float) -> float:
        m = re.search(r"_(\d+)(?:\D*$|$)", str(arch))
        if not m:
            return float(default)
        try:
            return float(m.group(1))
        except Exception:
            return float(default)

    @classmethod
    def _scaled_radius_from_arch(cls, arch: str, default_size: float, base_size: float, base_radius: float, min_r: float, max_r: float) -> float:
        size = cls._extract_arch_size(arch, default_size)
        ratio = max(0.25, size / max(1.0, base_size))
        return max(min_r, min(max_r, base_radius * (ratio ** 0.5)))

    @staticmethod
    def _parse_rotate(raw: str) -> tuple[float, float, float]:
        parts = [p.strip() for p in str(raw).split(",")]
        vals: list[float] = []
        for i in range(3):
            try:
                vals.append(float(parts[i]) if i < len(parts) else 0.0)
            except Exception:
                vals.append(0.0)
        return vals[0], vals[1], vals[2]

    @staticmethod
    def _rotation_quaternion_from_fl(rx: float, ry: float, rz: float) -> QQuaternion:
        # FL data often stores yaw-only objects as (-180, Y, -180). In Qt's Euler conversion this
        # pattern maps to a different facing than in-game. Normalize to the equivalent viewer form.
        tol = 0.25
        rx_f = float(rx)
        ry_f = float(ry)
        rz_f = float(rz)
        if abs(abs(rx_f) - 180.0) <= tol and abs(abs(rz_f) - 180.0) <= tol:
            rx_f = 0.0
            ry_f = -ry_f
            rz_f = 0.0
            if ry_f > 180.0:
                ry_f -= 360.0
            elif ry_f < -180.0:
                ry_f += 360.0
        return QQuaternion.fromEulerAngles(rx_f, ry_f, rz_f)

    @staticmethod
    def _parse_pos(raw: str) -> tuple[float, float, float]:
        parts = [p.strip() for p in str(raw).split(",")]
        vals: list[float] = []
        for i in range(3):
            try:
                vals.append(float(parts[i]) if i < len(parts) else 0.0)
            except Exception:
                vals.append(0.0)
        return vals[0], vals[1], vals[2]

    @staticmethod
    def _is_trade_lane_obj(obj) -> bool:
        arch = str(obj.data.get("archetype", "")).lower()
        name = str(obj.nickname).lower()
        return any(tag in name or tag in arch for tag in ("trade_lane_ring", "tradelane_ring"))

    def _tradelane_direction_quaternion(self, obj) -> QQuaternion | None:
        """Berechnet die Ring-Ausrichtung aus prev/next-Ring, falls verfügbar."""
        prev_nick = str(obj.data.get("prev_ring", "")).strip().lower()
        next_nick = str(obj.data.get("next_ring", "")).strip().lower()
        prev_obj = self._obj_by_nick.get(prev_nick)
        next_obj = self._obj_by_nick.get(next_nick)
        if prev_obj is None and next_obj is None:
            return None

        cur = QVector3D(*self._parse_pos(obj.data.get("pos", "0,0,0")))
        if prev_obj is not None and next_obj is not None:
            prev = QVector3D(*self._parse_pos(prev_obj.data.get("pos", "0,0,0")))
            nxt = QVector3D(*self._parse_pos(next_obj.data.get("pos", "0,0,0")))
            direction = nxt - prev
        elif next_obj is not None:
            nxt = QVector3D(*self._parse_pos(next_obj.data.get("pos", "0,0,0")))
            direction = nxt - cur
        else:
            prev = QVector3D(*self._parse_pos(prev_obj.data.get("pos", "0,0,0")))
            direction = cur - prev

        if direction.length() < 1e-6:
            return None
        direction = direction.normalized()
        yaw_deg = math.degrees(math.atan2(direction.x(), direction.z()))
        flat_len = math.sqrt(direction.x() * direction.x() + direction.z() * direction.z())
        pitch_deg = -math.degrees(math.atan2(direction.y(), flat_len))
        return QQuaternion.fromEulerAngles(float(pitch_deg), float(yaw_deg), 0.0)

    def _rotation_quaternion_for_object(self, obj) -> QQuaternion:
        if self._is_trade_lane_obj(obj):
            q = self._tradelane_direction_quaternion(obj)
            if q is not None:
                return q
        rx, ry, rz = self._parse_rotate(obj.data.get("rotate", "0,0,0"))
        return self._rotation_quaternion_from_fl(rx, ry, rz)

    def _create_object_entity(self, obj, scale: float):
        arch = obj.data.get("archetype", "").lower()
        name = obj.nickname.lower()
        is_trade_lane = any(tag in name or tag in arch for tag in ("trade_lane_ring", "tradelane_ring"))
        is_dock_ring = arch.strip() == "dock_ring"
        is_sun = any(x in arch for x in ("sun", "star"))
        is_planet = "planet" in arch
        is_jump_gate = any(x in arch for x in ("jumpgate", "jump_gate", "jumppoint_gate", "nomad_gate"))
        is_jump_hole = any(x in arch for x in ("jumphole", "jump_hole"))
        is_platform = (
            arch in {"wplatform", "small_wplatform"}
            or "platform" in arch
            or arch == "mplatform"
        )
        is_buoy_like = arch.endswith("buoy") or "buoy" in arch
        is_asteroid_like = arch.startswith("ast_")
        is_debris_like = "debris" in arch
        is_miner_like = "miner" in arch or arch.startswith("miningbase")
        is_nomad_structure = arch in {
            "dyson",
            "dyson_airlock",
            "dyson_airlock_inside",
            "dyson_city",
            "fuchu_core",
            "lair",
            "lair_core",
            "lair_platform",
            "co_base_ice_large02",
            "co_base_rock_large01",
            "co_base_rock_large02",
        }
        is_station_like = arch in {
            "shipyard",
            "space_factory01",
            "space_industrial",
            "space_shipping02",
            "space_port_dmg",
            "smallstation1",
            "largestation1",
            "outpost",
            "ithaca_station",
            "miningbase_badlands",
            "docking_fixture",
        } or arch.startswith("space_") or "station" in arch or arch.endswith("_base")
        is_prison = arch == "prison"
        is_tank_like = (
            arch in {"space_tankl4", "space_tankl4_dmg", "space_habitat_dmg"}
            or arch.startswith("space_tank")
            or arch.startswith("space_tanks")
            or "tank" in arch
            or "habitat" in arch
        )
        is_depot_like = arch.startswith("depot")
        is_capship = (
            arch in {"l_dreadnought", "l_dreadnought_nodock"}
            or "battleship" in arch
            or "cruiser" in arch
            or "dreadnought" in arch
        )
        is_transport = (
            arch == "large_transport"
            or "transport" in arch
            or "freighter" in arch
            or "liner" in arch
            or "train" in arch
            or arch == "hispania_sleeper_ship"
        )
        is_surprise_ship = arch.startswith("suprise_")
        is_hazard = arch == "blhazard" or "hazard" in arch or arch == "neutron_star"

        ent = QEntity3D(self._root)
        tr = QTransform3D()

        # Position
        pparts = [float(c.strip()) for c in obj.data.get("pos", "0,0,0").split(",")]
        fx = pparts[0] if len(pparts) > 0 else 0.0
        fy = pparts[1] if len(pparts) > 1 else 0.0
        fz = pparts[2] if len(pparts) > 2 else (pparts[1] if len(pparts) > 1 else 0.0)
        tr.setTranslation(QVector3D(fx * scale, fy * scale, fz * scale))
        tr.setRotation(self._rotation_quaternion_for_object(obj))

        # Picker
        picker = QObjectPicker3D(ent)
        picker.setHoverEnabled(False)
        picker.clicked.connect(lambda *_a, o=obj: self.object_selected.emit(o))

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
            sun_r = self._scaled_radius_from_arch(arch, default_size=2000.0, base_size=2000.0, base_radius=10.5, min_r=7.5, max_r=17.0)
            label_y_offset = max(label_y_offset, sun_r * 1.75)
            sun_core, sun_glow_in, sun_glow_out = self._sun_palette(arch, name)
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
            p_size = self._extract_arch_size(arch, 1800.0)
            p_r = max(2.5, min(160.0, float(p_size) * float(scale)))
            label_y_offset = max(label_y_offset, p_r * 1.45)
            p_color, cloud_color = self._planet_palette(arch, name)
            planet = QSphereMesh3D()
            planet.setRadius(p_r)
            planet_mat = self._make_phong(p_color, ambient_lighter=132)
            add_part(planet, planet_mat)

            cloud = QSphereMesh3D()
            cloud.setRadius(p_r * 1.05)
            cloud_mat = self._make_alpha(cloud_color, 0.16)
            add_part(cloud, cloud_mat)
        elif is_jump_gate:
            label_y_offset = max(label_y_offset, 5.2)
            gate_radius = 5.7
            add_portal_ring(gate_radius, 0.86, QColor(154, 164, 186), segments=14)
            add_portal_ring(gate_radius * 1.18, 0.42, QColor(116, 126, 152), segments=16)

            for i in range(6):
                spoke_mesh = QCuboidMesh3D()
                spoke_mesh.setXExtent(0.36)
                spoke_mesh.setYExtent(0.30)
                spoke_mesh.setZExtent(gate_radius * 0.95)
                spoke_mat = self._make_phong(QColor(108, 116, 142), ambient_lighter=132)
                spoke_tr = QTransform3D()
                spoke_tr.setTranslation(QVector3D(0.0, 0.0, gate_radius * 0.58))
                spoke_tr.setRotation(QQuaternion.fromAxisAndAngle(1.0, 0.0, 0.0, float(i * 60)))
                add_part(spoke_mesh, spoke_mat, spoke_tr)

            core_mesh = QSphereMesh3D()
            core_mesh.setRadius(1.55)
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
            ring_radius = 3.0 if is_trade_lane else 3.4
            ring_tube = 0.56 if is_trade_lane else 0.62
            # Explicit portal ring geometry, always upright/fly-through.
            add_portal_ring(ring_radius, ring_tube, QColor(74, 162, 255), segments=8 if is_trade_lane else 10)

            if not is_trade_lane:
                # Dock ring can keep a center hub; trade lanes skip this for performance.
                hub_mesh = QSphereMesh3D()
                hub_mesh.setRadius(0.8)
                hub_mat = self._make_phong(QColor(150, 170, 198), ambient_lighter=140)
                add_part(hub_mesh, hub_mat)
                add_forward_markers(z_front=ring_radius + 0.95, z_back=-(ring_radius + 0.95), size=0.5)
        elif is_buoy_like:
            label_y_offset = max(label_y_offset, 2.2)
            post_mesh = QCylinderMesh3D()
            post_mesh.setRadius(0.18 if "nav" in arch else 0.22)
            post_mesh.setLength(2.2 if "m10" in arch else 2.8)
            post_mat = self._make_phong(QColor(190, 188, 138) if "nav" in arch else QColor(170, 170, 185), ambient_lighter=132)
            add_part(post_mesh, post_mat)

            top_mesh = QSphereMesh3D()
            top_mesh.setRadius(0.42 if "gravity" in arch else 0.36)
            top_col = QColor(115, 185, 255)
            if "hazard" in arch:
                top_col = QColor(255, 118, 88)
            elif "nav" in arch:
                top_col = QColor(240, 208, 112)
            top_mat = self._make_alpha(top_col, 0.35)
            top_tr = QTransform3D()
            top_tr.setTranslation(QVector3D(0.0, 1.35, 0.0))
            add_part(top_mesh, top_mat, top_tr)
        elif is_platform:
            label_y_offset = max(label_y_offset, 3.2)
            core_mesh = QCylinderMesh3D()
            core_mesh.setRadius(0.88 if arch == "small_wplatform" else 1.12)
            core_mesh.setLength(2.6 if arch == "small_wplatform" else 3.5)
            core_mat = self._make_phong(QColor(122, 136, 160), ambient_lighter=136)
            add_part(core_mesh, core_mat)

            arms = 3 if arch == "small_wplatform" else 4
            arm_len = 3.6 if arch == "small_wplatform" else 4.5
            for i in range(arms):
                arm_mesh = QCuboidMesh3D()
                arm_mesh.setXExtent(0.28)
                arm_mesh.setYExtent(0.28)
                arm_mesh.setZExtent(arm_len)
                arm_mat = self._make_phong(QColor(102, 116, 142), ambient_lighter=132)
                arm_tr = QTransform3D()
                arm_tr.setRotation(QQuaternion.fromAxisAndAngle(0.0, 1.0, 0.0, float(i * (360.0 / arms))))
                add_part(arm_mesh, arm_mat, arm_tr)
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
            hub.setRadius(1.1)
            hub_mat = self._make_phong(QColor(126, 136, 148), ambient_lighter=132)
            add_part(hub, hub_mat)

            for i in range(4):
                arm_mesh = QCylinderMesh3D()
                arm_mesh.setRadius(0.16)
                arm_mesh.setLength(2.3)
                arm_mat = self._make_phong(QColor(104, 116, 136), ambient_lighter=128)
                arm_tr = QTransform3D()
                arm_tr.setTranslation(QVector3D(0.0, 0.0, 1.35))
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
            body_mesh = QCuboidMesh3D()
            body_mesh.setXExtent(2.5)
            body_mesh.setYExtent(2.3)
            body_mesh.setZExtent(6.2)
            body_mat = self._make_phong(QColor(126, 138, 160), ambient_lighter=136)
            add_part(body_mesh, body_mat)

            side_offsets = (QVector3D(2.2, 0.0, 0.0), QVector3D(-2.2, 0.0, 0.0))
            for off in side_offsets:
                mod_mesh = QCylinderMesh3D()
                mod_mesh.setRadius(0.86)
                mod_mesh.setLength(2.9)
                mod_mat = self._make_phong(QColor(104, 118, 145), ambient_lighter=132)
                mod_tr = QTransform3D()
                mod_tr.setTranslation(off)
                mod_tr.setRotation(QQuaternion.fromAxisAndAngle(0.0, 0.0, 1.0, 90.0))
                add_part(mod_mesh, mod_mat, mod_tr)
        elif is_tank_like:
            label_y_offset = max(label_y_offset, 3.4)
            tank_mesh = QCylinderMesh3D()
            tank_mesh.setRadius(1.35 if "dmg" not in arch else 1.2)
            tank_mesh.setLength(4.2)
            tank_mat = self._make_phong(QColor(112, 128, 145) if "dmg" not in arch else QColor(86, 94, 108), ambient_lighter=128)
            tank_tr = QTransform3D()
            tank_tr.setRotation(QQuaternion.fromAxisAndAngle(1.0, 0.0, 0.0, 90.0))
            add_part(tank_mesh, tank_mat, tank_tr)

            for off in (QVector3D(1.7, 0.0, 0.0), QVector3D(-1.7, 0.0, 0.0)):
                small_mesh = QSphereMesh3D()
                small_mesh.setRadius(0.62)
                small_mat = self._make_phong(QColor(102, 116, 136), ambient_lighter=126)
                small_tr = QTransform3D()
                small_tr.setTranslation(off)
                add_part(small_mesh, small_mat, small_tr)
        elif is_depot_like:
            label_y_offset = max(label_y_offset, 2.7)
            # Kompakter Tank-/Container-Cluster.
            for off, rad in (
                (QVector3D(0.0, 0.0, 0.0), 0.9),
                (QVector3D(1.45, 0.0, 0.45), 0.62),
                (QVector3D(-1.35, 0.2, -0.35), 0.56),
                (QVector3D(0.35, -0.15, -1.25), 0.48),
            ):
                dep_mesh = QSphereMesh3D()
                dep_mesh.setRadius(rad)
                dep_mat = self._make_phong(QColor(138, 118, 96), ambient_lighter=132)
                dep_tr = QTransform3D()
                dep_tr.setTranslation(off)
                add_part(dep_mesh, dep_mat, dep_tr)
        elif is_capship or is_transport or is_surprise_ship:
            label_y_offset = max(label_y_offset, 3.4)
            hull_mesh = QCylinderMesh3D()
            hull_mesh.setRadius(0.62 if is_surprise_ship else (0.95 if is_transport else 1.35))
            hull_mesh.setLength(6.8 if is_surprise_ship else (8.6 if is_transport else 12.4))
            hull_mat = self._make_phong(QColor(116, 130, 152), ambient_lighter=136)
            hull_tr = QTransform3D()
            hull_tr.setRotation(QQuaternion.fromAxisAndAngle(1.0, 0.0, 0.0, 90.0))
            add_part(hull_mesh, hull_mat, hull_tr)

            nose_mesh = QConeMesh3D() if QConeMesh3D is not None else QCylinderMesh3D()
            if QConeMesh3D is not None:
                nose_mesh.setLength(1.9 if is_surprise_ship else 2.5)
                nose_mesh.setBottomRadius(0.55 if is_surprise_ship else 0.85)
                try:
                    nose_mesh.setTopRadius(0.02)
                except Exception:
                    pass
            else:
                nose_mesh.setLength(1.6)
                nose_mesh.setRadius(0.52)
            nose_mat = self._make_phong(QColor(142, 154, 172), ambient_lighter=134)
            nose_tr = QTransform3D()
            nose_tr.setTranslation(QVector3D(0.0, 0.0, 3.9 if is_surprise_ship else (4.9 if is_transport else 6.8)))
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
                mesh.setRadius(3.5)
            elif any(x in arch for x in ("base", "station")):
                mesh.setRadius(3.5)
            else:
                mesh.setRadius(2.8)
            mat = self._make_phong(self._obj_color(obj), ambient_lighter=165)
            base_ent = QEntity3D(sphere_ent)
            base_ent.addComponent(mesh)
            base_ent.addComponent(mat)
            component_refs.extend([base_ent, mesh, mat])

        ent.addComponent(tr)
        ent.addComponent(picker)

        show_label = (not is_trade_lane) and (not is_buoy_like)
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
    @staticmethod
    def _zone_color(zone) -> QColor:
        n = zone.nickname.lower()
        d = zone.data
        dmg = 0.0
        try:
            dmg = float(str(d.get("damage", "")).strip() or "0")
        except Exception:
            dmg = 0.0
        if "death" in n or dmg > 0.0:
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
        rx, ry, rz = self._parse_rotate(zone.data.get("rotate", "0,0,0"))
        if shape == "CYLINDER":
            # Match 2D orientation exactly: cylinders are aligned by yaw in XZ plane.
            # Legacy patrol/path form "90, Y, -180" uses mirrored yaw in 2D.
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
            tr.setRotation(self._rotation_quaternion_from_fl(rx, ry, rz))

        ent.addComponent(mesh)
        ent.addComponent(mat)
        ent.addComponent(tr)
        return ent, tr, [mesh, mat, tr]

    # ==================================================================
    #  Auswahl
    # ==================================================================
    def set_selected(self, obj):
        if not QT3D_AVAILABLE:
            return
        new_obj = obj if obj in self._obj_map else None
        if new_obj is not None and new_obj is self._selected_obj:
            return
        flight_active = bool(getattr(self, "_flight", None) and self._flight.active)
        self._selected_obj = new_obj
        self._locked_axis = None
        if self._selected_obj is None:
            self._clear_axis_gizmo()
            return
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

    def set_item_visibility(self, item, visible: bool):
        """Einzelnes 2D-Item (Objekt oder Zone) in der 3D-Ansicht ein-/ausblenden."""
        if not QT3D_AVAILABLE:
            return
        enabled = bool(visible)
        entry_obj = self._obj_map.get(item)
        if entry_obj:
            ent, _tr = entry_obj
            try:
                ent.setEnabled(enabled)
            except Exception:
                pass
            lbl = self._obj_label_ent.get(item)
            if lbl is not None:
                try:
                    lbl.setEnabled(enabled and self._labels_visible)
                except Exception:
                    pass
            return
        entry_zone = self._zone_map.get(item)
        if entry_zone:
            ent, _tr = entry_zone
            try:
                ent.setEnabled(enabled)
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
        lbl_tr = self._obj_label_tr.get(obj)
        if lbl_tr is not None:
            yoff = float(self._obj_label_yoff.get(obj, 3.8))
            lbl_tr.setTranslation(QVector3D(fx * scale + 1.0, fy * scale + yoff, fz * scale + 1.0))
            self._update_label_scales()
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

    def update_object_rotation(self, obj):
        if not QT3D_AVAILABLE or obj not in self._obj_map:
            return
        _ent, tr = self._obj_map[obj]
        tr.setRotation(self._rotation_quaternion_for_object(obj))

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
        self._axis_gizmo_nodes.clear()
        self._axis_gizmo_center = None
        if self._locked_axis is not None:
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
        refs: list[Any] = []
        try:
            render_ns = getattr(Qt3DRender, "Qt3DRender", Qt3DRender)
            depth_cls = getattr(render_ns, "QDepthTest", None)
            if depth_cls is None:
                return refs
            no_depth_mask_cls = getattr(render_ns, "QNoDepthMask", None)
            effect = material.effect() if hasattr(material, "effect") else None
            if effect is None:
                return refs
            techniques = effect.techniques() if hasattr(effect, "techniques") else []
            for tech in list(techniques):
                passes = tech.renderPasses() if hasattr(tech, "renderPasses") else []
                for rpass in list(passes):
                    depth_state = depth_cls(rpass)
                    depth_fn = getattr(depth_cls, "Always", None)
                    if depth_fn is None:
                        enum_cls = getattr(depth_cls, "DepthFunction", None)
                        depth_fn = getattr(enum_cls, "Always", None) if enum_cls is not None else None
                    if depth_fn is not None and hasattr(depth_state, "setDepthFunction"):
                        depth_state.setDepthFunction(depth_fn)
                    if hasattr(rpass, "addRenderState"):
                        rpass.addRenderState(depth_state)
                        refs.append(depth_state)
                        if no_depth_mask_cls is not None:
                            ndm = no_depth_mask_cls(rpass)
                            rpass.addRenderState(ndm)
                            refs.append(ndm)
        except Exception:
            return refs
        return refs

    def _update_axis_gizmo_transforms(self):
        """Hält den Gizmo sichtbar: leicht zur Kamera versetzt und mit Zoom skaliert."""
        if self._axis_gizmo_center is None or not self._axis_gizmo_nodes:
            return
        try:
            cam_pos = self._camera.position()
        except Exception:
            return
        center = self._axis_gizmo_center
        cam_vec = cam_pos - center
        if cam_vec.length() < 1e-6:
            cam_dir = QVector3D(0.0, 0.0, 1.0)
            cam_dist = 1.0
        else:
            cam_dist = float(cam_vec.length())
            cam_dir = cam_vec.normalized()
        gizmo_scale = max(1.0, min(6.0, cam_dist / 260.0))
        arm_len = 20.0 * gizmo_scale
        camera_bias = cam_dir * (7.0 * gizmo_scale)
        for _axis, (tr, axis_dir, rotation) in self._axis_gizmo_nodes.items():
            try:
                tr.setTranslation(center + camera_bias + axis_dir * arm_len)
                tr.setRotation(rotation)
                tr.setScale(gizmo_scale)
            except Exception:
                pass

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
            self._flight_help_overlay.setVisible(False)
            self._reset_dust_distribution()
            self._reposition_flight_overlays()
        else:
            self._flight.stop()
            self._sync_orbit_state_from_camera()
            self._flight_help_overlay.setVisible(False)
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
        if snapshot is None:
            if self._flight_ship_entity is not None:
                self._flight_ship_entity.setEnabled(False)
            for ent in self._dust_entities:
                ent.setEnabled(False)
            self._flight_charge_bar.setVisible(False)
            return
        if self._flight_ship_entity is not None:
            self._flight_ship_entity.setEnabled(True)
            self._update_flight_ship_pose(snapshot)
        self._update_space_dust(snapshot)
        self._update_cruise_charge_bar(snapshot)

    def _update_flight_ship_pose(self, snapshot: dict[str, Any]):
        if self._flight_ship_tr is None:
            return
        try:
            x, y, z = snapshot.get("pos", (0.0, 0.0, 0.0))
            yaw_deg = float(snapshot.get("yaw_deg", 0.0))
            pitch_deg = float(snapshot.get("pitch_deg", 0.0))
            tilt_deg = float(snapshot.get("ship_tilt_deg", 0.0))
            # Render ship camera-near so it stays visible even when large objects/zones
            # intersect the camera->ship segment. Flight physics still use world position.
            pos = None
            cam = getattr(self, "_camera", None)
            if cam is not None:
                cam_pos = cam.position()
                cam_fwd = cam.viewCenter() - cam_pos
                if cam_fwd.length() > 1e-5:
                    cam_fwd = cam_fwd.normalized()
                    pos = cam_pos + cam_fwd * 2.1
            if pos is None:
                scale = float(getattr(self, "_scene_scale", 1.0) or 1.0)
                pos = QVector3D(float(x) * scale, float(y) * scale, float(z) * scale)
            self._flight_ship_tr.setTranslation(pos)
            self._flight_ship_tr.setRotation(QQuaternion.fromEulerAngles(pitch_deg + tilt_deg, yaw_deg, 0.0))
        except Exception:
            pass

    def _update_space_dust(self, snapshot: dict[str, Any]):
        if not self._dust_entities:
            return
        try:
            x, y, z = snapshot.get("pos", (0.0, 0.0, 0.0))
            f = snapshot.get("forward", (0.0, 0.0, 1.0))
            fwd = QVector3D(float(f[0]), float(f[1]), float(f[2]))
            if fwd.length() < 1e-5:
                fwd = QVector3D(0.0, 0.0, 1.0)
            fwd = fwd.normalized()
            world_up = QVector3D(0.0, 1.0, 0.0)
            right = QVector3D.crossProduct(fwd, world_up)
            if right.length() < 1e-5:
                right = QVector3D(1.0, 0.0, 0.0)
            right = right.normalized()
            up = QVector3D.crossProduct(right, fwd).normalized()
            scale = float(getattr(self, "_scene_scale", 1.0) or 1.0)
            ship_world = QVector3D(float(x) * scale, float(y) * scale, float(z) * scale)
            speed = float(snapshot.get("speed", 0.0))
            flow = max(8.0, speed * 0.22)
            dt = 0.016
            for i, tr in enumerate(self._dust_transforms):
                lp = self._dust_local_positions[i]
                lp.setZ(lp.z() - flow * dt)
                if lp.z() < 2.0:
                    lp.setX(random.uniform(-26.0, 26.0))
                    lp.setY(random.uniform(-14.0, 12.0))
                    lp.setZ(random.uniform(130.0, 220.0))
                self._dust_local_positions[i] = lp
                wpos = ship_world + right * lp.x() + up * lp.y() + fwd * lp.z()
                tr.setTranslation(wpos)
                self._dust_entities[i].setEnabled(True)
        except Exception:
            for ent in self._dust_entities:
                ent.setEnabled(False)

    def _update_cruise_charge_bar(self, snapshot: dict[str, Any]):
        _ = snapshot
        self._flight_charge_bar.setVisible(False)

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
        _ = text
        self._flight_overlay.clear()
        self._flight_overlay.setVisible(False)

    def _reposition_flight_overlays(self):
        host = self._container if hasattr(self, "_container") else self
        y = 8
        self._flight_overlay.move(8, y)
        self._flight_charge_bar.setGeometry(8, y + self._flight_overlay.height() + 6, 260, 20)
        if self._flight_help_overlay.isVisible():
            x = max(8, host.width() - self._flight_help_overlay.width() - 8)
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
