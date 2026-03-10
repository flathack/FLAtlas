from __future__ import annotations

from typing import Callable


def npc_find_section_range(sections: list[tuple[str, list[tuple[str, str]]]], start_idx: int) -> tuple[int, int]:
    end_idx = len(sections)
    for index in range(start_idx + 1, len(sections)):
        if str(sections[index][0]).strip().lower() == "mbase":
            end_idx = index
            break
    return start_idx, end_idx


def npc_attach_to_mbase(
    sections: list[tuple[str, list[tuple[str, str]]]],
    *,
    base_nickname: str,
    faction_nickname: str,
    npc_nickname: str,
    entry_get_value: Callable[[list[tuple[str, str]], str], str],
) -> list[tuple[str, list[tuple[str, str]]]]:
    base_low = str(base_nickname or "").strip().lower()
    faction = str(faction_nickname or "").strip() or "fc_ou_grp"
    npc = str(npc_nickname or "").strip()
    if not base_low or not npc:
        return sections

    mbase_idx: int | None = None
    for index, (sec_name, entries) in enumerate(sections):
        if str(sec_name).strip().lower() != "mbase":
            continue
        if entry_get_value(entries, "nickname").strip().lower() == base_low:
            mbase_idx = index
            break

    if mbase_idx is None:
        sections.append(
            (
                "MBase",
                [
                    ("nickname", base_nickname),
                    ("local_faction", faction),
                    ("diff", "1"),
                    ("msg_id_prefix", f"gcs_refer_base_{base_nickname}"),
                ],
            )
        )
        sections.append(("MVendor", [("num_offers", "10, 20")]))
        sections.append(("BaseFaction", [("faction", faction), ("weight", "10"), ("npc", npc)]))
        return sections

    start_idx, end_idx = npc_find_section_range(sections, mbase_idx)
    basefaction_idx: int | None = None
    for index in range(start_idx + 1, end_idx):
        sec_name, entries = sections[index]
        if str(sec_name).strip().lower() != "basefaction":
            continue
        if entry_get_value(entries, "faction").strip().lower() == faction.lower():
            basefaction_idx = index
            break

    if basefaction_idx is None:
        last_basefaction_idx: int | None = None
        mvendor_idx: int | None = None
        for index in range(start_idx + 1, end_idx):
            name = str(sections[index][0]).strip().lower()
            if name == "basefaction":
                last_basefaction_idx = index
            elif name == "mvendor" and mvendor_idx is None:
                mvendor_idx = index
        if last_basefaction_idx is not None:
            insert_at = last_basefaction_idx + 1
        elif mvendor_idx is not None:
            insert_at = mvendor_idx + 1
        else:
            insert_at = start_idx + 1
        sections.insert(insert_at, ("BaseFaction", [("faction", faction), ("weight", "10"), ("npc", npc)]))
        return sections

    sec_name, entries = sections[basefaction_idx]
    has_npc = any(str(key).strip().lower() == "npc" and str(value).strip().lower() == npc.lower() for key, value in entries)
    if not has_npc:
        sections[basefaction_idx] = (sec_name, list(entries) + [("npc", npc)])
    return sections


def npc_insert_gf_for_base(
    sections: list[tuple[str, list[tuple[str, str]]]],
    *,
    base_nickname: str,
    npc_entries: list[tuple[str, str]],
    entry_get_value: Callable[[list[tuple[str, str]], str], str],
) -> list[tuple[str, list[tuple[str, str]]]]:
    base_low = str(base_nickname or "").strip().lower()
    if not base_low:
        sections.append(("GF_NPC", list(npc_entries)))
        return sections

    mbase_idx: int | None = None
    for index, (sec_name, entries) in enumerate(sections):
        if str(sec_name).strip().lower() != "mbase":
            continue
        if entry_get_value(entries, "nickname").strip().lower() == base_low:
            mbase_idx = index
            break
    if mbase_idx is None:
        sections.append(("GF_NPC", list(npc_entries)))
        return sections

    start_idx, end_idx = npc_find_section_range(sections, mbase_idx)
    last_gf_idx: int | None = None
    first_room_idx: int | None = None
    last_basefaction_idx: int | None = None
    mvendor_idx: int | None = None
    for index in range(start_idx + 1, end_idx):
        sec = str(sections[index][0]).strip().lower()
        if sec == "gf_npc":
            last_gf_idx = index
        elif sec == "mroom" and first_room_idx is None:
            first_room_idx = index
        elif sec == "basefaction":
            last_basefaction_idx = index
        elif sec == "mvendor" and mvendor_idx is None:
            mvendor_idx = index

    if last_gf_idx is not None:
        insert_at = last_gf_idx + 1
    elif first_room_idx is not None:
        insert_at = first_room_idx
    elif last_basefaction_idx is not None:
        insert_at = last_basefaction_idx + 1
    elif mvendor_idx is not None:
        insert_at = mvendor_idx + 1
    else:
        insert_at = start_idx + 1

    sections.insert(insert_at, ("GF_NPC", list(npc_entries)))
    return sections


