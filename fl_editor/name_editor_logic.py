"""Helpers for name editor filtering and small row transforms."""

from __future__ import annotations


def filter_name_editor_rows(rows: list[dict], search: str) -> list[dict]:
    query = str(search or "").strip().lower()
    if not query:
        return list(rows)
    return [
        row
        for row in rows
        if query in str(row.get("global_id", "")).lower()
        or query in str(row.get("text", "")).lower()
        or query in str(row.get("dll", "")).lower()
    ]


def name_from_nickname_guess(nickname: str) -> str:
    raw = str(nickname or "").strip()
    if not raw:
        return ""
    parts = [part for part in raw.split("_") if part]
    if not parts:
        return raw
    return " ".join(part[:1].upper() + part[1:] for part in parts)


def usage_location_line(usage: dict) -> str:
    section = str(usage.get("section", "") or "").strip()
    nickname = str(usage.get("nickname", "") or "").strip() or "-"
    path = str(usage.get("path", "") or "").strip() or "-"
    return f"[{section}] {nickname} -> {path}"
