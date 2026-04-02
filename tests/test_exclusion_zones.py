from __future__ import annotations

from fl_editor.exclusion_zones import (
    patch_field_ini_exclusion_section,
    patch_field_ini_remove_exclusion,
    read_field_ini_exclusion_settings,
)


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


def test_patch_field_ini_exclusion_section_replaces_existing_shell_options_instead_of_appending():
    original = (
        "[Exclusion Zones]\n"
        "exclusion = Zone_Li05_shipyard_exclusion\n"
        "fog_far = 8000\n"
        "zone_shell = solar\\nebula\\generic_exclusion.3db\n"
        "shell_scalar = 1\n"
        "max_alpha = 0.5\n"
        "exclusion_tint = 40, 120, 120\n"
    )

    patched, changed = patch_field_ini_exclusion_section(
        original,
        "Zone_Li05_shipyard_exclusion",
        shell_options={
            "fog_far": 9000,
            "zone_shell": "solar\\nebula\\crow_exclusion.3db",
            "shell_scalar": 1.2,
            "max_alpha": 0.65,
            "exclusion_tint": "10, 20, 30",
        },
    )

    assert changed is True
    assert patched.count("fog_far =") == 1
    assert "fog_far = 9000" in patched
    assert patched.count("zone_shell =") == 1
    assert "zone_shell = solar\\nebula\\crow_exclusion.3db" in patched
    assert patched.count("shell_scalar =") == 1
    assert "shell_scalar = 1.2" in patched
    assert patched.count("max_alpha =") == 1
    assert "max_alpha = 0.65" in patched
    assert patched.count("exclusion_tint =") == 1
    assert "exclusion_tint = 10, 20, 30" in patched


def test_read_field_ini_exclusion_settings_returns_shell_values_for_existing_exclusion():
    ini_text = (
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

    data = read_field_ini_exclusion_settings(ini_text, "Zone_Li05_shipyard_exclusion")

    assert data == {
        "enabled": True,
        "fog_far": 8000,
        "zone_shell": "solar\\nebula\\generic_exclusion.3db",
        "shell_scalar": 1.0,
        "max_alpha": 0.5,
        "exclusion_tint": "40, 120, 120",
    }
