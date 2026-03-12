from __future__ import annotations

from dataclasses import dataclass

from fl_editor.system_editor_persistence import build_saved_system_sections


@dataclass
class _FakeEntity:
    nickname: str
    data: dict


def _extract_nickname(entries: list[tuple[str, str]]) -> str | None:
    for key, value in entries:
        if key.lower() == "nickname":
            return value
    return None


def test_build_saved_system_sections_replaces_existing_object_and_zone_entries():
    sections = [
        ("Object", [("nickname", "old_obj"), ("pos", "0, 0, 0")]),
        ("Zone", [("nickname", "zone_a"), ("shape", "SPHERE")]),
        ("Light", [("nickname", "light01")]),
    ]
    objects = [_FakeEntity("new_obj", {"_entries": [("nickname", "new_obj"), ("pos", "1, 2, 3")]})]
    zones = [_FakeEntity("zone_a", {"_entries": [("nickname", "zone_a"), ("shape", "BOX")]})]

    result = build_saved_system_sections(
        sections,
        objects,
        zones,
        extract_nickname_from_entries=_extract_nickname,
    )

    assert result == [
        ("Object", [("nickname", "new_obj"), ("pos", "1, 2, 3")]),
        ("Zone", [("nickname", "zone_a"), ("shape", "BOX")]),
        ("Light", [("nickname", "light01")]),
    ]


def test_build_saved_system_sections_appends_new_objects_and_zones():
    sections = []
    objects = [_FakeEntity("obj_a", {"_entries": [("nickname", "obj_a")]})]
    zones = [_FakeEntity("zone_a", {"_entries": [("nickname", "zone_a")]})]

    result = build_saved_system_sections(
        sections,
        objects,
        zones,
        extract_nickname_from_entries=_extract_nickname,
    )

    assert result == [
        ("Object", [("nickname", "obj_a")]),
        ("Zone", [("nickname", "zone_a")]),
    ]