def npc_detach_from_mbase(
    sections: list[tuple[str, list[tuple[str, str]]]],
    *,
    base_nickname: str,
    npc_nickname: str,
    entry_get_value: Callable[[list[tuple[str, str]], str], str],
) -> list[tuple[str, list[tuple[str, str]]]]:
    base_low = str(base_nickname or "").strip().lower()
    npc_low = str(npc_nickname or "").strip().lower()
    if not base_low or not npc_low:
        return sections

    mbase_idx: int | None = None
    for index, (sec_name, entries) in enumerate(sections):
        if str(sec_name).strip().lower() != "mbase":
            continue
        if entry_get_value(entries, "nickname").strip().lower() == base_low:
            mbase_idx = index
            break
    if mbase_idx is None:
        return sections

    start_idx, end_idx = npc_find_section_range(sections, mbase_idx)
    index = start_idx + 1
    while index < end_idx:
        sec_name, entries = sections[index]
        if str(sec_name).strip().lower() != "basefaction":
            index += 1
            continue
        new_entries = [
            (key, value)
            for key, value in entries
            if not (str(key).strip().lower() == "npc" and str(value).strip().lower() == npc_low)
        ]
        has_npc = any(str(key).strip().lower() == "npc" for key, _value in new_entries)
        if not has_npc:
            mission_count = sum(1 for key, _value in new_entries if str(key).strip().lower() == "mission_type")
            if mission_count == 0:
                sections.pop(index)
                end_idx -= 1
                continue
        sections[index] = (sec_name, new_entries)
        index += 1
    return sections


def npc_find_gf_section_index(
    sections: list[tuple[str, list[tuple[str, str]]]],
    *,
    npc_nickname: str,
    entry_get_value: Callable[[list[tuple[str, str]], str], str],
) -> int | None:
    npc_low = str(npc_nickname or "").strip().lower()
    if not npc_low:
        return None
    for index, (sec_name, entries) in enumerate(sections):
        if str(sec_name).strip().lower() != "gf_npc":
            continue
        if entry_get_value(entries, "nickname").strip().lower() == npc_low:
            return index
    return None


def npc_collect_for_base(
    sections: list[tuple[str, list[tuple[str, str]]]],
    *,
    base_nickname: str,
    entry_get_value: Callable[[list[tuple[str, str]], str], str],
) -> list[dict]:
    base_low = str(base_nickname or "").strip().lower()
    if not base_low:
        return []

    mbase_idx: int | None = None
    for index, (sec_name, entries) in enumerate(sections):
        if str(sec_name).strip().lower() != "mbase":
            continue
        if entry_get_value(entries, "nickname").strip().lower() == base_low:
            mbase_idx = index
            break

    npc_to_faction: dict[str, str] = {}
    if mbase_idx is not None:
        start_idx, end_idx = npc_find_section_range(sections, mbase_idx)
        for index in range(start_idx + 1, end_idx):
            sec_name, entries = sections[index]
            if str(sec_name).strip().lower() != "basefaction":
                continue
            faction = entry_get_value(entries, "faction").strip()
            for key, value in entries:
                if str(key).strip().lower() == "npc":
                    nickname = str(value).strip()
                    if nickname and nickname.lower() not in npc_to_faction:
                        npc_to_faction[nickname.lower()] = faction

    rows: list[dict] = []
    for sec_name, entries in sections:
        if str(sec_name).strip().lower() != "gf_npc":
            continue
        nickname = entry_get_value(entries, "nickname").strip()
        if not nickname:
            continue
        faction = npc_to_faction.get(nickname.lower(), "")
        if not faction:
            continue
        rows.append({"nickname": nickname, "faction": faction, "entries": list(entries)})
    rows.sort(key=lambda row: str(row.get("nickname", "")).lower())
    return rows
