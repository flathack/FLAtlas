from __future__ import annotations

from fl_editor.npc_editor_logic import (
    npc_apply_mission_and_rumors,
    npc_collect_multi,
    npc_multiline_values,
    npc_parse_rumor_id,
    npc_rumor_line_label,
    npc_split_csv,
)


def test_npc_multiline_values_filters_comments_and_blanks():
    assert npc_multiline_values("\nfoo\n# ignore\n ;ignore\nbar \n") == ["foo", "bar"]


def test_npc_collect_multi_reads_matching_entries():
    entries = [("misn", "a"), ("room", "bar"), ("misn", "b"), ("rumor", "c")]

    assert npc_collect_multi(entries, "misn") == ["a", "b"]


def test_npc_apply_mission_and_rumors_inserts_after_room():
    entries = [("nickname", "npc_a"), ("room", "bar"), ("voice", "trent")]

    result = npc_apply_mission_and_rumors(entries, ["m1"], ["r1"], ["r2"])

    assert result == [
        ("nickname", "npc_a"),
        ("room", "bar"),
        ("misn", "m1"),
        ("rumor", "r1"),
        ("rumor_type2", "r2"),
        ("voice", "trent"),
    ]


def test_npc_split_csv_and_parse_rumor_id_normalize_values():
    assert npc_split_csv(" base_0_rank , mission_end , 1 ", 4) == ["base_0_rank", "mission_end", "1", ""]
    assert npc_parse_rumor_id("131130 - text") == "131130"
    assert npc_parse_rumor_id("custom_id") == "custom_id"


def test_npc_rumor_line_label_adds_preview_and_truncates():
    label = npc_rumor_line_label(
        "base_0_rank, mission_end, 1, 131130",
        lambda rumor_id: "x" * 80 if rumor_id == "131130" else "",
    )

    assert label.startswith("base_0_rank, mission_end, 1, 131130 | ")
    assert label.endswith("...")
