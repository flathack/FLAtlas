from __future__ import annotations

from fl_editor.freelancer_mesh_data import FreelancerBounds
from fl_editor.view_3d_native_detail_state import centered_native_detail_camera_state
from fl_editor.view_3d_native_detail_state import selected_native_detail_state


def test_selected_native_detail_state_clears_without_matching_selection():
    missing = selected_native_detail_state(selected_obj=None, requested_obj=object(), has_scene_data=True)
    mismatch = selected_native_detail_state(selected_obj=object(), requested_obj=object(), has_scene_data=True)

    assert missing["clear_detail"] is True
    assert missing["store_detail"] is False
    assert mismatch["clear_detail"] is True
    assert mismatch["store_detail"] is False


def test_selected_native_detail_state_requires_scene_data_for_selected_object():
    obj = object()

    empty = selected_native_detail_state(selected_obj=obj, requested_obj=obj, has_scene_data=False)
    ready = selected_native_detail_state(selected_obj=obj, requested_obj=obj, has_scene_data=True)

    assert empty["clear_detail"] is True
    assert empty["store_detail"] is False
    assert ready["clear_detail"] is False
    assert ready["store_detail"] is True


def test_centered_native_detail_camera_state_uses_bounds_center_and_radius():
    state = centered_native_detail_camera_state(
        object_translation_xyz=(10.0, 20.0, 30.0),
        bounds=FreelancerBounds(
            min_xyz=(-2.0, -1.0, -4.0),
            max_xyz=(6.0, 5.0, 8.0),
            radius=50.0,
        ),
    )

    assert state["target_xyz"] == (12.0, 22.0, 32.0)
    assert state["pitch"] == 1.42
    assert state["yaw"] == 0.0
    assert state["distance"] == 150.0
