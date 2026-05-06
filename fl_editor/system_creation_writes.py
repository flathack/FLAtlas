from __future__ import annotations

from .ini_section_writes import (
    serialize_sections_to_ini_text,
    serialize_sections_to_ini_text_preserving_layout,
)


def build_system_ini_text(
    *,
    space_color: str,
    local_faction: str,
    music_space: str,
    music_danger: str,
    music_battle: str,
    ambient_color: str,
    bg_basic: str,
    bg_complex: str,
    bg_nebulae: str,
    light_nick: str,
    light_color: str,
    size: int | str,
) -> str:
    lines = [
        "[SystemInfo]",
        f"space_color = {space_color}",
        f"local_faction = {local_faction}",
        "",
        "[TexturePanels]",
        "file = universe\\heavens\\shapes.ini",
        "",
        "[Music]",
        f"space = {music_space}",
        f"danger = {music_danger}",
        f"battle = {music_battle}",
        "",
        "[Dust]",
        "spacedust = Dust",
        "",
        "[Ambient]",
        f"color = {ambient_color}",
        "",
        "[Background]",
        f"basic_stars = {bg_basic}",
        f"complex_stars = {bg_complex}",
        f"nebulae = {bg_nebulae}",
        "",
        "[LightSource]",
        f"nickname = {light_nick}",
        "pos = 0, 0, 0",
        f"color = {light_color}",
        f"range = {size}",
        "type = DIRECTIONAL",
        "atten_curve = DYNAMIC_DIRECTION",
        "",
    ]
    return "\n".join(lines)


def append_universe_system_section(
    sections: list,
    *,
    nickname: str,
    rel_path: str,
    pos_x: float,
    pos_y: float,
    strid_name: str,
) -> list:
    updated = list(sections)
    updated.append(
        (
            "system",
            [
                ("nickname", nickname),
                ("file", rel_path),
                ("pos", f"{pos_x:.0f}, {pos_y:.0f}"),
                ("visit", "0"),
                ("strid_name", str(strid_name)),
                ("ids_info", "66106"),
                ("NavMapScale", "1.360000"),
                ("msg_id_prefix", f"gcs_refer_system_{nickname}"),
            ],
        )
    )
    return updated


def serialize_universe_with_new_system(
    sections: list,
    *,
    nickname: str,
    rel_path: str,
    pos_x: float,
    pos_y: float,
    strid_name: str,
    original_text: str | None = None,
) -> str:
    updated = append_universe_system_section(
        sections,
        nickname=nickname,
        rel_path=rel_path,
        pos_x=pos_x,
        pos_y=pos_y,
        strid_name=strid_name,
    )
    if original_text is not None:
        return serialize_sections_to_ini_text_preserving_layout(updated, original_text)
    return serialize_sections_to_ini_text(updated)
