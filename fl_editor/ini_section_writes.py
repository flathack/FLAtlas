from __future__ import annotations

from pathlib import Path


def update_ids_entry_in_sections(
    sections: list,
    sec_type: str,
    obj_nick: str,
    key: str,
    value: str,
) -> bool:
    target_section = str(sec_type or "").strip().lower()
    target_nickname = str(obj_nick or "").strip().lower()
    target_key = str(key or "").strip().lower()

    for sec_name, entries in sections:
        if str(sec_name or "").strip().lower() != target_section:
            continue
        nickname = next(
            (entry_value for entry_key, entry_value in entries if str(entry_key or "").strip().lower() == "nickname"),
            "",
        )
        if str(nickname or "").strip().lower() != target_nickname:
            continue
        for index, (entry_key, _entry_value) in enumerate(entries):
            if str(entry_key or "").strip().lower() == target_key:
                entries[index] = (entry_key, value)
                return True
        return False
    return False


def serialize_sections_to_ini_text(sections: list) -> str:
    lines: list[str] = []
    for index, (sec_name, entries) in enumerate(sections):
        if index > 0:
            lines.append("")
        lines.append(f"[{sec_name}]")
        for key, value in entries:
            lines.append(f"{key} = {value}")
    return "\n".join(lines) + "\n"


def write_sections_to_file(filepath: str | Path, sections: list) -> None:
    Path(filepath).write_text(serialize_sections_to_ini_text(sections), encoding="utf-8")
