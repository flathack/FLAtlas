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


def faction_nick_from_display(raw: str, faction_display_by_nick: dict[str, str] | None = None) -> str:
    txt = str(raw or "").strip()
    if not txt:
        return ""
    if faction_display_by_nick:
        lowered = txt.lower()
        for nick, display in dict(faction_display_by_nick).items():
            nick_clean = str(nick or "").strip()
            display_clean = str(display or "").strip()
            haystack = f"{nick_clean} {display_clean}".lower()
            if lowered == haystack or lowered == nick_clean.lower() or lowered == display_clean.lower():
                return nick_clean
        parts = [part for part in re.split(r"[\s,_-]+", lowered) if part]
        for nick, display in dict(faction_display_by_nick).items():
            nick_clean = str(nick or "").strip()
            display_clean = str(display or "").strip()
            haystack = f"{nick_clean} {display_clean}".lower()
            if lowered in haystack or (parts and all(part in haystack for part in parts)):
                return nick_clean
    if " - " in txt:
        return txt.split(" - ", 1)[0].strip()
    return txt


def faction_display_from_any(raw: str, faction_display_by_nick: dict[str, str] | None = None) -> str:
    txt = str(raw or "").strip()
    if not txt:
        return ""
    nick = faction_nick_from_display(txt, faction_display_by_nick)
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
                        "body": str(src.get("body", "") if isinstance(src, dict) else "").strip(),
                        "head": str(src.get("head", "") if isinstance(src, dict) else "").strip(),
                        "lefthand": str(src.get("lefthand", "") if isinstance(src, dict) else "").strip(),
                        "righthand": str(src.get("righthand", "") if isinstance(src, dict) else "").strip(),
                    }
                )
                break
    return rows


def build_space_costume(head: str, body: str) -> str:
    head_txt = str(head or "").strip()
    body_txt = str(body or "").strip()
    if head_txt and body_txt:
        return f"{head_txt}, {body_txt}"
    return head_txt or body_txt


def choose_start_room(active_rooms: list[str], *, preferred: str = "", current: str = "") -> str:
    normalized = [str(room or "").strip() for room in list(active_rooms or []) if str(room or "").strip()]
    target = str(preferred or "").strip() or str(current or "").strip()
    if target and target in normalized:
        return target
    if "Deck" in normalized:
        return "Deck"
    return normalized[0] if normalized else ""


def build_start_room_state(
    *,
    active_rooms: list[str],
    preferred: str = "",
    current: str = "",
) -> dict[str, object]:
    normalized = [str(room or "").strip() for room in list(active_rooms or []) if str(room or "").strip()]
    return {
        "active_rooms": normalized,
        "target_room": choose_start_room(normalized, preferred=preferred, current=current),
    }


def build_default_room_reset_state(
    *,
    room_choices: list[tuple[str, bool]],
    default_scene_for_room_fn,
) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for room_name, default_on in list(room_choices or []):
        room_txt = str(room_name or "").strip()
        if not room_txt:
            continue
        rows.append(
            {
                "room_name": room_txt,
                "enabled": bool(default_on),
                "scene": str(default_scene_for_room_fn(room_txt) or "").strip(),
                "npc_rows": [],
            }
        )
    return {
        "rows": rows,
        "info_text": "Template-Raeume werden nach Auswahl automatisch vorausgewaehlt.",
    }


def build_room_row_state(
    *,
    room_name: str,
    enabled: bool,
    scene: str,
    scene_options: list[str],
    default_scene: str,
) -> dict[str, object]:
    room_txt = str(room_name or "").strip()
    options = [str(option or "").strip() for option in list(scene_options or []) if str(option or "").strip()]
    scene_val = str(scene or "").strip() or str(default_scene or "").strip()
    if scene_val and scene_val not in options:
        options.append(scene_val)
    return {
        "room_name": room_txt,
        "enabled": bool(enabled),
        "scene_options": options,
        "selected_scene": scene_val if scene_val in options else (options[0] if options else ""),
    }


def collect_active_room_names(
    *,
    row_count: int,
    room_name_at,
    enabled_at,
) -> list[str]:
    active_rooms: list[str] = []
    for row in range(max(0, int(row_count))):
        room_name = str(room_name_at(row) or "").strip()
        if room_name and bool(enabled_at(row)):
            active_rooms.append(room_name)
    return active_rooms


