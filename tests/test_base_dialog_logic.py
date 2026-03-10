from __future__ import annotations

from fl_editor.base_dialog_logic import (
    build_base_creation_payload,
    build_space_costume,
    choose_start_room,
    default_role_for_room,
    default_scene_for_room,
    faction_display_from_any,
    faction_nick_from_display,
    make_copied_npc_rows,
    normalize_role_for_room,
    safe_nick_part,
    scene_options_for_room,
    split_npc_list,
    xml_to_plain_preview,
)


def test_split_npc_list_deduplicates_and_normalizes_separators():
    assert split_npc_list("npc_a; npc_b,\nnpc_a, npc_c") == ["npc_a", "npc_b", "npc_c"]


def test_xml_to_plain_preview_handles_empty_and_markup():
    assert xml_to_plain_preview("") == "[Keine ids_info-Templatequelle gefunden]"
    assert xml_to_plain_preview("<RDL><TEXT><PARA>Hello</PARA><PARA/>World</TEXT></RDL>") == "Hello\nWorld"


def test_room_scene_helpers_include_defaults():
    opts = scene_options_for_room(
        "bar",
        {"bar": ["custom_scene.thn"]},
        {"deck": "deck.thn", "bar": "bar.thn"},
    )
    assert opts == ["custom_scene.thn", "bar.thn"]
    assert default_scene_for_room("unknown", {"deck": "deck.thn"}) == "deck.thn"


def test_role_helpers_normalize_to_allowed_room_roles():
    assert default_role_for_room("bar") == "bartender"
    assert normalize_role_for_room("newsvendor", "bar", {"bar": ["bartender", "NewsVendor"]}) == "NewsVendor"
    assert normalize_role_for_room("", "shipdealer", {"shipdealer": ["ShipDealer"]}) == "ShipDealer"


def test_faction_helpers_parse_display_values():
    display_map = {"li_n_grp": "li_n_grp - Liberty Navy"}
    assert faction_nick_from_display("li_n_grp - Liberty Navy") == "li_n_grp"
    assert faction_display_from_any("li_n_grp", display_map) == "li_n_grp - Liberty Navy"


def test_make_copied_npc_rows_builds_unique_rows_with_normalized_values():
    used_nicks = {"li01_01_base_bar_npc_01"}
    rows = make_copied_npc_rows(
        "bar",
        [
            {
                "nickname": "template_npc_01",
                "name_text": "Bartender Jane",
                "reputation": "li_n_grp",
                "affiliation": "",
                "role": "",
            },
            {
                "nickname": "template_npc_02",
                "name_text": "",
                "reputation": "li_p_grp - Liberty Police",
                "affiliation": "li_p_grp",
                "role": "NewsVendor",
            },
        ],
        used_nicks,
        base_nickname="Li01_01_Base",
        base_reputation_display="li_n_grp - Liberty Navy",
        faction_display_by_nick={
            "li_n_grp": "li_n_grp - Liberty Navy",
            "li_p_grp": "li_p_grp - Liberty Police",
        },
    )

    assert [row["nickname"] for row in rows] == ["li01_01_base_bar_npc_02", "li01_01_base_bar_npc_03"]
    assert rows[0]["reputation"] == "li_n_grp"
    assert rows[0]["affiliation"] == "li_n_grp"
    assert rows[0]["role"] == "bartender"
    assert rows[1]["name_text"] == "template_npc_02"
    assert rows[1]["role"] == "NewsVendor"


def test_safe_nick_part_strips_invalid_characters():
    assert safe_nick_part(" Li01/01 Base ") == "li01_01_base"


def test_build_space_costume_joins_only_non_empty_parts():
    assert build_space_costume("head_a", "body_b") == "head_a, body_b"
    assert build_space_costume("head_a", "") == "head_a"
    assert build_space_costume("", "body_b") == "body_b"
    assert build_space_costume("", "") == ""


def test_choose_start_room_prefers_requested_then_deck_then_first():
    assert choose_start_room(["Bar", "Deck"], preferred="Bar", current="Deck") == "Bar"
    assert choose_start_room(["Bar", "Deck"], preferred="Trader", current="Trader") == "Deck"
    assert choose_start_room(["Bar", "Trader"], preferred="", current="Trader") == "Trader"
    assert choose_start_room(["Bar", "Trader"], preferred="", current="") == "Bar"
    assert choose_start_room([], preferred="Deck", current="Bar") == ""


def test_build_base_creation_payload_collects_rooms_customizations_and_costume():
    payload = build_base_creation_payload(
        base_nickname="li01_01_base",
        obj_nickname="li01_01_obj",
        ids_name_text="Planet Manhattan",
        ids_info_template_xml="<RDL/>",
        archetype="planet_manhattan",
        loadout="loadout_a",
        reputation="li_n_grp",
        pilot="pilot_solar_easy",
        voice="atc_leg_f01",
        head="head_a",
        body="body_b",
        room_states=[
            {
                "room_name": "Deck",
                "enabled": True,
                "scene": "deck.thn",
                "npc_rows": [{"nickname": "npc_deck_01"}, {"nickname": ""}],
            },
            {
                "room_name": "Bar",
                "enabled": False,
                "scene": "bar.thn",
                "npc_rows": [{"nickname": "npc_bar_01"}],
            },
        ],
        start_room="Deck",
        price_variance=15,
        template_base="li01_03_base",
        copy_template_npcs=True,
        bgcs_base_run_by="li_p_grp",
    )

    assert payload["space_costume"] == "head_a, body_b"
    assert payload["rooms"] == ["Deck"]
    assert payload["room_customizations"]["deck"]["npcs"] == ["npc_deck_01"]
    assert payload["room_customizations"]["bar"]["scene"] == "bar.thn"
    assert payload["start_room"] == "Deck"
    assert payload["copy_template_npcs"] is True
