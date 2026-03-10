from __future__ import annotations

from .view_3d_camera import camera_position
from .view_3d_runtime_state import label_scale_for_distance, orbit_state_from_camera


def camera_update_effects_state(
    *,
    target_xyz: tuple[float, float, float],
    distance: float,
    yaw: float,
    pitch: float,
    label_positions_xyz: list[tuple[float, float, float]],
    scale_factor: float,
    scale_min: float,
    scale_max: float,
) -> dict[str, object]:
    camera_pos_xyz = camera_position(
        target_xyz=target_xyz,
        distance=distance,
        yaw=yaw,
        pitch=pitch,
    )
    label_scales = []
    for label_pos_xyz in label_positions_xyz:
        dx = float(label_pos_xyz[0]) - float(camera_pos_xyz[0])
        dy = float(label_pos_xyz[1]) - float(camera_pos_xyz[1])
        dz = float(label_pos_xyz[2]) - float(camera_pos_xyz[2])
        distance_to_camera = (dx * dx + dy * dy + dz * dz) ** 0.5
        label_scales.append(
            label_scale_for_distance(
                distance=distance_to_camera,
                scale_factor=scale_factor,
                scale_min=scale_min,
                scale_max=scale_max,
            )
        )
    return {
        "camera_pos_xyz": camera_pos_xyz,
        "label_scales": label_scales,
        "sky_translation_xyz": camera_pos_xyz,
    }


def synced_orbit_camera_state(*, camera_pos_xyz: tuple[float, float, float], view_center_xyz: tuple[float, float, float]) -> dict[str, object] | None:
    return orbit_state_from_camera(camera_pos_xyz=camera_pos_xyz, view_center_xyz=view_center_xyz)
