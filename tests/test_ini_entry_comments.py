from __future__ import annotations

from pathlib import Path

from fl_editor.ini_section_writes import serialize_sections_to_ini_text
from fl_editor.main_window import MainWindow
from fl_editor.models import SolarObject
from fl_editor.parser import FLParser


def test_parser_keeps_inline_comment_metadata_without_polluting_value(tmp_path: Path):
    path = tmp_path / "system.ini"
    path.write_text("[Object]\nnickname = test\nids_name = 32423 ; kommentar\n", encoding="utf-8")

    sections = FLParser().parse(str(path))
    entry = sections[0][1][1]

    assert entry == ("ids_name", "32423")
    assert getattr(entry, "inline_comment", "") == " ; kommentar"


def test_object_editor_raw_text_shows_inline_comments(tmp_path: Path, qapp):
    path = tmp_path / "system.ini"
    path.write_text("[Object]\nnickname = test\nids_name = 32423 ; kommentar\n", encoding="utf-8")
    sections = FLParser().parse(str(path))
    data = MainWindow._entries_to_data(sections[0][1])

    obj = SolarObject(data, 1.0)

    assert "ids_name = 32423 ; kommentar" in obj.raw_text()
    assert obj.data["ids_name"] == "32423"


def test_object_editor_apply_text_preserves_edited_inline_comments(qapp):
    obj = SolarObject({"nickname": "test", "pos": "0,0,0", "_entries": []}, 1.0)

    obj.apply_text("[Object]\nnickname = test\nids_name = 32424 ; neuer kommentar\n")

    assert obj.data["ids_name"] == "32424"
    assert "ids_name = 32424 ; neuer kommentar" in obj.raw_text()
    assert serialize_sections_to_ini_text([("Object", obj.data["_entries"])]) == (
        "[Object]\n"
        "nickname = test\n"
        "ids_name = 32424 ; neuer kommentar\n"
    )
