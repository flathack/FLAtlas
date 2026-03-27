from __future__ import annotations

from fl_editor.view_3d_camera import (
    build_camera_state_dict,
    camera_position,
    centered_item_camera_state,
    normalize_camera_state,
    panned_camera_target,
    zoomed_camera_distance,
)


def test_centered_item_camera_state_uses_zone_distance_rules():
    state = centered_item_camera_state(target_xyz=(1, 2, 3), system_radius=500.0, is_zone=True)

    assert state["target_xyz"] == (1.0, 2.0, 3.0)
    assert state["pitch"] == 1.42
    assert state["yaw"] == 0.0
    assert state["distance"] == 300.0


def test_build_and_normalize_camera_state_roundtrip():
    raw = build_camera_state_dict(target_xyz=(10, 20, 30), distance=400, yaw=0.5, pitch=1.0)
    normalized = normalize_camera_state(
        raw,
        fallback_target_xyz=(0, 0, 0),
        fallback_distance=100,
        fallback_yaw=0.0,
        fallback_pitch=0.0,
    )

    assert normalized == {
        "target_xyz": (10.0, 20.0, 30.0),
        "distance": 400.0,
        "yaw": 0.5,
        "pitch": 1.0,
    }


def test_camera_position_places_camera_in_front_of_target():
    pos = camera_position(target_xyz=(0, 0, 0), distance=100.0, yaw=0.0, pitch=0.0)

    assert pos == (0.0, 0.0, 100.0)


def test_zoomed_camera_distance_clamps():
    assert zoomed_camera_distance(25.0, 120) == 22.5
    assert zoomed_camera_distance(1.0, 120) == 2.0
    assert zoomed_camera_distance(20000.0, -120) == 15000.0


def test_panned_camera_target_moves_target_in_camera_plane():
    target = panned_camera_target(
        camera_pos_xyz=(0.0, 0.0, 100.0),
        target_xyz=(0.0, 0.0, 0.0),
        cam_distance=100.0,
        dx=10.0,
        dy=20.0,
    )

    assert target is not None
    tx, ty, tz = target
    assert round(tx, 2) == -1.5
    assert round(ty, 2) == 3.0
    assert round(tz, 2) == 0.0
