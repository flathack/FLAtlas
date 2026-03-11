from __future__ import annotations


def native_preview_color_key(
    *,
    model_name: str,
    level_name: str | None,
    part_name: str | None,
) -> str:
    return "|".join(
        value or ""
        for value in (part_name, model_name, level_name)
    )


def native_preview_rgb(
    *,
    model_name: str,
    level_name: str | None,
    part_name: str | None,
) -> tuple[int, int, int]:
    key = native_preview_color_key(
        model_name=model_name,
        level_name=level_name,
        part_name=part_name,
    )
    if not key:
        return (180, 190, 210)
    seed = 0
    for char in key:
        seed = ((seed * 131) + ord(char)) & 0xFFFFFFFF
    # Keep colors bright enough for dark and light preview backgrounds.
    red = 96 + ((seed >> 0) & 0x5F)
    green = 96 + ((seed >> 8) & 0x5F)
    blue = 96 + ((seed >> 16) & 0x5F)
    return (red, green, blue)
