from __future__ import annotations

from fl_editor.base_edit_logic import (
    assigned_nickname_set,
    available_nicknames,
    available_equip_groups,
    build_base_edit_property_state,
    build_base_edit_obj_properties,
    build_commodity_market_row,
    build_default_commodity_market_row,
    build_default_equip_market_row,
    build_equip_market_row,
    can_open_infocard,
    collect_ship_market_goods,
    collect_table_rows,
    normalize_solar_pilot_choices,
    object_entries_to_dict,
    preferred_equip_group_label,
    extract_assigned_nicknames,
    ship_slot_values,
    split_space_costume,
)


def test_split_space_costume_handles_empty_and_partial_values():
    assert split_space_costume("") == ("", "")
    assert split_space_costume("head_a") == ("head_a", "")
    assert split_space_costume("head_a, body_b") == ("head_a", "body_b")


def test_object_entries_to_dict_keeps_first_value_per_key_case_insensitively():
    obj_dict = object_entries_to_dict(
        [("Nickname", "a"), ("nickname", "b"), ("ids_info", "123")]
    )
    assert obj_dict == {"nickname": "a", "ids_info": "123"}


def test_normalize_solar_pilot_choices_filters_and_deduplicates():
    assert normalize_solar_pilot_choices(["pilot_solar_easy", "pilot_other", "pilot_solar_hard"]) == [
        "pilot_solar_easiest",
        "pilot_solar_easy",
        "pilot_solar_hard",
        "pilot_solar_hardest",
    ]


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


def test_build_base_edit_property_state_extracts_defaults_and_costume_parts():
    state = build_base_edit_property_state(
        obj_entries=[
            ("nickname", "li01_01_base"),
            ("space_costume", "head_a, body_b"),
            ("ids_name", "123"),
            ("ids_info", "456"),
            ("difficulty_level", "7"),
        ],
        pilots=["pilot_other", "pilot_solar_easy"],
    )

    assert state["obj_dict"]["nickname"] == "li01_01_base"
    assert state["head"] == "head_a"
    assert state["body"] == "body_b"
    assert state["ids_name"] == 123
    assert state["ids_info"] == 456
    assert state["difficulty_level"] == 7
    assert state["pilot_choices"] == [
        "pilot_solar_easiest",
        "pilot_solar_easy",
        "pilot_solar_hard",
        "pilot_solar_hardest",
    ]


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


def test_market_assignment_helpers_normalize_available_and_assigned_nicknames():
    rows = [["gun_a", "1"], [""], ["gun_b", "2"]]
    assert extract_assigned_nicknames(rows) == ["gun_a", "gun_b"]
    assigned = assigned_nickname_set(rows)
    assert assigned == {"gun_a", "gun_b"}
    assert available_nicknames(["gun_b", "gun_c", "gun_a", "gun_d"], assigned) == ["gun_c", "gun_d"]


def test_available_equip_groups_and_preferred_group_resolution():
    groups = {
        "Weapons": ["gun_a", "gun_b"],
        "Shields": ["shield_a"],
    }
    assert available_equip_groups(groups, {"gun_a"}) == [
        ("Weapons", ["gun_b"]),
        ("Shields", ["shield_a"]),
    ]
    assert preferred_equip_group_label("shield_a", groups) == "Shields"
    assert preferred_equip_group_label("unknown", groups) == "Weapons"


def test_equip_market_row_builders_fill_defaults():
    assert build_equip_market_row(["gun_a", "5"]) == ["gun_a", "5", "-1", "10", "10", "0", "1"]
    assert build_default_equip_market_row("gun_b") == ["gun_b", "0", "-1", "10", "10", "0", "1"]


def test_commodity_market_row_builders_include_price_cells():
    assert build_commodity_market_row(["food", "1", "-1", "5", "10", "0", "1.5"], {"food": 40}) == [
        "food", "1", "-1", "5", "10", "0", "1.5", "40", "60"
    ]
    assert build_default_commodity_market_row("water", {"water": 22}) == [
        "water", "0", "-1", "0", "0", "0", "1", "22", "22"
    ]


def test_collect_ship_market_goods_reuses_existing_and_builds_defaults():
    goods = collect_ship_market_goods(
        ["ship_a", "ship_b"],
        {"ship_a": ["ship_a", "1", "-1", "2", "3", "0", "1", "1"]},
    )

    assert goods == [
        ["ship_a", "1", "-1", "2", "3", "0", "1", "1"],
        ["ship_b", "1", "-1", "1", "1", "0", "1", "1"],
    ]


def test_ship_slot_values_fills_up_to_requested_slot_count():
    assert ship_slot_values(["ship_a", "ship_b"], ["ship_b"], slots=3) == ["ship_b", "", ""]


def test_can_open_infocard_requires_positive_integer():
    assert can_open_infocard(1) is True
    assert can_open_infocard("5") is True
    assert can_open_infocard(0) is False
    assert can_open_infocard("abc") is False
