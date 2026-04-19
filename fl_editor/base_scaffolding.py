from __future__ import annotations

from pathlib import Path
from typing import Callable

from .text_write_utils import write_text_atomic


ROOM_HOTSPOT_MAP: dict[str, str] = {
    "bar": "IDS_HOTSPOT_BAR",
    "trader": "IDS_HOTSPOT_COMMODITYTRADER_ROOM",
    "equipment": "IDS_HOTSPOT_EQUIPMENTDEALER_ROOM",
    "shipdealer": "IDS_HOTSPOT_SHIPDEALER_ROOM",
    "cityscape": "IDS_HOTSPOT_CITYSCAPE",
    "deck": "IDS_HOTSPOT_DECK",
}


def build_base_ini_text(
    *,
    base_nick: str,
    system_nick: str,
    start_room: str,
    price_variance: float,
    rooms: list[str],
) -> str:
    lines = [
        "[BaseInfo]",
        f"nickname = {base_nick}",
        f"start_room = {start_room}",
        f"price_variance = {float(price_variance):.2f}",
        "",
    ]
    for room_name in rooms:
        room_lower = str(room_name or "").strip().lower()
        rel = f"Universe\\Systems\\{system_nick}\\Bases\\Rooms\\{base_nick}_{room_lower}.ini"
        lines.extend(
            [
                "[Room]",
                f"nickname = {room_name}",
                f"file = {rel}",
                "",
            ]
        )
    return "\n".join(lines)


def write_room_ini(path: str | Path, content: str) -> Path:
    target = Path(path)
    target.write_text(normalize_generated_room_ini_text(content), encoding="utf-8")
    return target


