from __future__ import annotations

from fl_editor.rumor_editor_logic import (
    build_rumor_line,
    collect_rumor_scope_rows,
    rumor_form_data,
    rumor_row_label,
    rumor_split_csv,
)


def test_rumor_split_csv_pads_and_trims_values():
    assert rumor_split_csv(" base_0_rank , mission_end , 2 ") == ["base_0_rank", "mission_end", "2", ""]


def test_rumor_row_label_resolves_preview_and_truncates():
    row = {"kind": "rumor_type2", "line": "base_0_rank, mission_end, 1, 131130", "npc": "trent"}

    label = rumor_row_label(row, lambda rid: "x" * 90 if rid == "131130" else "")

    assert label.startswith("[R2] trent: base_0_rank, mission_end, 1, 131130 | ")
    assert label.endswith("...")


def test_collect_rumor_scope_rows_filters_and_collects_states():
    sections = [
        ("GF_NPC", [("nickname", "npc_a"), ("rumor", "base_0_rank, mission_end, 1, 131130")]),
        ("GF_NPC", [("nickname", "npc_b"), ("rumor_type2", "mission_end, mission_end, 3, 131131")]),
        ("GF_NPC", [("nickname", "npc_c"), ("rumor", "base_0_rank, mission_end, 1, 131132")]),
    ]
    npc_to_base = {"npc_a": "li01_01_base", "npc_b": "li01_01_base", "npc_c": "br01_01_base"}
    base_by_nick = {
        "li01_01_base": {
            "display": "Manhattan",
            "system": "LI01",
            "system_label": "LI01 - New York",
        },
        "br01_01_base": {
            "display": "New London",
            "system": "BR01",
            "system_label": "BR01 - New London",
        },
    }

    rows, states = collect_rumor_scope_rows(sections, npc_to_base, base_by_nick, "LI01", "")

    assert [row["npc"] for row in rows] == ["npc_a", "npc_b"]
    assert "base_0_rank" in states
    assert "mission_end" in states


def test_build_rumor_line_and_form_data_roundtrip():
    line = build_rumor_line(state_from=" base_0_rank ", state_to=" mission_end ", weight=4, rumor_id=" 131130 ")

    assert line == "base_0_rank, mission_end, 4, 131130"
    assert rumor_form_data("rumor_type2", line) == {
        "type_index": 1,
        "state_from": "base_0_rank",
        "state_to": "mission_end",
        "weight": 4,
        "rumor_id": "131130",
    }
