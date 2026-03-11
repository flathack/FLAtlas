"""Helpers for classifying jump gate/hole objects from OBJECT fields."""

from __future__ import annotations


def classify_jump_connection_kind(*, archetype: str, msg_id_prefix: str = "", reputation: str = "") -> str:
    """Return ``gate``, ``hole`` or ```` for non-jump objects.

    Primary detection uses archetype patterns. For mods that reuse custom
    archetypes (e.g. ``domgate``), fallback detection uses:
    - ``msg_id_prefix = gcs_refer_system_*`` plus non-empty ``reputation`` -> gate
    - ``msg_id_prefix = gcs_refer_system_*`` plus jumphole-like archetype -> hole
    """
    arch = str(archetype or "").strip().lower()
    msg = str(msg_id_prefix or "").strip().lower()
    rep = str(reputation or "").strip()

    if any(token in arch for token in ("jumpgate", "jump_gate", "jumppoint_gate", "nomad_gate")):
        return "gate"
    if any(token in arch for token in ("jumphole", "jump_hole")):
        return "hole"

    if msg.startswith("gcs_refer_system_"):
        if rep:
            return "gate"
        if any(token in arch for token in ("jumphole", "jump_hole")):
            return "hole"

    return ""
