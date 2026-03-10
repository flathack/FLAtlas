"""Status and presentation helpers for Mod Manager profiles."""

from __future__ import annotations

from typing import Callable


def mod_manager_partition_profiles(profiles: list[object]) -> tuple[list[dict], list[dict]]:
    repo_profiles = sorted(
        [
            profile
            for profile in profiles
            if isinstance(profile, dict) and str(profile.get("mode", "") or "").strip().lower() != "direct"
        ],
        key=lambda item: str(item.get("name", "")).lower(),
    )
    direct_profiles = sorted(
        [
            profile
            for profile in profiles
            if isinstance(profile, dict) and str(profile.get("mode", "") or "").strip().lower() == "direct"
        ],
        key=lambda item: str(item.get("name", "")).lower(),
    )
    return repo_profiles, direct_profiles


def mod_manager_display_name(profile: dict | None, is_flmm_repo_profile: bool) -> str:
    if not isinstance(profile, dict):
        return ""
    display_name = str(profile.get("name", "") or "")
    if is_flmm_repo_profile:
        return f"FLMM - {display_name}"
    return display_name


def mod_manager_status_summary(
    profile: dict | None,
    *,
    active_ids: set[str],
    editing_id: str,
    is_target_installation: bool,
    conflicting_active_ids: Callable[[dict | None], set[str]],
    partial_conflict_details: Callable[[dict | None], dict[str, set[str]]],
    profile_savegame_risk: Callable[[dict | None], dict[str, object]],
    tr_func: Callable[[str], str],
) -> tuple[str, set[str], dict[str, set[str]]]:
    if not isinstance(profile, dict):
        return "", set(), {}
    pid = str(profile.get("id", "") or "").strip()
    status_parts: list[str] = []
    if pid and pid in active_ids:
        status_parts.append(tr_func("mod_manager.status.active"))
    if pid and pid == editing_id:
        status_parts.append(tr_func("mod_manager.status.editing"))
    if bool(profile.get("opensp_enabled", False)):
        status_parts.append(tr_func("mod_manager.status.opensp"))
    if is_target_installation:
        status_parts.append(tr_func("mod_manager.status.target_installation"))
    conflicts = conflicting_active_ids(profile)
    partial_conflicts = partial_conflict_details(profile)
    risk = profile_savegame_risk(profile)
    risk_level = str(risk.get("level", "safe") or "safe").strip().lower()
    if risk_level == "warn":
        status_parts.append(tr_func("mod_manager.status.save_warn"))
    elif risk_level == "critical":
        status_parts.append(tr_func("mod_manager.status.save_critical"))
    if conflicts:
        status_parts.append(tr_func("mod_manager.status.incompatible"))
    elif partial_conflicts:
        status_parts.append(tr_func("mod_manager.status.partially_compatible"))
    return ", ".join(status_parts), conflicts, partial_conflicts
