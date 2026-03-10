from __future__ import annotations

from fl_editor.dialogs import (
    BaseCreationDialog,
    ConnectionDialog,
    DockingRingDialog,
    GateInfoDialog,
    PatrolZoneDialog,
    ZoneCreationDialog,
)


def test_base_creation_dialog_builds_default_room_state(qapp):
    dialog = BaseCreationDialog(
        None,
        system_nick="li01",
        archetypes=["space_police01"],
        loadouts=["police_loadout"],
        factions=["li_n_grp - Liberty Navy"],
        existing_bases=["li01_02_base"],
        next_base_num=1,
        pilots=["pilot_solar_easiest"],
        voices=["mc_leg_m01"],
        heads=["trent_head"],
        bodies=["trent_body"],
        template_room_details={},
        template_room_npcs={},
        template_virtual_targets={},
        ids_info_template_xml="<RDL><TEXT><PARA>Base Info</PARA></TEXT></RDL>",
    )

    assert dialog.room_table.rowCount() == 5
    assert dialog.room_npc_tabs.count() == 3
    assert dialog.start_room_cb.currentText() == "Deck"

    payload = dialog.payload()

    assert payload["base_nickname"] == "LI01_01_Base"
    assert payload["obj_nickname"] == "LI01_01"
    assert payload["rooms"] == ["Deck", "Bar", "Trader"]


def test_base_creation_dialog_applies_template_room_state(qapp):
    dialog = BaseCreationDialog(
        None,
        system_nick="li01",
        archetypes=["space_police01"],
        loadouts=["police_loadout"],
        factions=["li_n_grp - Liberty Navy"],
        existing_bases=[("Template Base", "li01_02_base")],
        next_base_num=1,
        pilots=["pilot_solar_easiest"],
        voices=["mc_leg_m01"],
        heads=["trent_head"],
        bodies=["trent_body"],
        template_room_details={
            "li01_02_base": [
                {"room": "Bar", "scene": "custom_bar.thn", "file": "bar.ini"},
                {"room": "Equipment", "scene": "custom_equipment.thn", "file": "equip.ini"},
            ]
        },
        template_room_npcs={
            "li01_02_base": {
                "bar": [{"nickname": "template_barman", "name_text": "Barman"}],
            }
        },
        template_virtual_targets={},
        ids_info_template_xml="<RDL><TEXT><PARA>Base Info</PARA></TEXT></RDL>",
    )

    dialog.template_cb.setCurrentIndex(1)

    assert dialog.room_npc_tabs.count() == 2
    assert dialog.start_room_cb.currentText() == "Bar"
    assert dialog.template_info_lbl.text().startswith("Template-R")

    bar_row = dialog._find_room_row("Bar")
    equipment_row = dialog._find_room_row("Equipment")
    deck_row = dialog._find_room_row("Deck")

    assert dialog.room_table.item(bar_row, 0).checkState().value == 2
    assert dialog.room_table.item(equipment_row, 0).checkState().value == 2
    assert dialog.room_table.item(deck_row, 0).checkState().value == 0

    payload = dialog.payload()

    assert payload["rooms"] == ["Bar", "Equipment"]
    assert payload["start_room"] == "Bar"
    assert payload["room_customizations"]["bar"]["scene"] == "custom_bar.thn"
    assert payload["room_customizations"]["equipment"]["scene"] == "custom_equipment.thn"


def test_docking_ring_dialog_builds_payload_for_new_base(qapp):
    dialog = DockingRingDialog(
        None,
        planet_nickname="li01_01",
        base_nickname="li01_01_base",
        loadouts=["docking_ring_li_01"],
        factions=["li_n_grp"],
        existing_bases=["li01_02_base"],
        pilots=["pilot_solar_easiest"],
        voices=["atc_leg_f01a"],
        needs_base=True,
    )

    payload = dialog.payload()

    assert payload["nickname"] == "Dock_Ring_li01_01"
    assert payload["base_nickname"] == "li01_01_base"
    assert payload["rooms"] == ["Deck", "Bar", "Trader"]
    assert payload["start_room"] == "Deck"


def test_docking_ring_dialog_refreshes_start_room_when_rooms_change(qapp):
    dialog = DockingRingDialog(
        None,
        planet_nickname="li01_01",
        base_nickname="li01_01_base",
        loadouts=["docking_ring_li_01"],
        factions=["li_n_grp"],
        existing_bases=["li01_02_base"],
        pilots=["pilot_solar_easiest"],
        voices=["atc_leg_f01a"],
        needs_base=True,
    )

    dialog.room_checks["Deck"].setChecked(False)
    dialog.room_checks["Bar"].setChecked(False)

    assert dialog.start_room_cb.currentText() == "Trader"
    assert [dialog.start_room_cb.itemText(i) for i in range(dialog.start_room_cb.count())] == ["Trader"]


def test_connection_dialog_builds_target_and_type_choices(qapp):
    dialog = ConnectionDialog(
        None,
        systems=[("li01", "universe\\li01.ini"), ("br01", "universe\\br01.ini")],
    )

    assert dialog.dest_cb.count() == 2
    assert dialog.dest_cb.currentText() == "li01"
    assert dialog.dest_cb.currentData() == "universe\\li01.ini"
    assert dialog.type_cb.count() == 3
    assert dialog.type_cb.currentText() == "Jump Hole"


def test_gate_info_dialog_builds_default_gate_settings(qapp):
    dialog = GateInfoDialog(
        None,
        loadouts=["jumpgate_li01", "jumpgate_br01"],
        factions=["li_n_grp", "br_n_grp"],
    )

    assert dialog.behavior_edit.text() == "NOTHING"
    assert dialog.difficulty_spin.value() == 1
    assert dialog.loadout_cb.currentText() == "jumpgate_li01"
    assert dialog.pilot_edit.text() == "pilot_solar_hardest"
    assert dialog.rep_cb.count() == 2


def test_zone_creation_dialog_switches_reference_list_by_type(qapp):
    dialog = ZoneCreationDialog(
        None,
        asteroids=["asteroid_a.ini", "asteroid_b.ini"],
        nebulas=["nebula_a.ini"],
    )

    assert dialog.ref_cb.count() == 2
    assert dialog.ref_cb.currentText() == "asteroid_a.ini"

    dialog.type_cb.setCurrentText("Nebula")

    assert dialog.ref_cb.count() == 1
    assert dialog.ref_cb.currentText() == "nebula_a.ini"


def test_patrol_zone_dialog_builds_payload_from_current_defaults(qapp):
    dialog = PatrolZoneDialog(
        None,
        encounters=["patrolp_assault"],
        factions=["li_n_grp"],
    )

    payload = dialog.payload()

    assert payload["usage"] == "patrol"
    assert payload["pop_type"] == "attack_patrol"
    assert payload["encounter"] == "patrolp_assault"
    assert payload["faction"] == "li_n_grp"
    assert payload["mission_eligible"] is True
    assert payload["encounter_pairs"][-1][1] == 10
