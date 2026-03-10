"""Savegame-related policy helpers for Mod Manager workflows."""

from __future__ import annotations


def mod_manager_savegame_risk_rank(level: str) -> int:
    order = {
        "safe": 0,
        "warn": 1,
        "critical": 2,
    }
    return int(order.get(str(level or "").strip().lower(), 0))


def mod_manager_should_manage_savegames(profile_or_active: dict | None, resolved_risk_level: str | None = None) -> bool:
    if not isinstance(profile_or_active, dict):
        return False
    mode = str(profile_or_active.get("mode", "") or "").strip().lower()
    if not mode:
        mode = "direct" if str(profile_or_active.get("direct_path", "") or "").strip() else "repo"
    if mode == "direct":
        return True
    level = str(
        resolved_risk_level
        or profile_or_active.get("savegame_risk_level", "")
        or "safe"
    ).strip().lower()
    return level in {"warn", "critical"}
