from __future__ import annotations

from pathlib import Path
from typing import Callable


ROOM_ORDER = {"deck": 1, "bar": 2, "trader": 3, "equipment": 4, "shipdealer": 5, "cityscape": 6}


def load_template_rooms(
    *,
    universe_sections: list[tuple[str, list[tuple[str, str]]]],
    template_base_nick: str,
    game_path: str,
    resolve_game_path_case_insensitive: Callable[[str, str], Path | None],
    parse_sections: Callable[[str], list[tuple[str, list[tuple[str, str]]]]],
    read_text_best_effort: Callable[[Path], str],
) -> dict[str, str]:
    result: dict[str, str] = {}
    target_base = str(template_base_nick or "").strip().lower()
    if not target_base:
        return result

    base_file_rel = ""
    for sec_name, entries in universe_sections:
        if str(sec_name).strip().lower() != "base":
            continue
        nickname = ""
        file_rel = ""
        for key, value in entries:
            normalized_key = str(key).strip().lower()
            if normalized_key == "nickname":
                nickname = str(value).strip()
            elif normalized_key == "file":
                file_rel = str(value).strip()
        if nickname.lower() == target_base:
            base_file_rel = file_rel
            break
    if not base_file_rel:
        return result

    base_ini = resolve_game_path_case_insensitive(game_path, base_file_rel)
    if not base_ini or not base_ini.exists():
        return result

    try:
        base_sections = parse_sections(str(base_ini))
    except Exception:
        return result

    for sec_name, entries in base_sections:
        if str(sec_name).strip().lower() != "room":
            continue
        room_nick = ""
        room_file_rel = ""
        for key, value in entries:
            normalized_key = str(key).strip().lower()
            if normalized_key == "nickname":
                room_nick = str(value).strip()
            elif normalized_key == "file":
                room_file_rel = str(value).strip()
        if not room_nick or not room_file_rel:
            continue
        room_path = resolve_game_path_case_insensitive(game_path, room_file_rel)
        if room_path and room_path.exists():
            try:
                result[room_nick.lower()] = read_text_best_effort(room_path)
            except Exception:
                continue
    return result


def load_base_room_template_details(
    *,
    universe_sections: list[tuple[str, list[tuple[str, str]]]],
    template_base_nick: str,
    game_path: str,
    resolve_game_path_case_insensitive: Callable[[str, str], Path | None],
    parse_sections: Callable[[str], list[tuple[str, list[tuple[str, str]]]]],
    read_text_best_effort: Callable[[Path], str],
    extract_room_scene_path: Callable[[str], str],
) -> list[dict]:
    rows: list[dict] = []
    room_templates = load_template_rooms(
        universe_sections=universe_sections,
        template_base_nick=template_base_nick,
        game_path=game_path,
        resolve_game_path_case_insensitive=resolve_game_path_case_insensitive,
        parse_sections=parse_sections,
        read_text_best_effort=read_text_best_effort,
    )

    target_base = str(template_base_nick or "").strip().lower()
    if not target_base:
        return rows

    base_file_rel = ""
    for sec_name, entries in universe_sections:
        if str(sec_name).strip().lower() != "base":
            continue
        nickname = ""
        file_rel = ""
        for key, value in entries:
            normalized_key = str(key).strip().lower()
            if normalized_key == "nickname":
                nickname = str(value).strip()
            elif normalized_key == "file":
                file_rel = str(value).strip()
        if nickname.lower() == target_base:
            base_file_rel = file_rel
            break
    if not base_file_rel:
        return rows

    base_ini = resolve_game_path_case_insensitive(game_path, base_file_rel)
    if not base_ini or not base_ini.exists():
        return rows
    try:
        base_sections = parse_sections(str(base_ini))
    except Exception:
        return rows

    for sec_name, entries in base_sections:
        if str(sec_name).strip().lower() != "room":
            continue
        room_nick = ""
        room_file_rel = ""
        for key, value in entries:
            normalized_key = str(key).strip().lower()
            if normalized_key == "nickname":
                room_nick = str(value).strip()
            elif normalized_key == "file":
                room_file_rel = str(value).strip()
        if not room_nick:
            continue
        scene = ""
        template_content = room_templates.get(room_nick.lower(), "")
        if template_content:
            try:
                scene = extract_room_scene_path(template_content)
            except Exception:
                scene = ""
        rows.append({"room": room_nick, "file": room_file_rel, "scene": scene})

    rows.sort(key=lambda row: (ROOM_ORDER.get(str(row.get("room", "")).lower(), 99), str(row.get("room", "")).lower()))
    return rows


def load_base_template_virtual_room_targets(
    *,
    template_rooms: dict[str, str],
    extract_virtual_room_targets: Callable[[str], list[str]],
) -> list[str]:
    targets: set[str] = set()
    for _room, content in template_rooms.items():
        for target in extract_virtual_room_targets(content):
            if target:
                targets.add(target.lower())
    return sorted(targets, key=lambda room: (ROOM_ORDER.get(room, 99), room))
