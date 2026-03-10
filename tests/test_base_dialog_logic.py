from __future__ import annotations

from fl_editor.base_dialog_logic import (
    build_template_apply_state,
    build_base_creation_payload,
    build_room_lock_state,
    build_default_room_reset_state,
    build_room_npc_display_rows,
    build_room_npc_tab_state,
    build_start_room_state,
    build_template_selection_context,
    collect_active_room_names,
    collect_room_npc_rows,
    collect_room_states,
    build_space_costume,
    build_template_room_plan,
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


def test_collect_active_room_names_keeps_enabled_non_empty_rooms():
    assert collect_active_room_names(
        row_count=4,
        room_name_at=lambda row: ["Deck", "", "Bar", "Trader"][row],
        enabled_at=lambda row: [True, True, False, True][row],
    ) == ["Deck", "Trader"]


def test_collect_room_states_builds_state_dicts_for_named_rows():
    assert collect_room_states(
        row_count=3,
        room_name_at=lambda row: ["Deck", "", "Bar"][row],
        enabled_at=lambda row: [True, False, False][row],
        scene_at=lambda row: ["deck.thn", "", "bar.thn"][row],
        npc_rows_at=lambda room_name: [{"nickname": f"{room_name.lower()}_npc"}],
    ) == [
        {
            "room_name": "Deck",
            "enabled": True,
            "scene": "deck.thn",
            "npc_rows": [{"nickname": "deck_npc"}],
        },
        {
            "room_name": "Bar",
            "enabled": False,
            "scene": "bar.thn",
            "npc_rows": [{"nickname": "bar_npc"}],
        },
    ]


def test_collect_room_npc_rows_deduplicates_and_normalizes_values():
    rows = collect_room_npc_rows(
        row_count=4,
        nickname_at=lambda row: ["npc_a", "", "NPC_A", "npc_b"][row],
        name_text_at=lambda row: ["Alice", "", "Ignored", ""][row],
        reputation_at=lambda row: ["li_n_grp - Liberty Navy", "", "x", "li_p_grp"][row],
        affiliation_at=lambda row: ["", "", "", "li_p_grp - Liberty Police"][row],
        role_at=lambda row: ["bartender", "", "trader", ""][row],
        room_name="bar",
        normalize_role=lambda role, room: "bartender" if room == "bar" and not role else role,
        faction_nick_from_display_fn=lambda raw: raw.split(" - ", 1)[0].strip(),
        default_role=lambda room: "bartender" if room == "bar" else "trader",
    )

    assert rows == [
        {
            "nickname": "npc_a",
            "name_text": "Alice",
            "reputation": "li_n_grp",
            "affiliation": "li_n_grp",
            "role": "bartender",
        },
        {
            "nickname": "npc_b",
            "name_text": "npc_b",
            "reputation": "li_p_grp",
            "affiliation": "li_p_grp",
            "role": "bartender",
        },
    ]


def test_build_room_npc_display_rows_deduplicates_and_builds_display_values():
    rows = build_room_npc_display_rows(
        rows=[
            {"nickname": "npc_a", "name_text": "", "reputation": "li_n_grp", "affiliation": "", "role": ""},
            {"nickname": "NPC_A", "name_text": "Ignored", "reputation": "x", "affiliation": "x", "role": "x"},
            {"nickname": "npc_b", "name_text": "Bob", "reputation": "", "affiliation": "li_p_grp", "role": "NewsVendor"},
        ],
        faction_display_from_any_fn=lambda raw: {
            "li_n_grp": "li_n_grp - Liberty Navy",
            "li_p_grp": "li_p_grp - Liberty Police",
        }.get(str(raw), ""),
        default_reputation_display="li_n_grp - Liberty Navy",
        normalize_role=lambda role, room: "bartender" if not role and room == "bar" else role,
        default_role=lambda room: "bartender" if room == "bar" else "trader",
        room_name="bar",
    )

    assert rows == [
        {
            "nickname": "npc_a",
            "name_text": "npc_a",
            "reputation_display": "li_n_grp - Liberty Navy",
            "affiliation_display": "li_n_grp - Liberty Navy",
            "role_display": "bartender",
        },
        {
            "nickname": "npc_b",
            "name_text": "Bob",
            "reputation_display": "li_n_grp - Liberty Navy",
            "affiliation_display": "li_p_grp - Liberty Police",
            "role_display": "NewsVendor",
        },
    ]


def test_build_room_npc_tab_state_keeps_only_active_rooms_and_selected_match():
    state = build_room_npc_tab_state(
        active_rooms=["Deck", "", "Bar"],
        current_room="bar",
    )

    assert state == {
        "active_rooms": ["Deck", "Bar"],
        "selected_room": "Bar",
    }


def test_build_start_room_state_keeps_active_rooms_and_prefers_match():
    state = build_start_room_state(
        active_rooms=["", "Bar", "Deck"],
        preferred="Bar",
        current="Deck",
    )

    assert state == {
        "active_rooms": ["Bar", "Deck"],
        "target_room": "Bar",
    }


def test_build_default_room_reset_state_builds_default_rows_and_info_text():
    state = build_default_room_reset_state(
        room_choices=[("Deck", True), ("Bar", False), ("", True)],
        default_scene_for_room_fn=lambda room: f"{room.lower()}.thn",
    )

    assert state == {
        "rows": [
            {"room_name": "Deck", "enabled": True, "scene": "deck.thn", "npc_rows": []},
            {"room_name": "Bar", "enabled": False, "scene": "bar.thn", "npc_rows": []},
        ],
        "info_text": "Template-Raeume werden nach Auswahl automatisch vorausgewaehlt.",
    }


def test_build_room_lock_state_builds_widget_state_for_locked_room():
    state = build_room_lock_state(
        room_name="Cityscape",
        locked=True,
        reason="Gesperrt",
    )

    assert state == {
        "room_name": "Cityscape",
        "locked": True,
        "force_unchecked": True,
        "check_enabled": False,
        "room_tooltip": "Gesperrt",
        "scene_enabled": False,
        "scene_tooltip": "Gesperrt",
        "npc_enabled": False,
        "npc_reason": "Gesperrt",
    }


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


def test_build_template_selection_context_normalizes_key_and_collects_lookup_values():
    context = build_template_selection_context(
        template_value=" Li01_03_Base ",
        template_room_details={"li01_03_base": [{"room": "Deck"}]},
        template_room_npcs={"li01_03_base": {"deck": [{"nickname": "npc_a"}]}},
        template_virtual_targets={"li01_03_base": ["cityscape"]},
    )

    assert context == {
        "base_key": "li01_03_base",
        "details": [{"room": "Deck"}],
        "room_npcs": {"deck": [{"nickname": "npc_a"}]},
        "virtual_targets": {"cityscape"},
    }


def test_build_template_selection_context_handles_empty_value():
    assert build_template_selection_context(
        template_value="",
        template_room_details={"x": [{"room": "Deck"}]},
        template_room_npcs={"x": {"deck": [{"nickname": "npc_a"}]}},
        template_virtual_targets={"x": ["cityscape"]},
    ) == {
        "base_key": "",
        "details": [],
        "room_npcs": {},
        "virtual_targets": set(),
    }


def test_build_template_room_plan_collects_applications_locks_and_info_text():
    plan = build_template_room_plan(
        details=[
            {"room": "Deck", "scene": "deck.thn", "file": "deck.ini"},
            {"room": "Bar", "scene": "bar.thn", "file": ""},
        ],
        room_npcs={
            "deck": [{"nickname": "template_npc_01", "name_text": "Deck NPC"}],
            "bar": [{"nickname": "template_npc_02", "name_text": "Bar NPC", "role": "NewsVendor"}],
        },
        virtual_targets={"deck", "cityscape", "shipdealer"},
        copy_template_npcs=True,
        base_nickname="Li01_01_Base",
        base_reputation_display="li_n_grp - Liberty Navy",
        faction_display_by_nick={"li_n_grp": "li_n_grp - Liberty Navy"},
    )

    assert plan["has_details"] is True
    assert plan["preferred_start"] == "Deck"
    assert [entry["room_name"] for entry in plan["applications"]] == ["Deck", "Bar"]
    assert plan["applications"][0]["npc_rows"][0]["nickname"] == "li01_01_base_deck_npc_01"
    assert plan["locked_rooms"] == {"cityscape", "shipdealer"}
    assert "Template-Räume:" in plan["info_text"]
    assert "Deck: deck.thn  (deck.ini)" in plan["info_text"]
    assert "Virtual Rooms erkannt (gesperrt): cityscape, shipdealer" in plan["info_text"]


def test_build_template_room_plan_without_details_reports_empty_template():
    plan = build_template_room_plan(
        details=[],
        room_npcs={},
        virtual_targets={"deck"},
        copy_template_npcs=False,
        base_nickname="li01_01_base",
        base_reputation_display="li_n_grp",
    )

    assert plan["has_details"] is False
    assert plan["applications"] == []
    assert plan["locked_rooms"] == {"deck"}
    assert plan["info_text"] == "Template-Räume:\n\nVirtual Rooms erkannt (gesperrt): deck"


def test_build_template_apply_state_normalizes_applications_and_locks():
    state = build_template_apply_state(
        plan={
            "has_details": True,
            "applications": [
                {"room_name": "Deck", "scene": "deck.thn", "npc_rows": [{"nickname": "npc_a"}]},
                {"room_name": "", "scene": "skip.thn", "npc_rows": []},
            ],
            "locked_rooms": {"cityscape"},
            "info_text": "Template-Räume:\nDeck",
            "preferred_start": "",
        },
        room_choices=[("Deck", True), ("Cityscape", False)],
    )

    assert state == {
        "has_details": True,
        "applications": [{"room_name": "Deck", "scene": "deck.thn", "npc_rows": [{"nickname": "npc_a"}]}],
        "room_locks": [
            {"room_name": "Deck", "locked": False, "reason": "Gesperrt: wird im Template als Virtual Room verwendet."},
            {"room_name": "Cityscape", "locked": True, "reason": "Gesperrt: wird im Template als Virtual Room verwendet."},
        ],
        "info_text": "Template-Räume:\nDeck",
        "preferred_start": "Deck",
    }
