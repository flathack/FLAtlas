from __future__ import annotations


def flight_camera_context_state(
    *,
    has_camera: bool,
    camera_pos_xyz: tuple[float, float, float] | None,
    camera_view_center_xyz: tuple[float, float, float] | None,
) -> dict[str, object]:
    if not has_camera:
        return {
            "camera_pos_xyz": None,
            "camera_view_center_xyz": None,
        }
    return {
        "camera_pos_xyz": camera_pos_xyz,
        "camera_view_center_xyz": camera_view_center_xyz,
    }


def flight_camera_context_from_camera(*, camera: object | None) -> dict[str, object]:
    if camera is None:
        return flight_camera_context_state(
            has_camera=False,
            camera_pos_xyz=None,
            camera_view_center_xyz=None,
        )
    cam_pos = camera.position()
    cam_view_center = camera.viewCenter()
    return flight_camera_context_state(
        has_camera=True,
        camera_pos_xyz=(cam_pos.x(), cam_pos.y(), cam_pos.z()),
        camera_view_center_xyz=(cam_view_center.x(), cam_view_center.y(), cam_view_center.z()),
    )


def flight_dust_apply_state(*, dust_count: int, enabled: bool) -> dict[str, object]:
    return {
        "enabled_states": [bool(enabled)] * max(0, int(dust_count)),
    }