def build_room_npc_tab_state(
    *,
    active_rooms: list[str],
    current_room: str,
) -> dict[str, object]:
    normalized_active = [str(room or "").strip() for room in list(active_rooms or []) if str(room or "").strip()]
    target_current = str(current_room or "").strip()
    selected_room = ""
    if target_current:
        for room_name in normalized_active:
            if room_name.lower() == target_current.lower():
                selected_room = room_name
                break
    return {
        "active_rooms": normalized_active,
        "selected_room": selected_room,
    }


def collect_room_states(
    *,
    row_count: int,
    room_name_at,
    enabled_at,
    scene_at,
    npc_rows_at,
) -> list[dict[str, object]]:
    room_states: list[dict[str, object]] = []
    for row in range(max(0, int(row_count))):
        room_name = str(room_name_at(row) or "").strip()
        if not room_name:
            continue
        room_states.append(
            {
                "room_name": room_name,
                "enabled": bool(enabled_at(row)),
                "scene": str(scene_at(row) or "").strip(),
                "npc_rows": list(npc_rows_at(room_name) or []),
            }
        )
    return room_states


def collect_room_npc_rows(
    *,
    row_count: int,
    nickname_at,
    name_text_at,
    reputation_at,
    affiliation_at,
    role_at,
    room_name: str,
    normalize_role,
    faction_nick_from_display_fn,
    default_role,
    extra_row_data_at=None,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in range(max(0, int(row_count))):
        nick = str(nickname_at(row) or "").strip()
        if not nick:
            continue
        low = nick.lower()
        if low in seen:
            continue
        seen.add(low)
        name_text = str(name_text_at(row) or "").strip()
        rep_text = str(reputation_at(row) or "").strip()
        aff_text = str(affiliation_at(row) or "").strip()
        role_text = str(role_at(row) or "").strip()
        rep_nick = str(faction_nick_from_display_fn(rep_text) or "").strip()
        aff_nick = str(faction_nick_from_display_fn(aff_text) or "").strip()
        role_norm = str(normalize_role(role_text, room_name) or "").strip()
        default_role_value = str(default_role(room_name) or "").strip()
        rows.append(
            {
                "nickname": nick,
                "name_text": name_text or nick,
                "reputation": rep_nick,
                "affiliation": aff_nick or rep_nick,
                "role": role_norm or default_role_value,
            }
        )
        if callable(extra_row_data_at):
            extra = extra_row_data_at(row)
            if isinstance(extra, dict):
                for key in ("body", "head", "lefthand", "righthand"):
                    value = str(extra.get(key, "") or "").strip()
                    if value:
                        rows[-1][key] = value
    return rows


def build_room_npc_display_rows(
    *,
    rows: list[dict],
    faction_display_from_any_fn,
    default_reputation_display: str,
    normalize_role,
    default_role,
    room_name: str,
) -> list[dict[str, str]]:
    display_rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in list(rows or []):
        nick = str(row.get("nickname", "") if isinstance(row, dict) else "").strip()
        if not nick:
            continue
        low = nick.lower()
        if low in seen:
            continue
        seen.add(low)
        name_text = str(row.get("name_text", "") if isinstance(row, dict) else "").strip() or nick
        rep = str(row.get("reputation", "") if isinstance(row, dict) else "").strip()
        aff = str(row.get("affiliation", "") if isinstance(row, dict) else "").strip()
        role = str(row.get("role", "") if isinstance(row, dict) else "").strip()
        rep_display = str(faction_display_from_any_fn(rep) or "").strip() or str(default_reputation_display or "").strip()
        aff_display = (
            str(faction_display_from_any_fn(aff) or "").strip()
            or rep_display
            or str(default_reputation_display or "").strip()
        )
        role_display = str(normalize_role(role or default_role(room_name), room_name) or "").strip()
        display_rows.append(
            {
                "nickname": nick,
                "name_text": name_text,
                "reputation_display": rep_display,
                "affiliation_display": aff_display,
                "role_display": role_display,
                "body": str(row.get("body", "") if isinstance(row, dict) else "").strip(),
                "head": str(row.get("head", "") if isinstance(row, dict) else "").strip(),
                "lefthand": str(row.get("lefthand", "") if isinstance(row, dict) else "").strip(),
                "righthand": str(row.get("righthand", "") if isinstance(row, dict) else "").strip(),
            }
        )
    return display_rows


def build_template_selection_context(
    *,
    template_value: str,
    template_room_details: dict[str, list[dict]],
    template_room_npcs: dict[str, dict[str, list[dict]]],
    template_virtual_targets: dict[str, list[str]],
) -> dict[str, object]:
    base_key = str(template_value or "").strip().lower()
    if not base_key:
        return {
            "base_key": "",
            "details": [],
            "room_npcs": {},
            "virtual_targets": set(),
        }
    return {
        "base_key": base_key,
        "details": list(template_room_details.get(base_key, [])),
        "room_npcs": dict(template_room_npcs.get(base_key, {})),
        "virtual_targets": set(template_virtual_targets.get(base_key, [])),
    }


def build_base_creation_payload(
    *,
    base_nickname: str,
    obj_nickname: str,
    ids_name_text: str,
    ids_info_template_xml: str,
    archetype: str,
    loadout: str,
    reputation: str,
    pilot: str,
    voice: str,
    head: str,
    body: str,
    room_states: list[dict],
    start_room: str,
    price_variance: int,
    template_base: str,
    copy_template_npcs: bool,
    randomize_npc_head_body: bool,
    bgcs_base_run_by: str,
) -> dict:
    rooms: list[str] = []
    room_customizations: dict[str, dict] = {}
    for state in list(room_states or []):
        room_name = str(state.get("room_name", "") if isinstance(state, dict) else "").strip()
        if not room_name:
            continue
        use_room = bool(state.get("enabled")) if isinstance(state, dict) else False
        scene_text = str(state.get("scene", "") if isinstance(state, dict) else "").strip()
        npc_rows = list(state.get("npc_rows", []) if isinstance(state, dict) else [])
        room_customizations[room_name.lower()] = {
            "scene": scene_text,
            "npc_rows": npc_rows,
            "npcs": [
                str(n.get("nickname", "")).strip()
                for n in npc_rows
                if isinstance(n, dict) and str(n.get("nickname", "")).strip()
            ],
        }
        if use_room:
            rooms.append(room_name)
    return {
        "base_nickname": str(base_nickname or "").strip(),
        "obj_nickname": str(obj_nickname or "").strip(),
        "ids_name_text": str(ids_name_text or "").strip(),
        "ids_info_template_xml": str(ids_info_template_xml or "").strip(),
        "archetype": str(archetype or "").strip(),
        "loadout": str(loadout or "").strip(),
        "reputation": str(reputation or "").strip(),
        "pilot": str(pilot or "").strip(),
        "voice": str(voice or "").strip(),
        "space_costume": build_space_costume(head, body),
        "rooms": rooms,
        "room_customizations": room_customizations,
        "start_room": str(start_room or "").strip(),
        "price_variance": int(price_variance or 0),
        "template_base": str(template_base or "").strip(),
        "copy_template_npcs": bool(copy_template_npcs),
        "randomize_npc_head_body": bool(randomize_npc_head_body),
        "bgcs_base_run_by": str(bgcs_base_run_by or "").strip(),
    }


def build_template_room_plan(
    *,
    details: list[dict],
    room_npcs: dict[str, list[dict]] | None,
    virtual_targets: set[str] | None,
    copy_template_npcs: bool,
    base_nickname: str,
    base_reputation_display: str,
    faction_display_by_nick: dict[str, str] | None = None,
    role_options_by_room: dict[str, list[str]] | None = None,
) -> dict:
    applications: list[dict] = []
    info_lines: list[str] = []
    preferred_start = ""
    used_nicks: set[str] = set()
    normalized_details = list(details or [])
    normalized_room_npcs = dict(room_npcs or {})
    for detail in normalized_details:
        room_name = str(detail.get("room", "") or "").strip()
        if not room_name:
            continue
        scene = str(detail.get("scene", "") or "").strip()
        room_file = str(detail.get("file", "") or "").strip()
        npc_rows = (
            make_copied_npc_rows(
                room_name,
                normalized_room_npcs.get(room_name.lower(), []),
                used_nicks,
                base_nickname=base_nickname,
                base_reputation_display=base_reputation_display,
                faction_display_by_nick=faction_display_by_nick,
                role_options_by_room=role_options_by_room,
            )
            if copy_template_npcs
            else []
        )
        applications.append(
            {
                "room_name": room_name,
                "scene": scene,
                "npc_rows": npc_rows,
            }
        )
        if not preferred_start:
            preferred_start = room_name
        line = f"{room_name}: {scene or '-'}"
        if room_file:
            line += f"  ({room_file})"
        info_lines.append(line)

    real_rooms = {
        str(detail.get("room", "") or "").strip().lower()
        for detail in normalized_details
        if str(detail.get("room", "") or "").strip()
    }
    locked_rooms = {
        str(room or "").strip().lower()
        for room in set(virtual_targets or set())
        if str(room or "").strip() and str(room or "").strip().lower() not in real_rooms
    }
    if locked_rooms:
        info_lines.append("")
        info_lines.append("Virtual Rooms erkannt (gesperrt): " + ", ".join(sorted(locked_rooms)))

    return {
        "applications": applications,
        "preferred_start": preferred_start,
        "locked_rooms": locked_rooms,
        "info_text": "Template-Räume:\n" + "\n".join(info_lines) if info_lines else "Template enthält keine Räume.",
        "has_details": bool(applications),
    }


def build_template_apply_state(
    *,
    plan: dict[str, object],
    room_choices: list[tuple[str, bool]],
    default_start_room: str = "Deck",
    lock_reason: str = "Gesperrt: wird im Template als Virtual Room verwendet.",
) -> dict[str, object]:
    locked_rooms = {str(room or "").strip().lower() for room in set(plan.get("locked_rooms", set()) or set())}
    applications = []
    for entry in list(plan.get("applications", []) or []):
        if not isinstance(entry, dict):
            continue
        room_name = str(entry.get("room_name", "") or "").strip()
        if not room_name:
            continue
        applications.append(
            {
                "room_name": room_name,
                "scene": str(entry.get("scene", "") or "").strip(),
                "npc_rows": list(entry.get("npc_rows", []) or []),
            }
        )
    room_locks = [
        {
            "room_name": str(room_name),
            "locked": str(room_name or "").strip().lower() in locked_rooms,
            "reason": lock_reason,
        }
        for room_name, _default in list(room_choices or [])
    ]
    return {
        "has_details": bool(plan.get("has_details")),
        "applications": applications,
        "room_locks": room_locks,
        "info_text": str(plan.get("info_text", "") or ""),
        "preferred_start": str(plan.get("preferred_start", "") or "") or str(default_start_room or "Deck"),
    }


def build_template_change_state(
    *,
    template_value: str,
    template_room_details: dict[str, list[dict]],
    template_room_npcs: dict[str, dict[str, list[dict]]],
    template_virtual_targets: dict[str, list[str]],
    room_choices: list[tuple[str, bool]],
    copy_template_npcs: bool,
    base_nickname: str,
    base_reputation_display: str,
    faction_display_by_nick: dict[str, str] | None = None,
    role_options_by_room: dict[str, list[str]] | None = None,
    default_start_room: str = "Deck",
) -> dict[str, object]:
    context = build_template_selection_context(
        template_value=template_value,
        template_room_details=template_room_details,
        template_room_npcs=template_room_npcs,
        template_virtual_targets=template_virtual_targets,
    )
    plan = build_template_room_plan(
        details=list(context["details"]),
        room_npcs=dict(context["room_npcs"]),
        virtual_targets=set(context["virtual_targets"]),
        copy_template_npcs=bool(copy_template_npcs),
        base_nickname=base_nickname,
        base_reputation_display=base_reputation_display,
        faction_display_by_nick=faction_display_by_nick,
        role_options_by_room=role_options_by_room,
    )
    apply_state = build_template_apply_state(
        plan=plan,
        room_choices=room_choices,
        default_start_room=default_start_room,
    )
    if bool(apply_state["has_details"]):
        return {
            "reset_to_defaults": False,
            "applications": list(apply_state["applications"]),
            "room_locks": list(apply_state["room_locks"]),
            "info_text": str(apply_state["info_text"]),
            "preferred_start": str(apply_state["preferred_start"]),
        }
    return {
        "reset_to_defaults": True,
        "applications": [],
        "room_locks": [
            {"room_name": str(room_name), "locked": False, "reason": ""}
            for room_name, _default in list(room_choices or [])
        ],
        "info_text": "",
        "preferred_start": str(default_start_room or "Deck"),
    }


def build_room_lock_state(
    *,
    room_name: str,
    locked: bool,
    reason: str = "",
) -> dict[str, object]:
    room_txt = str(room_name or "").strip()
    reason_txt = str(reason or "").strip()
    return {
        "room_name": room_txt,
        "locked": bool(locked),
        "force_unchecked": bool(locked),
        "check_enabled": not bool(locked),
        "room_tooltip": reason_txt if locked else "",
        "scene_enabled": not bool(locked),
        "scene_tooltip": reason_txt if locked else "",
        "npc_enabled": not bool(locked),
        "npc_reason": reason_txt if locked else "",
    }
