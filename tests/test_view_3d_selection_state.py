from __future__ import annotations

from fl_editor.view_3d_selection_state import (
    item_visibility_state,
    label_visibility_state,
    move_mode_state,
    position_update_state,
    selection_state,
)


def test_selection_state_handles_missing_same_and_move_selection():
    missing = selection_state(has_object=False, is_same_selected=False, move_mode=False, flight_active=False)
    same = selection_state(has_object=True, is_same_selected=True, move_mode=True, flight_active=False)
    move = selection_state(has_object=True, is_same_selected=False, move_mode=True, flight_active=False)

    assert missing["clear_gizmo"] is True
    assert same["selection_changed"] is False
    assert move["show_gizmo"] is True


def test_item_visibility_state_keeps_labels_in_sync_for_objects():
    obj = item_visibility_state(is_object=True, visible=True, labels_visible=False)
    zone = item_visibility_state(is_object=False, visible=False, labels_visible=True)

    assert obj["entity_enabled"] is True
    assert obj["label_enabled"] is False
    assert zone["entity_enabled"] is False
    assert zone["label_enabled"] is None


def test_label_visibility_state_applies_global_label_toggle():
    visible = label_visibility_state(enabled=True)
    hidden = label_visibility_state(enabled=False)

    assert visible["labels_visible"] is True
    assert visible["entity_enabled"] is True
    assert hidden["labels_visible"] is False
    assert hidden["entity_enabled"] is False


def test_move_mode_state_and_position_update_state_cover_gizmo_cases():
    move = move_mode_state(enabled=True, has_selected_obj=True, has_locked_axis=True)
    stop = move_mode_state(enabled=False, has_selected_obj=True, has_locked_axis=False)
    position = position_update_state(is_selected=True, move_mode=True, has_label=True, locked_axis="x")

    assert move["clear_locked_axis"] is True
    assert move["show_gizmo"] is True
    assert stop["clear_gizmo"] is True
    assert position["update_label"] is True
    assert position["rebuild_gizmo"] is True
    assert position["restore_locked_axis"] == "x"
