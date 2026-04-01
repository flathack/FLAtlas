"""Runtime helpers for workspace layout and non-universe view switching."""

from __future__ import annotations

from typing import Any

from .sidebar_layout import left_sidebar_width_state, normalized_browser_compact_width
from .view_actions import non_universe_toolbar_state


def set_left_sidebar_visible(window: Any, visible: bool) -> None:
    custom = getattr(window, "_apply_left_sidebar_visibility", None)
    if callable(custom):
        custom(bool(visible))
        return
    if hasattr(window, "left_stack"):
        window.left_stack.setVisible(bool(visible))
        if visible:
            sync_left_sidebar_compact_width(window)


def on_browser_compact_width_changed(window: Any, width: int) -> None:
    window._browser_compact_width = normalized_browser_compact_width(width)
    sync_left_sidebar_compact_width(window)


def on_left_stack_current_changed(window: Any, _idx: int) -> None:
    sync_left_sidebar_compact_width(window)


def sync_left_sidebar_compact_width(window: Any) -> None:
    if not hasattr(window, "left_stack"):
        return
    splitter = getattr(window, "_main_splitter", None)
    state = left_sidebar_width_state(
        is_browser=hasattr(window, "browser") and window.left_stack.currentWidget() is window.browser,
        compact_width=getattr(window, "_browser_compact_width", 240),
        splitter_sizes=splitter.sizes() if splitter is not None else None,
    )
    window.left_stack.setMinimumWidth(int(state["min_width"]))
    window.left_stack.setMaximumWidth(int(state["max_width"]))
    if splitter is None:
        return
    splitter_sizes = state.get("splitter_sizes")
    if splitter_sizes is not None:
        splitter.setSizes(list(splitter_sizes))


def apply_workspace_layout(window: Any, state: Any) -> None:
    if hasattr(window, "left_stack") and getattr(state, "left_widget", None) is not None:
        try:
            window.left_stack.setCurrentWidget(state.left_widget)
        except Exception:
            pass
    set_left_sidebar_visible(window, bool(getattr(state, "left_sidebar_visible", False)))
    custom_right = getattr(window, "_apply_right_sidebar_visibility", None)
    if callable(custom_right):
        custom_right(bool(getattr(state, "right_panel_visible", False)))
    elif hasattr(window, "right_panel"):
        window.right_panel.setVisible(bool(getattr(state, "right_panel_visible", False)))
    if hasattr(window, "legend_box"):
        window.legend_box.setVisible(bool(getattr(state, "legend_visible", False)))
    window._set_system_zoom_controls_visible(bool(getattr(state, "zoom_controls_visible", False)))
    window.view3d_switch.blockSignals(True)
    window.view3d_switch.setChecked(bool(getattr(state, "view3d_toggle_checked", False)))
    window.view3d_switch.setVisible(bool(getattr(state, "view3d_toggle_visible", False)))
    window.view3d_switch.setEnabled(bool(getattr(state, "view3d_toggle_enabled", False)))
    window.view3d_switch.blockSignals(False)
    if hasattr(window, "_sidebar_3d_btn"):
        window._sidebar_3d_btn.setEnabled(bool(getattr(state, "sidebar_3d_enabled", False)))
        window._sync_sidebar_3d_button(bool(getattr(state, "view3d_toggle_checked", False)))
    refresh_buttons = getattr(window, "_refresh_system_edge_sidebar_buttons", None)
    if callable(refresh_buttons):
        refresh_buttons()


def apply_non_universe_toolbar(window: Any) -> None:
    state = non_universe_toolbar_state()
    window._new_system_action.setVisible(bool(state["new_system_visible"]))
    window._uni_save_action.setVisible(bool(state["uni_save_visible"]))
    window._uni_undo_action.setVisible(bool(state["uni_undo_visible"]))
    window._uni_delete_action.setVisible(bool(state["uni_delete_visible"]))
    window._ids_scan_action.setVisible(bool(state["ids_scan_visible"]))
    window._ids_import_action.setVisible(bool(state["ids_import_visible"]))
    window.mode_lbl.setText(str(state["mode_text"]))


def activate_non_universe_view(
    window: Any,
    *,
    layout_state: Any,
    nav_key: str | None = None,
    current_widget: object | None = None,
    tab_key: str | None = None,
    open_extra_tab: bool = False,
    title: str | None = None,
    apply_toolbar: bool = False,
) -> None:
    window._set_placement_mode(False)
    window._clear_selection_ui()
    window._hide_zone_extra_editors()
    apply_workspace_layout(window, layout_state)
    if nav_key:
        window._set_global_nav_active(nav_key)
    if current_widget is not None:
        if open_extra_tab and tab_key:
            window._center_open_extra_tab(current_widget, str(title or ""), tab_key)
        elif tab_key:
            window._center_set_current_widget(current_widget, tab_key)
        else:
            window._center_set_current_widget(current_widget)
    if apply_toolbar:
        apply_non_universe_toolbar(window)
    if title is not None:
        window.setWindowTitle(window._title_with_version(title))
    window._build_standard_menu_bar()
