from __future__ import annotations


def build_base_object_entries(
    *,
    obj_nick: str,
    pos_str: str,
    ids_name_val: str,
    ids_info_val: str,
    archetype: str,
    base_nick: str,
    loadout: str = "",
    pilot: str = "",
    reputation: str = "",
    voice: str = "",
    space_costume: str = "",
) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = [
        ("nickname", obj_nick),
        ("pos", pos_str),
        ("rotate", "0, 0, 0"),
        ("ids_name", ids_name_val),
        ("ids_info", ids_info_val),
        ("Archetype", archetype),
        ("dock_with", base_nick),
        ("base", base_nick),
        ("behavior", "NOTHING"),
        ("difficulty_level", "1"),
    ]
    if loadout:
        entries.append(("loadout", loadout))
    if pilot:
        entries.append(("pilot", pilot))
    if reputation:
        entries.append(("reputation", reputation))
    if voice:
        entries.append(("voice", voice))
    if space_costume:
        entries.append(("space_costume", space_costume))
    return entries


def build_universe_base_entries(
    *,
    base_nick: str,
    system_nick: str,
    strid_name_val: str,
    file_rel: str,
    bgcs_base_run_by: str = "",
) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = [
        ("nickname", base_nick),
        ("system", system_nick),
        ("strid_name", str(strid_name_val)),
        ("file", file_rel),
    ]
    if bgcs_base_run_by:
        entries.append(("BGCS_base_run_by", bgcs_base_run_by))
    return entries
