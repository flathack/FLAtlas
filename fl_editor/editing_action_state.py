"""Helpers for editing action availability in system editor views."""

from __future__ import annotations


def system_has_tradelanes(objects) -> bool:
    for obj in objects:
        arch = str(getattr(obj, "data", {}).get("archetype", "")).lower()
        nick = str(getattr(obj, "nickname", "") or "").lower()
        if "trade_lane_ring" in arch or "tradelane_ring" in arch:
            return True
        if "trade_lane_ring" in nick or "tradelane_ring" in nick:
            return True
    return False


def build_editing_action_state(
    *,
    locked: bool,
    has_system: bool,
    has_tradelanes: bool,
    is_zone_selected: bool,
    has_base_selected: bool,
) -> dict[str, bool]:
    return {
        "edit_tradelane_enabled": bool(has_system and has_tradelanes and not locked),
        "edit_zone_pop_enabled": bool(is_zone_selected and not locked),
        "edit_base_enabled": bool(has_base_selected and not locked),
        "open_system_ini_enabled": bool(has_system and not locked),
    }
