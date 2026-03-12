from __future__ import annotations

from fl_editor.workspace_presets import extra_view_layout, list_editor_layout


def test_extra_view_layout_hides_nonessential_panels():
    assert extra_view_layout() == {
        "left_sidebar_visible": False,
        "right_panel_visible": False,
        "legend_visible": False,
        "zoom_controls_visible": False,
        "view3d_toggle_visible": False,
        "view3d_toggle_enabled": False,
        "view3d_toggle_checked": False,
        "sidebar_3d_enabled": False,
    }


def test_list_editor_layout_keeps_left_panel_only():
    marker = object()

    assert list_editor_layout(marker) == {
        "left_widget": marker,
        "left_sidebar_visible": True,
        "right_panel_visible": False,
        "legend_visible": False,
        "zoom_controls_visible": False,
        "view3d_toggle_visible": False,
        "view3d_toggle_enabled": False,
        "view3d_toggle_checked": False,
        "sidebar_3d_enabled": False,
    }
