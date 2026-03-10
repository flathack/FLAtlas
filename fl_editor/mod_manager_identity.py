"""Identity, path-key and active-state helpers for the Mod Manager."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path


def mod_manager_make_id(name: str, *, now: datetime | None = None) -> str:
    stamp = now or datetime.utcnow()
    base = f"{stamp.isoformat()}|{name}".encode("utf-8", errors="ignore")
    return hashlib.sha1(base).hexdigest()[:16]


def mod_manager_profile_source(profile: dict, repo_root_default: str = "") -> Path | None:
    mode = str(profile.get("mode", "") or "").strip().lower()
    if mode == "repo":
        repo_root_txt = str(profile.get("repo_root", "") or "").strip() or str(repo_root_default or "").strip()
        repo_root = Path(repo_root_txt) if repo_root_txt else None
        folder = str(profile.get("repo_folder", "") or "").strip()
        if not repo_root or not folder:
            return None
        return repo_root / folder
    if mode == "direct":
        direct_path = str(profile.get("direct_path", "") or "").strip()
        return Path(direct_path) if direct_path else None
    return None


def mod_manager_normalized_path_key(path: Path | str | None) -> str:
    if path is None:
        return ""
    try:
        candidate = Path(path)
    except Exception:
        return ""
    try:
        norm = candidate.resolve(strict=False)
    except Exception:
        norm = candidate
    return str(norm).replace("/", "\\").rstrip("\\").lower()


def mod_manager_profile_name_by_id(profiles: list[dict], mod_id: str | None) -> str:
    pid = str(mod_id or "").strip()
    if not pid:
        return ""
    for profile in profiles:
        if str(profile.get("id", "") or "").strip() == pid:
            return str(profile.get("name", "") or "").strip()
    return ""


def mod_manager_active_entries(active_entries: list[object]) -> list[dict]:
    return [dict(entry) for entry in active_entries if isinstance(entry, dict)]


def mod_manager_active_ids(active_entries: list[object]) -> set[str]:
    return {
        str(entry.get("mod_id", "") or "").strip()
        for entry in active_entries
        if isinstance(entry, dict) and str(entry.get("mod_id", "") or "").strip()
    }


def mod_manager_active_entry_by_id(active_entries: list[object], mod_id: str | None) -> dict | None:
    pid = str(mod_id or "").strip()
    if not pid:
        return None
    for entry in active_entries:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("mod_id", "") or "").strip() == pid:
            return entry
    return None


def mod_manager_has_active_entries(active_entries: list[object]) -> bool:
    return any(isinstance(entry, dict) for entry in active_entries)


def mod_manager_last_active_entry(active_entries: list[object]) -> dict | None:
    for entry in reversed(active_entries):
        if isinstance(entry, dict):
            return entry
    return None


def mod_manager_is_target_installation(profile: dict | None, clean_profile_id: str | None) -> bool:
    if not isinstance(profile, dict):
        return False
    pid = str(profile.get("id", "") or "").strip()
    if not pid:
        return False
    return pid == str(clean_profile_id or "").strip()
