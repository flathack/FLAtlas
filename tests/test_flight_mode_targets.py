from __future__ import annotations

from fl_editor.flight_mode_targets import autopilot_target_state, selection_target_state


def test_selection_target_state_defaults_name_only_when_distance_exists():
    assert selection_target_state(selected_name="rheinland_gate", selected_distance=125.0) == {
        "name": "rheinland_gate",
        "distance": 125.0,
    }
    assert selection_target_state(selected_name="", selected_distance=125.0) == {
        "name": "Selection",
        "distance": 125.0,
    }
    assert selection_target_state(selected_name="rheinland_gate", selected_distance=None) == {
        "name": "",
        "distance": None,
    }


def test_autopilot_target_state_only_exposes_distance_in_autopilot():
    assert autopilot_target_state(
        mode="AUTOPILOT",
        autopilot_mode="AUTOPILOT",
        auto_target_name="li01_to_li02",
        auto_target_distance=800.0,
    ) == {
        "name": "li01_to_li02",
        "distance": 800.0,
    }
    assert autopilot_target_state(
        mode="NORMAL",
        autopilot_mode="AUTOPILOT",
        auto_target_name="li01_to_li02",
        auto_target_distance=800.0,
    ) == {
        "name": "li01_to_li02",
        "distance": None,
    }
