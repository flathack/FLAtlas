from __future__ import annotations

from fl_editor.view_3d_event_routing import (
    should_capture_locked_axis_wheel,
    should_process_qt3d_interaction,
)


def test_capture_and_qt3d_interaction_decisions():
    assert should_capture_locked_axis_wheel(event_type="wheel", locked_axis="x", has_selected_obj=True) is True
    assert should_capture_locked_axis_wheel(event_type="wheel", locked_axis=None, has_selected_obj=True) is False
    assert should_capture_locked_axis_wheel(event_type="mouse_move", locked_axis="x", has_selected_obj=True) is False

    assert should_process_qt3d_interaction(qt3d_available=True, target_matches=True) is True
    assert should_process_qt3d_interaction(qt3d_available=False, target_matches=True) is False
    assert should_process_qt3d_interaction(qt3d_available=True, target_matches=False) is False
