from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QTreeWidgetItem, QWidget

from fl_editor.dialogs import (
    BaseCreationDialog,
    BuoyDialog,
    CategoryObjectDialog,
    ConnectionDialog,
    DockingRingDialog,
    ExclusionZoneDialog,
    GateInfoDialog,
    LightSourceDialog,
    ObjectRingDialog,
    ObjectCreationDialog,
    PatrolZoneDialog,
    SimpleZoneDialog,
    SolarCreationDialog,
    SystemCreationDialog,
    SystemSettingsDialog,
    TradeLaneDialog,
    ZonePopulationDialog,
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


def test_base_creation_dialog_loads_template_data_lazily(qapp):
    calls: list[str] = []

    def provider(template_nick: str) -> dict[str, object]:
        calls.append(template_nick)
        return {
            "details": [
                {"room": "Equipment", "scene": "lazy_equipment.thn", "file": "equip.ini"},
            ],
            "room_npcs": {
                "equipment": [
                    {"nickname": "lazy_vendor", "name_text": "Vendor"},
                ]
            },
            "virtual_targets": ["shipdealer"],
        }

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
        template_data_provider=provider,
        ids_info_template_xml="<RDL><TEXT><PARA>Base Info</PARA></TEXT></RDL>",
    )

    assert calls == []

    dialog.template_cb.setCurrentIndex(1)

    assert calls == ["li01_02_base"]
    equipment_row = dialog._find_room_row("Equipment")
    assert dialog.room_table.item(equipment_row, 0).checkState().value == 2
    assert dialog.room_npc_tabs.count() == 1

    payload = dialog.payload()

    assert payload["rooms"] == ["Equipment"]
    assert payload["room_customizations"]["equipment"]["scene"] == "lazy_equipment.thn"


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


def test_zone_population_dialog_detects_field_profile_and_prioritizes_field_pop_types(qapp):
    dialog = ZonePopulationDialog(
        None,
        zone_nickname="li01_asteroid_field",
        entries=[
            ("nickname", "li01_asteroid_field"),
            ("type", "asteroids"),
            ("pop_type", "field"),
        ],
        encounter_params=["area_assault"],
        all_encounters=["area_assault", "tradep_trade"],
        factions=["li_n_grp"],
    )

    assert dialog._zone_profile == "field"
    assert dialog.pop_type_combo.itemText(0) == "field"
    assert "lootable_field" in [dialog.pop_type_combo.itemText(i) for i in range(dialog.pop_type_combo.count())]
    assert dialog.toughness_spin.value() == 10
    assert dialog.density_spin.value() == 5
    assert dialog.repop_spin.value() == 25
    assert dialog.battle_spin.value() == 4
    assert dialog.relief_spin.value() == 25
    assert dialog.enc_tree.topLevelItemCount() == 1
    assert dialog.enc_tree.topLevelItem(0).text(0) == "area_assault"
    assert dialog.enc_tree.topLevelItem(0).text(1) == "10"
    assert dialog.enc_tree.topLevelItem(0).text(2) == "0.100000"
    assert dialog.enc_tree.topLevelItem(0).child(0).text(0) == "li_n_grp"
    assert dialog.enc_tree.topLevelItem(0).child(0).text(1) == "1.000000"


def test_zone_population_dialog_exposes_tooltips_for_population_fields(qapp):
    dialog = ZonePopulationDialog(
        None,
        zone_nickname="li01_trade_lane_zone",
        entries=[
            ("nickname", "li01_trade_lane_zone"),
            ("usage", "trade"),
        ],
        encounter_params=["tradep_trade"],
        all_encounters=["tradep_trade"],
        factions=["li_n_grp"],
    )

    assert "Vanilla liegt meist im Bereich 1 bis 19" in dialog.toughness_spin.toolTip()
    assert "field/lootable_field" in dialog.pop_type_combo.toolTip()
    assert "Format: <Zahl>, <Encounter>" in dialog.dr_list.toolTip()
    assert "Top-Level = Encounter" in dialog.enc_tree.toolTip()


