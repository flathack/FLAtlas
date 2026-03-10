from __future__ import annotations

from typing import Any


def object_nick_index(objects: list[Any]) -> dict[str, Any]:
    return {
        str(getattr(obj, "nickname", "")).strip().lower(): obj
        for obj in list(objects or [])
        if str(getattr(obj, "nickname", "")).strip()
    }


def scene_camera_state_from_points(points_xyz: list[tuple[float, float, float]]) -> dict[str, object]:
    if not points_xyz:
        return {
            "cam_target_xyz": (0.0, 0.0, 0.0),
            "cam_distance": 500.0,
            "system_center_xyz": (0.0, 0.0, 0.0),
            "system_radius": 500.0,
            "cam_yaw": 0.0,
            "cam_pitch": 1.42,
        }

    xs = [float(x) for x, _, _ in points_xyz]
    ys = [float(y) for _, y, _ in points_xyz]
    zs = [float(z) for _, _, z in points_xyz]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)
    cx = (min_x + max_x) * 0.5
    cy = (min_y + max_y) * 0.5
    cz = (min_z + max_z) * 0.5
    radius = max(max_x - min_x, max_z - min_z, (max_y - min_y) * 0.5, 120.0)
    return {
        "cam_target_xyz": (cx, cy, cz),
        "cam_distance": max(240.0, radius * 1.3),
        "system_center_xyz": (cx, cy, cz),
        "system_radius": radius,
        "cam_yaw": 0.0,
        "cam_pitch": 1.42,
    }
