from __future__ import annotations

from fl_editor.system_infocard_draft import build_system_infocard_draft_xml, collect_base_ids_from_universe_sections


def test_collect_base_ids_from_universe_sections_prefers_strid_and_ids_name():
    sections = [
        ("Base", [("nickname", "li01_01_base"), ("strid_name", "1234")]),
        ("Base", [("nickname", "li01_02_base"), ("ids_name", "5678")]),
        ("System", [("nickname", "li01")]),
    ]

    result = collect_base_ids_from_universe_sections(
        sections,
        entry_get_value=lambda entries, key: next((value for entry_key, value in entries if entry_key == key), ""),
    )

    assert result == {
        "li01_01_base": "1234",
        "li01_02_base": "5678",
    }


def test_build_system_infocard_draft_xml_renders_english_content():
    xml = build_system_infocard_draft_xml(
        sys_name="New York",
        lang="en",
        object_count=10,
        zone_count=3,
        star_count=1,
        nebula_count=2,
        asteroid_count=1,
        dest_names=["Texas"],
        local_faction_disp="Liberty Navy",
        base_names=["Manhattan"],
        planet_names=["Manhattan"],
    )

    assert "The New York system is a star system in Sirius." in xml
    assert "Jump connections: Texas" in xml
    assert "Bases: Manhattan" in xml


def test_build_system_infocard_draft_xml_renders_german_fallbacks():
    xml = build_system_infocard_draft_xml(
        sys_name="Hamburg",
        lang="de",
        object_count=5,
        zone_count=1,
        star_count=1,
        nebula_count=0,
        asteroid_count=0,
        dest_names=[],
        local_faction_disp="",
        base_names=[],
        planet_names=[],
    )

    assert "Das Hamburg-System ist ein Sternensystem in Sirius." in xml
    assert "Keine direkten Verbindungen erkannt." in xml
    assert "Lokale Fraktion: Unbekannt." in xml
