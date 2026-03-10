from __future__ import annotations

from pathlib import Path

from fl_editor.mod_manager_launch import (
    mod_manager_find_freelancer_exe,
    mod_manager_flmm_icon_candidates,
    mod_manager_game_root_for_profile,
    mod_manager_launch_profile,
    mod_manager_repo_icon_source_profile,
)


def test_mod_manager_launch_profile_prefers_selected_direct_profile():
    selected = {"id": "direct-a", "mode": "direct"}

    result = mod_manager_launch_profile(selected, {"id": "target", "mode": "direct"}, None, lambda mod_id: None)

    assert result == selected


def test_mod_manager_launch_profile_falls_back_to_target_and_active_profile():
    profiles = {
        "active-a": {"id": "active-a", "mode": "direct"},
        "active-b": {"id": "active-b", "mode": "repo"},
    }

    result_target = mod_manager_launch_profile(
        {"id": "repo-a", "mode": "repo"},
        {"id": "target-a", "mode": "direct"},
        {"mod_id": "active-b"},
        lambda mod_id: profiles.get(mod_id),
    )
    result_active = mod_manager_launch_profile(
        None,
        None,
        {"mod_id": "active-a"},
        lambda mod_id: profiles.get(mod_id),
    )

    assert result_target == {"id": "target-a", "mode": "direct"}
    assert result_active == {"id": "active-a", "mode": "direct"}


def test_mod_manager_game_root_and_repo_icon_source_profile(tmp_path: Path):
    direct_root = tmp_path / "direct_mod"
    direct_root.mkdir()
    clean_root = tmp_path / "clean"
    clean_root.mkdir()
    target = {"id": "target", "mode": "direct"}
    active_entry = {"mod_id": "active"}
    profiles = {"active": {"id": "active", "mode": "direct"}}

    assert mod_manager_game_root_for_profile({"mode": "direct"}, direct_root, clean_root) == direct_root
    assert mod_manager_game_root_for_profile({"mode": "repo"}, None, clean_root) == clean_root
    assert mod_manager_repo_icon_source_profile(target, active_entry, lambda mod_id: profiles.get(mod_id)) == target
    assert mod_manager_repo_icon_source_profile(None, active_entry, lambda mod_id: profiles.get(mod_id)) == profiles["active"]


def test_mod_manager_find_freelancer_exe_and_flmm_candidates(tmp_path: Path):
    game_root = tmp_path / "game"
    exe_dir = game_root / "EXE"
    exe_dir.mkdir(parents=True)
    exe_path = exe_dir / "freelancer.exe"
    exe_path.write_text("", encoding="utf-8")

    found = mod_manager_find_freelancer_exe(
        game_root,
        lambda root, rel: root / rel if (root / rel).exists() else None,
    )
    candidates = mod_manager_flmm_icon_candidates("/game/FLMM")

    assert found == exe_path
    assert candidates[0] == Path("/game/FLMM") / "FLModManager.exe"
