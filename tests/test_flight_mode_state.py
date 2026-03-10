from __future__ import annotations

from fl_editor.flight_mode_state import (
    mode_transition_state,
    normalized_chase_distance_ship_lengths,
    should_abort_cruise,
)


def test_mode_transition_state_resets_charge_and_clamps_speed_for_normal():
    state = mode_transition_state(
        mode="NORMAL",
        autopilot_mode="AUTOPILOT",
        cruise_charging_mode="CRUISE_CHARGING",
        normal_mode="NORMAL",
        speed=120.0,
        max_speed=80.0,
    )

    assert state["mode"] == "NORMAL"
    assert state["charge_elapsed"] == 0.0
    assert state["speed"] == 80.0


def test_mode_transition_state_resets_charge_for_cruise_charging():
    state = mode_transition_state(
        mode="CRUISE_CHARGING",
        autopilot_mode="AUTOPILOT",
        cruise_charging_mode="CRUISE_CHARGING",
        normal_mode="NORMAL",
        speed=20.0,
        max_speed=80.0,
    )

    assert state["charge_elapsed"] == 0.0


def test_should_abort_cruise_and_chase_distance_normalization():
    assert should_abort_cruise(mode="CRUISE_ACTIVE", cruise_charging_mode="CRUISE_CHARGING", cruise_active_mode="CRUISE_ACTIVE", s_hold_time=0.3) is True
    assert should_abort_cruise(mode="NORMAL", cruise_charging_mode="CRUISE_CHARGING", cruise_active_mode="CRUISE_ACTIVE", s_hold_time=1.0) is False
    assert normalized_chase_distance_ship_lengths(0.1) == 0.5
    assert normalized_chase_distance_ship_lengths(99.0) == 8.0
