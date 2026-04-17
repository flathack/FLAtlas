from __future__ import annotations

from fl_editor.dialogs import SolarCreationDialog


def test_planet_size_from_archetype_reads_numeric_suffix():
    assert SolarCreationDialog._planet_size_from_archetype("planet_earthgrncld_4000") == 4000
    assert SolarCreationDialog._planet_size_from_archetype("planet_moon_250.5") == 250
    assert SolarCreationDialog._planet_size_from_archetype("planet_unknown") is None
