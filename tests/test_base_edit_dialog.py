from __future__ import annotations

from fl_editor.dialogs import BaseEditDialog


def _build_dialog():
    return BaseEditDialog(
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


def test_base_edit_dialog_builds_tabs_and_initial_state(qapp):
    dialog = _build_dialog()

    assert dialog.tabs.count() == 4
    assert dialog.prop_nick.text() == "li01_01_base"
    assert dialog.prop_ids_info.value() == 5678
    assert dialog.equip_table.rowCount() == 1
    assert dialog.comm_table.rowCount() == 1
    assert len(dialog.ship_combos) == 3
    assert dialog.ship_combos[0].currentText() == "ge_fighter"


def test_base_edit_dialog_getters_reflect_user_changes(qapp):
    dialog = _build_dialog()

    dialog.prop_nick.setText("li01_99_base")
    dialog.prop_loadout.setCurrentText("custom_loadout")
    dialog.prop_ids_name.setValue(777)
    dialog.prop_ids_info.setValue(888)
    dialog.prop_name_text.setText("New Manhattan")
    dialog.prop_infocard_xml.setPlainText("<RDL><TEXT><PARA>Changed</PARA></TEXT></RDL>")
    dialog.equip_table.item(0, 0).setText("li_gun01_mark01")
    dialog.comm_table.item(0, 6).setText("2.0")
    dialog.ship_combos[0].setCurrentText("li_elite")
    dialog.ship_combos[1].setCurrentText("")

    obj = dialog.get_obj_properties()

    assert obj["nickname"] == "li01_99_base"
    assert obj["loadout"] == "custom_loadout"
    assert obj["ids_name"] == "777"
    assert obj["ids_info"] == "888"
    assert dialog.get_name_text() == "New Manhattan"
    assert dialog.get_infocard_xml() == "<RDL><TEXT><PARA>Changed</PARA></TEXT></RDL>"
    assert dialog.get_equip_nicknames() == ["li_gun01_mark01"]
    assert dialog.get_commodity_nicknames() == ["commodity_food"]
    assert dialog.get_ship_nicknames() == ["li_elite"]
    assert dialog.get_ship_market_goods() == [["li_elite", "1", "-1", "1", "1", "0", "1", "1"]]


def test_base_edit_dialog_delete_button_marks_delete_requested(qapp):
    dialog = _build_dialog()

    assert dialog.delete_requested is False

    dialog._on_delete_clicked()

    assert dialog.delete_requested is True
