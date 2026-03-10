from __future__ import annotations

from fl_editor.flight_mode_viewport import viewport_camera_pose_state


def test_viewport_camera_pose_state_for_chase_camera():
    state = viewport_camera_pose_state(
        orbit_cam_active=False,
        ship_pos_xyz=(100.0, 200.0, 300.0),
        scale=2.0,
        forward_xyz=(0.0, 0.0, 1.0),
        chase_distance_ship_lengths=3.0,
        orbit_yaw=0.0,
        orbit_pitch=0.0,
        orbit_distance=0.0,
    )

    assert state["cam_pos_xyz"] == (200.0, 400.0, 578.4)
    assert state["view_center_xyz"] == (200.0, 400.0, 820.0)
    assert state["sync_sky"] is True
    assert state["update_labels"] is True


def test_viewport_camera_pose_state_for_orbit_camera():
    state = viewport_camera_pose_state(
        orbit_cam_active=True,
        ship_pos_xyz=(0.0, 0.0, 0.0),
        scale=1.0,
        forward_xyz=(1.0, 0.0, 0.0),
        chase_distance_ship_lengths=2.0,
        orbit_yaw=0.0,
        orbit_pitch=0.0,
        orbit_distance=10.0,
    )

    assert state["cam_pos_xyz"] == (0.0, 0.0, 10.0)
    assert state["view_center_xyz"] == (0.0, 0.0, 0.0)
    assert state["sync_sky"] is True
    assert state["update_labels"] is True
