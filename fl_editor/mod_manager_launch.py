"""Launch and executable resolution helpers for Mod Manager."""

from __future__ import annotations

from pathlib import Path
from typing import Callable


def mod_manager_repo_icon_source_profile(
    clean_target_profile: dict | None,
    last_active_entry: dict | None,
    profile_by_id: Callable[[str], dict | None],
) -> dict | None:
    if isinstance(clean_target_profile, dict):
        return clean_target_profile
    active_id = str(last_active_entry.get("mod_id", "") if isinstance(last_active_entry, dict) else "").strip()
    active_profile = profile_by_id(active_id)
    if isinstance(active_profile, dict) and str(active_profile.get("mode", "") or "").strip().lower() == "direct":
        return active_profile
    return None


def mod_manager_launch_profile(
    selected_profile: dict | None,
    clean_target_profile: dict | None,
    last_active_entry: dict | None,
    profile_by_id: Callable[[str], dict | None],
) -> dict | None:
    if isinstance(selected_profile, dict):
        mode = str(selected_profile.get("mode", "") or "").strip().lower()
        if mode == "direct":
            return selected_profile
        if isinstance(clean_target_profile, dict):
            return clean_target_profile
    active_id = str(last_active_entry.get("mod_id", "") if isinstance(last_active_entry, dict) else "").strip()
    active_profile = profile_by_id(active_id)
    if isinstance(active_profile, dict) and str(active_profile.get("mode", "") or "").strip().lower() == "direct":
        return active_profile
    if isinstance(clean_target_profile, dict):
        return clean_target_profile
    return active_profile


def mod_manager_game_root_for_profile(
    profile: dict | None,
    profile_source: Path | None,
    clean_root: Path | None,
) -> Path | None:
    if not isinstance(profile, dict):
        return None
    mode = str(profile.get("mode", "") or "").strip().lower()
    if mode == "direct":
        return profile_source if profile_source is not None and profile_source.exists() and profile_source.is_dir() else None
    if clean_root is not None and clean_root.exists() and clean_root.is_dir():
        return clean_root
    return None


def mod_manager_find_freelancer_exe(
    game_root: Path | None,
    ci_resolve_func: Callable[[Path, str], Path | None],
) -> Path | None:
    if game_root is None:
        return None
    for rel in ("EXE/freelancer.exe", "freelancer.exe"):
        hit = ci_resolve_func(game_root, rel)
        if hit and hit.is_file():
            return hit
    return None


def mod_manager_find_flserver_exe(
    game_root: Path | None,
    ci_resolve_func: Callable[[Path, str], Path | None],
) -> Path | None:
    if game_root is None:
        return None
    for rel in ("EXE/flserver.exe", "flserver.exe"):
        hit = ci_resolve_func(game_root, rel)
        if hit and hit.is_file():
            return hit
    return None


def mod_manager_flmm_icon_candidates(flmm_install_path: str | None) -> list[Path]:
    candidates: list[Path] = []
    flmm_install = str(flmm_install_path or "").strip()
    if flmm_install:
        candidates.append(Path(flmm_install) / "FLModManager.exe")
    candidates.extend(
        [
            Path(r"C:\Program Files (x86)\Freelancer Mod Manager\FLModManager.exe"),
            Path(r"C:\Program Files\Freelancer Mod Manager\FLModManager.exe"),
        ]
    )
    return candidates
