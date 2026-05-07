"""Runtime helpers for system-tab lifecycle and tab switching."""

from __future__ import annotations

import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QMessageBox, QWidget

from .i18n import tr


def _ensure_system_tab_registered(window: Any, tab_key: str, sys_path: str) -> None:
    idx = window._center_tab_index_for_key(tab_key)
    if idx < 0:
        host = window._build_system_editor_host(tab_key)
        window._register_system_editor_host(host)
        if hasattr(window, "center_stack"):
            if window.center_stack.indexOf(host.view) < 0:
                window.center_stack.addWidget(host.view)
            if window.center_stack.indexOf(host.view3d) < 0:
                window.center_stack.addWidget(host.view3d)
        window._center_register_tab(host.view, window._system_tab_title(sys_path), tab_key, closable=True)
        idx = window._center_tab_index_for_key(tab_key)
        if idx >= 0:
            window._center_tab_specs[idx]["host_key"] = str(host.key)
    if idx >= 0:
        window._center_tab_specs[idx]["path"] = sys_path


def open_system_tab(window: Any, path: str, new_tab: bool = False) -> None:
    sys_path = str(path or "").strip()
    if not sys_path:
        return
    tab_key = window._system_tab_key(sys_path)
    current_key = str(window._center_current_tab_key or "").strip()
    if current_key and current_key != tab_key:
        window._capture_system_tab_state(current_key)
        window._capture_system_tab_document(current_key)
    if not new_tab and window._center_tab_index_for_key(tab_key) < 0:
        _ensure_system_tab_registered(window, tab_key, sys_path)
    elif new_tab:
        _ensure_system_tab_registered(window, tab_key, sys_path)
        window._ensure_system_tab_host(tab_key)
    host = window._ensure_system_tab_host(tab_key)
    window._set_active_system_editor_host(host.key)
    if window._filepath != sys_path:
        window._center_current_tab_key = tab_key
        spec = window._center_system_tab_spec(tab_key)
        document = spec.get("document") if isinstance(spec, dict) else None
        if (
            document is not None
            and hasattr(document, "path")
            and hasattr(document, "sections")
            and hasattr(document, "dirty")
            and str(getattr(document, "path", "") or "").strip() == sys_path
            and isinstance(getattr(document, "sections", None), list)
        ):
            window._apply_system_document(
                sys_path,
                deepcopy(getattr(document, "sections", []) or []),
                restore=None,
                dirty=bool(getattr(document, "dirty", False)),
                doc=document,
            )
        else:
            window._load(sys_path)
        window.browser.highlight_current(sys_path)
    else:
        window._center_current_tab_key = tab_key
        window._center_set_current_widget(window._active_system_editor_widget_for_current_mode(), tab_key)
    idx = window._center_tab_index_for_key(tab_key)
    if idx >= 0:
        window._center_tab_specs[idx]["title"] = window._system_tab_title(sys_path)
    window._restore_system_tab_state(tab_key)
    window._center_set_current_widget(window._active_system_editor_widget_for_current_mode(), tab_key)
    window._capture_system_tab_document(tab_key)


def on_center_tab_changed(window: Any, index: int) -> None:
    if window._center_tab_syncing or not hasattr(window, "center_stack"):
        return
    bar = getattr(window, "center_tab_bar", None)
    if bar is not None:
        is_reordering = getattr(bar, "is_reordering", None)
        if callable(is_reordering) and bool(is_reordering()):
            return
    if index < 0 or index >= len(window._center_tab_specs):
        return
    spec = window._center_tab_specs[index]
    key = str(spec.get("key", "") or "").strip()
    current_key = str(window._center_current_tab_key or "").strip()
    if current_key and current_key != key:
        window._capture_system_tab_state(current_key)
    if key == "universe":
        window._load_universe_action()
        window._center_sync_tab_bar()
    elif key == "trade":
        window._open_trade_routes_view()
        window._center_sync_tab_bar()
    elif key == "name":
        window._open_name_editor_view()
        window._center_sync_tab_bar()
    elif key == "ini":
        window._open_ini_editor_view()
        window._center_sync_tab_bar()
    elif key == "mods":
        window._open_mod_manager_view()
        window._center_sync_tab_bar()
    elif key == "settings":
        window._open_global_settings_view()
        window._center_sync_tab_bar()
    elif key == "npc":
        window._open_npc_editor()
        window._center_sync_tab_bar()
    elif key == "rumor":
        window._open_rumor_editor()
        window._center_sync_tab_bar()
    elif key == "news":
        window._open_news_editor()
        window._center_sync_tab_bar()
    elif key.startswith("system:"):
        open_system_tab(window, str(spec.get("path", "") or ""), new_tab=False)
        window._center_sync_tab_bar()
    else:
        widget = spec.get("widget")
        if isinstance(widget, QWidget):
            window._center_set_current_widget(widget, key)
            window._refresh_window_title()


def open_system_in_new_window(window: Any, path: str) -> None:
    target = str(path or "").strip()
    if not target:
        return
    try:
        target_path = Path(target).resolve()
    except Exception:
        target_path = Path(target)
    try:
        if getattr(sys, "frozen", False):
            cmd = [str(Path(sys.executable).resolve()), "--open-system", str(target_path)]
            cwd = str(Path(sys.executable).resolve().parent)
        else:
            app_entry = Path(__file__).resolve().parent.parent / "fl_atlas.py"
            cmd = [str(Path(sys.executable).resolve()), str(app_entry), "--open-system", str(target_path)]
            cwd = str(app_entry.parent)
        subprocess.Popen(cmd, cwd=cwd)
    except Exception as ex:
        QMessageBox.warning(
            window,
            tr("tabs.open_in_new_window_failed_title"),
            tr("tabs.open_in_new_window_failed").format(error=ex),
        )


def center_close_tabs_except(window: Any, keep_index: int) -> None:
    for i in range(len(window._center_tab_specs) - 1, -1, -1):
        if i == keep_index:
            continue
        if i >= len(window._center_tab_specs):
            continue
        if not bool(window._center_tab_specs[i].get("closable", False)):
            continue
        before = len(window._center_tab_specs)
        window._on_center_tab_close_requested(i)
        after = len(window._center_tab_specs)
        if after == before:
            break


def center_close_all_closable_tabs(window: Any) -> None:
    for i in range(len(window._center_tab_specs) - 1, -1, -1):
        if i >= len(window._center_tab_specs):
            continue
        if not bool(window._center_tab_specs[i].get("closable", False)):
            continue
        before = len(window._center_tab_specs)
        window._on_center_tab_close_requested(i)
        after = len(window._center_tab_specs)
        if after == before:
            break


def close_system_tabs_under_root(window: Any, root_path: Path) -> bool:
    try:
        root_resolved = root_path.resolve(strict=False)
    except Exception:
        root_resolved = Path(root_path)
    indices: list[int] = []
    for i, spec in enumerate(window._center_tab_specs):
        key = str(spec.get("key", "") or "").strip()
        if not key.startswith("system:"):
            continue
        sys_path = str(spec.get("path", "") or "").strip()
        if not sys_path:
            continue
        try:
            sys_resolved = Path(sys_path).resolve(strict=False)
        except Exception:
            sys_resolved = Path(sys_path)
        try:
            sys_resolved.relative_to(root_resolved)
            indices.append(i)
        except Exception:
            continue
    for i in reversed(indices):
        if i >= len(window._center_tab_specs):
            continue
        before = len(window._center_tab_specs)
        window._on_center_tab_close_requested(i)
        after = len(window._center_tab_specs)
        if after == before:
            return False
    return True
