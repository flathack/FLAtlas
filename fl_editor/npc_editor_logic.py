from __future__ import annotations

from typing import Callable


def npc_multiline_values(raw_text: str) -> list[str]:
    values: list[str] = []
    for line in str(raw_text or "").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or text.startswith(";"):
            continue
        values.append(text)
    return values


def npc_collect_multi(entries: list[tuple[str, str]], key: str) -> list[str]:
    target = str(key or "").strip().lower()
    return [str(value).strip() for entry_key, value in entries if str(entry_key).strip().lower() == target and str(value).strip()]


def npc_apply_mission_and_rumors(
    entries: list[tuple[str, str]],
    misn_lines: list[str],
    rumor_lines: list[str],
    rumor2_lines: list[str],
) -> list[tuple[str, str]]:
    kept = [
        (key, value)
        for key, value in entries
        if str(key).strip().lower() not in {"misn", "rumor", "rumor_type2"}
    ]
    insert_at = len(kept)
    for index, (key, _value) in enumerate(kept):
        if str(key).strip().lower() == "room":
            insert_at = index + 1
            break
    extras: list[tuple[str, str]] = []
    extras.extend([("misn", value) for value in misn_lines])
    extras.extend([("rumor", value) for value in rumor_lines])
    extras.extend([("rumor_type2", value) for value in rumor2_lines])
    return kept[:insert_at] + extras + kept[insert_at:]


def npc_split_csv(raw: str, width: int) -> list[str]:
    values = [item.strip() for item in str(raw or "").split(",")]
    if len(values) < width:
        values.extend([""] * (width - len(values)))
    return values[:width]


def npc_parse_rumor_id(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    digits: list[str] = []
    for char in text:
        if char.isdigit():
            digits.append(char)
            continue
        if digits:
            break
        return text
    return "".join(digits) if digits else text


def npc_rumor_line_label(line: str, resolve_name: Callable[[str], str]) -> str:
    values = npc_split_csv(line, 4)
    rumor_id = npc_parse_rumor_id(values[3])
    resolved = resolve_name(rumor_id) if rumor_id else ""
    preview = str(resolved or "").replace("\n", " ").strip()
    if len(preview) > 70:
        preview = preview[:67] + "..."
    if preview:
        return f"{line} | {preview}"
    return str(line).strip()
