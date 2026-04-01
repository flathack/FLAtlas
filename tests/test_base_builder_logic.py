from fl_editor.base_builder_logic import (
    build_base_builder_part_entries,
    find_base_builder_parent_nickname,
    is_base_builder_child_entries,
    suggest_base_builder_part_nickname,
)


def test_build_base_builder_part_entries_adds_parent_and_reputation():
    entries = build_base_builder_part_entries(
        parent_nickname="Br04_02",
        part_nickname="Br04_02_part_001",
        archetype="smallstation1",
        pos_xyz=(1.0, 2.0, 3.0),
        rotate_xyz=(0.0, -90.0, 0.0),
        reputation="br_m_grp",
        loadout="space_station_loadout",
    )

    assert ("parent", "Br04_02") in entries
    assert ("visit", "0") in entries
    assert ("reputation", "br_m_grp") in entries
    assert ("loadout", "space_station_loadout") in entries
    assert ("pos", "1.00, 2.00, 3.00") in entries
    assert ("rotate", "0.00, -90.00, 0.00") in entries


def test_find_base_builder_parent_nickname_reads_parent_entry():
    entries = [("nickname", "foo"), ("parent", "Li01_01"), ("archetype", "outpost")]

    assert find_base_builder_parent_nickname(entries) == "Li01_01"
    assert is_base_builder_child_entries(entries)
    assert is_base_builder_child_entries(entries, "li01_01")
    assert not is_base_builder_child_entries(entries, "Br04_02")


def test_suggest_base_builder_part_nickname_uses_next_numeric_suffix():
    nickname = suggest_base_builder_part_nickname(
        "Br04_02",
        ["Br04_02_part_001", "br04_02_part_003", "SomethingElse"],
    )

    assert nickname == "Br04_02_part_004"
