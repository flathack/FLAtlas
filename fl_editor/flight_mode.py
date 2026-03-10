"""Freelancer-artiger Flight-Mode Controller fuer die 3D-Ansicht."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from PySide6.QtCore import QElapsedTimer, QObject, QPointF, Qt, QTimer
from PySide6.QtGui import QVector3D

from .flight_mode_camera import (
    forward_vector_xyz,
    mouse_offset_state,
    seeded_flight_state_from_camera,
    toggled_orbit_camera_state,
    updated_manual_turn_state,
)
from .flight_mode_actions import autopilot_selection_state, free_flight_state, should_run_flight_action
from .flight_mode_hud import build_hud_snapshot, build_overlay_text
from .flight_mode_input import key_press_action, key_release_action
from .flight_mode_lifecycle import start_state, stop_state
from .flight_mode_mouse import mouse_move_state, mouse_press_state, mouse_release_state, wheel_state
from .flight_mode_navigation import build_lane_path_tuples, is_tradelane_item, item_world_pos_tuple
from .flight_mode_mode_paths import (
    autopilot_motion_state,
    tradelane_docking_state,
    tradelane_start_state,
    tradelane_travel_state,
)
from .flight_mode_update import (
    autopilot_interrupt_state,
    cruise_update_state,
    drive_input_state,
    steer_activation_state,
    updated_speed,
)
from .flight_mode_state import (
    mode_transition_state,
    normalized_chase_distance_ship_lengths,
    should_abort_cruise,
)
from .flight_mode_viewport import viewport_camera_pose_state
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
        state = start_state(normal_mode=self.NORMAL, max_speed=self.max_speed)
        self.active = bool(state["active"])
        self.mode = str(state["mode"])
        self.speed = float(state["speed"])
        self.mouse_flight_active = bool(state["mouse_flight_active"])
        self._lmb_down = bool(state["lmb_down"])
        self._lmb_hold_time = float(state["lmb_hold_time"])
        if state["clear_keys_down"]:
            self._keys_down.clear()
        self._shift_down = bool(state["shift_down"])
        self._s_hold_time = float(state["s_hold_time"])
        self._charge_elapsed = float(state["charge_elapsed"])
        self._auto_target = state["auto_target"]
        self._target_name = str(state["target_name"])
        self._auto_cruise_charging = bool(state["auto_cruise_charging"])
        self._auto_cruise_active = bool(state["auto_cruise_active"])
        self._lane_points = list(state["lane_points"])
        self._lane_index = int(state["lane_index"])
        self._orbit_cam_active = bool(state["orbit_cam_active"])
        self._orbit_dragging = bool(state["orbit_dragging"])
        self._load_constants()
        self._seed_from_selection_or_camera()
        self._elapsed.start()
        if state["start_timer"]:
            self._timer.start()
        self._set_overlay(str(state["overlay_text"]))
        if state["emit_hud"]:
            self._emit_hud()

    def stop(self):
        state = stop_state(normal_mode=self.NORMAL)
        self.active = bool(state["active"])
        self.mode = str(state["mode"])
        self.mouse_flight_active = bool(state["mouse_flight_active"])
        if state["clear_keys_down"]:
            self._keys_down.clear()
        self._shift_down = bool(state["shift_down"])
        if state["stop_timer"]:
            self._timer.stop()
        self._orbit_cam_active = bool(state["orbit_cam_active"])
        self._orbit_dragging = bool(state["orbit_dragging"])
        self._set_overlay(str(state["overlay_text"]))
        if state["emit_hud"]:
            self._emit_hud()

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def on_key_press(self, event) -> bool:
        if not self.active:
            return False
        key = int(event.key())
        mods = event.modifiers()
        state = key_press_action(
            active=self.active,
            key=key,
            shift_modifier_active=bool(mods & Qt.ShiftModifier),
            mode=self.mode,
            key_w=self._KEY_W,
            key_s=self._KEY_S,
            key_shift=self._KEY_SHIFT,
            key_esc=self._KEY_ESC,
            key_f2=self._KEY_F2,
            key_f3=self._KEY_F3,
            key_h=self._KEY_H,
            normal_mode=self.NORMAL,
            cruise_charging_mode=self.CRUISE_CHARGING,
            cruise_active_mode=self.CRUISE_ACTIVE,
            autopilot_mode=self.AUTOPILOT,
            tradelane_docking_mode=self.TRADELANE_DOCKING,
            tradelane_active_mode=self.TRADELANE_ACTIVE,
        )
        if not state["handled"]:
            return False
        if state.get("add_key", False):
            self._keys_down.add(key)
        if state.get("next_mode") is not None:
            self._set_mode(str(state["next_mode"]))
        if state.get("set_shift_down"):
            self._shift_down = True
        if state.get("disable_flight"):
            if self.editor and hasattr(self.editor, "_set_flight_mode"):
                self.editor._set_flight_mode(False)
            return True
        if state.get("start_autopilot"):
            self._start_autopilot()
            return True
        if state.get("start_tradelane"):
            self._start_tradelane()
            return True
        if state.get("toggle_orbit"):
            self._toggle_orbit_camera()
        if state.get("emit_hud"):
            self._emit_hud()
        return True

    def on_key_release(self, event) -> bool:
        key = int(event.key())
        state = key_release_action(
            active=self.active,
            key=key,
            key_shift=self._KEY_SHIFT,
            key_w=self._KEY_W,
            key_s=self._KEY_S,
        )
        if not state["handled"]:
            return False
        self._keys_down.discard(key)
        if state.get("clear_shift_down"):
            self._shift_down = False
        return True

    def on_mouse_press(self, event):
        state = mouse_press_state(
            active=self.active,
            is_left_button=event.button() == Qt.LeftButton,
            orbit_cam_active=self._orbit_cam_active,
            mouse_pos_xy=(float(event.position().x()), float(event.position().y())),
        )
        if not state["handled"]:
            return
        if state.get("orbit_dragging") is not None:
            self._orbit_dragging = bool(state["orbit_dragging"])
        if state.get("orbit_last_mouse_xy") is not None:
            self._orbit_last_mouse = event.position()
        if state.get("lmb_down") is not None:
            self._lmb_down = bool(state["lmb_down"])
        if state.get("lmb_hold_time") is not None:
            self._lmb_hold_time = float(state["lmb_hold_time"])
        if state.get("mouse_flight_active") is not None:
            self.mouse_flight_active = bool(state["mouse_flight_active"])
        if state.get("mouse_pos_xy") is not None:
            self.mouse_pos = event.position()

    def on_mouse_release(self, event):
        state = mouse_release_state(
            active=self.active,
            is_left_button=event.button() == Qt.LeftButton,
            orbit_cam_active=self._orbit_cam_active,
        )
        if not state["handled"]:
            return
        if state.get("orbit_dragging") is not None:
            self._orbit_dragging = bool(state["orbit_dragging"])
        if state.get("lmb_down") is not None:
            self._lmb_down = bool(state["lmb_down"])
        if state.get("lmb_hold_time") is not None:
            self._lmb_hold_time = float(state["lmb_hold_time"])
        if state.get("mouse_flight_active") is not None:
            self.mouse_flight_active = bool(state["mouse_flight_active"])
        if state.get("mouse_strength") is not None:
            self._mouse_strength = float(state["mouse_strength"])

    def on_mouse_move(self, event):
        state = mouse_move_state(
            active=self.active,
            orbit_cam_active=self._orbit_cam_active,
            orbit_dragging=self._orbit_dragging,
            orbit_last_mouse_xy=None
            if self._orbit_last_mouse is None
            else (float(self._orbit_last_mouse.x()), float(self._orbit_last_mouse.y())),
            mouse_pos_xy=(float(event.position().x()), float(event.position().y())),
            orbit_yaw=self._orbit_yaw,
            orbit_pitch=self._orbit_pitch,
        )
        if not state["handled"]:
            return
        if state.get("orbit_last_mouse_xy") is not None:
            self._orbit_last_mouse = event.position()
        if state.get("orbit_yaw") is not None:
            self._orbit_yaw = float(state["orbit_yaw"])
        if state.get("orbit_pitch") is not None:
            self._orbit_pitch = float(state["orbit_pitch"])
        if state.get("mouse_pos_xy") is not None:
            self.mouse_pos = event.position()

    def on_wheel(self, event):
        state = wheel_state(
            active=self.active,
            orbit_cam_active=self._orbit_cam_active,
            delta_y=float(event.angleDelta().y()),
            orbit_distance=self._orbit_distance,
        )
        if not state["handled"]:
            return
        self._orbit_distance = float(state["orbit_distance"])

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

        steer_state = steer_activation_state(
            lmb_down=self._lmb_down,
            mouse_flight_active=self.mouse_flight_active,
            lmb_hold_time=self._lmb_hold_time,
            dt=dt,
            steer_activation_delay=self.steer_activation_delay,
        )
        self._lmb_hold_time = float(steer_state["lmb_hold_time"])
        self.mouse_flight_active = bool(steer_state["mouse_flight_active"])

        drive_state = drive_input_state(
            keys_down=self._keys_down,
            key_w=self._KEY_W,
            key_s=self._KEY_S,
            s_hold_time=self._s_hold_time,
            dt=dt,
        )
        w_down = bool(drive_state["w_down"])
        s_down = bool(drive_state["s_down"])
        self._s_hold_time = float(drive_state["s_hold_time"])

        offset_x, offset_y, strength = self._mouse_offset()
        self._mouse_strength = strength

        autopilot_state = autopilot_interrupt_state(
            mode=self.mode,
            autopilot_mode=self.AUTOPILOT,
            normal_mode=self.NORMAL,
            w_down=w_down,
            s_down=s_down,
            mouse_flight_active=self.mouse_flight_active,
        )
        if autopilot_state["interrupt_autopilot"]:
            self._set_mode(str(autopilot_state["next_mode"]))
        elif self.mode == self.AUTOPILOT:
            self._update_autopilot(dt)

        if self.mode != self.AUTOPILOT:
            self._update_manual_turn(dt, offset_x, offset_y)

        cruise_state = cruise_update_state(
            mode=self.mode,
            cruise_charging_mode=self.CRUISE_CHARGING,
            cruise_active_mode=self.CRUISE_ACTIVE,
            normal_mode=self.NORMAL,
            charge_elapsed=self._charge_elapsed,
            dt=dt,
            cruise_charge_time=self.cruise_charge_time,
            should_abort_cruise=self._should_abort_cruise(),
        )
        self._charge_elapsed = float(cruise_state["charge_elapsed"])
        if cruise_state["next_mode"] is not None:
            self._set_mode(str(cruise_state["next_mode"]))

        self.speed = updated_speed(
            mode=self.mode,
            autopilot_mode=self.AUTOPILOT,
            tradelane_active_mode=self.TRADELANE_ACTIVE,
            cruise_active_mode=self.CRUISE_ACTIVE,
            normal_mode=self.NORMAL,
            speed=self.speed,
            max_speed=self.max_speed,
            cruise_speed=self.cruise_speed,
            accel=self.accel,
            brake=self.brake,
            dt=dt,
            w_down=w_down,
            s_down=s_down,
        )

        fwd = self._forward_vector()
        self.ship_pos += fwd * (self.speed * dt)
        self._apply_camera_pose()

    # ------------------------------------------------------------------
    # Modes
    # ------------------------------------------------------------------
    def _set_mode(self, mode: str):
        state = mode_transition_state(
            mode=mode,
            autopilot_mode=self.AUTOPILOT,
            cruise_charging_mode=self.CRUISE_CHARGING,
            normal_mode=self.NORMAL,
            speed=self.speed,
            max_speed=self.max_speed,
        )
        self.mode = str(state["mode"])
        if state["auto_cruise_charging"] is not None:
            self._auto_cruise_charging = bool(state["auto_cruise_charging"])
        if state["auto_cruise_active"] is not None:
            self._auto_cruise_active = bool(state["auto_cruise_active"])
        if state["charge_elapsed"] is not None:
            self._charge_elapsed = float(state["charge_elapsed"])
        self.speed = float(state["speed"])

    def _should_abort_cruise(self) -> bool:
        return should_abort_cruise(
            mode=self.mode,
            cruise_charging_mode=self.CRUISE_CHARGING,
            cruise_active_mode=self.CRUISE_ACTIVE,
            s_hold_time=self._s_hold_time,
        )

    def _start_autopilot(self):
        target = getattr(self.editor, "_selected", None)
        pos = self._item_world_pos(target)
        state = autopilot_selection_state(
            has_editor=self.editor is not None,
            target_name=getattr(target, "nickname", "Target"),
            target_pos_xyz=pos,
            autopilot_mode=self.AUTOPILOT,
        )
        if state is None:
            return
        self._auto_target = target
        self._target_name = str(state["auto_target_name"])
        self._set_mode(str(state["mode"]))

    def set_free_flight(self):
        state = free_flight_state(active=self.active, normal_mode=self.NORMAL)
        if state is None:
            return
        self._set_mode(str(state["mode"]))
        self._lane_points = list(state["lane_points"])
        self._lane_index = int(state["lane_index"])
        self._auto_target = state["auto_target"]
        self._target_name = str(state["target_name"])
        self._emit_hud()

    def start_autopilot_to_selection(self):
        if not should_run_flight_action(active=self.active):
            return
        self._start_autopilot()
        self._emit_hud()

    def start_dock_to_selected_tradelane(self):
        if not should_run_flight_action(active=self.active):
            return
        self._start_tradelane()
        self._emit_hud()

    def set_chase_distance_ship_lengths(self, value: float):
        try:
            self._chase_distance_ship_lengths = normalized_chase_distance_ship_lengths(value)
        except Exception:
            return

    def get_chase_distance_ship_lengths(self) -> float:
        return float(self._chase_distance_ship_lengths)

    def _update_autopilot(self, dt: float):
        pos = item_world_pos_tuple(self._auto_target)
        state = autopilot_motion_state(
            dt=dt,
            ship_pos_xyz=(self.ship_pos.x(), self.ship_pos.y(), self.ship_pos.z()),
            target_pos_xyz=pos,
            yaw=self.yaw,
            pitch=self.pitch,
            speed=self.speed,
            arrival_radius=self.arrival_radius,
            auto_cruise_distance=self.auto_cruise_distance,
            cruise_charge_time=self.cruise_charge_time,
            cruise_speed=self.cruise_speed,
            max_speed=self.max_speed,
            accel=self.accel,
            brake=self.brake,
            yaw_rate_max=self.yaw_rate_max,
            pitch_rate_max=self.pitch_rate_max,
            auto_cruise_charging=self._auto_cruise_charging,
            auto_cruise_active=self._auto_cruise_active,
            charge_elapsed=self._charge_elapsed,
        )
        if state["status"] == "invalid_target":
            self._set_mode(self.NORMAL)
            return
        self._target_name = getattr(self._auto_target, "nickname", "Target")
        if state["status"] == "arrived":
            self._set_mode(self.NORMAL)
            return
        self.yaw = float(state["yaw"])
        self.pitch = float(state["pitch"])
        self.speed = float(state["speed"])
        self._auto_cruise_charging = bool(state["auto_cruise_charging"])
        self._auto_cruise_active = bool(state["auto_cruise_active"])
        self._charge_elapsed = float(state["charge_elapsed"])

    def _start_tradelane(self):
        if not self.editor:
            return
        sel = getattr(self.editor, "_selected", None)
        if not self._is_tradelane(sel):
            return
        lane_path = self._build_lane_path(sel)
        self._lane_points = lane_path
        state = tradelane_start_state(
            lane_points_xyz=[(point.x(), point.y(), point.z()) for point in lane_path],
            ship_pos_xyz=(self.ship_pos.x(), self.ship_pos.y(), self.ship_pos.z()),
            forward_xyz=forward_vector_xyz(yaw=self.yaw, pitch=self.pitch),
            dock_radius=self.dock_radius,
            tradelane_speed=self.tradelane_speed,
        )
        if state["status"] == "invalid_path":
            self._lane_index = 0
            return
        self._lane_index = int(state["lane_index"])
        if state["status"] == "docking":
            self._set_mode(self.TRADELANE_DOCKING)
            return
        self.ship_pos = QVector3D(*state["ship_pos_xyz"])
        self.speed = float(state["speed"])
        self._set_mode(self.TRADELANE_ACTIVE)

    def _update_tradelane_docking(self, dt: float):
        state = tradelane_docking_state(
            dt=dt,
            lane_points_xyz=[(point.x(), point.y(), point.z()) for point in self._lane_points],
            ship_pos_xyz=(self.ship_pos.x(), self.ship_pos.y(), self.ship_pos.z()),
            yaw=self.yaw,
            pitch=self.pitch,
            speed=self.speed,
            arrival_radius=self.arrival_radius,
            cruise_speed=self.cruise_speed,
            max_speed=self.max_speed,
            accel=self.accel,
            brake=self.brake,
            tradelane_speed=self.tradelane_speed,
            yaw_rate_max=self.yaw_rate_max,
            pitch_rate_max=self.pitch_rate_max,
            forward_xyz=forward_vector_xyz(yaw=self.yaw, pitch=self.pitch),
        )
        if state["status"] == "invalid_path":
            self._set_mode(self.NORMAL)
            return
        if state["status"] == "active":
            self.ship_pos = QVector3D(*state["ship_pos_xyz"])
            self._lane_index = int(state["lane_index"])
            self.speed = float(state["speed"])
            self._set_mode(self.TRADELANE_ACTIVE)
            return
        self.yaw = float(state["yaw"])
        self.pitch = float(state["pitch"])
        self.speed = float(state["speed"])
        self.ship_pos = QVector3D(*state["ship_pos_xyz"])

    def _update_tradelane(self, dt: float):
        state = tradelane_travel_state(
            dt=dt,
            lane_points_xyz=[(point.x(), point.y(), point.z()) for point in self._lane_points],
            lane_index=self._lane_index,
            ship_pos_xyz=(self.ship_pos.x(), self.ship_pos.y(), self.ship_pos.z()),
            tradelane_speed=self.tradelane_speed,
            max_speed=self.max_speed,
        )
        self._lane_index = int(state["lane_index"])
        if "ship_pos_xyz" in state:
            self.ship_pos = QVector3D(*state["ship_pos_xyz"])
        if state.get("yaw") is not None:
            self.yaw = float(state["yaw"])
        if state.get("pitch") is not None:
            self.pitch = float(state["pitch"])
        if state["status"] == "finished":
            self._set_mode(self.NORMAL)
            self.speed = float(state["speed"])

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
        cam_pos_xyz = None
        view_center_xyz = None
        if cam is not None:
            cam_pos = cam.position()
            view_center = cam.viewCenter()
            cam_pos_xyz = (cam_pos.x(), cam_pos.y(), cam_pos.z())
            view_center_xyz = (view_center.x(), view_center.y(), view_center.z())
        state = seeded_flight_state_from_camera(
            cam_pos_xyz=cam_pos_xyz,
            view_center_xyz=view_center_xyz,
            scale=scale,
        )
        self.ship_pos = QVector3D(*state["ship_pos_xyz"])
        self.yaw = float(state["yaw"])
        self.pitch = float(state["pitch"])
        self.roll = float(state["roll"])

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
        viewport_size = None
        if self.viewport is not None:
            viewport_size = (int(self.viewport.width()), int(self.viewport.height()))
        return mouse_offset_state(
            viewport_size=viewport_size,
            mouse_pos_xy=(self.mouse_pos.x(), self.mouse_pos.y()),
            mouse_flight_active=self.mouse_flight_active,
        )

    def _update_manual_turn(self, dt: float, ox: float, oy: float):
        state = updated_manual_turn_state(
            dt=dt,
            ox=ox,
            oy=oy,
            yaw=self.yaw,
            pitch=self.pitch,
            yaw_rate=self._yaw_rate,
            pitch_rate=self._pitch_rate,
            yaw_rate_max=self.yaw_rate_max,
            pitch_rate_max=self.pitch_rate_max,
            turn_smoothing=self.turn_smoothing,
        )
        self.yaw = float(state["yaw"])
        self.pitch = float(state["pitch"])
        self.roll = float(state["roll"])
        self._yaw_rate = float(state["yaw_rate"])
        self._pitch_rate = float(state["pitch_rate"])

    def _forward_vector(self) -> QVector3D:
        return QVector3D(*forward_vector_xyz(yaw=self.yaw, pitch=self.pitch))

    def _apply_camera_pose(self):
        if self.viewport is None:
            return
        cam = getattr(self.viewport, "_camera", None)
        if cam is None:
            return
        scale = float(getattr(self.viewport, "_scene_scale", 1.0) or 1.0)
        fwd = self._forward_vector()
        state = viewport_camera_pose_state(
            orbit_cam_active=self._orbit_cam_active,
            ship_pos_xyz=(self.ship_pos.x(), self.ship_pos.y(), self.ship_pos.z()),
            scale=scale,
            forward_xyz=(fwd.x(), fwd.y(), fwd.z()),
            chase_distance_ship_lengths=self._chase_distance_ship_lengths,
            orbit_yaw=self._orbit_yaw,
            orbit_pitch=self._orbit_pitch,
            orbit_distance=self._orbit_distance,
        )
        cam.setPosition(QVector3D(*state["cam_pos_xyz"]))
        cam.setViewCenter(QVector3D(*state["view_center_xyz"]))
        if state["sync_sky"] and hasattr(self.viewport, "_sync_sky_to_camera"):
            self.viewport._sync_sky_to_camera()
        if state["update_labels"] and hasattr(self.viewport, "_update_label_scales"):
            self.viewport._update_label_scales()

    def _apply_orbit_camera_pose(self, cam, scale: float):
        state = viewport_camera_pose_state(
            orbit_cam_active=True,
            ship_pos_xyz=(self.ship_pos.x(), self.ship_pos.y(), self.ship_pos.z()),
            scale=scale,
            forward_xyz=None,
            chase_distance_ship_lengths=self._chase_distance_ship_lengths,
            orbit_yaw=self._orbit_yaw,
            orbit_pitch=self._orbit_pitch,
            orbit_distance=self._orbit_distance,
        )
        cam.setPosition(QVector3D(*state["cam_pos_xyz"]))
        cam.setViewCenter(QVector3D(*state["view_center_xyz"]))
        if state["sync_sky"] and hasattr(self.viewport, "_sync_sky_to_camera"):
            self.viewport._sync_sky_to_camera()
        if state["update_labels"] and hasattr(self.viewport, "_update_label_scales"):
            self.viewport._update_label_scales()

    def _toggle_orbit_camera(self):
        if self.viewport is None:
            return
        cam = getattr(self.viewport, "_camera", None)
        scale = float(getattr(self.viewport, "_scene_scale", 1.0) or 1.0)
        if cam is None or scale <= 0.0:
            return
        pos = cam.position()
        state = toggled_orbit_camera_state(
            orbit_active=self._orbit_cam_active,
            ship_pos_xyz=(self.ship_pos.x(), self.ship_pos.y(), self.ship_pos.z()),
            cam_pos_xyz=(pos.x(), pos.y(), pos.z()),
            scale=scale,
        )
        self._orbit_cam_active = bool(state["orbit_active"])
        self._orbit_dragging = bool(state["orbit_dragging"])
        self.mouse_flight_active = bool(state["mouse_flight_active"])
        self._lmb_down = bool(state["lmb_down"])
        if self._orbit_cam_active:
            self._orbit_distance = float(state["orbit_distance"])
            self._orbit_yaw = float(state["orbit_yaw"])
            self._orbit_pitch = float(state["orbit_pitch"])

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
        fwd = self._forward_vector()
        return build_hud_snapshot(
            mode=self.mode,
            speed=self.speed,
            max_speed=self.max_speed,
            ship_pos_xyz=(self.ship_pos.x(), self.ship_pos.y(), self.ship_pos.z()),
            yaw=self.yaw,
            pitch=self.pitch,
            pitch_rate=self._pitch_rate,
            forward_xyz=(fwd.x(), fwd.y(), fwd.z()),
            sel_name=sel_name,
            sel_dist=sel_dist,
            charge_elapsed=self._charge_elapsed,
            cruise_charge_time=self.cruise_charge_time,
            auto_cruise_charging=self._auto_cruise_charging,
            orbit_cam_active=self._orbit_cam_active,
            error=error or "",
            autopilot_mode=self.AUTOPILOT,
            cruise_charging_mode=self.CRUISE_CHARGING,
        )

    def _overlay_text(self) -> str:
        selection_name = ""
        selection_distance = None
        if self.editor is not None:
            sel = getattr(self.editor, "_selected", None)
            sp = self._item_world_pos(sel)
            if sp is not None:
                selection_distance = float((sp - self.ship_pos).length())
                selection_name = str(getattr(sel, "nickname", "Selection"))
        auto_target_distance = None
        if self.mode == self.AUTOPILOT and self._auto_target is not None:
            pos = self._item_world_pos(self._auto_target)
            if pos is not None:
                auto_target_distance = float((pos - self.ship_pos).length())
        return build_overlay_text(
            mode=self.mode,
            speed=self.speed,
            max_speed=self.max_speed,
            ship_pos_xyz=(self.ship_pos.x(), self.ship_pos.y(), self.ship_pos.z()),
            selection_name=selection_name,
            selection_distance=selection_distance,
            charge_elapsed=self._charge_elapsed,
            cruise_charge_time=self.cruise_charge_time,
            auto_cruise_charging=self._auto_cruise_charging,
            auto_cruise_active=self._auto_cruise_active,
            auto_target_name=self._target_name,
            auto_target_distance=auto_target_distance,
            autopilot_mode=self.AUTOPILOT,
            cruise_charging_mode=self.CRUISE_CHARGING,
        )

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
        pos = item_world_pos_tuple(item)
        if pos is None:
            return None
        return QVector3D(*pos)

    @staticmethod
    def _is_tradelane(item) -> bool:
        return is_tradelane_item(item)

    def _build_lane_path(self, selected_obj) -> list[QVector3D]:
        if not self.editor:
            return []
        tuples = build_lane_path_tuples(selected_obj, list(getattr(self.editor, "_objects", [])))
        return [QVector3D(*pos) for pos in tuples]
