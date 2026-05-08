from __future__ import annotations

from fl_editor.npc_mbase_ops import (
    npc_attach_to_mbase,
    npc_collect_for_base,
    npc_detach_from_mbase,
    npc_find_gf_section_index,
    npc_find_section_range,
    npc_insert_gf_for_base,
)


def _entry_get_value(entries: list[tuple[str, str]], key: str) -> str:
    for entry_key, value in entries:
        if str(entry_key).strip().lower() == str(key).strip().lower():
            return str(value)
    return ""


def test_npc_find_section_range_stops_at_next_mbase():
    sections = [("MBase", []), ("BaseFaction", []), ("MBase", []), ("GF_NPC", [])]

    assert npc_find_section_range(sections, 0) == (0, 2)


def test_npc_attach_to_mbase_creates_new_block_when_missing():
    sections: list[tuple[str, list[tuple[str, str]]]] = []

    result = npc_attach_to_mbase(
        sections,
        base_nickname="li01_01_base",
        faction_nickname="li_n_grp",
        npc_nickname="li01_01_npc_001",
        entry_get_value=_entry_get_value,
    )

    assert result[0][0] == "MBase"
    assert ("npc", "li01_01_npc_001") in result[2][1]


def test_npc_insert_gf_for_base_inserts_inside_matching_mbase_block():
    sections = [
        ("MBase", [("nickname", "li01_01_base")]),
        ("BaseFaction", [("faction", "li_n_grp"), ("weight", "10")]),
        ("MRoom", [("nickname", "Bar")]),
    ]

    result = npc_insert_gf_for_base(
        sections,
        base_nickname="li01_01_base",
        npc_entries=[("nickname", "li01_01_npc_001")],
        entry_get_value=_entry_get_value,
    )

    assert result[2][0] == "GF_NPC"


def test_npc_detach_from_mbase_removes_empty_basefaction():
    sections = [
        ("MBase", [("nickname", "li01_01_base")]),
        ("BaseFaction", [("faction", "li_n_grp"), ("weight", "10"), ("npc", "li01_01_npc_001")]),
    ]

    result = npc_detach_from_mbase(
        sections,
        base_nickname="li01_01_base",
        npc_nickname="li01_01_npc_001",
        entry_get_value=_entry_get_value,
    )

    assert len(result) == 1


def test_npc_find_gf_section_index_and_collect_for_base():
    sections = [
        ("MBase", [("nickname", "li01_01_base")]),
        ("BaseFaction", [("faction", "li_n_grp"), ("weight", "10"), ("npc", "li01_01_npc_001")]),
        ("GF_NPC", [("nickname", "li01_01_npc_001"), ("room", "bar")]),
    ]

    assert npc_find_gf_section_index(sections, npc_nickname="li01_01_npc_001", entry_get_value=_entry_get_value) == 2
    assert npc_collect_for_base(sections, base_nickname="li01_01_base", entry_get_value=_entry_get_value) == [
        {
            "nickname": "li01_01_npc_001",
            "faction": "li_n_grp",
            "entries": [("nickname", "li01_01_npc_001"), ("room", "bar")],
        }
    ]


def test_npc_collect_for_base_includes_fixture_only_local_gf_npc():
    sections = [
        ("MBase", [("nickname", "li01_01_base"), ("local_faction", "li_n_grp")]),
        ("MRoom", [("nickname", "Bar"), ("fixture", "li01_01_npc_001, Zs/NPC/Bartender/01/A/Stand, script.thn, bartender")]),
        ("GF_NPC", [("nickname", "li01_01_npc_001"), ("affiliation", "li_p_grp")]),
    ]

    assert npc_collect_for_base(sections, base_nickname="li01_01_base", entry_get_value=_entry_get_value) == [
        {
            "nickname": "li01_01_npc_001",
            "faction": "li_p_grp",
            "entries": [("nickname", "li01_01_npc_001"), ("affiliation", "li_p_grp")],
        }
    ]


def test_npc_collect_for_base_does_not_include_unrelated_global_gf_npc():
    sections = [
        ("MBase", [("nickname", "li01_01_base"), ("local_faction", "li_n_grp")]),
        ("GF_NPC", [("nickname", "li01_01_npc_001")]),
        ("MBase", [("nickname", "li01_02_base"), ("local_faction", "li_p_grp")]),
        ("GF_NPC", [("nickname", "li01_02_npc_001")]),
    ]

    rows = npc_collect_for_base(sections, base_nickname="li01_01_base", entry_get_value=_entry_get_value)

    assert [row["nickname"] for row in rows] == ["li01_01_npc_001"]