def test_zone_population_dialog_accept_blocks_total_encounter_chance_above_one(qapp, monkeypatch):
    dialog = ZonePopulationDialog(
        None,
        zone_nickname="li01_trade_lane_zone",
        entries=[
            ("nickname", "li01_trade_lane_zone"),
            ("usage", "trade"),
        ],
        encounter_params=["tradep_trade", "area_trade_transport"],
        all_encounters=["tradep_trade", "area_trade_transport"],
        factions=["li_n_grp"],
    )
    dialog.enc_tree.clear()
    first = QTreeWidgetItem(["tradep_trade", "12", "0.700000"])
    first.addChild(QTreeWidgetItem(["li_n_grp", "1.000000", ""]))
    second = QTreeWidgetItem(["area_trade_transport", "12", "0.500000"])
    second.addChild(QTreeWidgetItem(["li_n_grp", "1.000000", ""]))
    dialog.enc_tree.addTopLevelItem(first)
    dialog.enc_tree.addTopLevelItem(second)

    warning_calls: list[str] = []

    monkeypatch.setattr(
        "fl_editor.dialogs.QMessageBox.warning",
        lambda _parent, _title, text: warning_calls.append(text),
    )
    monkeypatch.setattr(
        "fl_editor.dialogs.QMessageBox.question",
        lambda *_args, **_kwargs: QMessageBox.Yes,
    )

    dialog.accept()

    assert warning_calls
    assert "Summe aller Encounter-Chancen" in warning_calls[0]
    assert dialog.result() == 0


def test_zone_population_dialog_accept_blocks_total_faction_weight_above_one(qapp, monkeypatch):
    dialog = ZonePopulationDialog(
        None,
        zone_nickname="li01_trade_lane_zone",
        entries=[
            ("nickname", "li01_trade_lane_zone"),
            ("usage", "trade"),
        ],
        encounter_params=["area_trade_transport"],
        all_encounters=["area_trade_transport"],
        factions=["co_kt_grp", "co_ni_grp", "co_shi_grp", "co_ss_grp"],
    )
    dialog.enc_tree.clear()
    encounter = QTreeWidgetItem(["area_trade_transport", "3", "0.180000"])
    encounter.addChild(QTreeWidgetItem(["co_kt_grp", "0.27", ""]))
    encounter.addChild(QTreeWidgetItem(["co_ni_grp", "0.27", ""]))
    encounter.addChild(QTreeWidgetItem(["co_shi_grp", "0.27", ""]))
    encounter.addChild(QTreeWidgetItem(["co_ss_grp", "0.30", ""]))
    dialog.enc_tree.addTopLevelItem(encounter)

    warning_calls: list[str] = []

    monkeypatch.setattr(
        "fl_editor.dialogs.QMessageBox.warning",
        lambda _parent, _title, text: warning_calls.append(text),
    )
    monkeypatch.setattr(
        "fl_editor.dialogs.QMessageBox.question",
        lambda *_args, **_kwargs: QMessageBox.Yes,
    )

    dialog.accept()

    assert warning_calls
    assert "Summe der Faction-Gewichte" in warning_calls[0]
    assert dialog.result() == 0


