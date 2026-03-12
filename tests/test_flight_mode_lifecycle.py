from __future__ import annotations

from fl_editor.flight_mode_lifecycle import start_state, stop_state


def test_start_state_resets_runtime_flags_and_starts_timer():
    state = start_state(normal_mode="NORMAL", max_speed=80.0)

    assert state["active"] is True
    assert state["mode"] == "NORMAL"
    assert state["speed"] == 80.0
    assert state["mouse_flight_active"] is False
    assert state["clear_keys_down"] is True
    assert state["lane_points"] == []
    assert state["lane_index"] == 0
    assert state["start_timer"] is True
    assert state["emit_hud"] is True


def test_stop_state_disables_runtime_and_stops_timer():
    state = stop_state(normal_mode="NORMAL")

    assert state["active"] is False
    assert state["mode"] == "NORMAL"
    assert state["clear_keys_down"] is True
    assert state["stop_timer"] is True
    assert state["orbit_cam_active"] is False
    assert state["emit_hud"] is True
