from __future__ import annotations

from fl_editor.universe_writes import (
    extract_nickname_from_entries,
    serialize_snapshot_sections,
    serialize_universe_sections_with_positions,
)


def test_extract_nickname_from_entries_returns_first_nickname():
    entries = [("ids_name", "1"), ("nickname", "li01"), ("pos", "0, 0")]

    assert extract_nickname_from_entries(entries) == "li01"


def test_serialize_universe_sections_with_positions_updates_and_inserts_pos():
    sections = [
        ("System", [("nickname", "li01"), ("pos", "1, 2")]),
        ("System", [("nickname", "li02"), ("ids_name", "2")]),
        ("Base", [("nickname", "li01_01_base")]),
    ]

    result = serialize_universe_sections_with_positions(
        sections,
        {"li01": (10.2, 20.7), "li02": (30.0, 40.0)},
    )

    assert "[System]\nnickname = li01\npos = 10, 21\n" in result
    assert "[System]\nnickname = li02\nids_name = 2\npos = 30, 40\n" in result
    assert "[Base]\nnickname = li01_01_base\n" in result


def test_serialize_snapshot_sections_replaces_and_appends_object_sections():
    sections = [
        ("Object", [("nickname", "old_obj")]),
        ("Base", [("nickname", "li01_01_base")]),
    ]
    objs = [
        {"_entries": [("nickname", "new_obj"), ("pos", "1, 2, 3")]},
        {"_entries": [("nickname", "extra_obj")]},
    ]

    result = serialize_snapshot_sections(sections, objs)

    assert "[Object]\nnickname = new_obj\npos = 1, 2, 3\n" in result
    assert "[Base]\nnickname = li01_01_base\n" in result
    assert result.endswith("[Object]\nnickname = extra_obj\n")