def test_zone_population_dialog_accept_allows_faction_weight_sum_of_exactly_one(qapp, monkeypatch):
    dialog = ZonePopulationDialog(
        None,
        zone_nickname="li01_trade_lane_zone",
        entries=[
            ("nickname", "li01_trade_lane_zone"),
            ("usage", "trade"),
        ],
        encounter_params=["area_trade_transport"],
        all_encounters=["area_trade_transport"],
        factions=["co_kt_grp", "co_ni_grp", "co_shi_grp", "co_ss_grp"],
    )
    dialog.enc_tree.clear()
    encounter = QTreeWidgetItem(["area_trade_transport", "3", "0.180000"])
    encounter.addChild(QTreeWidgetItem(["co_kt_grp", "0.27", ""]))
    encounter.addChild(QTreeWidgetItem(["co_ni_grp", "0.27", ""]))
    encounter.addChild(QTreeWidgetItem(["co_shi_grp", "0.27", ""]))
    encounter.addChild(QTreeWidgetItem(["co_ss_grp", "0.19", ""]))
    dialog.enc_tree.addTopLevelItem(encounter)

    warning_calls: list[str] = []
    question_calls: list[str] = []

    monkeypatch.setattr(
        "fl_editor.dialogs.QMessageBox.warning",
        lambda _parent, _title, text: warning_calls.append(text),
    )
    monkeypatch.setattr(
        "fl_editor.dialogs.QMessageBox.question",
        lambda *_args, **_kwargs: question_calls.append(_args[2]) or QMessageBox.Yes,
    )

    dialog.accept()

    assert warning_calls == []
    assert dialog.result() == 1


def test_zone_population_dialog_accept_blocks_encounter_without_faction(qapp, monkeypatch):
    dialog = ZonePopulationDialog(
        None,
        zone_nickname="li01_pop_zone",
        entries=[
            ("nickname", "li01_pop_zone"),
            ("pop_type", "attack_patrol"),
        ],
        encounter_params=["area_assault"],
        all_encounters=["area_assault"],
        factions=["li_n_grp"],
    )
    dialog.enc_tree.clear()
    dialog.enc_tree.addTopLevelItem(QTreeWidgetItem(["area_assault", "1", "0.100000"]))

    warning_calls: list[str] = []
    question_calls: list[str] = []

    monkeypatch.setattr(
        "fl_editor.dialogs.QMessageBox.warning",
        lambda _parent, _title, text: warning_calls.append(text),
    )
    monkeypatch.setattr(
        "fl_editor.dialogs.QMessageBox.question",
        lambda *_args, **_kwargs: question_calls.append("asked"),
    )

    dialog.accept()

    assert warning_calls
    assert "keine Faction-Zuordnung" in warning_calls[0]
    assert question_calls == []
    assert dialog.result() == 0


def test_zone_population_dialog_accept_warns_for_unusual_pop_type(qapp, monkeypatch):
    dialog = ZonePopulationDialog(
        None,
        zone_nickname="li01_trade_lane_zone",
        entries=[
            ("nickname", "li01_trade_lane_zone"),
            ("usage", "trade"),
            ("pop_type", "field"),
        ],
        encounter_params=["tradep_trade"],
        all_encounters=["tradep_trade"],
        factions=["li_n_grp"],
    )
    dialog.enc_tree.clear()
    encounter_item = QTreeWidgetItem(["tradep_trade", "12", "0.100000"])
    encounter_item.addChild(QTreeWidgetItem(["li_n_grp", "1.000000", ""]))
    dialog.enc_tree.addTopLevelItem(encounter_item)

    warning_calls: list[str] = []
    question_calls: list[str] = []

    monkeypatch.setattr(
        "fl_editor.dialogs.QMessageBox.warning",
        lambda _parent, _title, text: warning_calls.append(text),
    )
    monkeypatch.setattr(
        "fl_editor.dialogs.QMessageBox.question",
        lambda *_args, **_kwargs: question_calls.append(_args[2]) or QMessageBox.Yes,
    )

    dialog.accept()

    assert warning_calls == []
    assert question_calls
    assert "ungewoehnlich" in question_calls[0]
    assert dialog.result() == 1


