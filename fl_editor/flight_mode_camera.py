from __future__ import annotations

import math


def seeded_flight_state_from_camera(
    *,
    cam_pos_xyz: tuple[float, float, float] | None,
    view_center_xyz: tuple[float, float, float] | None,
    scale: float,
) -> dict[str, object]:
    if cam_pos_xyz is None or view_center_xyz is None or float(scale) <= 0.0:
        return {
            "ship_pos_xyz": (0.0, 0.0, 0.0),
            "yaw": 0.0,
            "pitch": 0.0,
            "roll": 0.0,
        }
    px, py, pz = (float(v) for v in cam_pos_xyz)
    vx, vy, vz = (float(v) for v in view_center_xyz)
    ship_pos = (px / float(scale), py / float(scale), pz / float(scale))
    fx, fy, fz = vx - px, vy - py, vz - pz
    flen = math.sqrt(fx * fx + fy * fy + fz * fz)
    if flen < 1e-5:
        fx, fy, fz = 0.0, 0.0, 1.0
        flen = 1.0
    fx /= flen
    fy /= flen
    fz /= flen
    yaw = math.atan2(fx, fz)
    pitch = math.asin(max(-1.0, min(1.0, fy)))
    pitch = max(math.radians(-85.0), min(math.radians(85.0), pitch))
    return {
        "ship_pos_xyz": ship_pos,
        "yaw": yaw,
        "pitch": pitch,
        "roll": 0.0,
    }


def mouse_offset_state(
    *,
    viewport_size: tuple[int, int] | None,
    mouse_pos_xy: tuple[float, float],
    mouse_flight_active: bool,
) -> tuple[float, float, float]:
    if viewport_size is None or not mouse_flight_active:
        return 0.0, 0.0, 0.0
    w = max(1, int(viewport_size[0]))
    h = max(1, int(viewport_size[1]))
    mx, my = (float(v) for v in mouse_pos_xy)
    cx, cy = w * 0.5, h * 0.5
    norm = max(1.0, min(w, h) * 0.5)
    ox = max(-1.0, min(1.0, (mx - cx) / norm))
    oy = max(-1.0, min(1.0, (my - cy) / norm))
    dead = 0.05
    if abs(ox) < dead:
        ox = 0.0
    if abs(oy) < dead:
        oy = 0.0
    strength = min(1.0, math.sqrt(ox * ox + oy * oy))
    return ox, oy, strength


def updated_manual_turn_state(
    *,
    dt: float,
    ox: float,
    oy: float,
    yaw: float,
    pitch: float,
    yaw_rate: float,
    pitch_rate: float,
    yaw_rate_max: float,
    pitch_rate_max: float,
    turn_smoothing: float,
) -> dict[str, float]:
    target_yaw_rate = -float(ox) * float(yaw_rate_max)
    target_pitch_rate = -float(oy) * float(pitch_rate_max)
    alpha = max(0.0, min(1.0, float(turn_smoothing) * float(dt)))
    next_yaw_rate = float(yaw_rate) + (target_yaw_rate - float(yaw_rate)) * alpha
    next_pitch_rate = float(pitch_rate) + (target_pitch_rate - float(pitch_rate)) * alpha
    next_yaw = float(yaw) + next_yaw_rate * float(dt)
    next_pitch = float(pitch) + next_pitch_rate * float(dt)
    next_pitch = max(math.radians(-85.0), min(math.radians(85.0), next_pitch))
    return {
        "yaw": next_yaw,
        "pitch": next_pitch,
        "roll": 0.0,
        "yaw_rate": next_yaw_rate,
        "pitch_rate": next_pitch_rate,
    }


def forward_vector_xyz(*, yaw: float, pitch: float) -> tuple[float, float, float]:
    cp = math.cos(float(pitch))
    fx = cp * math.sin(float(yaw))
    fy = math.sin(float(pitch))
    fz = cp * math.cos(float(yaw))
    flen = math.sqrt(fx * fx + fy * fy + fz * fz)
    if flen < 1e-6:
        return 0.0, 0.0, 1.0
    return fx / flen, fy / flen, fz / flen


def chase_camera_pose(
    *,
    ship_pos_xyz: tuple[float, float, float],
    forward_xyz: tuple[float, float, float],
    scale: float,
    chase_distance_ship_lengths: float,
    ship_len: float = 7.2,
    view_ahead: float = 220.0,
) -> dict[str, tuple[float, float, float]]:
    sx, sy, sz = (float(v) for v in ship_pos_xyz)
    fx, fy, fz = (float(v) for v in forward_xyz)
    world = (sx * float(scale), sy * float(scale), sz * float(scale))
    cam_pos = (
        world[0] - fx * (ship_len * float(chase_distance_ship_lengths)),
        world[1] - fy * (ship_len * float(chase_distance_ship_lengths)),
        world[2] - fz * (ship_len * float(chase_distance_ship_lengths)),
    )
    cam_view = (
        world[0] + fx * float(view_ahead),
        world[1] + fy * float(view_ahead),
        world[2] + fz * float(view_ahead),
    )
    return {"cam_pos_xyz": cam_pos, "cam_view_xyz": cam_view}


def orbit_camera_pose(
    *,
    ship_pos_xyz: tuple[float, float, float],
    scale: float,
    orbit_yaw: float,
    orbit_pitch: float,
    orbit_distance: float,
) -> dict[str, tuple[float, float, float]]:
    sx, sy, sz = (float(v) for v in ship_pos_xyz)
    center = (sx * float(scale), sy * float(scale), sz * float(scale))
    cp = math.cos(float(orbit_pitch))
    dx = cp * math.sin(float(orbit_yaw))
    dy = math.sin(float(orbit_pitch))
    dz = cp * math.cos(float(orbit_yaw))
    cam_pos = (
        center[0] + dx * float(orbit_distance),
        center[1] + dy * float(orbit_distance),
        center[2] + dz * float(orbit_distance),
    )
    return {"center_xyz": center, "cam_pos_xyz": cam_pos}


def toggled_orbit_camera_state(
    *,
    orbit_active: bool,
    ship_pos_xyz: tuple[float, float, float],
    cam_pos_xyz: tuple[float, float, float] | None,
    scale: float,
) -> dict[str, object]:
    if orbit_active:
        return {
            "orbit_active": False,
            "orbit_dragging": False,
            "mouse_flight_active": False,
            "lmb_down": False,
        }
    if cam_pos_xyz is None or float(scale) <= 0.0:
        return {
            "orbit_active": orbit_active,
            "orbit_dragging": False,
            "mouse_flight_active": False,
            "lmb_down": False,
        }
    sx, sy, sz = (float(v) for v in ship_pos_xyz)
    cx, cy, cz = (float(v) for v in cam_pos_xyz)
    center = (sx * float(scale), sy * float(scale), sz * float(scale))
    rx, ry, rz = cx - center[0], cy - center[1], cz - center[2]
    dist = math.sqrt(rx * rx + ry * ry + rz * rz)
    if dist < 1e-4:
        dist = 95.0
        rx, ry, rz = 0.0, 0.3, 1.0
    inv = 1.0 / dist
    dir_x, dir_y, dir_z = rx * inv, ry * inv, rz * inv
    return {
        "orbit_active": True,
        "orbit_dragging": False,
        "mouse_flight_active": False,
        "lmb_down": False,
        "orbit_distance": max(20.0, min(1200.0, dist)),
        "orbit_yaw": math.atan2(dir_x, dir_z),
        "orbit_pitch": math.asin(max(-1.0, min(1.0, dir_y))),
    }
