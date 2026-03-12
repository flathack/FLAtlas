"""Derived action state for game-path dependent UI controls."""

from __future__ import annotations


def build_game_path_action_state(
    *,
    has_storage_setup: bool,
    has_editing_profile: bool,
    primary_game_path: str | None,
    has_savegame_editor: bool,
) -> dict[str, bool]:
    has_editing_context = bool(has_editing_profile and str(primary_game_path or "").strip())
    return {
        "has_universe": bool(has_storage_setup),
        "has_editing_context": has_editing_context,
        "has_savegame_editor": bool(has_savegame_editor),
        "nav_settings_enabled": True,
        "mods_tab_enabled": True,
        "universe_enabled": has_editing_context,
        "trade_enabled": has_editing_context,
        "name_enabled": has_editing_context,
        "ini_enabled": has_editing_context,
        "npc_enabled": has_editing_context,
        "rumor_enabled": has_editing_context,
        "news_enabled": has_editing_context,
        "savegame_visible": bool(has_savegame_editor),
        "savegame_enabled": bool(has_savegame_editor),
        "browser_trade_enabled": has_editing_context,
    }
