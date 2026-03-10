from __future__ import annotations


def base_nickname_from_object_entries(entries: list[tuple[str, str]]) -> str:
    for key, value in entries:
        if str(key).strip().lower() == "base":
            nickname = str(value).strip()
            if nickname:
                return nickname
    for key, value in entries:
        if str(key).strip().lower() == "dock_with":
            nickname = str(value).strip()
            if nickname:
                return nickname
    return ""


def remove_base_from_universe_sections(
    sections: list[tuple[str, list[tuple[str, str]]]],
    base_nick: str,
) -> tuple[list[tuple[str, list[tuple[str, str]]]], bool]:
    target = str(base_nick or "").strip().lower()
    new_sections: list[tuple[str, list[tuple[str, str]]]] = []
    removed = False
    for sec_name, entries in sections:
        if str(sec_name).strip().lower() == "base":
            match = False
            for key, value in entries:
                if str(key).strip().lower() == "nickname" and str(value).strip().lower() == target:
                    match = True
                    break
            if match:
                removed = True
                continue
        new_sections.append((sec_name, entries))
    return new_sections, removed


def room_files_from_base_sections(sections: list[tuple[str, list[tuple[str, str]]]]) -> list[str]:
    files: list[str] = []
    for sec_name, entries in sections:
        if str(sec_name).strip().lower() != "room":
            continue
        for key, value in entries:
            if str(key).strip().lower() == "file":
                path = str(value).strip()
                if path:
                    files.append(path)
    return files
