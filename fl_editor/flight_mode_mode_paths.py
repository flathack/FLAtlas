from __future__ import annotations

import math


def _approach(cur: float, target: float, max_step: float) -> float:
    delta = target - cur
    if abs(delta) <= max_step:
        return target
    return cur + max_step * (1.0 if delta > 0.0 else -1.0)


def _wrap_pi(value: float) -> float:
    return (value + math.pi) % (2.0 * math.pi) - math.pi


def _approach_angle(cur: float, target: float, max_step: float) -> float:
    delta = _wrap_pi(target - cur)
    if abs(delta) <= max_step:
        return target
    return cur + max_step * (1.0 if delta > 0.0 else -1.0)


def _clamped_pitch(value: float) -> float:
    return max(math.radians(-85.0), min(math.radians(85.0), float(value)))


def autopilot_motion_state(
    *,
    dt: float,
    ship_pos_xyz: tuple[float, float, float],
    target_pos_xyz: tuple[float, float, float] | None,
    yaw: float,
    pitch: float,
    speed: float,
    arrival_radius: float,
    auto_cruise_distance: float,
    cruise_charge_time: float,
    cruise_speed: float,
    max_speed: float,
    accel: float,
    brake: float,
    yaw_rate_max: float,
    pitch_rate_max: float,
    auto_cruise_charging: bool,
    auto_cruise_active: bool,
    charge_elapsed: float,
) -> dict[str, object]:
    if target_pos_xyz is None:
        return {"status": "invalid_target"}

    sx, sy, sz = ship_pos_xyz
    tx, ty, tz = target_pos_xyz
    dx = tx - sx
    dy = ty - sy
    dz = tz - sz
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    if dist <= float(arrival_radius):
        return {"status": "arrived"}

    dir_x = dx / dist
    dir_y = dy / dist
    dir_z = dz / dist
    desired_yaw = math.atan2(dir_x, dir_z)
    desired_pitch = math.asin(max(-1.0, min(1.0, dir_y)))
    next_yaw = _approach_angle(float(yaw), desired_yaw, float(yaw_rate_max) * float(dt))
    next_pitch = _clamped_pitch(_approach(float(pitch), desired_pitch, float(pitch_rate_max) * float(dt)))

    next_charge_elapsed = float(charge_elapsed)
    next_charging = bool(auto_cruise_charging)
    next_active = bool(auto_cruise_active)
    if dist > float(auto_cruise_distance):
        if not next_active and not next_charging:
            next_charging = True
            next_charge_elapsed = 0.0
        if next_charging:
            next_charge_elapsed += float(dt)
            if next_charge_elapsed >= float(cruise_charge_time):
                next_charging = False
                next_active = True
    else:
        next_charging = False
        next_active = False
        next_charge_elapsed = 0.0

    target_speed = float(cruise_speed) if next_active else float(max_speed)
    if dist < float(arrival_radius) * 3.0:
        target_speed = min(target_speed, max(20.0, dist * 0.35))

    next_speed = float(speed)
    if next_speed < target_speed:
        next_speed = min(target_speed, next_speed + float(accel) * float(dt))
    else:
        next_speed = max(target_speed, next_speed - float(brake) * float(dt))

    return {
        "status": "continue",
        "target_distance": dist,
        "target_speed": target_speed,
        "yaw": next_yaw,
        "pitch": next_pitch,
        "speed": next_speed,
        "auto_cruise_charging": next_charging,
        "auto_cruise_active": next_active,
        "charge_elapsed": next_charge_elapsed,
    }


def tradelane_start_state(
    *,
    lane_points_xyz: list[tuple[float, float, float]],
    ship_pos_xyz: tuple[float, float, float],
    forward_xyz: tuple[float, float, float],
    dock_radius: float,
    tradelane_speed: float,
) -> dict[str, object]:
    if len(lane_points_xyz) < 2:
        return {"status": "invalid_path"}

    lane_start = lane_points_xyz[0]
    dx = lane_start[0] - ship_pos_xyz[0]
    dy = lane_start[1] - ship_pos_xyz[1]
    dz = lane_start[2] - ship_pos_xyz[2]
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    if dist > 1e-5:
        align = (
            float(forward_xyz[0]) * dx / dist
            + float(forward_xyz[1]) * dy / dist
            + float(forward_xyz[2]) * dz / dist
        )
    else:
        align = 1.0

    if dist > float(dock_radius) or align < 0.55:
        return {
            "status": "docking",
            "lane_index": 0,
            "distance_to_start": dist,
            "alignment": align,
        }

    return {
        "status": "active",
        "lane_index": 1,
        "ship_pos_xyz": lane_start,
        "speed": float(tradelane_speed),
    }


