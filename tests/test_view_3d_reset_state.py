from __future__ import annotations

from fl_editor.view_3d_reset_state import gizmo_clear_state, scene_clear_state


def test_scene_clear_state_resets_all_scene_collections_and_selection():
    state = scene_clear_state()

    assert state["clear_obj_map"] is True
    assert state["clear_zone_entities"] is True
    assert state["selected_obj"] is None
    assert state["locked_axis"] is None
    assert state["clear_axis_gizmo"] is True


def test_gizmo_clear_state_resets_nodes_and_locked_axis():
    state = gizmo_clear_state(has_locked_axis=True)
    unlocked = gizmo_clear_state(has_locked_axis=False)

    assert state["clear_entities"] is True
    assert state["axis_gizmo_center"] is None
    assert state["clear_locked_axis"] is True
    assert unlocked["clear_locked_axis"] is False
