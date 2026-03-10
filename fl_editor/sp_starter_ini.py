"""Helpers for reading and patching the OpenSP starter trigger."""

from __future__ import annotations

from typing import Callable


def sp_starter_current_from_lines(
    lines: list[str],
    find_ini_section_bounds: Callable[[list[str], str, str | None], tuple[int, int] | None],
) -> tuple[str, str] | None:
    bounds = find_ini_section_bounds(lines, "Trigger", "tr_fp7_cam_end")
    if bounds is None:
        return None
    start, end = bounds
    for idx in range(start + 1, end):
        line = str(lines[idx]).strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip().lower() != "act_setshipandloadout":
            continue
        parts = [item.strip() for item in value.split(",")]
        if len(parts) >= 2 and parts[0] and parts[1]:
            return parts[0], parts[1]
    return None


def sp_starter_set_in_text(
    raw_text: str,
    *,
    ship: str,
    loadout: str,
    find_ini_section_bounds: Callable[[list[str], str, str | None], tuple[int, int] | None],
) -> tuple[bool, str, str]:
    newline = "\r\n" if "\r\n" in raw_text else "\n"
    lines = str(raw_text).splitlines()
    bounds = find_ini_section_bounds(lines, "Trigger", "tr_fp7_cam_end")
    if bounds is None:
        return False, str(raw_text), "trigger_missing"
    start, end = bounds
    replacement = f"Act_SetShipAndLoadout = {ship}, {loadout}"
    found = False
    for idx in range(start + 1, end):
        line = str(lines[idx]).strip()
        if "=" not in line:
            continue
        key, _value = line.split("=", 1)
        if key.strip().lower() == "act_setshipandloadout":
            lines[idx] = replacement
            found = True
            break
    if not found:
        lines.insert(end, replacement)
    return True, newline.join(lines) + newline, ""
