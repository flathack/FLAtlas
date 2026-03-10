from fl_editor.system_creation_writes import (
    append_universe_system_section,
    build_system_ini_text,
    serialize_universe_with_new_system,
)


def test_build_system_ini_text_contains_expected_sections():
    text = build_system_ini_text(
        space_color="10, 20, 30",
        local_faction="fc_test_grp",
        music_space="music_space",
        music_danger="music_danger",
        music_battle="music_battle",
        ambient_color="1, 2, 3",
        bg_basic="stars_basic",
        bg_complex="stars_complex",
        bg_nebulae="nebulae",
        light_nick="li01_system_light",
        light_color="255, 255, 255",
        size=150000,
    )

    assert "[SystemInfo]" in text
    assert "local_faction = fc_test_grp" in text
    assert "[LightSource]" in text
    assert "nickname = li01_system_light" in text
    assert "range = 150000" in text


def test_append_universe_system_section_appends_expected_entries():
    sections = [("system", [("nickname", "old01")])]

    updated = append_universe_system_section(
        sections,
        nickname="li01",
        rel_path="systems\\li01\\li01.ini",
        pos_x=123.4,
        pos_y=567.8,
        strid_name="196000",
    )

    assert len(updated) == 2
    sec_name, entries = updated[-1]
    assert sec_name == "system"
    assert ("nickname", "li01") in entries
    assert ("file", "systems\\li01\\li01.ini") in entries
    assert ("pos", "123, 568") in entries
    assert ("ids_info", "66106") in entries


def test_serialize_universe_with_new_system_serializes_added_section():
    text = serialize_universe_with_new_system(
        [],
        nickname="li01",
        rel_path="systems\\li01\\li01.ini",
        pos_x=10,
        pos_y=20,
        strid_name="1234",
    )

    assert "[system]" in text
    assert "nickname = li01" in text
    assert "file = systems\\li01\\li01.ini" in text
    assert "strid_name = 1234" in text
