from __future__ import annotations

from types import SimpleNamespace

from fl_editor.view_3d_scene_state import object_nick_index, scene_camera_state_from_points


def test_object_nick_index_uses_lowercase_trimmed_nicknames():
    objects = [
        SimpleNamespace(nickname="  Alpha "),
        SimpleNamespace(nickname="Beta"),
        SimpleNamespace(nickname=""),
    ]

    index = object_nick_index(objects)

    assert set(index.keys()) == {"alpha", "beta"}
    assert index["alpha"] is objects[0]


def test_scene_camera_state_from_points_uses_bounds_and_defaults():
    populated = scene_camera_state_from_points([(0.0, 10.0, 20.0), (100.0, 30.0, -20.0)])
    empty = scene_camera_state_from_points([])

    assert populated["cam_target_xyz"] == (50.0, 20.0, 0.0)
    assert populated["system_center_xyz"] == (50.0, 20.0, 0.0)
    assert populated["system_radius"] == 120.0
    assert populated["cam_distance"] == 240.0
    assert populated["cam_pitch"] == 1.42

    assert empty["cam_target_xyz"] == (0.0, 0.0, 0.0)
    assert empty["cam_distance"] == 500.0
    assert empty["system_radius"] == 500.0
