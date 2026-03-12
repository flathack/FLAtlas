from __future__ import annotations

from fl_editor.view_3d_object_updates import object_position_update_state


def test_object_position_update_state_scales_position_and_label_offset():
    state = object_position_update_state(pos_raw="1,2,3", scale=10.0, label_y_offset=4.5)

    assert state["translation_xyz"] == (10.0, 20.0, 30.0)
    assert state["label_translation_xyz"] == (11.0, 24.5, 31.0)


def test_object_position_update_state_handles_short_pos_formats():
    state = object_position_update_state(pos_raw="5,6", scale=2.0, label_y_offset=3.8)

    assert state["translation_xyz"] == (10.0, 12.0, 0.0)
