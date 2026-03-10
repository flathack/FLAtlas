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


def flight_dust_apply_state(*, dust_count: int, enabled: bool) -> dict[str, object]:
    return {
        "enabled_states": [bool(enabled)] * max(0, int(dust_count)),
    }