def test_zone_population_dialog_build_entries_formats_chance_and_weight_as_floats(qapp):
    dialog = ZonePopulationDialog(
        None,
        zone_nickname="li01_trade_lane_zone",
        entries=[
            ("nickname", "li01_trade_lane_zone"),
            ("usage", "trade"),
        ],
        encounter_params=["tradep_trade"],
        all_encounters=["tradep_trade"],
        factions=["li_n_grp"],
    )

    dialog.enc_tree.topLevelItem(0).setText(1, "12")
    dialog.enc_tree.topLevelItem(0).setText(2, "0.1")
    dialog.enc_tree.topLevelItem(0).child(0).setText(1, "2")

    entries = dialog.build_entries()

    assert ("encounter", "tradep_trade, 12, 0.100000") in entries
    assert ("faction", "li_n_grp, 2.000000") in entries

def test_system_creation_dialog_builds_payload_from_user_inputs(qapp):
    dialog = SystemCreationDialog(
        None,
        music_space=["music_br_space"],
        music_danger=["music_br_danger"],
        music_battle=["music_br_battle"],
        bg_basic=[r"solar\starsphere\starsphere_stars_basic.cmp"],
        bg_complex=[r"solar\starsphere\starsphere_br01_stars.cmp"],
        bg_nebulae=[r"solar\starsphere\starsphere_br01.cmp"],
        factions=["li_n_grp"],
    )

    dialog.name_edit.setText("Taharka")
    dialog.prefix_edit.setText("te")
    dialog.size_spin.setValue(250000)

    payload = dialog.payload()

    assert payload["name"] == "Taharka"
    assert payload["prefix"] == "TE"
    assert payload["size"] == 250000
    assert payload["music_space"] == "music_br_space"
    assert payload["bg_basic"] == r"solar\starsphere\starsphere_stars_basic.cmp"
    assert payload["local_faction"] == "li_n_grp"


def test_system_settings_dialog_builds_result_data_from_current_values(qapp):
    dialog = SystemSettingsDialog(
        None,
        current={
            "nickname": "li01",
            "music_space": "music_li_space",
            "music_danger": "music_li_danger",
            "music_battle": "music_li_battle",
            "space_color": "1, 2, 3",
            "local_faction": "li_n_grp",
            "ambient_color": "4, 5, 6",
            "dust": "dust_light",
            "bg_basic": "basic_a",
            "bg_complex": "complex_a",
            "bg_nebulae": "nebula_a",
        },
        music_options={
            "space": ["music_li_space", "music_br_space"],
            "danger": ["music_li_danger"],
            "battle": ["music_li_battle"],
        },
        bg_options={
            "basic_stars": ["basic_a", "basic_b"],
            "complex_stars": ["complex_a"],
            "nebulae": ["nebula_a", "nebula_b"],
        },
        factions=["li_n_grp", "br_n_grp"],
        dust_options=["dust_light", "dust_heavy"],
    )

    dialog.music_space_cb.setCurrentText("music_br_space")
    dialog.local_faction_cb.setCurrentText("br_n_grp")
    dialog.dust_cb.setCurrentText("dust_heavy")
    dialog.bg_nebulae_cb.setCurrentText("nebula_b")

    result = dialog.result_data()

    assert result["music_space"] == "music_br_space"
    assert result["music_danger"] == "music_li_danger"
    assert result["music_battle"] == "music_li_battle"
    assert result["local_faction"] == "br_n_grp"
    assert result["dust"] == "dust_heavy"
    assert result["bg_nebulae"] == "nebula_b"


def test_solar_creation_dialog_builds_payload_from_inputs(qapp):
    dialog = SolarCreationDialog(
        None,
        title="Create Sun",
        archetypes=["med_sun"],
        default_radius=5000,
        default_damage=100,
        stars=["med_white_sun"],
        enable_planet_ring=True,
    )

    dialog.nick_edit.setText("sun_a")
    dialog.ids_name_edit.setText("Sun A")
    dialog.arch_cb.setCurrentText("med_sun")
    dialog.damage_spin.setValue(250)
    dialog.planet_ring_edit.setText("solar\\rings\\ring_a.ini")

    payload = dialog.payload()

    assert payload["nickname"] == "sun_a"
    assert payload["ids_name_text"] == "Sun A"
    assert payload["damage"] == 250
    assert payload["star"] == "med_white_sun"
    assert payload["planet_ring"] == "solar\\rings\\ring_a.ini"


