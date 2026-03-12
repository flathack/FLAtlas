from __future__ import annotations

from fl_editor.base_deletion import (
    base_nickname_from_object_entries,
    remove_mbase_block_for_base,
    remove_base_from_universe_sections,
    room_files_from_base_sections,
)


def test_base_nickname_from_object_entries_prefers_base_then_dock_with():
    assert base_nickname_from_object_entries([("dock_with", "li01_01_base")]) == "li01_01_base"
    assert base_nickname_from_object_entries([("dock_with", "li01_01_base"), ("base", "li01_02_base")]) == "li01_02_base"
    assert base_nickname_from_object_entries([("nickname", "foo")]) == ""


def test_remove_base_from_universe_sections_filters_matching_base_block():
    sections = [
        ("System", [("nickname", "li01")]),
        ("Base", [("nickname", "li01_01_base"), ("file", "a.ini")]),
        ("Base", [("nickname", "li01_02_base"), ("file", "b.ini")]),
    ]

    new_sections, removed = remove_base_from_universe_sections(sections, "li01_01_base")

    assert removed is True
    assert new_sections == [
        ("System", [("nickname", "li01")]),
        ("Base", [("nickname", "li01_02_base"), ("file", "b.ini")]),
    ]


def test_room_files_from_base_sections_collects_room_file_entries():
    sections = [
        ("BaseInfo", [("nickname", "li01_01_base")]),
        ("Room", [("nickname", "Deck"), ("file", "Universe\\Systems\\li01\\Bases\\Rooms\\li01_01_base_deck.ini")]),
        ("Room", [("nickname", "Bar"), ("file", "Universe\\Systems\\li01\\Bases\\Rooms\\li01_01_base_bar.ini")]),
    ]

    assert room_files_from_base_sections(sections) == [
        "Universe\\Systems\\li01\\Bases\\Rooms\\li01_01_base_deck.ini",
        "Universe\\Systems\\li01\\Bases\\Rooms\\li01_01_base_bar.ini",
    ]


def test_remove_mbase_block_for_base_removes_block_and_stray_gf_npc_sections():
    sections = [
        ("MBase", [("nickname", "li01_01_base")]),
        ("MVendor", [("num_offers", "0")]),
        ("GF_NPC", [("nickname", "npc_a")]),
        ("GF_NPC", [("nickname", "npc_b")]),
        ("NewsItem", [("foo", "bar")]),
        ("MBase", [("nickname", "li01_02_base")]),
        ("GF_NPC", [("nickname", "npc_a")]),
        ("GF_NPC", [("nickname", "npc_c")]),
    ]

    new_sections, removed, block_count, stray_removed = remove_mbase_block_for_base(sections, "li01_01_base")

    assert removed is True
    assert block_count == 5
    assert stray_removed == 1
    assert new_sections == [
        ("MBase", [("nickname", "li01_02_base")]),
        ("GF_NPC", [("nickname", "npc_c")]),
    ]


def test_remove_mbase_block_for_base_returns_original_when_missing():
    sections = [("MBase", [("nickname", "li01_02_base")])]

    new_sections, removed, block_count, stray_removed = remove_mbase_block_for_base(sections, "li01_01_base")

    assert new_sections == sections
    assert removed is False
    assert block_count == 0
    assert stray_removed == 0
