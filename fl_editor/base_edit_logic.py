from __future__ import annotations


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
