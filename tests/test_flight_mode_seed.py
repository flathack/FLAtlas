from __future__ import annotations

from fl_editor.flight_mode_seed import seeded_flight_state_from_selection


def test_seeded_flight_state_from_selection_offsets_ship_and_faces_target():
    state = seeded_flight_state_from_selection(selected_pos_xyz=(500.0, 100.0, 800.0))

    assert state == {
        "ship_pos_xyz": (2500.0, 0.0, 800.0),
        "yaw": -1.5707963267948966,
        "pitch": 0.0,
        "roll": 0.0,
    }


def test_seeded_flight_state_from_selection_returns_none_without_target():
    assert seeded_flight_state_from_selection(selected_pos_xyz=None) is None
