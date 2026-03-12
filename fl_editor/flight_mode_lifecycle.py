from __future__ import annotations


def start_state(*, normal_mode: str, max_speed: float) -> dict[str, object]:
    return {
        "active": True,
        "mode": normal_mode,
        "speed": float(max_speed),
        "mouse_flight_active": False,
        "lmb_down": False,
        "lmb_hold_time": 0.0,
        "clear_keys_down": True,
        "shift_down": False,
        "s_hold_time": 0.0,
        "charge_elapsed": 0.0,
        "auto_target": None,
        "target_name": "",
        "auto_cruise_charging": False,
        "auto_cruise_active": False,
        "lane_points": [],
        "lane_index": 0,
        "orbit_cam_active": False,
        "orbit_dragging": False,
        "overlay_text": "",
        "start_timer": True,
        "emit_hud": True,
    }


def stop_state(*, normal_mode: str) -> dict[str, object]:
    return {
        "active": False,
        "mode": normal_mode,
        "mouse_flight_active": False,
        "clear_keys_down": True,
        "shift_down": False,
        "stop_timer": True,
        "orbit_cam_active": False,
        "orbit_dragging": False,
        "overlay_text": "",
        "emit_hud": True,
    }
