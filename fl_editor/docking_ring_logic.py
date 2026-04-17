from __future__ import annotations


def build_docking_ring_room_state(
    *,
    room_names: list[str] | None,
    preferred_start_room: str = "",
    current_start_room: str = "",
) -> dict[str, object]:
    rooms = [str(name or "").strip() for name in list(room_names or []) if str(name or "").strip()]
    preferred = str(preferred_start_room or "").strip()
    current = str(current_start_room or "").strip()
    if preferred and preferred in rooms:
        start_room = preferred
    elif current and current in rooms:
        start_room = current
    elif "Deck" in rooms:
        start_room = "Deck"
    else:
        start_room = rooms[0] if rooms else ""
    return {
        "rooms": rooms,
        "start_room": start_room,
    }


def build_docking_ring_payload(
    *,
    nickname: str,
    archetype: str,
    loadout: str,
    faction: str,
    voice: str,
    costume: str,
    pilot: str,
    difficulty: int,
    ids_name: str,
    ids_info: str,
    needs_base: bool,
    base_nickname: str = "",
    existing_base_nickname: str = "",
    strid_name: int = 0,
    room_names: list[str] | None = None,
    start_room: str = "",
    price_variance: float = 0.15,
    template_base: str = "",
    create_fixture: bool = False,
    copy_template_npcs: bool = True,
) -> dict:
    room_state = build_docking_ring_room_state(
        room_names=room_names,
        preferred_start_room=start_room,
    )
    result: dict = {
        "nickname": str(nickname or "").strip(),
        "archetype": str(archetype or "").strip(),
        "loadout": str(loadout or "").strip(),
        "faction": str(faction or "").strip(),
        "voice": str(voice or "").strip(),
        "costume": str(costume or "").strip(),
        "pilot": str(pilot or "").strip(),
        "difficulty": int(difficulty),
        "ids_name": str(ids_name or "").strip(),
        "ids_info": str(ids_info or "").strip(),
        "create_fixture": bool(create_fixture),
        "copy_template_npcs": bool(copy_template_npcs),
    }
    if needs_base:
        result.update(
            {
                "base_nickname": str(base_nickname or "").strip(),
                "strid_name": int(strid_name),
                "rooms": list(room_state["rooms"]),
                "start_room": str(room_state["start_room"]),
                "price_variance": float(price_variance),
                "template_base": str(template_base or "").strip(),
            }
        )
    else:
        result["base_nickname"] = str(existing_base_nickname or "").strip()
    return result
