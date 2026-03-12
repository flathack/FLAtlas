from __future__ import annotations

from .flight_mode_camera import chase_camera_pose, orbit_camera_pose


def viewport_camera_pose_state(
    *,
    orbit_cam_active: bool,
    ship_pos_xyz: tuple[float, float, float],
    scale: float,
    forward_xyz: tuple[float, float, float] | None,
    chase_distance_ship_lengths: float,
    orbit_yaw: float,
    orbit_pitch: float,
    orbit_distance: float,
) -> dict[str, object]:
    if orbit_cam_active:
        pose = orbit_camera_pose(
            ship_pos_xyz=ship_pos_xyz,
            scale=scale,
            orbit_yaw=orbit_yaw,
            orbit_pitch=orbit_pitch,
            orbit_distance=orbit_distance,
        )
        return {
            "cam_pos_xyz": pose["cam_pos_xyz"],
            "view_center_xyz": pose["center_xyz"],
            "sync_sky": True,
            "update_labels": True,
        }

    pose = chase_camera_pose(
        ship_pos_xyz=ship_pos_xyz,
        forward_xyz=forward_xyz or (0.0, 0.0, 1.0),
        scale=scale,
        chase_distance_ship_lengths=chase_distance_ship_lengths,
    )
    return {
        "cam_pos_xyz": pose["cam_pos_xyz"],
        "view_center_xyz": pose["cam_view_xyz"],
        "sync_sky": True,
        "update_labels": True,
    }
