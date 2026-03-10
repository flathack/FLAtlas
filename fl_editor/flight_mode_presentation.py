from __future__ import annotations

from typing import Any, Callable

from PySide6.QtGui import QVector3D

from .flight_mode_editor_context import editor_target_context
from .flight_mode_hud import build_hud_bundle


def editor_hud_bundle(
    *,
    selected_item: Any,
    mode: str,
    autopilot_mode: str,
    auto_target: Any,
    target_name: str,
    ship_pos: QVector3D,
    item_world_pos: Callable[[Any], QVector3D | None],
    speed: float,
    max_speed: float,
    yaw: float,
    pitch: float,
    pitch_rate: float,
    forward_xyz: tuple[float, float, float],
    charge_elapsed: float,
    cruise_charge_time: float,
    auto_cruise_charging: bool,
    auto_cruise_active: bool,
    orbit_cam_active: bool,
    error: str,
    cruise_charging_mode: str,
) -> dict[str, object]:
    target_context = editor_target_context(
        selected_item=selected_item,
        mode=mode,
        autopilot_mode=autopilot_mode,
        auto_target=auto_target,
        target_name=target_name,
        ship_pos=ship_pos,
        item_world_pos=item_world_pos,
    )
    return build_hud_bundle(
        mode=mode,
        speed=speed,
        max_speed=max_speed,
        ship_pos_xyz=(ship_pos.x(), ship_pos.y(), ship_pos.z()),
        yaw=yaw,
        pitch=pitch,
        pitch_rate=pitch_rate,
        forward_xyz=forward_xyz,
        target_context=target_context,
        charge_elapsed=charge_elapsed,
        cruise_charge_time=cruise_charge_time,
        auto_cruise_charging=auto_cruise_charging,
        auto_cruise_active=auto_cruise_active,
        orbit_cam_active=orbit_cam_active,
        error=error,
        autopilot_mode=autopilot_mode,
        cruise_charging_mode=cruise_charging_mode,
    )
