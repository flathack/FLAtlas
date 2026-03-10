"""Helpers for cached universe edit state and section lookup."""

from __future__ import annotations

from pathlib import Path


def ensure_universe_sections_for_edit(
    uni_sections,
    uni_ini_path,
    *,
    primary_game_path: str | None,
    find_universe_ini_read,
    parse_sections,
):
    if uni_sections and uni_ini_path and Path(uni_ini_path).is_file():
        return True, uni_ini_path, uni_sections
    uni = find_universe_ini_read(primary_game_path)
    if not uni:
        return False, uni_ini_path, uni_sections
    return True, uni, parse_sections(str(uni))


def find_universe_system_section_index(sections, system_nickname: str, *, entry_get_value) -> int | None:
    nick_low = str(system_nickname or "").strip().lower()
    if not nick_low:
        return None
    for index, (sec_name, entries) in enumerate(sections):
        if str(sec_name).strip().lower() != "system":
            continue
        if str(entry_get_value(entries, "nickname")).strip().lower() == nick_low:
            return index
    return None
