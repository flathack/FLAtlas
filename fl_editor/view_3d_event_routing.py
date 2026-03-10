from __future__ import annotations


def filter_flight_event_state(*, active: bool, event_type: str) -> dict[str, object] | None:
    if not active:
        return None
    if event_type in {"key_press", "key_release"}:
        return {
            "handler_name": "on_key_press" if event_type == "key_press" else "on_key_release",
            "consume_mode": "handler_result",
        }
    if event_type in {"mouse_press", "mouse_release", "mouse_move", "wheel"}:
        return {
            "handler_name": {
                "mouse_press": "on_mouse_press",
                "mouse_release": "on_mouse_release",
                "mouse_move": "on_mouse_move",
                "wheel": "on_wheel",
            }[event_type],
            "consume_mode": "always_consume" if event_type in {"mouse_move", "wheel"} else "never_consume",
        }
    return None


def widget_flight_event_state(*, active: bool, event_type: str) -> dict[str, object] | None:
    if not active:
        return None
    if event_type in {"key_press", "key_release"}:
        return {
            "handler_name": "on_key_press" if event_type == "key_press" else "on_key_release",
            "accept_mode": "handler_result",
        }
    if event_type in {"mouse_move", "wheel"}:
        return {
            "handler_name": "on_mouse_move" if event_type == "mouse_move" else "on_wheel",
            "accept_mode": "always_accept",
        }
    if event_type in {"mouse_press", "mouse_release"}:
        return {
            "handler_name": "on_mouse_press" if event_type == "mouse_press" else "on_mouse_release",
            "accept_mode": "never_accept",
        }
    return None


def should_capture_locked_axis_wheel(*, event_type: str, locked_axis: str | None, has_selected_obj: bool) -> bool:
    return event_type == "wheel" and bool(locked_axis) and bool(has_selected_obj)


def should_process_qt3d_interaction(*, qt3d_available: bool, target_matches: bool) -> bool:
    return bool(qt3d_available and target_matches)
