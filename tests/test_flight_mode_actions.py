from __future__ import annotations

from fl_editor.flight_mode_actions import autopilot_selection_state, free_flight_state, should_run_flight_action


def test_autopilot_selection_state_requires_editor_and_target_position():
    assert autopilot_selection_state(
        has_editor=False,
        target_name="rheinland_gate",
        target_pos_xyz=(1.0, 2.0, 3.0),
        autopilot_mode="AUTOPILOT",
    ) is None

    assert autopilot_selection_state(
        has_editor=True,
        target_name="rheinland_gate",
        target_pos_xyz=None,
        autopilot_mode="AUTOPILOT",
    ) is None


def test_autopilot_selection_state_defaults_target_name():
    state = autopilot_selection_state(
        has_editor=True,
        target_name="",
        target_pos_xyz=(1.0, 2.0, 3.0),
        autopilot_mode="AUTOPILOT",
    )

    assert state == {
        "auto_target_name": "Target",
        "mode": "AUTOPILOT",
    }


def test_free_flight_state_clears_lane_and_target_state():
    state = free_flight_state(active=True, normal_mode="NORMAL")

    assert state == {
        "mode": "NORMAL",
        "lane_points": [],
        "lane_index": 0,
        "auto_target": None,
        "target_name": "",
    }
    assert free_flight_state(active=False, normal_mode="NORMAL") is None


def test_should_run_flight_action_reflects_active_state():
    assert should_run_flight_action(active=True) is True
    assert should_run_flight_action(active=False) is False
