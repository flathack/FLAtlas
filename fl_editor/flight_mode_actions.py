from __future__ import annotations


def autopilot_selection_state(
    *,
    has_editor: bool,
    target_name: str | None,
    target_pos_xyz: tuple[float, float, float] | None,
    autopilot_mode: str,
) -> dict[str, object] | None:
    if not has_editor or target_pos_xyz is None:
        return None
    return {
        "auto_target_name": target_name or "Target",
        "mode": autopilot_mode,
    }


def free_flight_state(*, active: bool, normal_mode: str) -> dict[str, object] | None:
    if not active:
        return None
    return {
        "mode": normal_mode,
        "lane_points": [],
        "lane_index": 0,
        "auto_target": None,
        "target_name": "",
    }


def should_run_flight_action(*, active: bool) -> bool:
    return bool(active)