def test_light_source_dialog_builds_payload_from_inputs(qapp):
    dialog = LightSourceDialog(
        None,
        nickname="light_a",
        types=["POINT", "DIRECTIONAL"],
        atten_curves=["DYNAMIC_DIRECTION"],
    )

    dialog.type_cb.setCurrentText("POINT")
    dialog.range_spin.setValue(42000)

    payload = dialog.payload()

    assert payload["nickname"] == "light_a"
    assert payload["type"] == "POINT"
    assert payload["range"] == 42000


def test_object_creation_dialog_builds_payload_from_inputs(qapp):
    dialog = ObjectCreationDialog(
        None,
        archetypes=["station_a"],
        loadouts=["loadout_a"],
        factions=["li_n_grp"],
    )

    dialog.nick_edit.setText("station_obj")
    dialog.ids_name_edit.setText("Station Object")
    dialog.loadout_cb.setCurrentText("loadout_a")
    dialog.faction_cb.setCurrentText("li_n_grp")

    payload = dialog.payload()

    assert payload["nickname"] == "station_obj"
    assert payload["ids_name_text"] == "Station Object"
    assert payload["loadout"] == "loadout_a"
    assert payload["faction"] == "li_n_grp"


def test_object_ring_dialog_builds_payload_and_preview_updates(qapp):
    previews: list[dict[str, object]] = []

    def _preview_builder(payload, _parent):
        previews.append(dict(payload))
        return QMessageBox()

    dialog = ObjectRingDialog(
        None,
        object_label="Test Object",
        ring_presets=["solar\\rings\\test.ini"],
        initial_state={
            "enabled": True,
            "ring_ini": "solar\\rings\\test.ini",
            "zone_nickname": "test_ring",
            "outer_radius": 3200.0,
            "inner_radius": 1400.0,
            "thickness": 300.0,
            "rotate_x": 10.0,
            "rotate_y": 20.0,
            "rotate_z": 30.0,
        },
        preview_builder=_preview_builder,
    )

    dialog.outer_spin.setValue(3300.0)
    dialog._preview_refresh_timer.stop()
    dialog._refresh_preview()
    payload = dialog.payload()

    assert payload["zone_nickname"] == "test_ring"
    assert payload["outer_radius"] == 3300.0
    assert payload["ring_ini"] == "solar\\rings\\test.ini"
    assert previews


def test_object_ring_dialog_uses_debounced_preview_refresh(qapp):
    previews: list[dict[str, object]] = []

    def _preview_builder(payload, _parent):
        previews.append(dict(payload))
        return QMessageBox()

    dialog = ObjectRingDialog(
        None,
        object_label="Test Object",
        ring_presets=["solar\\rings\\test.ini"],
        preview_builder=_preview_builder,
    )

    initial_count = len(previews)
    dialog.outer_spin.setValue(3400.0)

    assert dialog._preview_refresh_timer.isActive() is True
    assert len(previews) == initial_count


def test_object_ring_dialog_preserves_preview_camera_state_on_refresh(qapp):
    restored_states: list[dict[str, object]] = []

    class _PreviewWidget(QWidget):
        def __init__(self):
            super().__init__()
            self._state = {
                "center": (1.0, 2.0, 3.0),
                "position": (4.0, 5.0, 6.0),
                "distance": 7.0,
                "yaw_deg": 8.0,
                "pitch_deg": 9.0,
                "zoom_factor": 1.25,
            }

        def get_preview_camera_state(self):
            return dict(self._state)

        def set_preview_camera_state(self, state):
            restored_states.append(dict(state))

    def _preview_builder(_payload, _parent):
        return _PreviewWidget()

    dialog = ObjectRingDialog(
        None,
        object_label="Test Object",
        ring_presets=["solar\\rings\\test.ini"],
        preview_builder=_preview_builder,
    )

    dialog._refresh_preview()

    assert restored_states
    assert restored_states[-1]["position"] == (4.0, 5.0, 6.0)


