from __future__ import annotations


def build_patrol_zone_payload(
    *,
    name: str,
    usage: str,
    comment: str,
    sort: int,
    radius: int,
    damage: int,
    toughness: int,
    density: int,
    repop_time: int,
    max_battle_size: int,
    pop_type: str,
    relief_time: int,
    path_label: str,
    path_index: int,
    encounter: str,
    faction: str,
    levels_text: str,
    default_chance: int,
    last_diff_enabled: bool,
    last_chance: int,
    mission_eligible: bool,
) -> dict[str, object]:
    levels: list[int] = []
    for token in str(levels_text or "").split(","):
        t = token.strip()
        if not t:
            continue
        try:
            n = int(t)
        except ValueError:
            continue
        if n > 0:
            levels.append(n)
    if not levels:
        levels = [2, 5, 8, 11, 14, 17, 19]

    pairs: list[tuple[int, int]] = []
    for i, lvl in enumerate(levels):
        chance = int(last_chance) if bool(last_diff_enabled) and i == len(levels) - 1 else int(default_chance)
        pairs.append((lvl, chance))

    return {
        "name": str(name or "").strip(),
        "usage": str(usage or "").strip().lower() or "patrol",
        "comment": str(comment or "").strip(),
        "sort": int(sort),
        "radius": int(radius),
        "damage": int(damage),
        "toughness": int(toughness),
        "density": int(density),
        "repop_time": int(repop_time),
        "max_battle_size": int(max_battle_size),
        "pop_type": str(pop_type or "").strip() or "attack_patrol",
        "relief_time": int(relief_time),
        "path_label": str(path_label or "").strip(),
        "path_index": int(path_index),
        "encounter": str(encounter or "").strip(),
        "faction": str(faction or "").strip(),
        "encounter_pairs": pairs,
        "mission_eligible": bool(mission_eligible),
    }


def build_exclusion_zone_data(
    *,
    nickname: str,
    shape: str,
    comment: str,
    sort: int,
    link_to_field_zone: bool,
    shell_enabled: bool = False,
    shell_fog_far: int = 0,
    shell_path: str = "",
    shell_scalar: float = 1.0,
    shell_max_alpha: float = 0.5,
    shell_tint: str = "",
) -> dict[str, object]:
    return {
        "nickname": str(nickname or "").strip(),
        "shape": str(shape or "").strip().upper(),
        "comment": str(comment or "").strip(),
        "sort": int(sort),
        "link_to_field_zone": bool(link_to_field_zone),
        "shell_enabled": bool(shell_enabled),
        "shell_fog_far": int(shell_fog_far),
        "shell_path": str(shell_path or "").strip(),
        "shell_scalar": float(shell_scalar),
        "shell_max_alpha": float(shell_max_alpha),
        "shell_tint": str(shell_tint or "").strip(),
    }


def build_solar_creation_payload(
    *,
    nickname: str,
    ids_name_text: str,
    archetype: str,
    burn_color: str,
    radius: int,
    damage: int,
    star: str,
    atmosphere_range: int,
    planet_ring: str,
) -> dict[str, object]:
    return {
        "nickname": str(nickname or "").strip(),
        "ids_name_text": str(ids_name_text or "").strip(),
        "archetype": str(archetype or "").strip(),
        "burn_color": str(burn_color or "").strip(),
        "radius": int(radius),
        "damage": int(damage),
        "star": str(star or "").strip(),
        "atmosphere_range": int(atmosphere_range),
        "planet_ring": str(planet_ring or "").strip(),
    }


def build_light_source_payload(
    *,
    nickname: str,
    light_type: str,
    color: str,
    range_value: int,
    atten_curve: str,
) -> dict[str, object]:
    return {
        "nickname": str(nickname or "").strip(),
        "type": str(light_type or "").strip().upper(),
        "color": str(color or "").strip(),
        "range": int(range_value),
        "atten_curve": str(atten_curve or "").strip(),
    }


def build_object_creation_payload(
    *,
    nickname: str,
    ids_name_text: str,
    archetype: str,
    loadout: str,
    faction: str,
) -> dict[str, str]:
    return {
        "nickname": str(nickname or "").strip(),
        "ids_name_text": str(ids_name_text or "").strip(),
        "archetype": str(archetype or "").strip(),
        "loadout": str(loadout or "").strip(),
        "faction": str(faction or "").strip(),
    }


def build_category_object_payload(
    *,
    archetype: str,
    ids_name_text: str,
    loadout: str,
    faction: str = "",
    rep: str = "",
) -> dict[str, str]:
    out = {
        "archetype": str(archetype or "").strip(),
        "ids_name_text": str(ids_name_text or "").strip(),
        "loadout": str(loadout or "").strip(),
    }
    faction_txt = str(faction or "").strip()
    rep_txt = str(rep or "").strip()
    if faction_txt:
        out["faction"] = faction_txt
    if rep_txt:
        out["rep"] = rep_txt
    return out


def build_buoy_payload(
    *,
    buoy_type: str,
    pattern: str,
    count: int,
    spacing: int,
) -> dict[str, object]:
    pat = str(pattern or "").strip().upper()
    return {
        "buoy_type": str(buoy_type or "").strip(),
        "pattern": pat,
        "count": 1 if pat == "SINGLE" else (int(count) if pat == "CIRCLE" else 0),
        "spacing": int(spacing),
        "radius": 0,
    }


def build_trade_lane_payload(
    *,
    ring_count: int,
    spacing: int,
    start_num: int,
    loadout: str,
    reputation: str,
    difficulty_level: int,
    pilot: str,
    ids_name: str,
    space_name_start: str,
    space_name_end: str,
) -> dict[str, object]:
    return {
        "ring_count": int(ring_count),
        "spacing": int(spacing),
        "start_num": int(start_num),
        "loadout": str(loadout or "").strip(),
        "reputation": str(reputation or "").strip(),
        "difficulty_level": int(difficulty_level),
        "pilot": str(pilot or "").strip(),
        "ids_name": str(ids_name or "").strip() or "0",
        "space_name_start": str(space_name_start or "").strip() or "0",
        "space_name_end": str(space_name_end or "").strip() or "0",
    }
