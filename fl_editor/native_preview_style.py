from __future__ import annotations


def native_preview_color_key(
    *,
    model_name: str,
    level_name: str | None,
    part_name: str | None,
    group_start: int | None = None,
    group_count: int | None = None,
) -> str:
    return "|".join(
        (
            part_name or "",
            model_name or "",
            level_name or "",
            "" if group_start is None else str(group_start),
            "" if group_count is None else str(group_count),
        )
    )


def native_preview_rgb(
    *,
    model_name: str,
    level_name: str | None,
    part_name: str | None,
    group_start: int | None = None,
    group_count: int | None = None,
) -> tuple[int, int, int]:
    key = native_preview_color_key(
        model_name=model_name,
        level_name=level_name,
        part_name=part_name,
        group_start=group_start,
        group_count=group_count,
    )
    if not key:
        return (180, 190, 210)
    seed = 0
    for char in key:
        seed = ((seed * 131) + ord(char)) & 0xFFFFFFFF
    # Keep colors bright enough for dark and light preview backgrounds.
    red = 140 + ((seed >> 0) & 0x73)
    green = 140 + ((seed >> 8) & 0x73)
    blue = 140 + ((seed >> 16) & 0x73)
    return (red, green, blue)
