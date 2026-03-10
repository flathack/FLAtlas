from __future__ import annotations

from fl_editor.base_creation import build_base_object_entries, build_universe_base_entries, update_universe_base_entries


def test_build_base_object_entries_keeps_required_fields_and_optional_values():
    entries = build_base_object_entries(
        obj_nick="li01_01_base_obj",
        pos_str="1.00, 0.00, 2.00",
        ids_name_val="123",
        ids_info_val="456",
        archetype="space_police01",
        base_nick="li01_01_base",
        loadout="base_loadout",
        pilot="pilot_solar_easy",
        reputation="li_n_grp",
        voice="atc_leg_f01a",
        space_costume="head, body",
    )

    assert entries[:10] == [
        ("nickname", "li01_01_base_obj"),
        ("pos", "1.00, 0.00, 2.00"),
        ("rotate", "0, 0, 0"),
        ("ids_name", "123"),
        ("ids_info", "456"),
        ("Archetype", "space_police01"),
        ("dock_with", "li01_01_base"),
        ("base", "li01_01_base"),
        ("behavior", "NOTHING"),
        ("difficulty_level", "1"),
    ]
    assert ("loadout", "base_loadout") in entries
    assert ("pilot", "pilot_solar_easy") in entries
    assert ("reputation", "li_n_grp") in entries
    assert ("voice", "atc_leg_f01a") in entries
    assert ("space_costume", "head, body") in entries


def test_build_base_object_entries_omits_empty_optional_values():
    entries = build_base_object_entries(
        obj_nick="li01_01_base_obj",
        pos_str="1, 0, 2",
        ids_name_val="123",
        ids_info_val="456",
        archetype="space_police01",
        base_nick="li01_01_base",
    )

    keys = [key for key, _value in entries]
    assert "loadout" not in keys
    assert "pilot" not in keys
    assert "reputation" not in keys
    assert "voice" not in keys
    assert "space_costume" not in keys


def test_build_universe_base_entries_appends_bgcs_only_when_present():
    entries = build_universe_base_entries(
        base_nick="li01_01_base",
        system_nick="li01",
        strid_name_val="123",
        file_rel="Universe\\Systems\\li01\\Bases\\li01_01_base.ini",
        bgcs_base_run_by="li_p_grp",
    )
    assert entries == [
        ("nickname", "li01_01_base"),
        ("system", "li01"),
        ("strid_name", "123"),
        ("file", "Universe\\Systems\\li01\\Bases\\li01_01_base.ini"),
        ("BGCS_base_run_by", "li_p_grp"),
    ]

    entries_without_bgcs = build_universe_base_entries(
        base_nick="li01_01_base",
        system_nick="li01",
        strid_name_val="123",
        file_rel="Universe\\Systems\\li01\\Bases\\li01_01_base.ini",
    )
    assert entries_without_bgcs == [
        ("nickname", "li01_01_base"),
        ("system", "li01"),
        ("strid_name", "123"),
        ("file", "Universe\\Systems\\li01\\Bases\\li01_01_base.ini"),
    ]


def test_update_universe_base_entries_rewrites_known_fields_and_drops_empty_bgcs():
    entries = [
        ("nickname", "old_base"),
        ("system", "old_sys"),
        ("strid_name", "1"),
        ("file", "old.ini"),
        ("BGCS_base_run_by", "old_grp"),
        ("custom", "keep"),
    ]

    updated = update_universe_base_entries(
        entries,
        base_nick="li01_01_base",
        system_nick="li01",
        strid_name_val="123",
        file_rel="Universe\\Systems\\li01\\Bases\\li01_01_base.ini",
    )

    assert updated == [
        ("nickname", "li01_01_base"),
        ("system", "li01"),
        ("strid_name", "123"),
        ("file", "Universe\\Systems\\li01\\Bases\\li01_01_base.ini"),
        ("custom", "keep"),
    ]


def test_update_universe_base_entries_appends_missing_fields():
    updated = update_universe_base_entries(
        [],
        base_nick="li01_01_base",
        system_nick="li01",
        strid_name_val="123",
        file_rel="Universe\\Systems\\li01\\Bases\\li01_01_base.ini",
        bgcs_base_run_by="li_p_grp",
    )

    assert updated == [
        ("nickname", "li01_01_base"),
        ("system", "li01"),
        ("strid_name", "123"),
        ("file", "Universe\\Systems\\li01\\Bases\\li01_01_base.ini"),
        ("BGCS_base_run_by", "li_p_grp"),
    ]
