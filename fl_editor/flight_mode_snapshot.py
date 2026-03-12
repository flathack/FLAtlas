from __future__ import annotations

from .flight_mode_targets import autopilot_target_state, selection_target_state


def flight_target_context_state(
    *,
    selection_name: str | None,
    selection_distance: float | None,
    mode: str,
    autopilot_mode: str,
    auto_target_name: str,
    auto_target_distance: float | None,
) -> dict[str, object]:
    return {
        "selection": selection_target_state(
            selected_name=selection_name,
            selected_distance=selection_distance,
        ),
        "autopilot": autopilot_target_state(
            mode=mode,
            autopilot_mode=autopilot_mode,
            auto_target_name=auto_target_name,
            auto_target_distance=auto_target_distance,
        ),
    }
