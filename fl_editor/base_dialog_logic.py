from __future__ import annotations


DEFAULT_ROOM_SCENE_PRESETS = {
    "deck": "Scripts\\Bases\\Li_08_Deck_ambi_int_01.thn",
    "bar": "Scripts\\Bases\\Li_09_bar_ambi_int_s020x.thn",
    "trader": "Scripts\\Bases\\Li_01_Trader_ambi_int_01.thn",
    "equipment": "Scripts\\Bases\\Li_01_equipment_ambi_int_01.thn",
    "shipdealer": "Scripts\\Bases\\Li_01_shipdealer_ambi_int_01.thn",
    "cityscape": "Scripts\\Bases\\Li_01_cityscape_ambi_day_01.thn",
}

DEFAULT_ROLE_OPTIONS_BY_ROOM = {
    "bar": ["bartender", "BarFly", "NewsVendor"],
    "trader": ["trader"],
    "equipment": ["Equipment"],
    "shipdealer": ["ShipDealer"],
    "deck": ["ShipDealer", "trader", "Equipment", "bartender"],
    "cityscape": ["trader"],
}


def split_npc_list(raw: str) -> list[str]:
    vals: list[str] = []
    seen: set[str] = set()
    for token in str(raw or "").replace(";", ",").replace("\n", ",").split(","):
        nick = token.strip()
        if not nick:
            continue
        low = nick.lower()
        if low in seen:
            continue
        seen.add(low)
        vals.append(nick)
    return vals


def xml_to_plain_preview(raw_xml: str) -> str:
    txt = str(raw_xml or "").strip()
    if not txt:
        return "[Keine ids_info-Templatequelle gefunden]"
    compact = txt.replace("<PARA/>", "\n").replace("<PARA>", "").replace("</PARA>", "")
    compact = compact.replace("<TEXT>", "").replace("</TEXT>", "")
    compact = compact.replace("<RDL>", "").replace("</RDL>", "")
    return compact.strip() or txt


def default_scene_for_room(
    room_name: str,
    room_scene_presets: dict[str, str] | None = None,
) -> str:
    presets = room_scene_presets or DEFAULT_ROOM_SCENE_PRESETS
    return presets.get(str(room_name or "").strip().lower(), presets["deck"])


def scene_options_for_room(
    room_name: str,
    scene_options_by_room: dict[str, list[str]] | None = None,
    room_scene_presets: dict[str, str] | None = None,
) -> list[str]:
    room = str(room_name or "").strip().lower()
    out = list((scene_options_by_room or {}).get(room, []))
    default_scene = default_scene_for_room(room, room_scene_presets)
    if default_scene not in out:
        out.append(default_scene)
    return out


def default_role_for_room(room_name: str) -> str:
    room = str(room_name or "").strip().lower()
    if room == "shipdealer":
        return "ShipDealer"
    if room == "equipment":
        return "Equipment"
    if room == "bar":
        return "bartender"
    return "trader"


def role_options_for_room(
    room_name: str,
    role_options_by_room: dict[str, list[str]] | None = None,
) -> list[str]:
    room = str(room_name or "").strip().lower()
    opts = list((role_options_by_room or DEFAULT_ROLE_OPTIONS_BY_ROOM).get(room, ["trader"]))
    return opts


def normalize_role_for_room(
    role: str,
    room_name: str,
    role_options_by_room: dict[str, list[str]] | None = None,
) -> str:
    raw = str(role or "").strip()
    opts = role_options_for_room(room_name, role_options_by_room)
    if not raw:
        return opts[0] if opts else "trader"
    low = raw.lower()
    for opt in opts:
        if opt.lower() == low:
            return opt
    return opts[0] if opts else raw


def safe_nick_part(raw: str) -> str:
    src = str(raw or "").strip().lower()
    if not src:
        return ""
    out = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in src)
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_")


def faction_nick_from_display(raw: str) -> str:
    txt = str(raw or "").strip()
    if not txt:
        return ""
    if " - " in txt:
        return txt.split(" - ", 1)[0].strip()
    return txt


def faction_display_from_any(raw: str, faction_display_by_nick: dict[str, str] | None = None) -> str:
    txt = str(raw or "").strip()
    if not txt:
        return ""
    nick = faction_nick_from_display(txt)
    return dict(faction_display_by_nick or {}).get(nick.lower(), txt)


def make_copied_npc_rows(
    room_name: str,
    template_rows: list[dict],
    used_nicks: set[str],
    *,
    base_nickname: str,
    base_reputation_display: str,
    faction_display_by_nick: dict[str, str] | None = None,
    role_options_by_room: dict[str, list[str]] | None = None,
) -> list[dict]:
    rows: list[dict] = []
    base_part = safe_nick_part(base_nickname) or "base"
    room_part = safe_nick_part(room_name) or "room"
    counter = 1
    for src in list(template_rows or []):
        name_text = str(src.get("name_text", "") if isinstance(src, dict) else "").strip()
        if not name_text:
            name_text = str(src.get("nickname", "") if isinstance(src, dict) else "").strip()
        rep = str(src.get("reputation", "") if isinstance(src, dict) else "").strip()
        aff = str(src.get("affiliation", "") if isinstance(src, dict) else "").strip()
        role = str(src.get("role", "") if isinstance(src, dict) else "").strip()
        rep_disp = faction_display_from_any(rep, faction_display_by_nick) or base_reputation_display
        aff_disp = faction_display_from_any(aff, faction_display_by_nick) or rep_disp or base_reputation_display
        while True:
            cand = f"{base_part}_{room_part}_npc_{counter:02d}"
            counter += 1
            low = cand.lower()
            if low not in used_nicks:
                used_nicks.add(low)
                rows.append(
                    {
                        "nickname": cand,
                        "name_text": name_text or cand,
                        "reputation": faction_nick_from_display(rep_disp),
                        "affiliation": faction_nick_from_display(aff_disp),
                        "role": role or default_role_for_room(room_name),
                    }
                )
                break
    return rows
