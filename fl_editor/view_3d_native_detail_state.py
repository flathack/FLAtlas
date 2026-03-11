from __future__ import annotations

from typing import Any

from .freelancer_mesh_data import FreelancerBounds


def selected_native_detail_state(
    *,
    selected_obj: Any,
    requested_obj: Any,
    has_scene_data: bool,
) -> dict[str, object]:
    if selected_obj is None:
        return {
            "clear_detail": True,
            "store_detail": False,
        }
    if requested_obj is not selected_obj:
        return {
            "clear_detail": True,
            "store_detail": False,
        }
    if not has_scene_data:
        return {
            "clear_detail": True,
            "store_detail": False,
        }
    return {
        "clear_detail": False,
        "store_detail": True,
    }


def centered_native_detail_camera_state(
    *,
    object_translation_xyz: tuple[float, float, float],
    bounds: FreelancerBounds,
) -> dict[str, object]:
    center_x = (bounds.min_xyz[0] + bounds.max_xyz[0]) * 0.5
    center_y = (bounds.min_xyz[1] + bounds.max_xyz[1]) * 0.5
    center_z = (bounds.min_xyz[2] + bounds.max_xyz[2]) * 0.5
    radius = bounds.radius
    if radius is None or radius <= 1e-6:
        radius = max(
            abs(bounds.max_xyz[0] - bounds.min_xyz[0]),
            abs(bounds.max_xyz[1] - bounds.min_xyz[1]),
            abs(bounds.max_xyz[2] - bounds.min_xyz[2]),
            1.0,
        ) * 0.5
    return {
        "target_xyz": (
            float(object_translation_xyz[0]) + center_x,
            float(object_translation_xyz[1]) + center_y,
            float(object_translation_xyz[2]) + center_z,
        ),
        "pitch": 1.42,
        "yaw": 0.0,
        "distance": max(120.0, float(radius) * 3.0),
    }
