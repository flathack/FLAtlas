from __future__ import annotations

from fl_editor.mod_manager_savegame_policy import (
    mod_manager_savegame_risk_rank,
    mod_manager_should_manage_savegames,
)


def test_mod_manager_savegame_risk_rank_orders_levels():
    assert mod_manager_savegame_risk_rank("safe") < mod_manager_savegame_risk_rank("warn")
    assert mod_manager_savegame_risk_rank("warn") < mod_manager_savegame_risk_rank("critical")


def test_mod_manager_should_manage_savegames_handles_direct_and_repo_profiles():
    assert mod_manager_should_manage_savegames({"mode": "direct"})
    assert mod_manager_should_manage_savegames({"mode": "repo", "savegame_risk_level": "warn"})
    assert not mod_manager_should_manage_savegames({"mode": "repo", "savegame_risk_level": "safe"})
    assert mod_manager_should_manage_savegames({"direct_path": "/tmp/mod"})
