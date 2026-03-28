from __future__ import annotations

from .view_3d_camera import zoomed_camera_distance


def axis_scroll_delta(*, delta: int, axis_step_world: float, locked_axis: str | None) -> tuple[float, float, float]:
    step = float(axis_step_world) * (1.0 if int(delta) > 0 else -1.0)
    return (
        step if locked_axis == "x" else 0.0,
        step if locked_axis == "y" else 0.0,
        step if locked_axis == "z" else 0.0,
    )


def mouse_press_interaction(
    *,
    button: str,
    locked_axis: str | None,
) -> dict[str, object]:
    if button == "left":
        if locked_axis is not None:
            return {"handled": True, "clear_locked_axis": True}
        return {"handled": True, "drag_mode": "orbit"}
    if button == "right":
        return {"handled": True, "drag_mode": "pan"}
    return {"handled": False}


def mouse_move_interaction(
    *,
    drag_mode: str | None,
    delta_x: float,
    delta_y: float,
    cam_yaw: float,
    cam_pitch: float,
) -> dict[str, object]:
    if drag_mode == "orbit":
        return {
            "handled": True,
            "cam_yaw": float(cam_yaw) - float(delta_x) * 0.008,
            "cam_pitch": max(-1.45, min(1.45, float(cam_pitch) + float(delta_y) * 0.008)),
            "update_camera": True,
        }
    if drag_mode == "pan":
        return {
            "handled": True,
            "pan_dx": float(delta_x),
            "pan_dy": float(delta_y),
        }
    return {"handled": False}


def mouse_release_interaction(*, button: str) -> dict[str, object]:
    if button in ("left", "right"):
        return {"handled": True, "clear_drag_state": True}
    return {"handled": False}


def wheel_interaction(
    *,
    delta: int,
    locked_axis: str | None,
    has_selected_obj: bool,
    control_modifier_active: bool,
    cam_distance: float,
    axis_step_world: float,
    max_camera_distance: float,
) -> dict[str, object]:
    if locked_axis and has_selected_obj:
        return {
            "handled": True,
            "axis_delta": axis_scroll_delta(delta=delta, axis_step_world=axis_step_world, locked_axis=locked_axis),
        }
    if control_modifier_active and has_selected_obj:
        return {
            "handled": True,
            "height_delta": float(delta) / 120.0 * 100.0,
        }
    return {
        "handled": True,
        "cam_distance": zoomed_camera_distance(float(cam_distance), int(delta), max_distance=float(max_camera_distance)),
        "update_camera": True,
    }
