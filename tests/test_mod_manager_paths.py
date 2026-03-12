from __future__ import annotations

from pathlib import Path

from fl_editor.mod_manager_paths import (
    mod_manager_accounts_dir,
    mod_manager_default_savegames_dir,
    mod_manager_profile_savegames_dir,
    mod_manager_safe_name_for_fs,
    mod_manager_singleplayer_dir,
    mod_manager_unique_path,
)


def test_mod_manager_accounts_and_default_dirs_use_home_override(tmp_path: Path):
    accounts = mod_manager_accounts_dir(tmp_path)

    assert accounts == tmp_path / "Documents" / "My Games" / "Freelancer" / "Accts"
    assert mod_manager_default_savegames_dir(tmp_path) == accounts / "Savegames_Default"
    assert mod_manager_singleplayer_dir(tmp_path) == accounts / "SinglePlayer"


def test_mod_manager_safe_name_for_fs_normalizes_values():
    assert mod_manager_safe_name_for_fs("  My Mod!?  ") == "My_Mod"
    assert mod_manager_safe_name_for_fs("") == "mod"


def test_mod_manager_profile_savegames_dir_uses_profile_fields(tmp_path: Path):
    path = mod_manager_profile_savegames_dir({"id": "abc12345xyz", "name": "Cool Mod"}, tmp_path)

    assert path == tmp_path / "Documents" / "My Games" / "Freelancer" / "Accts" / "Savegames_Cool_Mod_abc12345"


def test_mod_manager_unique_path_returns_available_backup_name(tmp_path: Path):
    target = tmp_path / "Savegames_Default"
    target.mkdir()
    first_candidate = tmp_path / "Savegames_Default_old_20260310_101010"
    first_candidate.mkdir()

    result = mod_manager_unique_path(target, timestamp="20260310_101010")

    assert result == tmp_path / "Savegames_Default_old_20260310_101010_2"
