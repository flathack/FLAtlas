from __future__ import annotations

import random

from fl_editor.view_3d_flight_visuals import dust_update_state, flight_ship_render_pose, initial_dust_positions


def test_initial_dust_positions_match_expected_ranges():
    positions = initial_dust_positions(5, random.Random(123))

    assert len(positions) == 5
    for x, y, z in positions:
        assert -26.0 <= x <= 26.0
        assert -14.0 <= y <= 12.0
        assert 8.0 <= z <= 180.0


def test_flight_ship_render_pose_prefers_camera_near_position():
    state = flight_ship_render_pose(
        snapshot={"pos": (10.0, 20.0, 30.0), "yaw_deg": 15.0, "pitch_deg": 5.0, "ship_tilt_deg": 2.0},
        scene_scale=10.0,
        camera_pos_xyz=(0.0, 0.0, 0.0),
        camera_view_center_xyz=(0.0, 0.0, 10.0),
    )

    assert state["pos_xyz"] == (0.0, 0.0, 2.1)
    assert state["rotation_euler_deg"] == (7.0, 15.0, 0.0)


def test_flight_ship_render_pose_falls_back_to_scaled_world_position():
    state = flight_ship_render_pose(
        snapshot={"pos": (1.0, 2.0, 3.0)},
        scene_scale=5.0,
        camera_pos_xyz=None,
        camera_view_center_xyz=None,
    )

    assert state["pos_xyz"] == (5.0, 10.0, 15.0)
    assert state["rotation_euler_deg"] == (0.0, 0.0, 0.0)


def test_dust_update_state_advances_and_reseeds_particles():
    state = dust_update_state(
        snapshot={"pos": (1.0, 2.0, 3.0), "forward": (0.0, 0.0, 1.0), "speed": 100.0},
        local_positions_xyz=[(1.0, 2.0, 1.0), (0.0, 0.0, 20.0)],
        scene_scale=2.0,
        dt=0.5,
        rng=random.Random(42),
    )

    assert state["enabled"] is True
    assert len(state["local_positions_xyz"]) == 2
    reseeded = state["local_positions_xyz"][0]
    assert -26.0 <= reseeded[0] <= 26.0
    assert -14.0 <= reseeded[1] <= 12.0
    assert 130.0 <= reseeded[2] <= 220.0
    assert round(state["local_positions_xyz"][1][2], 1) == 9.0
    assert len(state["world_positions_xyz"]) == 2