def normalize_generated_room_ini_text(content: str) -> str:
    raw_lines = str(content or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned_lines: list[str] = []
    blank_pending = False
    for raw_line in raw_lines:
        line = str(raw_line or "").rstrip()
        if not line.strip():
            if cleaned_lines:
                blank_pending = True
            continue
        if blank_pending and cleaned_lines:
            cleaned_lines.append("")
            blank_pending = False
        cleaned_lines.append(line)
    while cleaned_lines and not str(cleaned_lines[-1]).strip():
        cleaned_lines.pop()
    return "\n".join(cleaned_lines) + "\n"


def write_base_ini(
    path: str | Path,
    *,
    base_nick: str,
    system_nick: str,
    start_room: str,
    price_variance: float,
    rooms: list[str],
) -> Path:
    target = Path(path)
    write_text_atomic(
        target,
        build_base_ini_text(
            base_nick=base_nick,
            system_nick=system_nick,
            start_room=start_room,
            price_variance=price_variance,
            rooms=rooms,
        ),
    )
    return target


def build_nav_hotspots(all_rooms: list[str], start_room: str) -> list[tuple[str, str]]:
    nav: list[tuple[str, str]] = [("IDS_HOTSPOT_EXIT", start_room)]
    for room in all_rooms:
        room_text = str(room or "").strip()
        if room_text.lower() == str(start_room or "").strip().lower():
            continue
        hotspot = ROOM_HOTSPOT_MAP.get(room_text.lower(), f"IDS_HOTSPOT_{room_text.upper()}")
        nav.append((hotspot, room_text))
    return nav


def resolve_scene_template_content(
    *,
    room_name: str,
    scene_override: str,
    scene_templates_by_room: dict[str, dict[str, str]] | None,
) -> str:
    room_key = str(room_name or "").strip().lower()
    scene_key = str(scene_override or "").strip()
    if not room_key or not scene_key or not isinstance(scene_templates_by_room, dict):
        return ""
    room_templates = scene_templates_by_room.get(room_key, {})
    if not isinstance(room_templates, dict):
        return ""
    return str(room_templates.get(scene_key, "") or "")


def normalize_room_navigation(
    content: str,
    room_name: str,
    all_rooms: list[str],
    start_room: str,
) -> str:
    nav_expected = build_nav_hotspots(all_rooms, start_room)
    lines = str(content or "").splitlines()
    result: list[str] = []
    i = 0
    insertion_point: int | None = None
    preserved_exit_names: set[str] = set()
    preserved_exit_targets: set[str] = set()
    valid_targets = {str(room or "").strip().lower() for room in all_rooms if str(room or "").strip()}
    room_name_key = str(room_name or "").strip().lower()
    if room_name_key:
        valid_targets.add(room_name_key)

    while i < len(lines):
        stripped = lines[i].strip().lower()
        if stripped == "[hotspot]":
            block: list[str] = [lines[i]]
            i += 1
            while i < len(lines) and not lines[i].strip().lower().startswith("["):
                block.append(lines[i])
                i += 1
            is_exit_door = False
            has_virtual_target = False
            direct_target = ""
            hotspot_name = ""
            room_switch_target = ""
            for line in block:
                stripped_line = line.strip()
                if "=" not in stripped_line:
                    continue
                key, _, value = stripped_line.partition("=")
                key = key.strip().lower()
                value = value.strip()
                if key == "behavior" and value.lower() == "exitdoor":
                    is_exit_door = True
                elif key in ("virtual_room", "set_virtual_room") and value:
                    has_virtual_target = True
                    if value.strip().lower() in valid_targets:
                        direct_target = value.strip()
                elif key == "name" and value:
                    hotspot_name = value
                elif key == "room_switch" and value:
                    room_switch_target = value
            if direct_target:
                rewritten_block: list[str] = []
                room_switch_written = False
                for line in block:
                    stripped_line = line.strip()
                    if "=" not in stripped_line:
                        rewritten_block.append(line)
                        continue
                    key, _, _value = stripped_line.partition("=")
                    normalized_key = key.strip().lower()
                    if normalized_key == "behavior":
                        rewritten_block.append("behavior = ExitDoor")
                        is_exit_door = True
                        continue
                    if normalized_key == "room_switch":
                        rewritten_block.append(f"room_switch = {direct_target}")
                        room_switch_written = True
                        room_switch_target = direct_target
                        continue
                    if normalized_key in ("virtual_room", "set_virtual_room"):
                        continue
                    rewritten_block.append(line)
                if not room_switch_written:
                    insert_at = len(rewritten_block)
                    for block_index, block_line in enumerate(rewritten_block):
                        if str(block_line).strip().lower().startswith("behavior ="):
                            insert_at = block_index + 1
                            break
                    rewritten_block.insert(insert_at, f"room_switch = {direct_target}")
                    room_switch_target = direct_target
                block = rewritten_block
                has_virtual_target = False
            if is_exit_door and not has_virtual_target:
                target_key = str(room_switch_target or "").strip().lower()
                if target_key and target_key in valid_targets:
                    preserved_exit_targets.add(target_key)
                    result.extend(block)
                    insertion_point = len(result)
                continue
            if is_exit_door and has_virtual_target and hotspot_name:
                preserved_exit_names.add(hotspot_name.strip().lower())
            result.extend(block)
            continue
        result.append(lines[i])
        i += 1

    if insertion_point is None:
        while result and result[-1].strip() == "":
            result.pop()
        result.append("")
        insertion_point = len(result)

    nav_lines: list[str] = []
    for hotspot_name, target in nav_expected:
        if str(target).strip().lower() in preserved_exit_targets:
            continue
        if str(hotspot_name).strip().lower() in preserved_exit_names:
            continue
        nav_lines.extend(
            [
                "[Hotspot]",
                f"name = {hotspot_name}",
                "behavior = ExitDoor",
                f"room_switch = {target}",
                "",
            ]
        )
    result[insertion_point:insertion_point] = nav_lines
    return "\n".join(result)


def generate_room_ini_text(room_name: str, all_rooms: list[str], start_room: str) -> str:
    room_lower = str(room_name or "").strip().lower()
    lines: list[str] = []

    if room_lower == "deck":
        lines.extend([
            "[Room_Info]",
            "set_script = Scripts\\Bases\\Li_08_Deck_hardpoint_01.thn",
            "scene = all, ambient, Scripts\\Bases\\Li_08_Deck_ambi_int_01.thn",
            "animation = Sc_loop",
        ])
    elif room_lower == "bar":
        lines.extend([
            "[Room_Info]",
            "set_script = Scripts\\Bases\\Li_09_bar_hardpoint_s020x.thn",
            "scene = all, ambient, Scripts\\Bases\\Li_09_bar_ambi_int_s020x.thn",
        ])
    elif room_lower == "trader":
        lines.extend([
            "[Room_Info]",
            "set_script = Scripts\\Bases\\Li_01_Trader_hardpoint_01.thn",
            "scene = all, ambient, Scripts\\Bases\\Li_01_Trader_ambi_int_01.thn",
        ])
    elif room_lower == "equipment":
        lines.extend([
            "[Room_Info]",
            "set_script = scripts\\bases\\Li_01_equipment_hardpoint_01.thn",
            "scene = all, ambient, Scripts\\Bases\\Li_01_equipment_ambi_int_01.thn",
        ])
    elif room_lower == "shipdealer":
        lines.extend([
            "[Room_Info]",
            "set_script = Scripts\\Bases\\Li_01_shipdealer_hardpoint_01.thn",
            "scene = all, ambient, Scripts\\Bases\\Li_01_shipdealer_ambi_int_01.thn",
        ])
    elif room_lower == "cityscape":
        lines.extend([
            "[Room_Info]",
            "set_script = Scripts\\Bases\\Li_01_cityscape_hardpoint_01.thn",
            "animation = Sc_loop",
            "scene = all, ambient, Scripts\\Bases\\Li_01_cityscape_ambi_day_01.thn",
        ])
    else:
        lines.extend([
            "[Room_Info]",
            "set_script = Scripts\\Bases\\Li_08_Deck_hardpoint_01.thn",
            "scene = all, ambient, Scripts\\Bases\\Li_08_Deck_ambi_int_01.thn",
        ])

    lines.append("")

    if room_lower == "trader":
        lines.extend(["[Spiels]", "CommodityDealer = manhattan_commodity_spiel", ""])
    elif room_lower == "equipment":
        lines.extend(["[Spiels]", "EquipmentDealer = manhattan_equipment_spiel", ""])
    elif room_lower == "shipdealer":
        lines.extend(["[Spiels]", "ShipDealer = manhattan_ship_spiel", ""])

    if room_lower == "bar":
        lines.extend(["[Room_Sound]", "ambient = ambience_deck_space_smaller", ""])
    elif room_lower in ("deck", "cityscape"):
        lines.extend(["[Room_Sound]", "ambient = ambience_deck_space_smaller", ""])
    elif room_lower == "equipment":
        lines.extend(["[Room_Sound]", "ambient = ambience_equip_ground_larger", ""])
    elif room_lower == "shipdealer":
        lines.extend(["[Room_Sound]", "ambient = ambience_shipbuy", ""])
    elif room_lower == "trader":
        lines.extend(["[Room_Sound]", "ambient = ambience_comm", ""])
    else:
        lines.extend(["[Room_Sound]", "ambient = ambience_deck_space_smaller", ""])

    lines.extend(["[Camera]", "name = Camera_0", ""])

    if room_lower in ("bar", "trader", "equipment", "shipdealer"):
        lines.extend(["[CharacterPlacement]", "name = Zg/PC/Player/01/A/Stand", ""])

    if room_lower in ("deck", "cityscape", "equipment"):
        lines.extend(["[PlayerShipPlacement]", "name = X/Shipcentre/01", ""])

    if room_lower == "shipdealer":
        lines.extend([
            "[ForSaleShipPlacement]", "name = X/Shipcentre/01", "",
            "[ForSaleShipPlacement]", "name = X/Shipcentre/02", "",
            "[ForSaleShipPlacement]", "name = X/Shipcentre/03", "",
        ])

    for hotspot_name, target in build_nav_hotspots(all_rooms, start_room):
        lines.extend([
            "[Hotspot]",
            f"name = {hotspot_name}",
            "behavior = ExitDoor",
            f"room_switch = {target}",
            "",
        ])

    if room_lower == "bar":
        lines.extend([
            "[Hotspot]", "name = IDS_HOTSPOT_NEWSVENDOR",
            "behavior = NewsVendor", "",
            "[Hotspot]", "name = IDS_HOTSPOT_MISSIONVENDOR",
            "behavior = MissionVendor", "",
        ])
    elif room_lower == "trader":
        lines.extend([
            "[Hotspot]", "name = IDS_DEALER_FRONT_DESK",
            "behavior = FrontDesk", "state_read = 1", "state_send = 2", "",
            "[Hotspot]", "name = IDS_HOTSPOT_COMMODITYTRADER",
            "behavior = StartDealer", "state_read = 2", "state_send = 1", "",
        ])
    elif room_lower == "equipment":
        lines.extend([
            "[Hotspot]", "name = IDS_NN_REPAIR_YOUR_SHIP",
            "behavior = Repair", "",
            "[Hotspot]", "name = IDS_DEALER_FRONT_DESK",
            "behavior = FrontDesk", "state_read = 1", "state_send = 2", "",
            "[Hotspot]", "name = IDS_HOTSPOT_EQUIPMENTDEALER",
            "behavior = StartEquipDealer", "state_read = 2", "state_send = 1", "",
        ])
    elif room_lower == "shipdealer":
        lines.extend([
            "[Hotspot]", "name = IDS_NN_REPAIR_YOUR_SHIP",
            "behavior = Repair", "",
            "[Hotspot]", "name = IDS_DEALER_FRONT_DESK",
            "behavior = FrontDesk", "state_read = 1", "state_send = 2", "",
            "[Hotspot]", "name = IDS_HOTSPOT_SHIPDEALER",
            "behavior = StartShipDealer", "state_read = 2", "state_send = 1", "",
        ])
    elif room_lower in ("deck", "cityscape"):
        lines.extend([
            "[Hotspot]", "name = IDS_NN_REPAIR_YOUR_SHIP",
            "behavior = Repair", "",
        ])

    return "\n".join(lines)


def create_base_room_files(
    *,
    rooms_dir: str | Path,
    base_nick: str,
    rooms: list[str],
    start_room: str,
    template_rooms: dict[str, str],
    room_customizations: dict,
    scene_templates_by_room: dict[str, dict[str, str]] | None,
    adapt_template_room: Callable[[str, str, list[str]], str],
    generate_room_ini: Callable[[str, list[str], str], str],
    override_room_scene: Callable[[str, str], str],
    normalize_room_navigation_callback: Callable[[str, str, list[str], str], str],
    room_exists_message: Callable[[str], str],
    room_created_message: Callable[[str], str],
) -> list[str]:
    target_rooms_dir = Path(rooms_dir)
    target_rooms_dir.mkdir(parents=True, exist_ok=True)
    results: list[str] = []

    for room_name in rooms:
        room_lower = str(room_name or "").strip().lower()
        room_file = target_rooms_dir / f"{base_nick}_{room_lower}.ini"
        if room_file.exists():
            results.append(room_exists_message(room_file.name))
            continue

        room_cfg = room_customizations.get(room_lower, {}) if isinstance(room_customizations, dict) else {}
        scene_override = str(room_cfg.get("scene", "")).strip() if isinstance(room_cfg, dict) else ""
        scene_template_content = resolve_scene_template_content(
            room_name=room_name,
            scene_override=scene_override,
            scene_templates_by_room=scene_templates_by_room,
        )

        if scene_template_content:
            content = adapt_template_room(scene_template_content, base_nick, rooms)
        elif room_lower in template_rooms:
            content = adapt_template_room(template_rooms[room_lower], base_nick, rooms)
        else:
            content = generate_room_ini(room_name, rooms, start_room)

        if scene_override and not scene_template_content:
            content = override_room_scene(content, scene_override)
        content = normalize_room_navigation_callback(content, room_name, rooms, start_room)

        write_room_ini(room_file, content)
        results.append(room_created_message(room_file.name))

    return results


def sync_base_room_files(
    *,
    rooms_dir: str | Path,
    base_nick: str,
    selected_rooms: list[str],
    existing_rooms: list[str],
    start_room: str,
    template_rooms: dict[str, str],
    room_customizations: dict,
    room_scene_by_name: dict[str, str],
    scene_templates_by_room: dict[str, dict[str, str]] | None,
    adapt_template_room: Callable[[str, str, list[str]], str],
    read_room_text: Callable[[Path], str],
    generate_room_ini: Callable[[str, list[str], str], str],
    override_room_scene: Callable[[str, str], str],
    normalize_room_navigation_callback: Callable[[str, str, list[str], str], str],
    remove_room_file: Callable[[Path], None],
) -> None:
    target_rooms_dir = Path(rooms_dir)
    target_rooms_dir.mkdir(parents=True, exist_ok=True)
    selected_rooms_lower = {str(room or "").strip().lower() for room in selected_rooms}
    existing_rooms_lower = {str(room or "").strip().lower() for room in existing_rooms}

    for room_name in selected_rooms:
        room_lower = str(room_name or "").strip().lower()
        room_file = target_rooms_dir / f"{base_nick}_{room_lower}.ini"
        room_cfg = room_customizations.get(room_lower, {}) if isinstance(room_customizations, dict) else {}
        scene_override = str(room_cfg.get("scene", "")).strip() if isinstance(room_cfg, dict) else ""
        scene_template_content = resolve_scene_template_content(
            room_name=room_name,
            scene_override=scene_override,
            scene_templates_by_room=scene_templates_by_room,
        )
        if scene_template_content:
            content = adapt_template_room(scene_template_content, base_nick, selected_rooms)
        elif room_lower in template_rooms:
            content = adapt_template_room(template_rooms[room_lower], base_nick, selected_rooms)
        elif room_file.exists():
            content = read_room_text(room_file)
        else:
            content = generate_room_ini(room_name, selected_rooms, start_room)

        current_scene = str(room_scene_by_name.get(room_lower, "")).strip()
        apply_scene_override = bool(scene_override and scene_override.lower() != current_scene.lower())
        if apply_scene_override and not scene_template_content:
            content = override_room_scene(content, scene_override)
        content = normalize_room_navigation_callback(content, room_name, selected_rooms, start_room)
        write_room_ini(room_file, content)

    for old_room in existing_rooms_lower - selected_rooms_lower:
        old_file = target_rooms_dir / f"{base_nick}_{old_room}.ini"
        if old_file.exists():
            remove_room_file(old_file)
