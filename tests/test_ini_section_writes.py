from __future__ import annotations

from pathlib import Path

from fl_editor.ini_section_writes import (
    append_ini_section_block,
    serialize_sections_to_ini_text,
    update_ids_entry_in_sections,
    write_sections_to_file,
)


def test_update_ids_entry_in_sections_updates_matching_object_case_insensitively():
    sections = [
        ("Object", [("nickname", "Li01_TradeLane_1"), ("ids_info", "123")]),
        ("Zone", [("nickname", "zone_a"), ("ids_info", "456")]),
    ]

    updated = update_ids_entry_in_sections(sections, "object", "li01_tradelane_1", "ids_info", "999")

    assert updated is True
    assert sections[0][1][1] == ("ids_info", "999")


def test_update_ids_entry_in_sections_returns_false_when_key_missing():
    sections = [("Object", [("nickname", "li01_station")])]

    updated = update_ids_entry_in_sections(sections, "object", "li01_station", "ids_name", "12")

    assert updated is False


def test_serialize_sections_to_ini_text_preserves_blank_line_between_sections():
    text = serialize_sections_to_ini_text(
        [
            ("System", [("nickname", "li01")]),
            ("Base", [("nickname", "li01_01_base"), ("ids_info", "66")]),
        ]
    )

    assert text == (
        "[System]\n"
        "nickname = li01\n"
        "\n"
        "[Base]\n"
        "nickname = li01_01_base\n"
        "ids_info = 66\n"
    )


def test_write_sections_to_file_writes_utf8_ini_text(tmp_path: Path):
    filepath = tmp_path / "test.ini"

    write_sections_to_file(filepath, [("System", [("nickname", "li01")])])

    assert filepath.read_text(encoding="utf-8") == "[System]\nnickname = li01\n"


def test_serialize_sections_to_ini_text_matches_system_document_write_format():
    text = serialize_sections_to_ini_text(
        [
            ("System", [("nickname", "li01"), ("file", "systems\\li01.ini")]),
            ("Object", [("nickname", "li01_station"), ("ids_name", "1234")]),
        ]
    )

    assert text == (
        "[System]\n"
        "nickname = li01\n"
        "file = systems\\li01.ini\n"
        "\n"
        "[Object]\n"
        "nickname = li01_station\n"
        "ids_name = 1234\n"
    )


def test_append_ini_section_block_appends_with_leading_separator(tmp_path: Path):
    filepath = tmp_path / "universe.ini"
    filepath.write_text("[System]\nnickname = li01\n", encoding="utf-8")

    append_ini_section_block(filepath, "Base", [("nickname", "li01_01_base"), ("system", "li01")])

    assert filepath.read_text(encoding="utf-8") == (
        "[System]\n"
        "nickname = li01\n"
        "\n"
        "[Base]\n"
        "nickname = li01_01_base\n"
        "system = li01\n"
    )
