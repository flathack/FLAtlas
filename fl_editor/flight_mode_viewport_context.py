from __future__ import annotations

from typing import Any, Callable


def viewport_camera_pose_context(
    *,
    viewport: Any,
    pose_builder: Callable[..., dict[str, object]],
    orbit_cam_active: bool,
    ship_pos_xyz: tuple[float, float, float],
    forward_xyz: tuple[float, float, float],
    chase_distance_ship_lengths: float,
    orbit_yaw: float,
    orbit_pitch: float,
    orbit_distance: float,
) -> tuple[object | None, dict[str, object] | None]:
    if viewport is None:
        return None, None
    cam = getattr(viewport, "_camera", None)
    if cam is None:
        return None, None
    scale = float(getattr(viewport, "_scene_scale", 1.0) or 1.0)
    state = pose_builder(
        orbit_cam_active=orbit_cam_active,
        ship_pos_xyz=ship_pos_xyz,
        scale=scale,
        forward_xyz=forward_xyz,
        chase_distance_ship_lengths=chase_distance_ship_lengths,
        orbit_yaw=orbit_yaw,
        orbit_pitch=orbit_pitch,
        orbit_distance=orbit_distance,
    )
    return cam, state


def viewport_orbit_toggle_context(
    *,
    viewport: Any,
    orbit_toggle_builder: Callable[..., dict[str, object]],
    orbit_active: bool,
    ship_pos_xyz: tuple[float, float, float],
) -> dict[str, object] | None:
    if viewport is None:
        return None
    cam = getattr(viewport, "_camera", None)
    scale = float(getattr(viewport, "_scene_scale", 1.0) or 1.0)
    if cam is None or scale <= 0.0:
        return None
    pos = cam.position()
    return orbit_toggle_builder(
        orbit_active=orbit_active,
        ship_pos_xyz=ship_pos_xyz,
        cam_pos_xyz=(pos.x(), pos.y(), pos.z()),
        scale=scale,
    )
