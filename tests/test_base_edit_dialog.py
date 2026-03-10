from __future__ import annotations

from fl_editor.dialogs import BaseEditDialog


def test_base_edit_dialog_builds_tabs_and_initial_state(qapp):
    dialog = BaseEditDialog(
        None,
        "li01_01_base",
        obj_entries=[
            ("nickname", "li01_01_base"),
            ("archetype", "space_police01"),
            ("loadout", "police_loadout"),
            ("pilot", "pilot_solar_hard"),
            ("ids_name", "1234"),
            ("ids_info", "5678"),
            ("space_costume", "trent_head, trent_body"),
        ],
        misc_goods=[["ge_s_scanner_01", "0", "-1", "10", "10", "0", "1"]],
        comm_goods=[["commodity_food", "0", "-1", "5", "10", "0", "1.5"]],
        ship_goods=[["ge_fighter", "1", "-1", "1", "1", "0", "1", "1"]],
        all_equip_groups={"Weapons": ["ge_s_scanner_01", "li_gun01_mark01"]},
        all_commodity_nicks=["commodity_food", "commodity_water"],
        commodity_prices={"commodity_food": 100},
        all_ship_nicks=["ge_fighter", "li_elite"],
        pilots=["pilot_solar_hard"],
        voices=["trent_voice"],
        heads=["trent_head"],
        bodies=["trent_body"],
        archetypes=["space_police01"],
        loadouts=["police_loadout"],
        factions=["li_p_grp"],
        current_name_text="Manhattan",
        current_infocard_xml="<RDL><TEXT>Test</TEXT></RDL>",
    )

    assert dialog.tabs.count() == 4
    assert dialog.prop_nick.text() == "li01_01_base"
    assert dialog.prop_ids_info.value() == 5678
    assert dialog.equip_table.rowCount() == 1
    assert dialog.comm_table.rowCount() == 1
    assert len(dialog.ship_combos) == 3
    assert dialog.ship_combos[0].currentText() == "ge_fighter"
