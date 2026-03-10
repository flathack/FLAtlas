from __future__ import annotations

from typing import Callable


def build_saved_system_sections(
    sections: list[tuple[str, list[tuple[str, str]]]],
    objects: list,
    zones: list,
    *,
    extract_nickname_from_entries: Callable[[list[tuple[str, str]]], str | None],
) -> list[tuple[str, list[tuple[str, str]]]]:
    obj_idx = 0
    zone_idx = 0
    saved_sections: list[tuple[str, list[tuple[str, str]]]] = []

    for sec_name, entries in sections:
        lower_name = str(sec_name or "").strip().lower()
        if lower_name == "object":
            if obj_idx < len(objects):
                saved_sections.append((sec_name, list(objects[obj_idx].data["_entries"])))
                obj_idx += 1
            else:
                saved_sections.append((sec_name, list(entries)))
            continue
        if lower_name == "zone":
            target_nickname = extract_nickname_from_entries(entries)
            matched = False
            for idx, zone in enumerate(zones[zone_idx:], start=zone_idx):
                if str(zone.nickname or "") == str(target_nickname or ""):
                    saved_sections.append((sec_name, list(zone.data["_entries"])))
                    zone_idx = idx + 1
                    matched = True
                    break
            if not matched:
                saved_sections.append((sec_name, list(entries)))
            continue
        saved_sections.append((sec_name, list(entries)))

    for obj in objects[obj_idx:]:
        saved_sections.append(("Object", list(obj.data["_entries"])))
    for zone in zones[zone_idx:]:
        saved_sections.append(("Zone", list(zone.data["_entries"])))
    return saved_sections
