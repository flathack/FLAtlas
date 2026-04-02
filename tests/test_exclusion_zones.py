from __future__ import annotations

from fl_editor.exclusion_zones import patch_field_ini_exclusion_section, patch_field_ini_remove_exclusion


def test_patch_field_ini_exclusion_section_writes_nebula_shell_options():
    original = (
        "[Properties]\n"
        "flag = nebula\n"
        "\n"
        "[Fog]\n"
        "fog_enabled = 1\n"
    )

    patched, changed = patch_field_ini_exclusion_section(
        original,
        "Zone_Li05_shipyard_exclusion",
        shell_options={
            "fog_far": 8000,
            "zone_shell": "solar\\nebula\\generic_exclusion.3db",
            "shell_scalar": 1,
            "max_alpha": 0.5,
            "exclusion_tint": "40, 120, 120",
        },
    )

    assert changed is True
    assert "[Exclusion Zones]" in patched
    assert "exclusion = Zone_Li05_shipyard_exclusion" in patched
    assert "fog_far = 8000" in patched
    assert "zone_shell = solar\\nebula\\generic_exclusion.3db" in patched
    assert "shell_scalar = 1" in patched
    assert "max_alpha = 0.5" in patched
    assert "exclusion_tint = 40, 120, 120" in patched


def test_patch_field_ini_remove_exclusion_removes_following_shell_option_lines():
    original = (
        "[Exclusion Zones]\n"
        "exclusion = Zone_Li05_shipyard_exclusion\n"
        "fog_far = 8000\n"
        "zone_shell = solar\\nebula\\generic_exclusion.3db\n"
        "shell_scalar = 1\n"
        "max_alpha = 0.5\n"
        "exclusion_tint = 40, 120, 120\n"
        "exclusion = Zone_Li05_other_exclusion\n"
        "exclude_billboards = 1\n"
    )

    patched, changed = patch_field_ini_remove_exclusion(original, "Zone_Li05_shipyard_exclusion")

    assert changed is True
    assert "Zone_Li05_shipyard_exclusion" not in patched
    assert "fog_far = 8000" not in patched
    assert "zone_shell = solar\\nebula\\generic_exclusion.3db" not in patched
    assert "shell_scalar = 1" not in patched
    assert "max_alpha = 0.5" not in patched
    assert "exclusion_tint = 40, 120, 120" not in patched
    assert "exclusion = Zone_Li05_other_exclusion" in patched
    assert "exclude_billboards = 1" in patched
