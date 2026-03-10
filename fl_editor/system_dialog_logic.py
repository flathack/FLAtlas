from __future__ import annotations


def build_system_creation_payload(
    *,
    name: str,
    prefix: str,
    size: int,
    space_color: str,
    music_space: str,
    music_danger: str,
    music_battle: str,
    ambient_color: str,
    bg_basic: str,
    bg_complex: str,
    bg_nebulae: str,
    light_color: str,
    local_faction: str,
) -> dict[str, object]:
    return {
        "name": str(name or "").strip(),
        "prefix": str(prefix or "").strip().upper(),
        "size": int(size),
        "space_color": str(space_color or "").strip(),
        "music_space": str(music_space or "").strip(),
        "music_danger": str(music_danger or "").strip(),
        "music_battle": str(music_battle or "").strip(),
        "ambient_color": str(ambient_color or "").strip(),
        "bg_basic": str(bg_basic or "").strip(),
        "bg_complex": str(bg_complex or "").strip(),
        "bg_nebulae": str(bg_nebulae or "").strip(),
        "light_color": str(light_color or "").strip(),
        "local_faction": str(local_faction or "").strip(),
    }


def build_system_settings_result(
    *,
    music_space: str,
    music_danger: str,
    music_battle: str,
    space_color: str,
    local_faction: str,
    ambient_color: str,
    dust: str,
    bg_basic: str,
    bg_complex: str,
    bg_nebulae: str,
) -> dict[str, str]:
    return {
        "music_space": str(music_space or "").strip(),
        "music_danger": str(music_danger or "").strip(),
        "music_battle": str(music_battle or "").strip(),
        "space_color": str(space_color or "").strip(),
        "local_faction": str(local_faction or "").strip(),
        "ambient_color": str(ambient_color or "").strip(),
        "dust": str(dust or "").strip(),
        "bg_basic": str(bg_basic or "").strip(),
        "bg_complex": str(bg_complex or "").strip(),
        "bg_nebulae": str(bg_nebulae or "").strip(),
    }
