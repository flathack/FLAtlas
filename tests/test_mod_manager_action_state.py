from __future__ import annotations

from fl_editor.mod_manager_action_state import mod_manager_action_state


def test_mod_manager_action_state_for_direct_profile():
    state = mod_manager_action_state(
        {"id": "direct-a", "mode": "direct", "name": "Direct A", "opensp_enabled": True},
        has_active=False,
        active_ids=set(),
        active_entry=None,
        conflicts=set(),
        editing_mod_id="",
        repo_setup_complete=True,
        can_edit_sp_starter_ship=True,
        has_profile_source=True,
    )

    assert state["open_folder_enabled"]
    assert state["edit_ctx_enabled"]
    assert not state["activate_enabled"]
    assert state["new_repo_enabled"]
    assert state["opensp_enabled"]
    assert state["opensp_visible"]
    assert state["opensp_checked"]
    assert not state["create_install_from_mod_enabled"]
    assert state["set_target_enabled"]
    assert not state["force_saves_visible"]
    assert state["profile_header_name"] == "Direct A"


def test_mod_manager_action_state_for_repo_profile_enables_create_install_from_mod_when_possible():
    state = mod_manager_action_state(
        {"id": "repo-a", "mode": "repo", "name": "Repo A"},
        has_active=False,
        active_ids=set(),
        active_entry=None,
        conflicts=set(),
        editing_mod_id="",
        repo_setup_complete=True,
        can_edit_sp_starter_ship=False,
        has_profile_source=True,
    )

    assert state["activate_enabled"]
    assert state["create_install_from_mod_enabled"]


def test_mod_manager_action_state_for_repo_profile_with_conflict_and_active_entry():
    state = mod_manager_action_state(
        {"id": "repo-a", "mode": "repo", "name": "Repo A", "force_save_backup": True},
        has_active=True,
        active_ids={"other-active"},
        active_entry={"mod_id": "repo-a"},
        conflicts={"other-active"},
        editing_mod_id="repo-a",
        repo_setup_complete=False,
        can_edit_sp_starter_ship=False,
        has_profile_source=False,
    )

    assert state["open_folder_enabled"]
    assert not state["edit_ctx_enabled"]
    assert not state["clear_edit_ctx_enabled"]
    assert not state["activate_enabled"]
    assert state["deactivate_enabled"]
    assert not state["new_repo_enabled"]
    assert not state["opensp_visible"]
    assert state["force_saves_enabled"]
    assert state["force_saves_visible"]
    assert state["force_saves_checked"]


def test_mod_manager_action_state_without_selection_disables_selection_actions():
    state = mod_manager_action_state(
        None,
        has_active=False,
        active_ids=set(),
        active_entry=None,
        conflicts=set(),
        editing_mod_id="editing-a",
        repo_setup_complete=True,
        can_edit_sp_starter_ship=False,
        has_profile_source=False,
    )

    assert not state["open_folder_enabled"]
    assert not state["activate_enabled"]
    assert not state["create_install_from_mod_enabled"]
    assert state["clear_edit_ctx_enabled"]
    assert state["new_repo_enabled"]
    assert state["profile_header_name"] == ""
