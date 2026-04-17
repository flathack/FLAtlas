from __future__ import annotations

from PySide6.QtCore import Qt

from fl_editor.dialogs import DockingRingDialog


def test_docking_ring_dialog_prefills_user_friendly_defaults_and_template_data(qapp):
    dialog = DockingRingDialog(
        None,
        planet_nickname="li01_01",
        base_nickname="li01_01_base",
        loadouts=["docking_ring_li_01"],
        factions=["li_n_grp - Liberty Navy"],
        existing_bases=[("Template Base", "li01_02_base")],
        pilots=["pilot_solar_easiest"],
        voices=["atc_leg_f01a"],
        needs_base=True,
        default_faction="li_n_grp - Liberty Navy",
        ids_name_text="Planet Manhattan Docking Ring",
        strid_name_value=1234,
    )
    dialog.template_cb.setCurrentIndex(1)

    payload = dialog.payload()

    assert payload["nickname"] == "Dock_Ring_li01_01"
    assert payload["ids_name"] == "Planet Manhattan Docking Ring"
    assert payload["ids_info"] == "66141"
    assert payload["base_nickname"] == "li01_01_base"
    assert payload["strid_name"] == 1234
    assert payload["rooms"] == ["Deck", "Bar", "Trader"]
    assert payload["start_room"] == "Deck"
    assert payload["template_base"] == "li01_02_base"
    assert payload["create_fixture"] is False
    assert payload["copy_template_npcs"] is True
    assert dialog.faction_cb.currentText() == "li_n_grp - Liberty Navy"
    assert dialog.voice_cb.currentText() == "atc_leg_m01"
    assert dialog.faction_cb.completer() is not None
    assert dialog.faction_cb.completer().filterMode() == Qt.MatchContains
    assert dialog.template_cb.itemText(1) == "Template Base"
    assert dialog.template_cb.itemData(1) == "li01_02_base"


def test_docking_ring_dialog_allows_enabling_fixture_creation(qapp):
    dialog = DockingRingDialog(
        None,
        planet_nickname="li01_01",
        base_nickname="li01_01_base",
        loadouts=["docking_ring_li_01"],
        factions=["li_n_grp - Liberty Navy"],
        needs_base=False,
    )

    dialog.create_fixture_cb.setChecked(True)

    payload = dialog.payload()

    assert payload["create_fixture"] is True
    assert payload["copy_template_npcs"] is False


def test_docking_ring_dialog_template_selection_enables_template_rooms(qapp):
    dialog = DockingRingDialog(
        None,
        planet_nickname="li01_01",
        base_nickname="li01_01_base",
        loadouts=["docking_ring_li_01"],
        factions=["li_n_grp - Liberty Navy"],
        existing_bases=[("Planet Pittsburgh", "li06_02_base")],
        template_room_names_provider=lambda template_nick: ["Bar", "Planetscape", "Planetscape2"] if template_nick == "li06_02_base" else [],
        needs_base=True,
    )

    dialog.template_cb.setCurrentIndex(1)

    payload = dialog.payload()

    assert "Planetscape" in dialog.room_checks
    assert dialog.room_checks["Trader"].isChecked() is False
    assert dialog.room_checks["Planetscape"].isChecked() is True
    assert dialog.room_checks["Planetscape2"].isChecked() is True
    assert dialog.room_checks["Deck"].isChecked() is False
    assert payload["rooms"] == ["Bar", "Planetscape", "Planetscape2"]
    assert payload["start_room"] == "Planetscape"


def test_docking_ring_dialog_prefers_cityscape_as_template_start_room(qapp):
    dialog = DockingRingDialog(
        None,
        planet_nickname="li01_01",
        base_nickname="li01_01_base",
        loadouts=["docking_ring_li_01"],
        factions=["li_n_grp - Liberty Navy"],
        existing_bases=[("Houston", "li04_01_base")],
        template_room_names_provider=lambda template_nick: ["Bar", "Trader", "Equipment", "ShipDealer", "Cityscape"] if template_nick == "li04_01_base" else [],
        needs_base=True,
    )

    dialog.template_cb.setCurrentIndex(1)

    payload = dialog.payload()

    assert payload["rooms"] == ["Bar", "Trader", "Equipment", "ShipDealer", "Cityscape"]
    assert payload["start_room"] == "Cityscape"
