from __future__ import annotations

from fl_editor.flight_mode_camera import (
    chase_camera_pose,
    forward_vector_xyz,
    mouse_offset_state,
    orbit_camera_pose,
    seeded_flight_state_from_camera,
    toggled_orbit_camera_state,
    updated_manual_turn_state,
)


def test_seeded_flight_state_from_camera_uses_camera_direction():
    state = seeded_flight_state_from_camera(
        cam_pos_xyz=(100.0, 20.0, 50.0),
        view_center_xyz=(100.0, 20.0, 150.0),
        scale=10.0,
    )

    assert state["ship_pos_xyz"] == (10.0, 2.0, 5.0)
    assert round(state["yaw"], 3) == 0.0
    assert round(state["pitch"], 3) == 0.0


def test_mouse_offset_state_normalizes_and_applies_deadzone():
    ox, oy, strength = mouse_offset_state(
        viewport_size=(1000, 800),
        mouse_pos_xy=(700.0, 400.0),
        mouse_flight_active=True,
    )

    assert round(ox, 2) == 0.5
    assert oy == 0.0
    assert round(strength, 2) == 0.5


def test_updated_manual_turn_state_moves_rates_and_clamps_pitch():
    state = updated_manual_turn_state(
        dt=0.1,
        ox=0.5,
        oy=-0.5,
        yaw=0.0,
        pitch=0.0,
        yaw_rate=0.0,
        pitch_rate=0.0,
        yaw_rate_max=1.0,
        pitch_rate_max=2.0,
        turn_smoothing=8.0,
    )

    assert round(state["yaw_rate"], 2) == -0.4
    assert round(state["pitch_rate"], 2) == 0.8
    assert round(state["yaw"], 2) == -0.04


def test_forward_and_camera_pose_helpers_compute_positions():
    fwd = forward_vector_xyz(yaw=0.0, pitch=0.0)
    chase = chase_camera_pose(ship_pos_xyz=(10.0, 0.0, 20.0), forward_xyz=fwd, scale=2.0, chase_distance_ship_lengths=2.0)
    orbit = orbit_camera_pose(ship_pos_xyz=(10.0, 0.0, 20.0), scale=2.0, orbit_yaw=0.0, orbit_pitch=0.0, orbit_distance=50.0)

    assert fwd == (0.0, 0.0, 1.0)
    assert chase["cam_pos_xyz"] == (20.0, 0.0, 25.6)
    assert orbit["center_xyz"] == (20.0, 0.0, 40.0)
    assert orbit["cam_pos_xyz"] == (20.0, 0.0, 90.0)


def test_toggled_orbit_camera_state_enters_and_exits_orbit():
    enter = toggled_orbit_camera_state(
        orbit_active=False,
        ship_pos_xyz=(10.0, 0.0, 20.0),
        cam_pos_xyz=(20.0, 0.0, 90.0),
        scale=2.0,
    )
    exit_state = toggled_orbit_camera_state(
        orbit_active=True,
        ship_pos_xyz=(10.0, 0.0, 20.0),
        cam_pos_xyz=(20.0, 0.0, 90.0),
        scale=2.0,
    )

    assert enter["orbit_active"] is True
    assert round(enter["orbit_distance"], 1) == 50.0
    assert exit_state["orbit_active"] is False
