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


def native_detail_transform_state(
    *,
    nickname: str,
    archetype: str,
    bounds: FreelancerBounds | None,
    label_y_offset: float,
    cmp_up_correction_euler_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> dict[str, object]:
    mesh_radius = _bounds_radius(bounds)
    target_radius = max(float(label_y_offset), 1.0)
    scale = 1.0
    if mesh_radius is not None and mesh_radius > 1e-6 and mesh_radius > target_radius:
        scale = max(0.0005, min(1.0, target_radius / mesh_radius))
    rotate_euler_deg = (
        float(cmp_up_correction_euler_deg[0]),
        float(cmp_up_correction_euler_deg[1]),
        float(cmp_up_correction_euler_deg[2]),
    )
    # Some native trade-lane CMP meshes come in horizontal (XZ ring plane).
    # In System3DView, portal rings are expected upright (XY ring plane).
    if _is_trade_lane_object(nickname=nickname, archetype=archetype):
        thin_axis = _bounds_thin_axis(bounds)
        if thin_axis == "y":
            rotate_euler_deg = (
                rotate_euler_deg[0] + 90.0,
                rotate_euler_deg[1],
                rotate_euler_deg[2],
            )
    return {
        "scale": float(scale),
        "rotate_euler_deg": rotate_euler_deg,
    }


def native_detail_transform_cache_key(
    *,
    scale: float,
    rotate_euler_deg: tuple[float, float, float],
) -> tuple[float, tuple[float, float, float]]:
    return (
        round(float(scale), 6),
        (
            round(float(rotate_euler_deg[0]), 3),
            round(float(rotate_euler_deg[1]), 3),
            round(float(rotate_euler_deg[2]), 3),
        ),
    )


def _bounds_radius(bounds: FreelancerBounds | None) -> float | None:
    if bounds is None:
        return None
    radius = bounds.radius
    if radius is not None and radius > 1e-6:
        return float(radius)
    extents = (
        abs(bounds.max_xyz[0] - bounds.min_xyz[0]),
        abs(bounds.max_xyz[1] - bounds.min_xyz[1]),
        abs(bounds.max_xyz[2] - bounds.min_xyz[2]),
    )
    longest = max(extents, default=0.0)
    if longest <= 1e-6:
        return None
    return float(longest) * 0.5


def _bounds_thin_axis(bounds: FreelancerBounds | None) -> str | None:
    if bounds is None:
        return None
    extents = {
        "x": abs(bounds.max_xyz[0] - bounds.min_xyz[0]),
        "y": abs(bounds.max_xyz[1] - bounds.min_xyz[1]),
        "z": abs(bounds.max_xyz[2] - bounds.min_xyz[2]),
    }
    return min(extents, key=extents.get)


def _is_trade_lane_object(*, nickname: str, archetype: str) -> bool:
    lowered_name = str(nickname or "").lower()
    lowered_arch = str(archetype or "").lower()
    return any(tag in lowered_name or tag in lowered_arch for tag in ("trade_lane_ring", "tradelane_ring"))
