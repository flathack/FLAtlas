from __future__ import annotations

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
