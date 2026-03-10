"""Helpers for UI view and tab state decisions."""

from __future__ import annotations

from .settings_navigation import canonical_global_settings_tab_key


def global_settings_tab_index(tab_key: str, tab_order: dict[str, int | None], tab_count: int) -> int:
    key = canonical_global_settings_tab_key(tab_key)
    idx = int(tab_order.get(key, -1) or -1)
    if idx < 0:
        idx = 0
    if tab_count <= 0:
        return 0
    return max(0, min(idx, tab_count - 1))


def name_editor_sub_view_state(key: str) -> dict[str, object]:
    normalized = str(key or "").strip().lower()
    show_info = normalized == "info"
    return {
        "show_info": show_info,
        "stack_index": 1 if show_info else 0,
        "show_name_actions": not show_info,
        "show_info_actions": show_info,
    }
