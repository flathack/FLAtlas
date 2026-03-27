from __future__ import annotations

from fl_editor.freelancer_mesh_data import FreelancerBounds
from fl_editor.view_3d_native_detail_state import (
    centered_native_detail_camera_state,
    native_detail_transform_cache_key,
    native_detail_transform_state,
    selected_native_detail_state,
)


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
        scene_scale=0.5,
    )

    assert state["target_xyz"] == (11.0, 21.0, 31.0)
    assert state["pitch"] == 1.42
    assert state["yaw"] == 0.0
    assert state["distance"] == 120.0


def test_native_detail_transform_state_uses_scene_scale_for_world_sized_geometry():
    bounds = FreelancerBounds(min_xyz=(-400.0, -400.0, -400.0), max_xyz=(400.0, 400.0, 400.0), radius=400.0)
    state = native_detail_transform_state(
        nickname="Li01_Trade_Lane_Ring_189",
        archetype="Trade_Lane_Ring",
        bounds=bounds,
        label_y_offset=2.8,
        scene_scale=0.01,
    )

    assert float(state["scale"]) == 0.01


def test_native_detail_transform_state_uprights_trade_lane_when_thin_axis_is_y():
    bounds = FreelancerBounds(min_xyz=(-5.0, -0.25, -5.0), max_xyz=(5.0, 0.25, 5.0), radius=5.0)
    state = native_detail_transform_state(
        nickname="Li01_Trade_Lane_Ring_189",
        archetype="Trade_Lane_Ring",
        bounds=bounds,
        label_y_offset=2.8,
    )

    assert state["rotate_euler_deg"] == (90.0, 0.0, 0.0)


def test_native_detail_transform_cache_key_rounds_values_stably():
    key = native_detail_transform_cache_key(
        scale=0.123456789,
        rotate_euler_deg=(89.9998, 0.0004, -0.0004),
    )

    assert key == (0.123457, (90.0, 0.0, -0.0))


def test_native_detail_transform_state_applies_cmp_up_correction():
    bounds = FreelancerBounds(min_xyz=(-5.0, -5.0, -5.0), max_xyz=(5.0, 5.0, 5.0), radius=5.0)
    state = native_detail_transform_state(
        nickname="Li01_08",
        archetype="Jump_gate",
        bounds=bounds,
        label_y_offset=2.8,
        cmp_up_correction_euler_deg=(-90.0, 0.0, 0.0),
    )

    assert state["rotate_euler_deg"] == (-90.0, 0.0, 0.0)


def test_native_detail_transform_state_defaults_to_no_correction():
    bounds = FreelancerBounds(min_xyz=(-5.0, -5.0, -5.0), max_xyz=(5.0, 5.0, 5.0), radius=5.0)
    state = native_detail_transform_state(
        nickname="Li01_08",
        archetype="Jump_gate",
        bounds=bounds,
        label_y_offset=2.8,
    )

    assert state["rotate_euler_deg"] == (0.0, 0.0, 0.0)


def test_native_detail_transform_state_combines_cmp_correction_with_trade_lane_rotation():
    bounds = FreelancerBounds(min_xyz=(-5.0, -0.25, -5.0), max_xyz=(5.0, 0.25, 5.0), radius=5.0)
    state = native_detail_transform_state(
        nickname="Li01_Trade_Lane_Ring_189",
        archetype="Trade_Lane_Ring",
        bounds=bounds,
        label_y_offset=2.8,
        cmp_up_correction_euler_deg=(10.0, 20.0, 30.0),
    )

    assert state["rotate_euler_deg"] == (100.0, 20.0, 30.0)
