"""UI action-state helpers for Mod Manager selections."""

from __future__ import annotations


def mod_manager_action_state(
    profile: dict | None,
    *,
    has_active: bool,
    active_ids: set[str],
    active_entry: dict | None,
    conflicts: set[str],
    editing_mod_id: str,
    repo_setup_complete: bool,
    can_edit_sp_starter_ship: bool,
    has_profile_source: bool,
) -> dict[str, object]:
    has_sel = isinstance(profile, dict)
    mode = str(profile.get("mode", "") or "").strip().lower() if has_sel else ""
    pid = str(profile.get("id", "") or "").strip() if has_sel else ""
    is_direct = bool(has_sel and mode == "direct")
    is_repo = bool(has_sel and mode != "direct")
    return {
        "open_folder_enabled": has_sel,
        "edit_ctx_enabled": has_sel and not has_active,
        "clear_edit_ctx_enabled": bool(str(editing_mod_id or "").strip()) and not has_active,
        "activate_enabled": has_sel and mode != "direct" and pid not in active_ids and not conflicts,
        "delete_enabled": has_sel,
        "deactivate_enabled": has_sel and active_entry is not None,
        "new_repo_enabled": bool(repo_setup_complete),
        "edit_sp_ship_enabled": bool(can_edit_sp_starter_ship),
        "opensp_enabled": is_direct,
        "opensp_visible": is_direct,
        "opensp_checked": bool(profile.get("opensp_enabled", False)) if is_direct else False,
        "set_target_enabled": is_direct and has_profile_source,
        "force_saves_enabled": is_repo,
        "force_saves_visible": is_repo,
        "force_saves_checked": bool(profile.get("force_save_backup", False)) if is_repo else False,
        "profile_header_name": str(profile.get("name", "") or "").strip() if has_sel else "",
    }
