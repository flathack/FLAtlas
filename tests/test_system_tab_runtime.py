from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fl_editor.system_tab_runtime import (
    center_close_all_closable_tabs,
    center_close_tabs_except,
    close_system_tabs_under_root,
    on_center_tab_changed,
    open_system_tab,
)


class _CenterStackStub:
    def __init__(self):
        self.widgets: list[object] = []

    def indexOf(self, widget):
        try:
            return self.widgets.index(widget)
        except ValueError:
            return -1

    def addWidget(self, widget):
        self.widgets.append(widget)


def _build_window():
    host = SimpleNamespace(key="system:li01", view=object(), view3d=object())
    window = SimpleNamespace()
    window._center_tab_specs = []
    window._center_tab_syncing = False
    window._center_current_tab_key = "universe"
    window._filepath = ""
    window.browser = SimpleNamespace(highlight_current=lambda path: setattr(window, "highlighted_path", path))
    window.view = object()
    window.center_stack = _CenterStackStub()
    window.loaded_paths = []
    window.current_widgets = []
    window.registered_hosts = []
    window.synced = 0
    window._build_system_editor_host = lambda key: SimpleNamespace(key=key, view=object(), view3d=object())
    window._register_system_editor_host = lambda host_obj: window.registered_hosts.append(host_obj)
    window._ensure_system_tab_host = lambda key: next((h for h in window.registered_hosts if h.key == key), host)
    window._set_active_system_editor_host = lambda key: setattr(window, "active_host_key", key)
    window._active_system_editor_widget_for_current_mode = lambda: host.view
    window._capture_system_tab_state = lambda key: setattr(window, "captured_state_key", key)
    window._capture_system_tab_document = lambda key: setattr(window, "captured_doc_key", key)
    window._populate_quick_editor_options = lambda: setattr(window, "quick_options_called", True)
    window._load = lambda path: window.loaded_paths.append(path)
    window._restore_system_tab_state = lambda key: setattr(window, "restored_key", key)
    window._center_set_current_widget = lambda widget, key=None: window.current_widgets.append((widget, key))
    window._center_sync_tab_bar = lambda: setattr(window, "synced", window.synced + 1)
    window._refresh_window_title = lambda: setattr(window, "refreshed_title", True)
    window._load_universe_action = lambda: setattr(window, "universe_loaded", True)
    window._open_trade_routes_view = lambda: setattr(window, "trade_opened", True)
    window._open_name_editor_view = lambda: setattr(window, "name_opened", True)
    window._open_ini_editor_view = lambda: setattr(window, "ini_opened", True)
    window._open_mod_manager_view = lambda: setattr(window, "mods_opened", True)
    window._open_global_settings_view = lambda: setattr(window, "settings_opened", True)
    window._open_npc_editor = lambda: setattr(window, "npc_opened", True)
    window._open_rumor_editor = lambda: setattr(window, "rumor_opened", True)
    window._open_news_editor = lambda: setattr(window, "news_opened", True)
    window._ini_editor_capture_tab_document = lambda key: setattr(window, "captured_ini_doc_key", key)
    window._activate_ini_editor_workspace = lambda key, reload_tree=False: True
    window._ini_editor_apply_tab_document = lambda spec: setattr(window, "applied_ini_spec", spec)
    window._center_register_tab = lambda widget, title, key, closable: window._center_tab_specs.append(
        {"widget": widget, "title": title, "key": key, "closable": closable}
    )
    window._system_tab_key = lambda path: f"system:{Path(path).stem.lower()}"
    window._system_tab_title = lambda path: f"System {Path(path).stem}"
    window._center_tab_index_for_key = lambda key: next(
        (idx for idx, spec in enumerate(window._center_tab_specs) if str(spec.get("key", "")) == str(key)),
        -1,
    )
    window._center_system_tab_spec = lambda key=None: next(
        (spec for spec in window._center_tab_specs if str(spec.get("key", "")) == str(key or window._center_current_tab_key)),
        None,
    )
    window._apply_system_document = lambda path, sections, restore=None, dirty=False, doc=None: setattr(
        window,
        "applied_system_document",
        {"path": path, "sections": sections, "dirty": dirty, "doc": doc},
    )
    return window


def test_open_system_tab_registers_host_and_loads_path():
    window = _build_window()

    open_system_tab(window, "C:/mods/DATA/UNIVERSE/li01.ini", new_tab=False)

    assert len(window._center_tab_specs) == 1
    assert window._center_tab_specs[0]["path"].endswith("li01.ini")
    assert window.active_host_key == "system:li01"
    assert window.loaded_paths == ["C:/mods/DATA/UNIVERSE/li01.ini"]
    assert window.highlighted_path == "C:/mods/DATA/UNIVERSE/li01.ini"
    assert window.restored_key == "system:li01"


def test_on_center_tab_changed_routes_known_views():
    window = _build_window()
    window._center_tab_specs = [{"key": "trade", "widget": object(), "closable": False}]

    on_center_tab_changed(window, 0)

    assert window.trade_opened is True
    assert window.synced == 1


def test_center_close_tabs_helpers_stop_on_cancelled_close():
    window = _build_window()
    window._center_tab_specs = [
        {"key": "universe", "closable": False},
        {"key": "system:a", "closable": True},
        {"key": "system:b", "closable": True},
    ]

    def _close(index):
        if index == 1:
            return
        window._center_tab_specs.pop(index)

    window._on_center_tab_close_requested = _close

    center_close_tabs_except(window, 1)

    assert [spec["key"] for spec in window._center_tab_specs] == ["universe", "system:a"]

    window._center_tab_specs = [
        {"key": "universe", "closable": False},
        {"key": "system:a", "closable": True},
        {"key": "system:b", "closable": True},
    ]
    window._on_center_tab_close_requested = lambda index: window._center_tab_specs.pop(index)
    center_close_all_closable_tabs(window)
    assert [spec["key"] for spec in window._center_tab_specs] == ["universe"]


def test_close_system_tabs_under_root_closes_matching_tabs_only():
    window = _build_window()
    root = Path("C:/mods")
    window._center_tab_specs = [
        {"key": "system:a", "path": str(root / "DATA" / "a.ini"), "closable": True},
        {"key": "system:b", "path": "D:/other/b.ini", "closable": True},
        {"key": "mods", "path": "", "closable": False},
    ]

    def _close(index):
        window._center_tab_specs.pop(index)

    window._on_center_tab_close_requested = _close

    ok = close_system_tabs_under_root(window, root)

    assert ok is True
    assert [spec["key"] for spec in window._center_tab_specs] == ["system:b", "mods"]
