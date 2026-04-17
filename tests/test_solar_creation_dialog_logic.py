from __future__ import annotations

from PySide6.QtWidgets import QApplication

from fl_editor.dialogs import SolarCreationDialog


def test_planet_size_from_archetype_reads_numeric_suffix():
    assert SolarCreationDialog._planet_size_from_archetype("planet_earthgrncld_4000") == 4000
    assert SolarCreationDialog._planet_size_from_archetype("planet_moon_250.5") == 250
    assert SolarCreationDialog._planet_size_from_archetype("planet_unknown") is None


def test_solar_creation_dialog_updates_ids_info_text_from_provider(qapp):
    dialog = SolarCreationDialog(
        None,
        "Create Planet",
        ["planet_desored_1500", "planet_earthgrncld_4000"],
        default_radius=1500,
        default_damage=200000,
        enable_planet_ring=True,
        ids_info_text_provider=lambda archetype: {
            "planet_desored_1500": "Pittsburgh template",
            "planet_earthgrncld_4000": "Manhattan template",
        }.get(str(archetype), ""),
    )
    try:
        assert dialog.ids_info_edit.toPlainText().strip() == "Pittsburgh template"
        dialog.arch_cb.setCurrentText("planet_earthgrncld_4000")
        QApplication.processEvents()
        assert dialog.ids_info_edit.toPlainText().strip() == "Manhattan template"
    finally:
        dialog.close()
