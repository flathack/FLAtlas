from __future__ import annotations

from types import SimpleNamespace

from fl_editor.workspace_runtime import (
    activate_non_universe_view,
    apply_workspace_layout,
    on_browser_compact_width_changed,
    set_left_sidebar_visible,
    sync_left_sidebar_compact_width,
)


class _WidgetStub:
    def __init__(self):
        self.visible = None
        self.enabled = None

    def setVisible(self, value):
        self.visible = bool(value)

    def setEnabled(self, value):
        self.enabled = bool(value)


class _LeftStackStub(_WidgetStub):
    def __init__(self):
        super().__init__()
        self.current_widget = None
        self.min_width = None
        self.max_width = None

    def setCurrentWidget(self, widget):
        self.current_widget = widget

    def currentWidget(self):
        return self.current_widget

    def setMinimumWidth(self, value):
        self.min_width = int(value)

    def setMaximumWidth(self, value):
        self.max_width = int(value)


class _SwitchStub(_WidgetStub):
    def __init__(self):
        super().__init__()
        self.checked = None
        self.blocked = []

    def blockSignals(self, value):
        self.blocked.append(bool(value))

    def setChecked(self, value):
        self.checked = bool(value)


class _SplitterStub:
    def __init__(self, sizes):
        self._sizes = list(sizes)
        self.applied_sizes = None

    def sizes(self):
        return list(self._sizes)

    def setSizes(self, sizes):
        self.applied_sizes = list(sizes)


def _build_window():
    window = SimpleNamespace()
    window.browser = object()
    window.left_stack = _LeftStackStub()
    window.right_panel = _WidgetStub()
    window.legend_box = _WidgetStub()
    window.view3d_switch = _SwitchStub()
    window._sidebar_3d_btn = _WidgetStub()
    window._browser_compact_width = 240
    window._main_splitter = _SplitterStub([320, 900, 280])
    window.zoom_visible = None
    window.sidebar_sync = None
    window._set_system_zoom_controls_visible = lambda value: setattr(window, "zoom_visible", bool(value))
    window._sync_sidebar_3d_button = lambda value: setattr(window, "sidebar_sync", bool(value))
    window._set_placement_mode = lambda value: setattr(window, "placement_mode", bool(value))
    window._clear_selection_ui = lambda: setattr(window, "selection_cleared", True)
    window._hide_zone_extra_editors = lambda: setattr(window, "zones_hidden", True)
    window._set_global_nav_active = lambda key: setattr(window, "nav_key", key)
    window._center_set_current_widget = lambda widget, key=None: setattr(window, "current_widget_args", (widget, key))
    window._center_open_extra_tab = lambda widget, title, key: setattr(window, "extra_tab_args", (widget, title, key))
    window._new_system_action = _WidgetStub()
    window._uni_save_action = _WidgetStub()
    window._uni_undo_action = _WidgetStub()
    window._uni_delete_action = _WidgetStub()
    window._ids_scan_action = _WidgetStub()
    window._ids_import_action = _WidgetStub()
    window.mode_lbl = SimpleNamespace(text=None, setText=lambda value: setattr(window.mode_lbl, "text", value))
    window._title_with_version = lambda title: f"{title} vX"
    window.setWindowTitle = lambda value: setattr(window, "window_title", value)
    window._build_standard_menu_bar = lambda: setattr(window, "menu_built", True)
    return window


def test_apply_workspace_layout_updates_workspace_widgets():
    window = _build_window()
    left_widget = object()
    state = SimpleNamespace(
        left_widget=left_widget,
        left_sidebar_visible=True,
        right_panel_visible=True,
        legend_visible=False,
        zoom_controls_visible=True,
        view3d_toggle_visible=True,
        view3d_toggle_enabled=True,
        view3d_toggle_checked=False,
        sidebar_3d_enabled=True,
    )

    apply_workspace_layout(window, state)

    assert window.left_stack.current_widget is left_widget
    assert window.left_stack.visible is True
    assert window.right_panel.visible is True
    assert window.legend_box.visible is False
    assert window.zoom_visible is True
    assert window.view3d_switch.visible is True
    assert window.view3d_switch.enabled is True
    assert window.view3d_switch.checked is False
    assert window._sidebar_3d_btn.enabled is True
    assert window.sidebar_sync is False


def test_sync_left_sidebar_compact_width_for_browser_updates_bounds():
    window = _build_window()
    window.left_stack.setCurrentWidget(window.browser)

    on_browser_compact_width_changed(window, 180)

    assert window._browser_compact_width == 210
    assert window.left_stack.min_width == 210
    assert window.left_stack.max_width == 210
    assert window._main_splitter.applied_sizes is not None


def test_activate_non_universe_view_runs_common_sequence():
    window = _build_window()
    page = object()
    state = SimpleNamespace(
        left_widget=None,
        left_sidebar_visible=False,
        right_panel_visible=False,
        legend_visible=False,
        zoom_controls_visible=False,
        view3d_toggle_visible=False,
        view3d_toggle_enabled=False,
        view3d_toggle_checked=False,
        sidebar_3d_enabled=False,
    )

    activate_non_universe_view(
        window,
        layout_state=state,
        nav_key="mods",
        current_widget=page,
        tab_key="mods",
        title="Mod Manager",
        apply_toolbar=True,
    )

    assert window.placement_mode is False
    assert window.selection_cleared is True
    assert window.zones_hidden is True
    assert window.nav_key == "mods"
    assert window.current_widget_args == (page, "mods")
    assert window.window_title == "Mod Manager vX"
    assert window.menu_built is True
    assert window.mode_lbl.text == ""
    assert window._new_system_action.visible is False


def test_activate_non_universe_view_can_open_extra_tab():
    window = _build_window()
    page = object()
    state = SimpleNamespace(
        left_widget=None,
        left_sidebar_visible=False,
        right_panel_visible=False,
        legend_visible=False,
        zoom_controls_visible=False,
        view3d_toggle_visible=False,
        view3d_toggle_enabled=False,
        view3d_toggle_checked=False,
        sidebar_3d_enabled=False,
    )

    activate_non_universe_view(
        window,
        layout_state=state,
        nav_key="news",
        current_widget=page,
        tab_key="news",
        open_extra_tab=True,
        title="News",
    )

    assert window.extra_tab_args == (page, "News", "news")
    assert not hasattr(window, "current_widget_args")


def test_set_left_sidebar_visible_triggers_compact_sync():
    window = _build_window()
    window.left_stack.setCurrentWidget(window.browser)

    set_left_sidebar_visible(window, True)
    sync_left_sidebar_compact_width(window)

    assert window.left_stack.visible is True
    assert window.left_stack.min_width is not None