def test_category_object_dialog_builds_payload_with_optional_rep_fields(qapp):
    dialog = CategoryObjectDialog(
        None,
        title="Create Wreck",
        archetypes=["wreck_a"],
        loadouts=["loadout_a"],
        factions=["li_n_grp"],
        show_reputation=True,
    )

    dialog.ids_name_edit.setText("Wreck A")
    dialog.loadout_cb.setCurrentText("loadout_a")
    dialog.faction_cb.setCurrentText("li_n_grp")
    dialog.rep_edit.setText("rep_a")

    payload = dialog.payload()

    assert payload["ids_name_text"] == "Wreck A"
    assert payload["faction"] == "li_n_grp"
    assert payload["rep"] == "rep_a"


def test_buoy_dialog_updates_pattern_and_payload(qapp):
    dialog = BuoyDialog(None)

    dialog.pattern_cb.setCurrentText("SINGLE")
    payload = dialog.payload()

    assert payload["pattern"] == "SINGLE"
    assert payload["count"] == 1

    dialog.pattern_cb.setCurrentText("CIRCLE")
    dialog.count_spin.setValue(6)
    payload = dialog.payload()

    assert payload["pattern"] == "CIRCLE"
    assert payload["count"] == 6


def test_exclusion_zone_dialog_builds_data_from_inputs(qapp):
    dialog = ExclusionZoneDialog(
        None,
        nickname_suggestion="zone_exclusion_a",
        default_pos=(0.0, 0.0, 0.0),
        default_size=(1.0, 1.0, 1.0),
    )

    dialog.shape_cb.setCurrentText("CYLINDER")
    dialog.comment_edit.setText("Field Exclusion")

    data = dialog.get_data()

    assert data["nickname"] == "zone_exclusion_a"
    assert data["shape"] == "CYLINDER"
    assert data["comment"] == "Field Exclusion"
    assert data["link_to_field_zone"] is True


def test_simple_zone_dialog_exposes_current_form_state(qapp):
    dialog = SimpleZoneDialog(None)

    dialog.name_edit.setText("zone_pop_a")
    dialog.comment_edit.setText("Population Zone")
    dialog.shape_cb.setCurrentText("CYLINDER")
    dialog.sort_spin.setValue(76)
    dialog.damage_spin.setValue(15)

    assert dialog.name_edit.text() == "zone_pop_a"
    assert dialog.comment_edit.text() == "Population Zone"
    assert dialog.shape_cb.currentText() == "CYLINDER"
    assert dialog.sort_spin.value() == 76
    assert dialog.damage_spin.value() == 15


def test_trade_lane_dialog_builds_payload_from_inputs(qapp):
    dialog = TradeLaneDialog(
        None,
        system_nick="li01",
        start_num=5,
        ring_count=4,
        distance=20000.0,
        factions=["li_n_grp"],
        extra_loadouts=["custom_lane_a"],
    )

    dialog.spacing_spin.setValue(10000)
    dialog.loadout_cb.setCurrentText("custom_lane_a")
    dialog.reputation_cb.setCurrentText("li_n_grp")
    dialog.ids_name_edit.setText("Trade Route A")
    dialog.space_name_end_edit.setText("Manhattan")

    payload = dialog.payload()

    assert payload["ring_count"] == 3
    assert payload["loadout"] == "custom_lane_a"
    assert payload["reputation"] == "li_n_grp"
    assert payload["ids_name"] == "Trade Route A"
    assert payload["space_name_start"] == "0"
    assert payload["space_name_end"] == "Manhattan"
