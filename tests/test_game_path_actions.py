from __future__ import annotations

from fl_editor.game_path_actions import build_game_path_action_state


def test_build_game_path_action_state_enables_editing_actions_when_context_exists():
    state = build_game_path_action_state(
        has_storage_setup=True,
        has_editing_profile=True,
        primary_game_path="/games/freelancer",
        has_savegame_editor=True,
    )

    assert state["has_universe"] is True
    assert state["has_editing_context"] is True
    assert state["universe_enabled"] is True
    assert state["trade_enabled"] is True
    assert state["name_enabled"] is True
    assert state["ini_enabled"] is True
    assert state["savegame_visible"] is True
    assert state["savegame_enabled"] is True
    assert state["browser_trade_enabled"] is True


def test_build_game_path_action_state_disables_editing_actions_without_context():
    state = build_game_path_action_state(
        has_storage_setup=False,
        has_editing_profile=False,
        primary_game_path="",
        has_savegame_editor=False,
    )

    assert state["has_universe"] is False
    assert state["has_editing_context"] is False
    assert state["mods_tab_enabled"] is True
    assert state["universe_enabled"] is False
    assert state["trade_enabled"] is False
    assert state["name_enabled"] is False
    assert state["ini_enabled"] is False
    assert state["savegame_visible"] is False
    assert state["savegame_enabled"] is False
    assert state["nav_settings_enabled"] is True
