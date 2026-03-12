"""Helpers for assigning infocard ids to scene items."""

from __future__ import annotations


def assign_ids_info_entry(entries, ids_info: str, *, entry_set):
    updated = entry_set(list(entries), "ids_info", str(ids_info))
    return updated, str(ids_info)
