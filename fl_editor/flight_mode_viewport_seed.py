from __future__ import annotations

from typing import Any, Callable


def viewport_camera_seed_state(
    *,
    viewport: Any,
    seed_builder: Callable[..., dict[str, object]],
) -> dict[str, object]:
    cam = getattr(viewport, "_camera", None) if viewport is not None else None
    scale = float(getattr(viewport, "_scene_scale", 1.0) or 1.0) if viewport is not None else 1.0
    cam_pos_xyz = None
    view_center_xyz = None
    if cam is not None:
        cam_pos = cam.position()
        view_center = cam.viewCenter()
        cam_pos_xyz = (cam_pos.x(), cam_pos.y(), cam_pos.z())
        view_center_xyz = (view_center.x(), view_center.y(), view_center.z())
    return seed_builder(
        cam_pos_xyz=cam_pos_xyz,
        view_center_xyz=view_center_xyz,
        scale=scale,
    )
