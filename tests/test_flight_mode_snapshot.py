from __future__ import annotations

from fl_editor.flight_mode_snapshot import flight_target_context_state


def test_flight_target_context_state_builds_selection_and_autopilot_context():
    state = flight_target_context_state(
        selection_name="rheinland_gate",
        selection_distance=150.0,
        mode="AUTOPILOT",
        autopilot_mode="AUTOPILOT",
        auto_target_name="li01_to_li02",
        auto_target_distance=800.0,
    )

    assert state["selection"] == {
        "name": "rheinland_gate",
        "distance": 150.0,
    }
    assert state["autopilot"] == {
        "name": "li01_to_li02",
        "distance": 800.0,
    }


def test_flight_target_context_state_handles_missing_distances():
    state = flight_target_context_state(
        selection_name="rheinland_gate",
        selection_distance=None,
        mode="NORMAL",
        autopilot_mode="AUTOPILOT",
        auto_target_name="li01_to_li02",
        auto_target_distance=800.0,
    )

    assert state["selection"] == {
        "name": "",
        "distance": None,
    }
    assert state["autopilot"] == {
        "name": "li01_to_li02",
        "distance": None,
    }
