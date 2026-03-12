from __future__ import annotations


def mode_transition_state(
    *,
    mode: str,
    autopilot_mode: str,
    cruise_charging_mode: str,
    normal_mode: str,
    speed: float,
    max_speed: float,
) -> dict[str, object]:
    state: dict[str, object] = {
        "mode": mode,
        "auto_cruise_charging": False,
        "auto_cruise_active": False,
        "charge_elapsed": None,
        "speed": float(speed),
    }
    if mode == autopilot_mode:
        state["auto_cruise_charging"] = None
        state["auto_cruise_active"] = None
    if mode == cruise_charging_mode:
        state["charge_elapsed"] = 0.0
    if mode == normal_mode:
        state["charge_elapsed"] = 0.0
        state["speed"] = max(0.0, min(float(speed), float(max_speed)))
    return state


def should_abort_cruise(*, mode: str, cruise_charging_mode: str, cruise_active_mode: str, s_hold_time: float) -> bool:
    if mode not in (cruise_charging_mode, cruise_active_mode):
        return False
    return float(s_hold_time) > 0.2


def normalized_chase_distance_ship_lengths(value: float) -> float:
    return max(0.5, min(8.0, float(value)))