def tradelane_docking_state(
    *,
    dt: float,
    lane_points_xyz: list[tuple[float, float, float]],
    ship_pos_xyz: tuple[float, float, float],
    yaw: float,
    pitch: float,
    speed: float,
    arrival_radius: float,
    cruise_speed: float,
    max_speed: float,
    accel: float,
    brake: float,
    tradelane_speed: float,
    yaw_rate_max: float,
    pitch_rate_max: float,
    forward_xyz: tuple[float, float, float],
) -> dict[str, object]:
    if len(lane_points_xyz) < 2:
        return {"status": "invalid_path"}

    lane_start = lane_points_xyz[0]
    dx = lane_start[0] - ship_pos_xyz[0]
    dy = lane_start[1] - ship_pos_xyz[1]
    dz = lane_start[2] - ship_pos_xyz[2]
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    if dist <= float(arrival_radius) * 0.65:
        return {
            "status": "active",
            "ship_pos_xyz": lane_start,
            "lane_index": 1,
            "speed": float(tradelane_speed),
        }

    dir_x = dx / dist
    dir_y = dy / dist
    dir_z = dz / dist
    desired_yaw = math.atan2(dir_x, dir_z)
    desired_pitch = math.asin(max(-1.0, min(1.0, dir_y)))
    next_yaw = _approach_angle(float(yaw), desired_yaw, float(yaw_rate_max) * float(dt))
    next_pitch = _clamped_pitch(_approach(float(pitch), desired_pitch, float(pitch_rate_max) * float(dt)))

    target_speed = min(float(cruise_speed), max(float(max_speed), dist * 0.35))
    next_speed = float(speed)
    if next_speed < target_speed:
        next_speed = min(target_speed, next_speed + float(accel) * float(dt))
    else:
        next_speed = max(target_speed, next_speed - float(brake) * float(dt))

    next_ship_pos_xyz = (
        ship_pos_xyz[0] + float(forward_xyz[0]) * next_speed * float(dt),
        ship_pos_xyz[1] + float(forward_xyz[1]) * next_speed * float(dt),
        ship_pos_xyz[2] + float(forward_xyz[2]) * next_speed * float(dt),
    )
    return {
        "status": "continue",
        "yaw": next_yaw,
        "pitch": next_pitch,
        "speed": next_speed,
        "ship_pos_xyz": next_ship_pos_xyz,
        "target_speed": target_speed,
        "distance_to_start": dist,
    }


def tradelane_travel_state(
    *,
    dt: float,
    lane_points_xyz: list[tuple[float, float, float]],
    lane_index: int,
    ship_pos_xyz: tuple[float, float, float],
    tradelane_speed: float,
    max_speed: float,
) -> dict[str, object]:
    if int(lane_index) >= len(lane_points_xyz):
        return {
            "status": "finished",
            "lane_index": int(lane_index),
            "speed": min(float(tradelane_speed), float(max_speed)),
        }

    travel = float(tradelane_speed) * float(dt)
    next_lane_index = int(lane_index)
    pos_x, pos_y, pos_z = ship_pos_xyz
    yaw = None
    pitch = None
    while travel > 0.0 and next_lane_index < len(lane_points_xyz):
        tx, ty, tz = lane_points_xyz[next_lane_index]
        dx = tx - pos_x
        dy = ty - pos_y
        dz = tz - pos_z
        seg_len = math.sqrt(dx * dx + dy * dy + dz * dz)
        if seg_len < 1e-5:
            next_lane_index += 1
            continue
        if travel >= seg_len:
            pos_x, pos_y, pos_z = tx, ty, tz
            travel -= seg_len
            next_lane_index += 1
        else:
            dir_x = dx / seg_len
            dir_y = dy / seg_len
            dir_z = dz / seg_len
            pos_x += dir_x * travel
            pos_y += dir_y * travel
            pos_z += dir_z * travel
            travel = 0.0
        yaw = math.atan2(dx / seg_len, dz / seg_len)
        pitch = math.asin(max(-1.0, min(1.0, dy / seg_len)))

    if next_lane_index >= len(lane_points_xyz):
        return {
            "status": "finished",
            "lane_index": next_lane_index,
            "ship_pos_xyz": (pos_x, pos_y, pos_z),
            "speed": min(float(tradelane_speed), float(max_speed)),
            "yaw": yaw,
            "pitch": pitch,
        }

    return {
        "status": "continue",
        "lane_index": next_lane_index,
        "ship_pos_xyz": (pos_x, pos_y, pos_z),
        "yaw": yaw,
        "pitch": pitch,
    }
