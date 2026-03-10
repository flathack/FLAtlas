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


def flight_overlay_layout(
    *,
    host_width: float,
    overlay_height: float,
    help_overlay_visible: bool,
    help_overlay_width: float,
) -> dict[str, object]:
    y = 8
    overlay_pos = (8, y)
    charge_bar_geometry = (8, y + int(float(overlay_height)) + 6, 260, 20)
    help_overlay_pos = None
    if help_overlay_visible:
        help_overlay_pos = (max(8, int(float(host_width) - float(help_overlay_width) - 8)), y)
    return {
        "overlay_pos": overlay_pos,
        "charge_bar_geometry": charge_bar_geometry,
        "help_overlay_pos": help_overlay_pos,
    }
