from __future__ import annotations

from fl_editor.base_edit_logic import (
    build_base_edit_obj_properties,
    collect_ship_market_goods,
    collect_table_rows,
    split_space_costume,
)


def test_split_space_costume_handles_empty_and_partial_values():
    assert split_space_costume("") == ("", "")
    assert split_space_costume("head_a") == ("head_a", "")
    assert split_space_costume("head_a, body_b") == ("head_a", "body_b")


def test_build_base_edit_obj_properties_normalizes_output():
    payload = build_base_edit_obj_properties(
        nickname="li01_01_base",
        archetype="planet_manhattan",
        loadout="loadout_a",
        reputation="li_n_grp",
        pilot="pilot_solar_easy",
        voice="atc_leg_f01",
        head="head_a",
        body="body_b",
        ids_name=123,
        ids_info=456,
        behavior="NOTHING",
        difficulty_level=2,
    )

    assert payload == {
        "nickname": "li01_01_base",
        "archetype": "planet_manhattan",
        "loadout": "loadout_a",
        "reputation": "li_n_grp",
        "pilot": "pilot_solar_easy",
        "voice": "atc_leg_f01",
        "space_costume": "head_a, body_b",
        "ids_name": "123",
        "ids_info": "456",
        "behavior": "NOTHING",
        "difficulty_level": "2",
    }


def test_collect_table_rows_filters_empty_nicknames_and_honors_max_cols():
    rows = collect_table_rows(
        [
            ["nick_a", "1", "2", "3"],
            ["", "x", "y", "z"],
            ["nick_b", "4", "5", "6"],
        ],
        max_cols=3,
    )

    assert rows == [["nick_a", "1", "2"], ["nick_b", "4", "5"]]


def test_collect_ship_market_goods_reuses_existing_and_builds_defaults():
    goods = collect_ship_market_goods(
        ["ship_a", "ship_b"],
        {"ship_a": ["ship_a", "1", "-1", "2", "3", "0", "1", "1"]},
    )

    assert goods == [
        ["ship_a", "1", "-1", "2", "3", "0", "1", "1"],
        ["ship_b", "1", "-1", "1", "1", "0", "1", "1"],
    ]
