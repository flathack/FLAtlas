from __future__ import annotations


def object_entries_to_dict(obj_entries: list[tuple[str, str]]) -> dict[str, str]:
    obj_dict: dict[str, str] = {}
    for key, value in list(obj_entries or []):
        norm_key = str(key or "").strip().lower()
        if norm_key and norm_key not in obj_dict:
            obj_dict[norm_key] = str(value or "")
    return obj_dict


def normalize_solar_pilot_choices(pilots: list[str]) -> list[str]:
    merged = list(
        dict.fromkeys(
            [
                "pilot_solar_easiest",
                "pilot_solar_easy",
                "pilot_solar_hard",
                "pilot_solar_hardest",
            ]
            + [str(p or "").strip() for p in list(pilots or []) if str(p or "").strip()]
        )
    )
    return [pilot for pilot in merged if pilot.lower().startswith("pilot_solar")]


def build_base_edit_property_state(
    *,
    obj_entries: list[tuple[str, str]],
    pilots: list[str],
) -> dict[str, object]:
    obj_dict = object_entries_to_dict(obj_entries)
    head, body = split_space_costume(obj_dict.get("space_costume", ""))
    return {
        "obj_dict": obj_dict,
        "head": head,
        "body": body,
        "pilot_choices": normalize_solar_pilot_choices(pilots),
        "ids_name": int(obj_dict.get("ids_name", "0") or 0),
        "ids_info": int(obj_dict.get("ids_info", "0") or 0),
        "difficulty_level": int(obj_dict.get("difficulty_level", "1") or 1),
    }


def split_space_costume(costume_val: str) -> tuple[str, str]:
    parts = [p.strip() for p in str(costume_val or "").split(",", 1)] if costume_val else ["", ""]
    if len(parts) < 2:
        parts.append("")
    return parts[0], parts[1]


def build_space_costume(head: str, body: str) -> str:
    head_txt = str(head or "").strip()
    body_txt = str(body or "").strip()
    if head_txt and body_txt:
        return f"{head_txt}, {body_txt}"
    return head_txt or body_txt


def build_base_edit_obj_properties(
    *,
    nickname: str,
    archetype: str,
    loadout: str,
    reputation: str,
    pilot: str,
    voice: str,
    head: str,
    body: str,
    ids_name: int | str,
    ids_info: int | str,
    behavior: str,
    difficulty_level: int | str,
) -> dict[str, str]:
    return {
        "nickname": str(nickname or "").strip(),
        "archetype": str(archetype or "").strip(),
        "loadout": str(loadout or "").strip(),
        "reputation": str(reputation or "").strip(),
        "pilot": str(pilot or "").strip(),
        "voice": str(voice or "").strip(),
        "space_costume": build_space_costume(head, body),
        "ids_name": str(ids_name),
        "ids_info": str(ids_info),
        "behavior": str(behavior or "").strip(),
        "difficulty_level": str(difficulty_level),
    }


def collect_table_rows(raw_rows: list[list[str]], *, max_cols: int | None = None) -> list[list[str]]:
    out: list[list[str]] = []
    for row in list(raw_rows or []):
        values = [str(cell or "").strip() for cell in list(row or [])]
        if max_cols is not None:
            values = values[:max_cols]
        if values and values[0]:
            out.append(values)
    return out


def collect_ship_market_goods(selected_nicks: list[str], ship_market_data: dict[str, list[str]]) -> list[list[str]]:
    result: list[list[str]] = []
    for nick in [str(v or "").strip() for v in list(selected_nicks or []) if str(v or "").strip()]:
        existing = ship_market_data.get(nick.lower())
        if existing:
            result.append(list(existing))
        else:
            result.append([nick, "1", "-1", "1", "1", "0", "1", "1"])
    return result


def can_open_infocard(ids_info: int | str) -> bool:
    try:
        return int(ids_info) > 0
    except (TypeError, ValueError):
        return False


def extract_assigned_nicknames(rows: list[list[str]]) -> list[str]:
    return [str(row[0]).strip() for row in list(rows or []) if row and str(row[0]).strip()]


def assigned_nickname_set(rows: list[list[str]]) -> set[str]:
    return {nick.lower() for nick in extract_assigned_nicknames(rows)}


def available_nicknames(all_nicks: list[str], assigned_lower: set[str]) -> list[str]:
    return [
        str(nick).strip()
        for nick in sorted([str(n).strip() for n in list(all_nicks or []) if str(n).strip()], key=str.lower)
        if str(nick).strip().lower() not in assigned_lower
    ]


def build_equip_market_row(row: list[str]) -> list[str]:
    values = [str(cell or "").strip() for cell in list(row or [])]
    if not values or not values[0]:
        return []
    defaults = ["0", "-1", "10", "10", "0", "1"]
    return [values[0]] + [
        values[col].strip() if col < len(values) and str(values[col]).strip() else defaults[col - 1]
        for col in range(1, 7)
    ]


def build_default_equip_market_row(nick: str) -> list[str]:
    return [str(nick or "").strip(), "0", "-1", "10", "10", "0", "1"]


def commodity_price_cells(base_price: int | str, multi_str: str) -> tuple[str, str]:
    try:
        base = int(base_price or 0)
    except (TypeError, ValueError):
        base = 0
    try:
        multi = float(multi_str)
    except (ValueError, TypeError):
        multi = 1.0
    return str(base), str(round(base * multi))


def build_commodity_market_row(row: list[str], commodity_prices: dict[str, int]) -> list[str]:
    values = [str(cell or "").strip() for cell in list(row or [])]
    if not values or not values[0]:
        return []
    nick = values[0]
    defaults = ["0", "-1", "0", "0", "0", "1"]
    core = [nick] + [
        values[col].strip() if col < len(values) and str(values[col]).strip() else defaults[col - 1]
        for col in range(1, 7)
    ]
    base_price, end_price = commodity_price_cells(commodity_prices.get(nick, 0), core[6])
    return core + [base_price, end_price]


def build_default_commodity_market_row(nick: str, commodity_prices: dict[str, int]) -> list[str]:
    return build_commodity_market_row([str(nick or "").strip(), "0", "-1", "0", "0", "0", "1"], commodity_prices)


def ship_slot_values(all_ship_nicks: list[str], assigned_ships: list[str], *, slots: int = 3) -> list[str]:
    normalized_assigned = [str(ship or "").strip() for ship in list(assigned_ships or [])]
    result: list[str] = []
    for slot in range(slots):
        if slot < len(normalized_assigned) and normalized_assigned[slot]:
            result.append(normalized_assigned[slot])
        else:
            result.append("")
    return result
