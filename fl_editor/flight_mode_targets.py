from __future__ import annotations


def selection_target_state(*, selected_name: str | None, selected_distance: float | None) -> dict[str, object]:
    if selected_distance is None:
        return {
            "name": "",
            "distance": None,
        }
    return {
        "name": str(selected_name or "Selection"),
        "distance": float(selected_distance),
    }


def autopilot_target_state(
    *,
    mode: str,
    autopilot_mode: str,
    auto_target_name: str,
    auto_target_distance: float | None,
) -> dict[str, object]:
    if mode != autopilot_mode or auto_target_distance is None:
        return {
            "name": str(auto_target_name or ""),
            "distance": None,
        }
    return {
        "name": str(auto_target_name or ""),
        "distance": float(auto_target_distance),
    }
