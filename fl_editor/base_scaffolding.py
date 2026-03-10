from __future__ import annotations

from pathlib import Path

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
    target.write_text(content, encoding="utf-8")
    return target


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


def normalize_room_navigation(
    content: str,
    room_name: str,
    all_rooms: list[str],
    start_room: str,
) -> str:
    del room_name
    nav_expected = build_nav_hotspots(all_rooms, start_room)
    lines = str(content or "").splitlines()
    result: list[str] = []
    i = 0
    insertion_point: int | None = None
    preserved_exit_names: set[str] = set()

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
            hotspot_name = ""
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
                elif key == "name" and value:
                    hotspot_name = value
            if is_exit_door and not has_virtual_target:
                if insertion_point is None:
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
