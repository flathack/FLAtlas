"""Freelancer-artiger Flight-Mode Controller fuer die 3D-Ansicht."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from PySide6.QtCore import QElapsedTimer, QObject, QPointF, Qt, QTimer
from PySide6.QtGui import QVector3D

from .path_utils import parse_position


class FlightModeController(QObject):
    NORMAL = "NORMAL"
    CRUISE_CHARGING = "CRUISE_CHARGING"
    CRUISE_ACTIVE = "CRUISE_ACTIVE"
    AUTOPILOT = "AUTOPILOT"
    TRADELANE_DOCKING = "TRADELANE_DOCKING"
    TRADELANE_ACTIVE = "TRADELANE_ACTIVE"

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.viewport = None
        self.editor = None
        self.active = False
        self.mode = self.NORMAL

        self.max_speed = 80.0
        self.cruise_speed = 300.0
        self.cruise_charge_time = 4.0
        self.auto_cruise_distance = 9000.0
        self.arrival_radius = 260.0
        self.dock_radius = 450.0
        self.tradelane_speed = 2500.0
        self.yaw_rate_max = math.radians(105.0)
        self.pitch_rate_max = math.radians(92.0)
        self.roll_max = math.radians(18.0)
        self.turn_smoothing = 8.0
        self.accel = 90.0
        self.brake = 160.0

        self.speed = 0.0
        self.yaw = 0.0
        self.pitch = 0.0
        self.roll = 0.0
        self._yaw_rate = 0.0
        self._pitch_rate = 0.0
        self.ship_pos = QVector3D(0.0, 0.0, 0.0)

        self.mouse_pos = QPointF(0.0, 0.0)
        self.mouse_flight_active = False
        self._lmb_down = False
        self._lmb_hold_time = 0.0
        self.steer_activation_delay = 0.18
        self._mouse_strength = 0.0
        self._keys_down: set[int] = set()
        self._shift_down = False
        self._s_hold_time = 0.0

        self._charge_elapsed = 0.0
        self._auto_target = None
        self._target_name = ""
        self._auto_cruise_charging = False
        self._auto_cruise_active = False

        self._lane_points: list[QVector3D] = []
        self._lane_index = 0

        self._elapsed = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._on_tick)
        self.hud_callback = None
        self._KEY_W = int(Qt.Key_W)
        self._KEY_S = int(Qt.Key_S)
        self._KEY_SHIFT = int(Qt.Key_Shift)
        self._KEY_ESC = int(Qt.Key_Escape)
        self._KEY_F2 = int(Qt.Key_F2)
        self._KEY_F3 = int(Qt.Key_F3)
        self._KEY_H = int(Qt.Key_H)

        # Free orbit camera around the ship (toggle with H).
        self._orbit_cam_active = False
        self._orbit_dragging = False
        self._orbit_last_mouse = QPointF(0.0, 0.0)
        self._orbit_yaw = 0.0
        self._orbit_pitch = 0.35
        self._orbit_distance = 95.0
        self._chase_distance_ship_lengths = 1.8

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self, viewport: Any, editor: Any):
        self.viewport = viewport
        self.editor = editor
        self.active = True
        self.mode = self.NORMAL
        self.speed = self.max_speed
        self.mouse_flight_active = False
        self._lmb_down = False
        self._lmb_hold_time = 0.0
        self._keys_down.clear()
        self._shift_down = False
        self._s_hold_time = 0.0
        self._charge_elapsed = 0.0
        self._auto_target = None
        self._target_name = ""
        self._auto_cruise_charging = False
        self._auto_cruise_active = False
        self._lane_points = []
        self._lane_index = 0
        self._orbit_cam_active = False
        self._orbit_dragging = False
        self._load_constants()
        self._seed_from_selection_or_camera()
        self._elapsed.start()
        self._timer.start()
        self._set_overlay("")
        self._emit_hud()

    def stop(self):
        self.active = False
        self.mode = self.NORMAL
        self.mouse_flight_active = False
        self._keys_down.clear()
        self._shift_down = False
        self._timer.stop()
        self._orbit_cam_active = False
        self._orbit_dragging = False
        self._set_overlay("")
        self._emit_hud()

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def on_key_press(self, event) -> bool:
        if not self.active:
            return False
        key = int(event.key())
        mods = event.modifiers()
        # Cruise als Toggle: Shift+W einmal drücken zum Ein-/Ausschalten.
        if key == self._KEY_W and (mods & Qt.ShiftModifier):
            if self.mode in (self.CRUISE_CHARGING, self.CRUISE_ACTIVE):
                self._set_mode(self.NORMAL)
            elif self.mode not in (self.AUTOPILOT, self.TRADELANE_ACTIVE):
                self._set_mode(self.CRUISE_CHARGING)
            self._emit_hud()
            return True
        self._keys_down.add(key)
        if key == self._KEY_SHIFT:
            self._shift_down = True
            return True
        if key == self._KEY_ESC:
            if self.editor and hasattr(self.editor, "_set_flight_mode"):
                self.editor._set_flight_mode(False)
            return True
        if key == self._KEY_F2:
            self._start_autopilot()
            return True
        if key == self._KEY_F3:
            self._start_tradelane()
            return True
        if key == self._KEY_H:
            self._toggle_orbit_camera()
            self._emit_hud()
            return True
        if self.mode == self.TRADELANE_DOCKING and key in (self._KEY_W, self._KEY_S):
            self._set_mode(self.NORMAL)
            self._emit_hud()
            return True
        if self.mode == self.TRADELANE_ACTIVE:
            return True
        if key in (self._KEY_W, self._KEY_S):
            return True
        return False

    def on_key_release(self, event) -> bool:
        if not self.active:
            return False
        key = int(event.key())
        self._keys_down.discard(key)
        if key == self._KEY_SHIFT:
            self._shift_down = False
            return True
        if key in (self._KEY_W, self._KEY_S):
            return True
        return False

    def on_mouse_press(self, event):
        if not self.active:
            return
        if event.button() == Qt.LeftButton:
            if self._orbit_cam_active:
                self._orbit_dragging = True
                self._orbit_last_mouse = event.position()
                self._lmb_down = False
                self.mouse_flight_active = False
                return
            self._lmb_down = True
            self._lmb_hold_time = 0.0
            self.mouse_flight_active = False
            self.mouse_pos = event.position()

    def on_mouse_release(self, event):
        if not self.active:
            return
        if event.button() == Qt.LeftButton:
            if self._orbit_cam_active:
                self._orbit_dragging = False
                return
            self._lmb_down = False
            self._lmb_hold_time = 0.0
            self.mouse_flight_active = False
            self._mouse_strength = 0.0

    def on_mouse_move(self, event):
        if not self.active:
            return
        if self._orbit_cam_active:
            pos = event.position()
            if self._orbit_dragging:
                d = pos - self._orbit_last_mouse
                self._orbit_last_mouse = pos
                self._orbit_yaw -= float(d.x()) * 0.008
                self._orbit_pitch = max(-1.35, min(1.35, self._orbit_pitch + float(d.y()) * 0.008))
            return
        self.mouse_pos = event.position()

    def on_wheel(self, event):
        if not self.active or not self._orbit_cam_active:
            return
        delta = float(event.angleDelta().y())
        zoom = 0.86 if delta > 0.0 else 1.14
        self._orbit_distance = max(20.0, min(1200.0, self._orbit_distance * zoom))

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def _on_tick(self):
        if not self.active:
            return
        dt_ms = self._elapsed.restart()
        if dt_ms <= 0:
            return
        dt = max(0.001, min(0.05, dt_ms / 1000.0))
        try:
            self.update(dt)
            self._emit_hud()
        except Exception as ex:
            self._set_overlay(f"Flight error: {ex}")
            self._emit_hud(error=str(ex))
            self.stop()

    def update(self, dt: float):
        if not self.active or self.viewport is None:
            return
        if self.mode == self.TRADELANE_ACTIVE:
            self._update_tradelane(dt)
            self._apply_camera_pose()
            return
        if self.mode == self.TRADELANE_DOCKING:
            self._update_tradelane_docking(dt)
            self._apply_camera_pose()
            return

        if self._lmb_down and not self.mouse_flight_active:
            self._lmb_hold_time += dt
            if self._lmb_hold_time >= self.steer_activation_delay:
                self.mouse_flight_active = True

        w_down = self._KEY_W in self._keys_down
        s_down = self._KEY_S in self._keys_down
        self._s_hold_time = self._s_hold_time + dt if s_down else 0.0

        offset_x, offset_y, strength = self._mouse_offset()
        self._mouse_strength = strength

        if self.mode == self.AUTOPILOT:
            if w_down or s_down or self.mouse_flight_active:
                self._set_mode(self.NORMAL)
            else:
                self._update_autopilot(dt)

        if self.mode != self.AUTOPILOT:
            self._update_manual_turn(dt, offset_x, offset_y)

        if self.mode == self.CRUISE_CHARGING:
            self._charge_elapsed += dt
            if self._should_abort_cruise():
                self._set_mode(self.NORMAL)
            elif self._charge_elapsed >= self.cruise_charge_time:
                self._set_mode(self.CRUISE_ACTIVE)
        elif self.mode == self.CRUISE_ACTIVE:
            if self._should_abort_cruise():
                self._set_mode(self.NORMAL)

        if self.mode not in (self.AUTOPILOT, self.TRADELANE_ACTIVE):
            if self.mode == self.CRUISE_ACTIVE:
                self.speed = min(self.cruise_speed, self.speed + self.accel * dt)
            elif self.mode == self.NORMAL:
                # Freiflug: Geschwindigkeit bleibt nach Bremsen erhalten.
                # Nur W beschleunigt, S bremst.
                if w_down and not s_down:
                    self.speed = min(self.max_speed, self.speed + self.accel * dt)
                if s_down:
                    self.speed = max(0.0, self.speed - self.brake * dt)
            else:
                if w_down and not s_down:
                    self.speed = min(self.max_speed, self.speed + self.accel * dt)
                if s_down:
                    self.speed = max(0.0, self.speed - self.brake * dt)

        fwd = self._forward_vector()
        self.ship_pos += fwd * (self.speed * dt)
        self._apply_camera_pose()

    # ------------------------------------------------------------------
    # Modes
    # ------------------------------------------------------------------
    def _set_mode(self, mode: str):
        self.mode = mode
        if mode != self.AUTOPILOT:
            self._auto_cruise_charging = False
            self._auto_cruise_active = False
        if mode == self.CRUISE_CHARGING:
            self._charge_elapsed = 0.0
        if mode == self.NORMAL:
            self._charge_elapsed = 0.0
            self.speed = max(0.0, min(self.speed, self.max_speed))

    def _should_abort_cruise(self) -> bool:
        if self.mode not in (self.CRUISE_CHARGING, self.CRUISE_ACTIVE):
            return False
        # Cruise bleibt aktiv bis explizit beendet (Shift+W) oder über Bremsen (S).
        if self._s_hold_time > 0.2:
            return True
        return False

    def _start_autopilot(self):
        if not self.editor:
            return
        target = getattr(self.editor, "_selected", None)
        pos = self._item_world_pos(target)
        if pos is None:
            return
        self._auto_target = target
        self._target_name = getattr(target, "nickname", "Target")
        self._set_mode(self.AUTOPILOT)

    def set_free_flight(self):
        if not self.active:
            return
        self._set_mode(self.NORMAL)
        self._lane_points = []
        self._lane_index = 0
        self._auto_target = None
        self._target_name = ""
        self._emit_hud()

    def start_autopilot_to_selection(self):
        if not self.active:
            return
        self._start_autopilot()
        self._emit_hud()

    def start_dock_to_selected_tradelane(self):
        if not self.active:
            return
        self._start_tradelane()
        self._emit_hud()

    def set_chase_distance_ship_lengths(self, value: float):
        try:
            v = float(value)
        except Exception:
            return
        self._chase_distance_ship_lengths = max(0.5, min(8.0, v))

    def get_chase_distance_ship_lengths(self) -> float:
        return float(self._chase_distance_ship_lengths)

    def _update_autopilot(self, dt: float):
        pos = self._item_world_pos(self._auto_target)
        if pos is None:
            self._set_mode(self.NORMAL)
            return
        self._target_name = getattr(self._auto_target, "nickname", "Target")
        to_target = pos - self.ship_pos
        dist = to_target.length()
        if dist <= self.arrival_radius:
            self._set_mode(self.NORMAL)
            return

        dir_n = to_target.normalized()
        desired_yaw = math.atan2(float(dir_n.x()), float(dir_n.z()))
        desired_pitch = math.asin(max(-1.0, min(1.0, float(dir_n.y()))))
        self.yaw = self._approach_angle(self.yaw, desired_yaw, self.yaw_rate_max * dt)
        self.pitch = self._approach(self.pitch, desired_pitch, self.pitch_rate_max * dt)
        self.pitch = max(math.radians(-85.0), min(math.radians(85.0), self.pitch))

        if dist > self.auto_cruise_distance:
            if not self._auto_cruise_active and not self._auto_cruise_charging:
                self._auto_cruise_charging = True
                self._charge_elapsed = 0.0
            if self._auto_cruise_charging:
                self._charge_elapsed += dt
                if self._charge_elapsed >= self.cruise_charge_time:
                    self._auto_cruise_charging = False
                    self._auto_cruise_active = True
        else:
            self._auto_cruise_charging = False
            self._auto_cruise_active = False
            self._charge_elapsed = 0.0

        target_speed = self.cruise_speed if self._auto_cruise_active else self.max_speed
        if dist < self.arrival_radius * 3.0:
            target_speed = min(target_speed, max(20.0, dist * 0.35))
        if self.speed < target_speed:
            self.speed = min(target_speed, self.speed + self.accel * dt)
        else:
            self.speed = max(target_speed, self.speed - self.brake * dt)

    def _start_tradelane(self):
        if not self.editor:
            return
        sel = getattr(self.editor, "_selected", None)
        if not self._is_tradelane(sel):
            return
        lane_path = self._build_lane_path(sel)
        if len(lane_path) < 2:
            return
        self._lane_points = lane_path
        self._lane_index = 0
        lane_start = lane_path[0]
        dist = (lane_start - self.ship_pos).length()
        align = QVector3D.dotProduct(self._forward_vector(), (lane_start - self.ship_pos).normalized()) if dist > 1e-5 else 1.0
        if dist > self.dock_radius or align < 0.55:
            self._set_mode(self.TRADELANE_DOCKING)
            return
        self._lane_index = 1
        self.ship_pos = QVector3D(lane_path[0])
        self.speed = self.tradelane_speed
        self._set_mode(self.TRADELANE_ACTIVE)

    def _update_tradelane_docking(self, dt: float):
        if len(self._lane_points) < 2:
            self._set_mode(self.NORMAL)
            return
        lane_start = self._lane_points[0]
        to_start = lane_start - self.ship_pos
        dist = to_start.length()
        if dist <= self.arrival_radius * 0.65:
            self.ship_pos = QVector3D(lane_start)
            self._lane_index = 1
            self.speed = self.tradelane_speed
            self._set_mode(self.TRADELANE_ACTIVE)
            return
        dir_n = to_start.normalized()
        desired_yaw = math.atan2(float(dir_n.x()), float(dir_n.z()))
        desired_pitch = math.asin(max(-1.0, min(1.0, float(dir_n.y()))))
        self.yaw = self._approach_angle(self.yaw, desired_yaw, self.yaw_rate_max * dt)
        self.pitch = self._approach(self.pitch, desired_pitch, self.pitch_rate_max * dt)
        self.pitch = max(math.radians(-85.0), min(math.radians(85.0), self.pitch))
        # Beschleunigt bis zum Docking-Ring.
        target_speed = min(self.cruise_speed, max(self.max_speed, dist * 0.35))
        if self.speed < target_speed:
            self.speed = min(target_speed, self.speed + self.accel * dt)
        else:
            self.speed = max(target_speed, self.speed - self.brake * dt)
        self.ship_pos += self._forward_vector() * (self.speed * dt)

    def _update_tradelane(self, dt: float):
        if self._lane_index >= len(self._lane_points):
            self._set_mode(self.NORMAL)
            self.speed = min(self.speed, self.max_speed)
            return
        travel = self.tradelane_speed * dt
        while travel > 0.0 and self._lane_index < len(self._lane_points):
            target = self._lane_points[self._lane_index]
            seg = target - self.ship_pos
            seg_len = seg.length()
            if seg_len < 1e-5:
                self._lane_index += 1
                continue
            if travel >= seg_len:
                self.ship_pos = QVector3D(target)
                travel -= seg_len
                self._lane_index += 1
            else:
                dir_n = seg / seg_len
                self.ship_pos += dir_n * travel
                travel = 0.0
            if seg_len > 1e-5:
                dir_n = seg.normalized()
                self.yaw = math.atan2(float(dir_n.x()), float(dir_n.z()))
                self.pitch = math.asin(max(-1.0, min(1.0, float(dir_n.y()))))
        if self._lane_index >= len(self._lane_points):
            self._set_mode(self.NORMAL)
            self.speed = min(self.speed, self.max_speed)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _seed_from_selection_or_camera(self):
        # Startposition: Y=0 und 2000m neben dem ausgewählten Objekt.
        try:
            sel = getattr(self.editor, "_selected", None)
            if sel is not None and not hasattr(sel, "sys_path"):
                fx, _fy, fz = parse_position(getattr(sel, "data", {}).get("pos", "0,0,0"))
                target = QVector3D(float(fx), 0.0, float(fz))
                self.ship_pos = target + QVector3D(2000.0, 0.0, 0.0)
                to_target = target - self.ship_pos
                if to_target.length() < 1e-5:
                    to_target = QVector3D(-1.0, 0.0, 0.0)
                dir_n = to_target.normalized()
                self.yaw = math.atan2(float(dir_n.x()), float(dir_n.z()))
                self.pitch = 0.0
                self.roll = 0.0
                return
        except Exception:
            pass

        self._seed_from_camera()

    def _seed_from_camera(self):
        cam = getattr(self.viewport, "_camera", None)
        scale = float(getattr(self.viewport, "_scene_scale", 1.0) or 1.0)
        if cam is None:
            self.ship_pos = QVector3D(0.0, 0.0, 0.0)
            self.yaw = 0.0
            self.pitch = 0.0
            self.roll = 0.0
            return
        cam_pos = cam.position()
        # Interne Flugkoordinaten in unskalierten Systemeinheiten.
        self.ship_pos = QVector3D(
            float(cam_pos.x()) / scale,
            float(cam_pos.y()) / scale,
            float(cam_pos.z()) / scale,
        )
        fwd = cam.viewCenter() - cam.position()
        if fwd.length() < 1e-5:
            fwd = QVector3D(0.0, 0.0, 1.0)
        fwd = fwd.normalized()
        self.yaw = math.atan2(float(fwd.x()), float(fwd.z()))
        # Aktuelle Blickrichtung übernehmen (verhindert schwarzen Horizont beim Start).
        self.pitch = math.asin(max(-1.0, min(1.0, float(fwd.y()))))
        self.pitch = max(math.radians(-85.0), min(math.radians(85.0), self.pitch))
        self.roll = 0.0

    def _load_constants(self):
        self.cruise_speed = 300.0
        self.cruise_charge_time = 4.0
        if not self.editor:
            return
        game_path = ""
        if hasattr(self.editor, "browser") and hasattr(self.editor.browser, "path_edit"):
            game_path = self.editor.browser.path_edit.text().strip()
        if not game_path and hasattr(self.editor, "_cfg"):
            game_path = self.editor._cfg.get("game_path", "")
        if not game_path:
            return
        base = Path(game_path)
        candidates = [base / "DATA" / "constants.ini", base / "constants.ini", base / "DATA" / "constants" / "constants.ini"]
        ini_path = None
        for p in candidates:
            if p.exists():
                ini_path = p
                break
        if ini_path is None:
            return
        try:
            for line in ini_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                raw = line.strip()
                if "=" not in raw:
                    continue
                k, _, v = raw.partition("=")
                key = k.strip().lower()
                val = v.strip()
                if key in ("cruise_speed", "cruising_speed"):
                    self.cruise_speed = float(val)
                elif key in ("cruise_charge_time", "cruise_charge_delay"):
                    self.cruise_charge_time = float(val)
        except Exception:
            pass

    def _mouse_offset(self) -> tuple[float, float, float]:
        if self.viewport is None:
            return 0.0, 0.0, 0.0
        if not self.mouse_flight_active:
            return 0.0, 0.0, 0.0
        w = max(1, int(self.viewport.width()))
        h = max(1, int(self.viewport.height()))
        center = QPointF(w * 0.5, h * 0.5)
        norm = max(1.0, min(w, h) * 0.5)
        ox = (float(self.mouse_pos.x()) - float(center.x())) / norm
        oy = (float(self.mouse_pos.y()) - float(center.y())) / norm
        ox = max(-1.0, min(1.0, ox))
        oy = max(-1.0, min(1.0, oy))
        dead = 0.05
        if abs(ox) < dead:
            ox = 0.0
        if abs(oy) < dead:
            oy = 0.0
        strength = min(1.0, math.sqrt(ox * ox + oy * oy))
        return ox, oy, strength

    def _update_manual_turn(self, dt: float, ox: float, oy: float):
        # Invertiert, damit "Maus links" auch "Schiff links" bedeutet.
        target_yaw_rate = -ox * self.yaw_rate_max
        target_pitch_rate = -oy * self.pitch_rate_max
        alpha = max(0.0, min(1.0, self.turn_smoothing * dt))
        self._yaw_rate += (target_yaw_rate - self._yaw_rate) * alpha
        self._pitch_rate += (target_pitch_rate - self._pitch_rate) * alpha
        self.yaw += self._yaw_rate * dt
        self.pitch += self._pitch_rate * dt
        self.pitch = max(math.radians(-85.0), min(math.radians(85.0), self.pitch))
        # Kein Roll-Effekt: nur Lenken statt seitlichem "Drehen".
        self.roll = 0.0

    def _forward_vector(self) -> QVector3D:
        cp = math.cos(self.pitch)
        return QVector3D(
            cp * math.sin(self.yaw),
            math.sin(self.pitch),
            cp * math.cos(self.yaw),
        ).normalized()

    def _apply_camera_pose(self):
        if self.viewport is None:
            return
        cam = getattr(self.viewport, "_camera", None)
        if cam is None:
            return
        scale = float(getattr(self.viewport, "_scene_scale", 1.0) or 1.0)
        if self._orbit_cam_active:
            self._apply_orbit_camera_pose(cam, scale)
            return
        fwd = self._forward_vector()
        ship_world = QVector3D(
            float(self.ship_pos.x()) * scale,
            float(self.ship_pos.y()) * scale,
            float(self.ship_pos.z()) * scale,
        )
        # Third-person chase camera: closer and directly behind the ship (no height offset).
        ship_len = 7.2
        cam_pos = ship_world - fwd * (ship_len * self._chase_distance_ship_lengths)
        cam_view = ship_world + fwd * 220.0
        cam.setPosition(cam_pos)
        cam.setViewCenter(cam_view)
        if hasattr(self.viewport, "_sync_sky_to_camera"):
            self.viewport._sync_sky_to_camera()
        if hasattr(self.viewport, "_update_label_scales"):
            self.viewport._update_label_scales()

    def _apply_orbit_camera_pose(self, cam, scale: float):
        center = QVector3D(
            float(self.ship_pos.x()) * scale,
            float(self.ship_pos.y()) * scale,
            float(self.ship_pos.z()) * scale,
        )
        cp = math.cos(self._orbit_pitch)
        dir_vec = QVector3D(
            cp * math.sin(self._orbit_yaw),
            math.sin(self._orbit_pitch),
            cp * math.cos(self._orbit_yaw),
        )
        cam_pos = center + dir_vec * self._orbit_distance
        cam.setPosition(cam_pos)
        cam.setViewCenter(center)
        if hasattr(self.viewport, "_sync_sky_to_camera"):
            self.viewport._sync_sky_to_camera()
        if hasattr(self.viewport, "_update_label_scales"):
            self.viewport._update_label_scales()

    def _toggle_orbit_camera(self):
        if self.viewport is None:
            return
        cam = getattr(self.viewport, "_camera", None)
        scale = float(getattr(self.viewport, "_scene_scale", 1.0) or 1.0)
        if cam is None or scale <= 0.0:
            return
        if not self._orbit_cam_active:
            center = QVector3D(
                float(self.ship_pos.x()) * scale,
                float(self.ship_pos.y()) * scale,
                float(self.ship_pos.z()) * scale,
            )
            pos = cam.position()
            rel = pos - center
            dist = float(rel.length())
            if dist < 1e-4:
                dist = 95.0
                rel = QVector3D(0.0, 0.3, 1.0)
            dir_n = rel / dist
            self._orbit_distance = max(20.0, min(1200.0, dist))
            self._orbit_yaw = math.atan2(float(dir_n.x()), float(dir_n.z()))
            self._orbit_pitch = math.asin(max(-1.0, min(1.0, float(dir_n.y()))))
            self._orbit_cam_active = True
            self._orbit_dragging = False
            self.mouse_flight_active = False
            self._lmb_down = False
        else:
            self._orbit_cam_active = False
            self._orbit_dragging = False
            self.mouse_flight_active = False

    def _set_overlay(self, text: str):
        if self.viewport is not None and hasattr(self.viewport, "set_flight_overlay_text"):
            self.viewport.set_flight_overlay_text(text)

    def _emit_hud(self, error: str | None = None):
        cb = self.hud_callback
        try:
            if not self.active:
                if cb is not None:
                    cb(None)
                if self.viewport is not None and hasattr(self.viewport, "update_flight_visuals"):
                    self.viewport.update_flight_visuals(None)
                return
            snap = self.get_hud_snapshot(error=error)
            if cb is not None:
                cb(snap)
            if self.viewport is not None and hasattr(self.viewport, "update_flight_visuals"):
                self.viewport.update_flight_visuals(snap)
        except Exception:
            pass

    def get_hud_snapshot(self, error: str | None = None) -> dict[str, Any] | None:
        if not self.active:
            return None
        sel_name = ""
        sel_dist = None
        if self.editor is not None:
            sel = getattr(self.editor, "_selected", None)
            sp = self._item_world_pos(sel)
            if sp is not None:
                sel_dist = float((sp - self.ship_pos).length())
                sel_name = str(getattr(sel, "nickname", "Selection"))
        return {
            "mode": self.mode,
            "speed": float(self.speed),
            "max_speed": float(self.max_speed),
            "pos": (float(self.ship_pos.x()), float(self.ship_pos.y()), float(self.ship_pos.z())),
            "yaw_deg": math.degrees(self.yaw),
            "pitch_deg": math.degrees(self.pitch),
            "ship_tilt_deg": max(-16.0, min(16.0, math.degrees(self._pitch_rate) * 0.16)),
            "forward": (float(self._forward_vector().x()), float(self._forward_vector().y()), float(self._forward_vector().z())),
            "target_name": sel_name,
            "target_distance": sel_dist,
            "charge_progress": min(1.0, self._charge_elapsed / max(0.01, self.cruise_charge_time)),
            "charge_active": bool(self.mode == self.CRUISE_CHARGING or (self.mode == self.AUTOPILOT and self._auto_cruise_charging)),
            "orbit_cam_active": bool(self._orbit_cam_active),
            "error": error or "",
        }

    def _overlay_text(self) -> str:
        px = float(self.ship_pos.x())
        py = float(self.ship_pos.y())
        pz = float(self.ship_pos.z())
        lines = [
            f"Flight | {self.mode}",
            f"Speed: {self.speed:.1f} m/s",
            f"Max: {self.max_speed:.0f} m/s",
            f"Pos: X {px:.1f}  Y {py:.1f}  Z {pz:.1f}",
        ]
        if self.editor is not None:
            sel = getattr(self.editor, "_selected", None)
            sp = self._item_world_pos(sel)
            if sp is not None:
                dist = (sp - self.ship_pos).length()
                name = getattr(sel, "nickname", "Selection")
                lines.append(f"Target: {name} | Dist: {dist:.1f} m")
        if self.mode == self.CRUISE_CHARGING:
            p = min(1.0, self._charge_elapsed / max(0.01, self.cruise_charge_time))
            lines.append(f"Cruise Charge: {p * 100.0:.0f}%")
        if self.mode == self.AUTOPILOT and self._auto_cruise_charging:
            p = min(1.0, self._charge_elapsed / max(0.01, self.cruise_charge_time))
            lines.append(f"Auto Cruise Charge: {p * 100.0:.0f}%")
        if self.mode == self.AUTOPILOT and self._auto_cruise_active:
            lines.append("Auto Cruise: ACTIVE")
        if self.mode == self.AUTOPILOT and self._auto_target is not None:
            pos = self._item_world_pos(self._auto_target)
            if pos is not None:
                dist = (pos - self.ship_pos).length()
                lines.append(f"Target: {self._target_name} ({dist:.0f} m)")
        return "\n".join(lines)

    def draw_overlay(self, painter):
        _ = painter

    @staticmethod
    def _approach(cur: float, target: float, max_step: float) -> float:
        d = target - cur
        if abs(d) <= max_step:
            return target
        return cur + max_step * (1.0 if d > 0.0 else -1.0)

    @staticmethod
    def _wrap_pi(a: float) -> float:
        return (a + math.pi) % (2.0 * math.pi) - math.pi

    def _approach_angle(self, cur: float, target: float, max_step: float) -> float:
        d = self._wrap_pi(target - cur)
        if abs(d) <= max_step:
            return target
        return cur + max_step * (1.0 if d > 0.0 else -1.0)

    def _item_world_pos(self, item) -> QVector3D | None:
        if item is None:
            return None
        try:
            fx, fy, fz = parse_position(getattr(item, "data", {}).get("pos", "0,0,0"))
            return QVector3D(fx, fy, fz)
        except Exception:
            return None

    @staticmethod
    def _is_tradelane(item) -> bool:
        if item is None:
            return False
        data = getattr(item, "data", {})
        arch = str(data.get("archetype", "")).lower()
        nick = str(getattr(item, "nickname", "")).lower()
        return ("trade_lane_ring" in arch or "tradelane_ring" in arch or "trade_lane_ring" in nick or "tradelane_ring" in nick)

    def _build_lane_path(self, selected_obj) -> list[QVector3D]:
        if not self.editor:
            return []
        all_objs = list(getattr(self.editor, "_objects", []))
        ring_map: dict[str, Any] = {}
        for obj in all_objs:
            if self._is_tradelane(obj):
                ring_map[obj.nickname.lower()] = obj
        if not ring_map:
            return []

        cur = selected_obj
        seen: set[str] = set()
        while cur:
            prev = str(cur.data.get("prev_ring", "")).strip().lower()
            if not prev or prev in seen or prev not in ring_map:
                break
            seen.add(prev)
            cur = ring_map.get(prev)
        path: list[QVector3D] = []
        seen.clear()
        while cur:
            nl = cur.nickname.lower()
            if nl in seen:
                break
            seen.add(nl)
            pos = self._item_world_pos(cur)
            if pos is not None:
                path.append(pos)
            nxt = str(cur.data.get("next_ring", "")).strip().lower()
            if not nxt or nxt not in ring_map:
                break
            cur = ring_map.get(nxt)
        return path
