from __future__ import annotations

from fl_editor.flight_mode_mouse import mouse_move_state, mouse_press_state, mouse_release_state, wheel_state


def test_mouse_press_state_handles_orbit_and_free_flight_modes():
    orbit = mouse_press_state(
        active=True,
        is_left_button=True,
        orbit_cam_active=True,
        mouse_pos_xy=(10.0, 20.0),
    )
    free = mouse_press_state(
        active=True,
        is_left_button=True,
        orbit_cam_active=False,
        mouse_pos_xy=(30.0, 40.0),
    )

    assert orbit["orbit_dragging"] is True
    assert orbit["orbit_last_mouse_xy"] == (10.0, 20.0)
    assert free["lmb_down"] is True
    assert free["mouse_pos_xy"] == (30.0, 40.0)


def test_mouse_release_state_resets_expected_flags():
    orbit = mouse_release_state(active=True, is_left_button=True, orbit_cam_active=True)
    free = mouse_release_state(active=True, is_left_button=True, orbit_cam_active=False)

    assert orbit["orbit_dragging"] is False
    assert free["lmb_down"] is False
    assert free["mouse_strength"] == 0.0


def test_mouse_move_state_updates_orbit_angles_or_mouse_position():
    orbit = mouse_move_state(
        active=True,
        orbit_cam_active=True,
        orbit_dragging=True,
        orbit_last_mouse_xy=(10.0, 20.0),
        mouse_pos_xy=(20.0, 10.0),
        orbit_yaw=1.0,
        orbit_pitch=0.0,
    )
    free = mouse_move_state(
        active=True,
        orbit_cam_active=False,
        orbit_dragging=False,
        orbit_last_mouse_xy=None,
        mouse_pos_xy=(5.0, 6.0),
        orbit_yaw=1.0,
        orbit_pitch=0.0,
    )

    assert round(float(orbit["orbit_yaw"]), 3) == 0.92
    assert round(float(orbit["orbit_pitch"]), 3) == -0.08
    assert orbit["orbit_last_mouse_xy"] == (20.0, 10.0)
    assert free["mouse_pos_xy"] == (5.0, 6.0)


def test_wheel_state_clamps_orbit_distance():
    zoom_in = wheel_state(active=True, orbit_cam_active=True, delta_y=120.0, orbit_distance=30.0)
    zoom_out = wheel_state(active=True, orbit_cam_active=True, delta_y=-120.0, orbit_distance=2000.0)
    ignored = wheel_state(active=False, orbit_cam_active=True, delta_y=120.0, orbit_distance=30.0)

    assert round(float(zoom_in["orbit_distance"]), 1) == 25.8
    assert float(zoom_out["orbit_distance"]) == 1200.0
    assert ignored["handled"] is False
