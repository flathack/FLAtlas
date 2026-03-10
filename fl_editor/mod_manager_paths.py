"""Filesystem path helpers for Mod Manager and savegame handling."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def mod_manager_accounts_dir(home: Path | None = None) -> Path:
    base_home = home if home is not None else Path.home()
    return base_home / "Documents" / "My Games" / "Freelancer" / "Accts"


def mod_manager_safe_name_for_fs(name: str) -> str:
    raw = str(name or "").strip()
    if not raw:
        return "mod"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._-")
    return safe or "mod"


def mod_manager_profile_savegames_dir(profile_or_active: dict, home: Path | None = None) -> Path:
    pid = str(profile_or_active.get("id", "") or profile_or_active.get("mod_id", "") or "").strip()
    name = str(profile_or_active.get("name", "") or profile_or_active.get("mod_name", "") or "").strip()
    base = mod_manager_safe_name_for_fs(name or pid or "profile")
    suffix = mod_manager_safe_name_for_fs(pid)[:8] if pid else ""
    folder = f"Savegames_{base}_{suffix}" if suffix else f"Savegames_{base}"
    return mod_manager_accounts_dir(home) / folder


def mod_manager_default_savegames_dir(home: Path | None = None) -> Path:
    return mod_manager_accounts_dir(home) / "Savegames_Default"


def mod_manager_singleplayer_dir(home: Path | None = None) -> Path:
    return mod_manager_accounts_dir(home) / "SinglePlayer"


def mod_manager_unique_path(path: Path, timestamp: str | None = None) -> Path:
    if not path.exists():
        return path
    stamp = str(timestamp or datetime.now().strftime("%Y%m%d_%H%M%S"))
    candidate = path.with_name(f"{path.name}_old_{stamp}")
    if not candidate.exists():
        return candidate
    idx = 2
    while True:
        candidate = path.with_name(f"{path.name}_old_{stamp}_{idx}")
        if not candidate.exists():
            return candidate
        idx += 1
