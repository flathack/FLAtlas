from __future__ import annotations

import math

from fl_editor.view_3d_runtime_state import flight_overlay_layout, label_scale_for_distance, orbit_state_from_camera


def test_orbit_state_from_camera_builds_expected_angles_and_distance():
    state = orbit_state_from_camera(
        camera_pos_xyz=(0.0, 0.0, 100.0),
        view_center_xyz=(0.0, 0.0, 0.0),
    )

    assert state is not None
    assert state["target_xyz"] == (0.0, 0.0, 0.0)
    assert state["distance"] == 100.0
    assert round(float(state["yaw"]), 3) == 0.0
    assert round(float(state["pitch"]), 3) == 0.0


def test_orbit_state_from_camera_returns_none_for_degenerate_vector():
    assert orbit_state_from_camera(camera_pos_xyz=(1.0, 2.0, 3.0), view_center_xyz=(1.0, 2.0, 3.0)) is None


def test_label_scale_for_distance_clamps_to_bounds():
    assert label_scale_for_distance(distance=10.0, scale_factor=0.1, scale_min=2.0, scale_max=5.0) == 2.0
    assert label_scale_for_distance(distance=40.0, scale_factor=0.1, scale_min=2.0, scale_max=5.0) == 4.0
    assert label_scale_for_distance(distance=100.0, scale_factor=0.1, scale_min=2.0, scale_max=5.0) == 5.0


def test_flight_overlay_layout_positions_help_overlay_on_right():
    state = flight_overlay_layout(
        host_width=1000.0,
        overlay_height=40.0,
        help_overlay_visible=True,
        help_overlay_width=250.0,
    )

    assert state["overlay_pos"] == (8, 8)
    assert state["charge_bar_geometry"] == (8, 54, 260, 20)
    assert state["help_overlay_pos"] == (742, 8)
