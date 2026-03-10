from __future__ import annotations


def _entry_value(entries: list[tuple[str, str]], key: str) -> str:
    target = str(key or "").strip().lower()
    for entry_key, entry_value in entries:
        if str(entry_key).strip().lower() == target:
            return str(entry_value).strip()
    return ""


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


def remove_mbase_block_for_base(
    sections: list[tuple[str, list[tuple[str, str]]]],
    base_nick: str,
) -> tuple[list[tuple[str, list[tuple[str, str]]]], bool, int, int]:
    base_low = str(base_nick or "").strip().lower()
    if not base_low:
        return sections, False, 0, 0

    mbase_idx: int | None = None
    for index, (sec_name, entries) in enumerate(sections):
        if str(sec_name).strip().lower() != "mbase":
            continue
        if _entry_value(entries, "nickname").strip().lower() == base_low:
            mbase_idx = index
            break

    if mbase_idx is None:
        return sections, False, 0, 0

    end_idx = len(sections)
    for index in range(mbase_idx + 1, len(sections)):
        if str(sections[index][0]).strip().lower() == "mbase":
            end_idx = index
            break

    npc_nicks: set[str] = set()
    for index in range(mbase_idx + 1, end_idx):
        sec_name, entries = sections[index]
        if str(sec_name).strip().lower() != "gf_npc":
            continue
        npc_nick = _entry_value(entries, "nickname").strip().lower()
        if npc_nick:
            npc_nicks.add(npc_nick)

    block_count = max(0, end_idx - mbase_idx)
    remaining = list(sections[:mbase_idx]) + list(sections[end_idx:])
    if not npc_nicks:
        return remaining, True, block_count, 0

    filtered: list[tuple[str, list[tuple[str, str]]]] = []
    stray_removed = 0
    for sec_name, entries in remaining:
        if str(sec_name).strip().lower() == "gf_npc":
            npc_nick = _entry_value(entries, "nickname").strip().lower()
            if npc_nick and npc_nick in npc_nicks:
                stray_removed += 1
                continue
        filtered.append((sec_name, entries))
    return filtered, True, block_count, stray_removed
