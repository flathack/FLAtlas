"""Helpers for assigning infocard ids to universe system sections."""

from __future__ import annotations


def assign_universe_system_ids_info(sections, index: int, ids_info: str, *, entry_set):
    sec_name, entries = sections[index]
    updated_entries = entry_set(entries, "ids_info", str(ids_info))
    updated_sections = list(sections)
    updated_sections[index] = (sec_name, updated_entries)
    return updated_sections, updated_entries
