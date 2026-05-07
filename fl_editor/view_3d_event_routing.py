from __future__ import annotations


def should_capture_locked_axis_wheel(*, event_type: str, locked_axis: str | None, has_selected_obj: bool) -> bool:
    return event_type == "wheel" and bool(locked_axis) and bool(has_selected_obj)


def should_process_qt3d_interaction(*, qt3d_available: bool, target_matches: bool) -> bool:
    return bool(qt3d_available and target_matches)
