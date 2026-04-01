from __future__ import annotations

from .npc_mbase_ops import npc_find_section_range


def npc_room_density(room_name: str) -> int:
    room = npc_room_key(room_name)
    if room == "bar":
        return 7
    if room == "shipdealer":
        return 2
    if room == "equipment":
        return 2
    return 3


def npc_room_key(room_name: str) -> str:
    room = str(room_name or "").strip().lower()
    if room in ("shipdealer", "ship_dealer", "ship-dealer"):
        return "shipdealer"
    if room in ("equipment", "equip"):
        return "equipment"
    if room in ("trader", "commoditytrader"):
        return "trader"
    if room == "deck":
        return "deck"
    if room == "bar":
        return "bar"
    if room == "cityscape":
        return "cityscape"
    return room


def npc_canonical_mroom_name(room_name: str) -> str:
    room = npc_room_key(room_name)
    if room == "shipdealer":
        return "ShipDealer"
    if room == "equipment":
        return "Equipment"
    if room == "deck":
        return "Deck"
    return room


def npc_allowed_roles_for_room(room_name: str) -> list[str]:
    room = npc_room_key(room_name)
    if room == "bar":
        return ["bartender", "BarFly", "NewsVendor"]
    if room == "trader":
        return ["trader"]
    if room == "equipment":
        return ["Equipment"]
    if room == "shipdealer":
        return ["ShipDealer"]
    if room == "deck":
        return ["ShipDealer", "trader", "Equipment", "bartender"]
    if room == "cityscape":
        return ["trader"]
    return ["trader"]


def npc_normalize_role_for_room(role: str, room_name: str) -> str:
    allowed = npc_allowed_roles_for_room(room_name)
    raw = str(role or "").strip()
    if not raw:
        return allowed[0]
    raw_low = raw.lower()
    for candidate in allowed:
        if candidate.lower() == raw_low:
            return candidate
    return allowed[0]


def npc_fixture_scene_for_role(role: str) -> tuple[str, str]:
    role_text = str(role or "").strip().lower()
    if role_text == "shipdealer":
        return "scripts\\vendors\\li_shipdealer_fidget.thn", "ShipDealer"
    if role_text == "equipment":
        return "scripts\\vendors\\li_equipdealer_fidget.thn", "Equipment"
    if role_text == "bartender":
        return "scripts\\vendors\\li_host_fidget.thn", "bartender"
    if role_text == "newsvendor":
        return "scripts\\vendors\\li_bartender_fidget.thn", "NewsVendor"
    if role_text == "barfly":
        return "scripts\\vendors\\li_bartender_fidget.thn", "BarFly"
    if role_text == "trader":
        return "scripts\\vendors\\li_commtrader_fidget.thn", "trader"
    return "scripts\\vendors\\li_commtrader_fidget.thn", "trader"


def npc_upsert_mrooms_for_base(
    sections: list[tuple[str, list[tuple[str, str]]]],
    *,
    base_nickname: str,
    room_fixtures: dict[str, list[tuple[str, str]]],
    entry_get_value,
) -> bool:
    base_low = str(base_nickname or "").strip().lower()
    if not base_low:
        return False
    mbase_idx: int | None = None
    for index, (sec_name, entries) in enumerate(sections):
        if str(sec_name).strip().lower() != "mbase":
            continue
        if entry_get_value(entries, "nickname").strip().lower() == base_low:
            mbase_idx = index
            break
    if mbase_idx is None:
        return False

    start_idx, end_idx = npc_find_section_range(sections, mbase_idx)
    target_rooms = {npc_canonical_mroom_name(room).lower() for room in room_fixtures.keys() if str(room or "").strip()}
    removed = False
    for index in range(end_idx - 1, start_idx, -1):
        sec_name, entries = sections[index]
        if str(sec_name).strip().lower() != "mroom":
            continue
        nickname = entry_get_value(entries, "nickname").strip().lower()
        if nickname in target_rooms:
            sections.pop(index)
            removed = True

    start_idx, end_idx = npc_find_section_range(sections, mbase_idx)
    last_gf_idx: int | None = None
    last_basefaction_idx: int | None = None
    mvendor_idx: int | None = None
    for index in range(start_idx + 1, end_idx):
        section_name = str(sections[index][0]).strip().lower()
        if section_name == "gf_npc":
            last_gf_idx = index
        elif section_name == "basefaction":
            last_basefaction_idx = index
        elif section_name == "mvendor" and mvendor_idx is None:
            mvendor_idx = index

    if last_gf_idx is not None:
        insert_at = last_gf_idx + 1
    elif mvendor_idx is not None:
        insert_at = mvendor_idx + 1
    elif last_basefaction_idx is not None:
        insert_at = last_basefaction_idx
    else:
        insert_at = start_idx + 1

    added = False
    order = {"deck": 1, "bar": 2, "trader": 3, "equipment": 4, "shipdealer": 5, "cityscape": 6}
    for room_name in sorted(room_fixtures.keys(), key=lambda value: (order.get(str(value).lower(), 99), str(value).lower())):
        fixture_rows = room_fixtures.get(room_name, [])
        if not fixture_rows:
            continue
        room_key = npc_room_key(room_name)
        room_nick = npc_canonical_mroom_name(room_name)
        entries: list[tuple[str, str]] = [
            ("nickname", room_nick),
            ("character_density", str(npc_room_density(room_key))),
        ]
        seen_fixture_npcs: set[str] = set()
        for npc, role in fixture_rows:
            if not str(npc or "").strip():
                continue
            npc_low = str(npc).strip().lower()
            if npc_low in seen_fixture_npcs:
                continue
            seen_fixture_npcs.add(npc_low)
            role_normalized = npc_normalize_role_for_room(role, room_key)
            script, role_out = npc_fixture_scene_for_role(role_normalized)
            pose_role = "Bartender" if str(role_out).strip().lower() == "bartender" else role_out
            entries.append(("fixture", f"{npc}, Zs/NPC/{pose_role}/01/A/Stand, {script}, {role_out}"))
        if len(entries) <= 2:
            continue
        sections.insert(insert_at, ("MRoom", entries))
        insert_at += 1
        added = True

    return removed or added
