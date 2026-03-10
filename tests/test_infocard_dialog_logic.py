from __future__ import annotations

from fl_editor.infocard_dialog_logic import validate_infocard_xml


def test_validate_infocard_xml_accepts_valid_xml():
    ok, value = validate_infocard_xml("<RDL><TEXT>Hello</TEXT></RDL>")

    assert ok is True
    assert value == "<RDL><TEXT>Hello</TEXT></RDL>"


def test_validate_infocard_xml_rejects_empty_and_invalid_xml():
    ok, value = validate_infocard_xml("   ")
    assert ok is False
    assert value == ""

    ok, value = validate_infocard_xml("<RDL>")
    assert ok is False
    assert value


def test_validate_infocard_xml_trims_valid_xml():
    ok, value = validate_infocard_xml("  <RDL><TEXT>Hi</TEXT></RDL>  ")

    assert ok is True
    assert value == "<RDL><TEXT>Hi</TEXT></RDL>"
