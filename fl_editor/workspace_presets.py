"""Reusable workspace layout presets for non-universe views."""

from __future__ import annotations


def extra_view_layout() -> dict[str, object]:
    return {
        "left_sidebar_visible": False,
        "right_panel_visible": False,
        "legend_visible": False,
        "zoom_controls_visible": False,
        "view3d_toggle_visible": False,
        "view3d_toggle_enabled": False,
        "view3d_toggle_checked": False,
        "sidebar_3d_enabled": False,
    }


def list_editor_layout(left_widget) -> dict[str, object]:
    return {
        "left_widget": left_widget,
        "left_sidebar_visible": True,
        "right_panel_visible": False,
        "legend_visible": False,
        "zoom_controls_visible": False,
        "view3d_toggle_visible": False,
        "view3d_toggle_enabled": False,
        "view3d_toggle_checked": False,
        "sidebar_3d_enabled": False,
    }
