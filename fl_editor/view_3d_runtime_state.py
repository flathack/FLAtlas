from __future__ import annotations

import math


def orbit_state_from_camera(
    *,
    camera_pos_xyz: tuple[float, float, float] | None,
    view_center_xyz: tuple[float, float, float] | None,
) -> dict[str, object] | None:
    if camera_pos_xyz is None or view_center_xyz is None:
        return None
    vx = float(camera_pos_xyz[0]) - float(view_center_xyz[0])
    vy = float(camera_pos_xyz[1]) - float(view_center_xyz[1])
    vz = float(camera_pos_xyz[2]) - float(view_center_xyz[2])
    dist = math.sqrt(vx * vx + vy * vy + vz * vz)
    if dist < 1e-6:
        return None
    dir_x = vx / dist
    dir_y = vy / dist
    dir_z = vz / dist
    return {
        "target_xyz": (float(view_center_xyz[0]), float(view_center_xyz[1]), float(view_center_xyz[2])),
        "distance": max(0.001, dist),
        "yaw": math.atan2(dir_x, dir_z),
        "pitch": math.asin(max(-1.0, min(1.0, dir_y))),
    }


def label_scale_for_distance(*, distance: float, scale_factor: float, scale_min: float, scale_max: float) -> float:
    return max(float(scale_min), min(float(scale_max), float(distance) * float(scale_factor)))
