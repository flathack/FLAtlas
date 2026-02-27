from fl_editor.exclusion_zones import (
    add_exclusion_entry,
    generate_exclusion_nickname,
    patch_field_ini_exclusion_section,
    patch_system_ini_for_exclusion,
)


def test_generate_exclusion_nickname_is_unique():
    existing = [
        "Zone_BR01_Zone_BR01_Field_exclusion_1",
        "Zone_BR01_Zone_BR01_Field_exclusion_2",
    ]
    nick = generate_exclusion_nickname("BR01", "Zone_BR01_Field", existing)
    assert nick == "Zone_BR01_Zone_BR01_Field_exclusion_3"


def test_add_exclusion_entry_appends_without_duplicates():
    entries = [
        ("nickname", "Zone_BR01_Field"),
        ("shape", "ELLIPSOID"),
        ("size", "12000, 6000, 10000"),
    ]
    updated, changed = add_exclusion_entry(entries, "Zone_BR01_Field_exclusion_1")
    assert changed is True
    assert updated[-1] == ("exclusion", "Zone_BR01_Field_exclusion_1")

    updated2, changed2 = add_exclusion_entry(updated, "Zone_BR01_Field_exclusion_1")
    assert changed2 is False
    assert [e for e in updated2 if e[0].lower() == "exclusion"] == [
        ("exclusion", "Zone_BR01_Field_exclusion_1")
    ]


def test_patch_system_ini_for_exclusion_appends_only_new_zone_block_when_unlinked():
    original = """; system comment
[SystemInfo]
space_color = 0, 0, 0

[Zone]
nickname = Zone_BR01_Field
shape = ELLIPSOID
size = 12000, 6000, 10000

[Zone]
nickname = Zone_Other
shape = SPHERE
size = 500
"""

    exclusion_entries = [
        ("nickname", "Zone_BR01_Field_exclusion_1"),
        ("pos", "0, 0, 0"),
        ("shape", "SPHERE"),
        ("size", "2000"),
        ("property_flags", "131072"),
    ]

    patched = patch_system_ini_for_exclusion(
        original,
        field_zone_nickname="Zone_BR01_Field",
        exclusion_zone_nickname="Zone_BR01_Field_exclusion_1",
        exclusion_zone_entries=exclusion_entries,
        link_to_field_zone=False,
    )

    assert "; system comment" in patched
    assert "nickname = Zone_Other\nshape = SPHERE\nsize = 500" in patched
    assert "exclusion = Zone_BR01_Field_exclusion_1" not in patched
    assert "[Zone]\nnickname = Zone_BR01_Field_exclusion_1\npos = 0, 0, 0\nshape = SPHERE\nsize = 2000\nproperty_flags = 131072" in patched


def test_patch_field_ini_exclusion_section_adds_exclusion():
    field_ini = """; asteroid field template
[TexturePanels]
file = universe\\liberty\\li01\\shapes.ini

[Exclusion Zones]
exclusion = Zone_Li01_existing_exclusion
"""
    patched, changed = patch_field_ini_exclusion_section(
        field_ini,
        "Zone_Li01_badlands_low_density_asteroids",
    )
    assert changed is True
    assert "[Exclusion Zones]" in patched
    assert "exclusion = Zone_Li01_existing_exclusion" in patched
    assert "exclusion = Zone_Li01_badlands_low_density_asteroids" in patched


def test_patch_field_ini_exclusion_section_inserts_after_properties_when_missing():
    field_ini = """[TexturePanels]
file = solar\\asteroids\\mine_shapes.ini

[Field]
cube_size = 250

[properties]
flag = mine_danger_objects

[Cube]
xaxis_rotation = 8, 40, 90, 158
"""
    patched, changed = patch_field_ini_exclusion_section(
        field_ini,
        "Zone_Rh04_nomad_shipyard_exclusion",
    )
    assert changed is True
    assert patched.index("[properties]") < patched.index("[Exclusion Zones]") < patched.index("[Cube]")
    assert "exclusion = Zone_Rh04_nomad_shipyard_exclusion" in patched
