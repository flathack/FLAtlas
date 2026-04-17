from __future__ import annotations

from fl_editor.simple_dialog_logic import (
    build_buoy_payload,
    build_category_object_payload,
    build_exclusion_zone_data,
    build_light_source_payload,
    build_object_creation_payload,
    build_patrol_zone_payload,
    build_solar_creation_payload,
    build_trade_lane_payload,
)


def test_build_patrol_zone_payload_normalizes_to_single_vanilla_style_encounter():
    payload = build_patrol_zone_payload(
        name=" path_a ",
        usage=" Patrol ",
        comment=" test ",
        sort=76,
        radius=750,
        damage=0,
        toughness=19,
        density=10,
        repop_time=90,
        max_battle_size=10,
        pop_type=" lane_patrol ",
        relief_time=30,
        path_label=" patrol ",
        path_index=1,
        encounter=" patrolp_assault ",
        faction=" li_n_grp ",
        levels_text="2, 5, nope, 19",
        default_chance=70,
        last_diff_enabled=True,
        last_chance=10,
        mission_eligible=True,
    )

    assert payload["name"] == "path_a"
    assert payload["usage"] == "patrol"
    assert payload["pop_type"] == "lane_patrol"
    assert payload["encounter_level"] == 19
    assert payload["encounter_chance"] == 0.7
    assert payload["encounter_pairs"] == [(19, 0.7)]
    assert payload["density_restrictions"] == [
        "1, patroller",
        "1, police_patroller",
        "1, pirate_patroller",
        "4, lawfuls",
        "4, unlawfuls",
    ]


def test_build_exclusion_zone_data_normalizes_shape():
    assert build_exclusion_zone_data(
        nickname=" zone_a ",
        shape=" sphere ",
        comment=" comment ",
        sort=99,
        link_to_field_zone=True,
        shell_enabled=True,
        shell_fog_far=8000,
        shell_path=" solar\\nebula\\generic_exclusion.3db ",
        shell_scalar=1.1,
        shell_max_alpha=0.5,
        shell_tint=" 40, 120, 120 ",
    ) == {
        "nickname": "zone_a",
        "shape": "SPHERE",
        "comment": "comment",
        "sort": 99,
        "link_to_field_zone": True,
        "shell_enabled": True,
        "shell_fog_far": 8000,
        "shell_path": "solar\\nebula\\generic_exclusion.3db",
        "shell_scalar": 1.1,
        "shell_max_alpha": 0.5,
        "shell_tint": "40, 120, 120",
    }


def test_build_solar_creation_payload_normalizes_strings():
    assert build_solar_creation_payload(
        nickname=" sol_a ",
        ids_name_text=" Sun A ",
        archetype=" med_star ",
        burn_color="1, 2, 3",
        radius=5000,
        damage=100,
        star=" med_white_sun ",
        atmosphere_range=6000,
        planet_ring=" ring.ini ",
    )["planet_ring"] == "ring.ini"


def test_build_light_source_payload_normalizes_type():
    assert build_light_source_payload(
        nickname="light_a",
        light_type=" directional ",
        color="255, 255, 255",
        range_value=100000,
        atten_curve=" DYNAMIC_DIRECTION ",
    )["type"] == "DIRECTIONAL"


def test_build_object_creation_payload_normalizes_fields():
    assert build_object_creation_payload(
        nickname=" obj_a ",
        ids_name_text=" Name ",
        archetype=" station ",
        loadout=" loadout_a ",
        faction=" li_n_grp ",
    ) == {
        "nickname": "obj_a",
        "ids_name_text": "Name",
        "archetype": "station",
        "loadout": "loadout_a",
        "faction": "li_n_grp",
    }


def test_build_category_object_payload_omits_empty_optional_fields():
    assert build_category_object_payload(
        archetype=" wreck ",
        ids_name_text=" Wreck ",
        loadout=" loadout_a ",
        faction="",
        rep="",
    ) == {
        "archetype": "wreck",
        "ids_name_text": "Wreck",
        "loadout": "loadout_a",
    }


def test_build_buoy_payload_handles_single_and_circle():
    assert build_buoy_payload(
        buoy_type="nav_buoy",
        pattern="single",
        count=8,
        spacing=3000,
    )["count"] == 1
    assert build_buoy_payload(
        buoy_type="nav_buoy",
        pattern="circle",
        count=8,
        spacing=3000,
    )["count"] == 8


def test_build_trade_lane_payload_defaults_zero_name_fields():
    assert build_trade_lane_payload(
        ring_count=5,
        spacing=7500,
        start_num=1,
        loadout=" trade_lane_ring_li_01 ",
        reputation=" li_n_grp ",
        difficulty_level=1,
        pilot=" pilot_solar_easiest ",
        ids_name="",
        space_name_start="",
        space_name_end="end_name",
    ) == {
        "ring_count": 5,
        "spacing": 7500,
        "start_num": 1,
        "loadout": "trade_lane_ring_li_01",
        "reputation": "li_n_grp",
        "difficulty_level": 1,
        "pilot": "pilot_solar_easiest",
        "ids_name": "0",
        "space_name_start": "0",
        "space_name_end": "end_name",
    }
