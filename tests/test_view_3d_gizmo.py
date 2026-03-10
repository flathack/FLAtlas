from __future__ import annotations

from fl_editor.view_3d_gizmo import (
    gizmo_click_state,
    gizmo_default_colors,
    gizmo_highlight_colors,
    gizmo_transform_state,
    toggled_locked_axis,
)


def test_gizmo_transform_state_computes_translation_and_scale():
    state = gizmo_transform_state(
        center_xyz=(0.0, 0.0, 0.0),
        cam_pos_xyz=(0.0, 0.0, 260.0),
        axis_dir_xyz=(1.0, 0.0, 0.0),
    )

    assert state is not None
    assert state["scale"] == 1.0
    tx, ty, tz = state["translation_xyz"]
    assert round(tx, 2) == 20.0
    assert round(ty, 2) == 0.0
    assert round(tz, 2) == 7.0


def test_gizmo_highlight_and_default_colors_cover_all_axes():
    colors = gizmo_highlight_colors("y")
    defaults = gizmo_default_colors()

    assert set(colors.keys()) == {"x", "y", "z"}
    assert set(defaults.keys()) == {"x", "y", "z"}
    assert colors["y"].getRgb()[:3] == (180, 255, 180)
    assert defaults["x"][0].getRgb()[:3] == (255, 80, 80)


def test_toggled_locked_axis_respects_selection_and_toggle():
    assert toggled_locked_axis(None, "x", has_selection=False) is None
    assert toggled_locked_axis(None, "x", has_selection=True) == "x"
    assert toggled_locked_axis("x", "x", has_selection=True) is None


def test_gizmo_click_state_describes_filter_and_color_effects():
    no_selection = gizmo_click_state(None, "x", has_selection=False)
    activate = gizmo_click_state(None, "x", has_selection=True)
    deactivate = gizmo_click_state("x", "x", has_selection=True)

    assert no_selection["has_selection"] is False
    assert activate["next_axis"] == "x"
    assert activate["highlight_axis"] == "x"
    assert activate["install_event_filter"] is True
    assert deactivate["next_axis"] is None
    assert deactivate["reset_colors"] is True
    assert deactivate["remove_event_filter"] is True
