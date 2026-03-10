from __future__ import annotations

from fl_editor.mod_manager_status import (
    mod_manager_display_name,
    mod_manager_partition_profiles,
    mod_manager_status_summary,
)


def test_mod_manager_partition_profiles_sorts_repo_and_direct_separately():
    profiles = [
        {"name": "Zulu", "mode": "direct"},
        {"name": "Beta", "mode": "repo"},
        {"name": "Alpha", "mode": "direct"},
        {"name": "Gamma", "mode": "repo"},
    ]

    repo_profiles, direct_profiles = mod_manager_partition_profiles(profiles)

    assert [profile["name"] for profile in repo_profiles] == ["Beta", "Gamma"]
    assert [profile["name"] for profile in direct_profiles] == ["Alpha", "Zulu"]


def test_mod_manager_display_name_prefixes_flmm_profiles():
    assert mod_manager_display_name({"name": "Ships Pack"}, False) == "Ships Pack"
    assert mod_manager_display_name({"name": "Ships Pack"}, True) == "FLMM - Ships Pack"


def test_mod_manager_status_summary_combines_active_risk_and_conflict_labels():
    profile = {"id": "mod-a", "opensp_enabled": True}
    translations = {
        "mod_manager.status.active": "Active",
        "mod_manager.status.editing": "Editing",
        "mod_manager.status.opensp": "OpenSP",
        "mod_manager.status.target_installation": "Target",
        "mod_manager.status.save_warn": "Save warning",
        "mod_manager.status.save_critical": "Save critical",
        "mod_manager.status.incompatible": "Incompatible",
        "mod_manager.status.partially_compatible": "Partial",
    }

    status, conflicts, partial_conflicts = mod_manager_status_summary(
        profile,
        active_ids={"mod-a"},
        editing_id="mod-a",
        is_target_installation=True,
        conflicting_active_ids=lambda item: {"other-hard"},
        partial_conflict_details=lambda item: {"other-soft": {"data/test.ini"}},
        profile_savegame_risk=lambda item: {"level": "warn"},
        tr_func=lambda key: translations[key],
    )

    assert status == "Active, Editing, OpenSP, Target, Save warning, Incompatible"
    assert conflicts == {"other-hard"}
    assert partial_conflicts == {"other-soft": {"data/test.ini"}}
