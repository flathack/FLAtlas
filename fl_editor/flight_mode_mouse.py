from __future__ import annotations


def mouse_press_state(
    *,
    active: bool,
    is_left_button: bool,
    orbit_cam_active: bool,
    mouse_pos_xy: tuple[float, float],
) -> dict[str, object]:
    if not active or not is_left_button:
        return {"handled": False}
    if orbit_cam_active:
        return {
            "handled": True,
            "orbit_dragging": True,
            "orbit_last_mouse_xy": mouse_pos_xy,
            "lmb_down": False,
            "mouse_flight_active": False,
        }
    return {
        "handled": True,
        "lmb_down": True,
        "lmb_hold_time": 0.0,
        "mouse_flight_active": False,
        "mouse_pos_xy": mouse_pos_xy,
    }


def mouse_release_state(*, active: bool, is_left_button: bool, orbit_cam_active: bool) -> dict[str, object]:
    if not active or not is_left_button:
        return {"handled": False}
    if orbit_cam_active:
        return {"handled": True, "orbit_dragging": False}
    return {
        "handled": True,
        "lmb_down": False,
        "lmb_hold_time": 0.0,
        "mouse_flight_active": False,
        "mouse_strength": 0.0,
    }


def mouse_move_state(
    *,
    active: bool,
    orbit_cam_active: bool,
    orbit_dragging: bool,
    orbit_last_mouse_xy: tuple[float, float] | None,
    mouse_pos_xy: tuple[float, float],
    orbit_yaw: float,
    orbit_pitch: float,
) -> dict[str, object]:
    if not active:
        return {"handled": False}
    if orbit_cam_active:
        state: dict[str, object] = {"handled": True}
        if orbit_dragging and orbit_last_mouse_xy is not None:
            dx = float(mouse_pos_xy[0]) - float(orbit_last_mouse_xy[0])
            dy = float(mouse_pos_xy[1]) - float(orbit_last_mouse_xy[1])
            state["orbit_last_mouse_xy"] = mouse_pos_xy
            state["orbit_yaw"] = float(orbit_yaw) - dx * 0.008
            state["orbit_pitch"] = max(-1.35, min(1.35, float(orbit_pitch) + dy * 0.008))
        return state
    return {"handled": True, "mouse_pos_xy": mouse_pos_xy}


def wheel_state(*, active: bool, orbit_cam_active: bool, delta_y: float, orbit_distance: float) -> dict[str, object]:
    if not active or not orbit_cam_active:
        return {"handled": False}
    zoom = 0.86 if float(delta_y) > 0.0 else 1.14
    return {
        "handled": True,
        "orbit_distance": max(20.0, min(1200.0, float(orbit_distance) * zoom)),
    }
