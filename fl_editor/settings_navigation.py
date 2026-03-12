"""Helpers for settings navigation and tab-key normalization."""

from __future__ import annotations


_TAB_ALIASES: dict[str, str] = {
    "allgemein": "general",
    "general": "general",
    "system_editor": "system_editor",
    "mod_manager": "mod_manager",
    "editors": "editors",
    "editoren": "editors",
    "savegame_editor": "editors",
    "npc_editor": "editors",
    "rumor_editor": "editors",
    "news_editor": "editors",
    "dev_status": "dev_status",
    "dev": "dev_status",
}


def canonical_global_settings_tab_key(tab_key: str) -> str:
    key = str(tab_key or "").strip().lower()
    return _TAB_ALIASES.get(key, "general")
