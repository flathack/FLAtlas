from __future__ import annotations

import math

MIN_ORBIT_CAMERA_DISTANCE = 2.0


def centered_item_camera_state(
    *,
    target_xyz: tuple[float, float, float],
    system_radius: float,
    is_zone: bool,
) -> dict[str, object]:
    return {
        "target_xyz": tuple(float(v) for v in target_xyz),
        "pitch": 1.42,
        "yaw": 0.0,
        "distance": max(
            180.0 if is_zone else 120.0,
            float(system_radius) * (0.6 if is_zone else 0.45),
        ),
    }


def build_camera_state_dict(
    *,
    target_xyz: tuple[float, float, float],
    distance: float,
    yaw: float,
    pitch: float,
) -> dict[str, float]:
    tx, ty, tz = (float(v) for v in target_xyz)
    return {
        "target_x": tx,
        "target_y": ty,
        "target_z": tz,
        "distance": float(distance),
        "yaw": float(yaw),
        "pitch": float(pitch),
    }


def normalize_camera_state(
    state: dict[str, float] | None,
    *,
    fallback_target_xyz: tuple[float, float, float],
    fallback_distance: float,
    fallback_yaw: float,
    fallback_pitch: float,
) -> dict[str, object] | None:
    if not state:
        return None
    tx, ty, tz = (float(v) for v in fallback_target_xyz)
    try:
        return {
            "target_xyz": (
                float(state.get("target_x", tx)),
                float(state.get("target_y", ty)),
                float(state.get("target_z", tz)),
            ),
            "distance": max(0.001, float(state.get("distance", fallback_distance))),
            "yaw": float(state.get("yaw", fallback_yaw)),
            "pitch": float(state.get("pitch", fallback_pitch)),
        }
    except Exception:
        return None


def camera_position(
    *,
    target_xyz: tuple[float, float, float],
    distance: float,
    yaw: float,
    pitch: float,
) -> tuple[float, float, float]:
    tx, ty, tz = (float(v) for v in target_xyz)
    cp = math.cos(float(pitch))
    return (
        tx + cp * math.sin(float(yaw)) * float(distance),
        ty + math.sin(float(pitch)) * float(distance),
        tz + cp * math.cos(float(yaw)) * float(distance),
    )


def zoomed_camera_distance(
    distance: float,
    delta: int,
    *,
    min_distance: float = MIN_ORBIT_CAMERA_DISTANCE,
    max_distance: float = 15000.0,
) -> float:
    zoom = 0.9 if delta > 0 else 1.1
    return max(float(min_distance), min(float(max_distance), float(distance) * zoom))


def panned_camera_target(
    *,
    camera_pos_xyz: tuple[float, float, float],
    target_xyz: tuple[float, float, float],
    cam_distance: float,
    dx: float,
    dy: float,
) -> tuple[float, float, float] | None:
    px, py, pz = (float(v) for v in camera_pos_xyz)
    tx, ty, tz = (float(v) for v in target_xyz)

    fwd_x, fwd_y, fwd_z = tx - px, ty - py, tz - pz
    fwd_len = math.sqrt(fwd_x * fwd_x + fwd_y * fwd_y + fwd_z * fwd_z)
    if fwd_len < 1e-6:
        return None
    fwd_x /= fwd_len
    fwd_y /= fwd_len
    fwd_z /= fwd_len

    right_x = -fwd_z
    right_y = 0.0
    right_z = fwd_x
    right_len = math.sqrt(right_x * right_x + right_y * right_y + right_z * right_z)
    if right_len < 1e-6:
        return None
    right_x /= right_len
    right_y /= right_len
    right_z /= right_len

    up_x = right_y * fwd_z - right_z * fwd_y
    up_y = right_z * fwd_x - right_x * fwd_z
    up_z = right_x * fwd_y - right_y * fwd_x
    up_len = math.sqrt(up_x * up_x + up_y * up_y + up_z * up_z)
    if up_len < 1e-6:
        return None
    up_x /= up_len
    up_y /= up_len
    up_z /= up_len

    factor = float(cam_distance) * 0.0015
    shift_x = (-right_x * float(dx) + up_x * float(dy)) * factor
    shift_y = (-right_y * float(dx) + up_y * float(dy)) * factor
    shift_z = (-right_z * float(dx) + up_z * float(dy)) * factor
    return (tx + shift_x, ty + shift_y, tz + shift_z)
