from __future__ import annotations

import math


def charge_progress(charge_elapsed: float, cruise_charge_time: float) -> float:
    return min(1.0, float(charge_elapsed) / max(0.01, float(cruise_charge_time)))


def ship_tilt_degrees(pitch_rate: float) -> float:
    return max(-16.0, min(16.0, math.degrees(float(pitch_rate)) * 0.16))


def build_hud_snapshot(
    *,
    mode: str,
    speed: float,
    max_speed: float,
    ship_pos_xyz: tuple[float, float, float],
    yaw: float,
    pitch: float,
    pitch_rate: float,
    forward_xyz: tuple[float, float, float],
    sel_name: str,
    sel_dist: float | None,
    charge_elapsed: float,
    cruise_charge_time: float,
    auto_cruise_charging: bool,
    orbit_cam_active: bool,
    error: str,
    autopilot_mode: str,
    cruise_charging_mode: str,
) -> dict[str, object]:
    return {
        "mode": mode,
        "speed": float(speed),
        "max_speed": float(max_speed),
        "pos": tuple(float(v) for v in ship_pos_xyz),
        "yaw_deg": math.degrees(float(yaw)),
        "pitch_deg": math.degrees(float(pitch)),
        "ship_tilt_deg": ship_tilt_degrees(pitch_rate),
        "forward": tuple(float(v) for v in forward_xyz),
        "target_name": str(sel_name or ""),
        "target_distance": None if sel_dist is None else float(sel_dist),
        "charge_progress": charge_progress(charge_elapsed, cruise_charge_time),
        "charge_active": bool(mode == cruise_charging_mode or (mode == autopilot_mode and auto_cruise_charging)),
        "orbit_cam_active": bool(orbit_cam_active),
        "error": error or "",
    }


def build_overlay_text(
    *,
    mode: str,
    speed: float,
    max_speed: float,
    ship_pos_xyz: tuple[float, float, float],
    selection_name: str,
    selection_distance: float | None,
    charge_elapsed: float,
    cruise_charge_time: float,
    auto_cruise_charging: bool,
    auto_cruise_active: bool,
    auto_target_name: str,
    auto_target_distance: float | None,
    autopilot_mode: str,
    cruise_charging_mode: str,
) -> str:
    px, py, pz = (float(v) for v in ship_pos_xyz)
    lines = [
        f"Flight | {mode}",
        f"Speed: {float(speed):.1f} m/s",
        f"Max: {float(max_speed):.0f} m/s",
        f"Pos: X {px:.1f}  Y {py:.1f}  Z {pz:.1f}",
    ]
    if selection_name and selection_distance is not None:
        lines.append(f"Target: {selection_name} | Dist: {float(selection_distance):.1f} m")
    if mode == cruise_charging_mode:
        p = charge_progress(charge_elapsed, cruise_charge_time)
        lines.append(f"Cruise Charge: {p * 100.0:.0f}%")
    if mode == autopilot_mode and auto_cruise_charging:
        p = charge_progress(charge_elapsed, cruise_charge_time)
        lines.append(f"Auto Cruise Charge: {p * 100.0:.0f}%")
    if mode == autopilot_mode and auto_cruise_active:
        lines.append("Auto Cruise: ACTIVE")
    if mode == autopilot_mode and auto_target_name and auto_target_distance is not None:
        lines.append(f"Target: {auto_target_name} ({float(auto_target_distance):.0f} m)")
    return "\n".join(lines)
