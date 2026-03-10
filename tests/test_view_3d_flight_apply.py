from __future__ import annotations

from fl_editor.view_3d_flight_apply import flight_camera_context_state, flight_dust_apply_state


def test_flight_camera_context_state_without_camera():
    assert flight_camera_context_state(
        has_camera=False,
        camera_pos_xyz=(1.0, 2.0, 3.0),
        camera_view_center_xyz=(4.0, 5.0, 6.0),
    ) == {
        "camera_pos_xyz": None,
        "camera_view_center_xyz": None,
    }


def test_flight_camera_context_state_with_camera():
    assert flight_camera_context_state(
        has_camera=True,
        camera_pos_xyz=(1.0, 2.0, 3.0),
        camera_view_center_xyz=(4.0, 5.0, 6.0),
    ) == {
        "camera_pos_xyz": (1.0, 2.0, 3.0),
        "camera_view_center_xyz": (4.0, 5.0, 6.0),
    }


def test_flight_dust_apply_state_repeats_enabled_flag():
    assert flight_dust_apply_state(dust_count=3, enabled=True) == {
        "enabled_states": [True, True, True],
    }
    assert flight_dust_apply_state(dust_count=2, enabled=False) == {
        "enabled_states": [False, False],
    }
