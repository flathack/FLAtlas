"""Helpers for serializing universe and snapshot writes."""

from __future__ import annotations


def extract_nickname_from_entries(entries) -> str | None:
    for key, value in entries:
        if str(key).lower() == "nickname":
            return value
    return None


def serialize_universe_sections_with_positions(
    sections,
    pos_map: dict[str, tuple[float, float]],
) -> str:
    lines: list[str] = []
    for sec_name, entries in sections:
        lines.append(f"[{sec_name}]")
        if str(sec_name).lower() == "system":
            nick = extract_nickname_from_entries(entries)
            nick_lower = str(nick).lower() if nick is not None else None
            wrote_pos = False
            for key, value in entries:
                if str(key).lower() == "pos" and nick_lower and nick_lower in pos_map:
                    px, py = pos_map[nick_lower]
                    lines.append(f"pos = {px:.0f}, {py:.0f}")
                    wrote_pos = True
                else:
                    lines.append(f"{key} = {value}")
            if nick_lower and nick_lower in pos_map and not wrote_pos:
                px, py = pos_map[nick_lower]
                lines.append(f"pos = {px:.0f}, {py:.0f}")
        else:
            for key, value in entries:
                lines.append(f"{key} = {value}")
        lines.append("")
    return "\n".join(lines)


def serialize_snapshot_sections(sections, objs) -> str:
    lines: list[str] = []
    obj_iter = iter(objs)
    for sec_name, entries in sections:
        lines.append(f"[{sec_name}]")
        if str(sec_name).lower() == "object":
            try:
                obj = next(obj_iter)
                for key, value in obj.get("_entries", []):
                    lines.append(f"{key} = {value}")
            except StopIteration:
                for key, value in entries:
                    lines.append(f"{key} = {value}")
        else:
            for key, value in entries:
                lines.append(f"{key} = {value}")
        lines.append("")
    for obj in obj_iter:
        lines.append("[Object]")
        for key, value in obj.get("_entries", []):
            lines.append(f"{key} = {value}")
        lines.append("")
    return "\n".join(lines)
