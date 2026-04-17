"""Helpers for settings navigation and tab-key normalization."""

from __future__ import annotations


_TAB_ALIASES: dict[str, str] = {
    "allgemein": "general",
    "general": "general",
    "pinned_tools": "pinned_tools",
    "pinned": "pinned_tools",
    "system_editor": "system_editor",
    "mod_manager": "mod_manager",
    "editors": "editors",
    "editoren": "editors",
    "suite_apps": "suite_apps",
    "suite": "suite_apps",
    "fl_atlas_suite_apps": "suite_apps",
    "savegame_editor": "suite_apps",
    "npc_editor": "suite_apps",
    "rumor_editor": "suite_apps",
    "news_editor": "suite_apps",
    "reset": "reset",
    "dev_status": "dev_status",
    "dev": "dev_status",
}


def canonical_global_settings_tab_key(tab_key: str) -> str:
    key = str(tab_key or "").strip().lower()
    return _TAB_ALIASES.get(key, "general")
