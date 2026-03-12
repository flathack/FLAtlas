"""Helpers for resolving universe-system infocard ids."""

from __future__ import annotations


def universe_system_ids_info(sections, system_nickname: str, *, entry_get_value, safe_int) -> int:
    nick_low = str(system_nickname or "").strip().lower()
    if not nick_low:
        return 0
    for sec_name, entries in sections:
        if str(sec_name).strip().lower() != "system":
            continue
        if str(entry_get_value(entries, "nickname")).strip().lower() != nick_low:
            continue
        return safe_int(entry_get_value(entries, "ids_info"))
    return 0
