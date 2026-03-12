"""Helpers for linked-system navigation from scene objects."""

from __future__ import annotations


def goto_destination_nickname(goto_value: str) -> str:
    tokens = [token.strip() for token in str(goto_value or "").split(",") if token.strip()]
    if not tokens:
        return ""
    return tokens[0].upper()


def linked_system_path(systems: list[dict], destination_nickname: str) -> str | None:
    dest = str(destination_nickname or "").strip().upper()
    if not dest:
        return None
    for system in systems:
        if str(system.get("nickname", "")).upper() == dest:
            path = system.get("path")
            return str(path) if path else None
    return None
