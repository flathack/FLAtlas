"""Helpers for persisting generated universe system infocard ids."""

from __future__ import annotations


def should_refresh_universe_system_editor(selected_nick: str | None, system_nickname: str) -> bool:
    return str(selected_nick or "").strip().lower() == str(system_nickname or "").strip().lower()
