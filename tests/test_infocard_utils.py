from __future__ import annotations

from fl_editor.infocard_utils import (
    build_infocard_xml_from_fields,
    default_infocard_xml_template,
    escape_xml_text,
    infocard_apply_tra_to_state,
    infocard_flags_to_css,
    infocard_normalize_align,
    infocard_normalize_color,
    xml_to_plain_preview,
)


def test_default_infocard_template_contains_rdl_shell():
    template = default_infocard_xml_template()

    assert template.startswith("<RDL>")
    assert template.endswith("</RDL>")


def test_escape_xml_text_escapes_reserved_chars():
    assert escape_xml_text("<tag a='1'>&\"") == "&lt;tag a=&apos;1&apos;&gt;&amp;&quot;"


def test_xml_to_plain_preview_flattens_markup():
    assert xml_to_plain_preview("<RDL><TEXT>Hello</TEXT><PARA/><TEXT>World</TEXT></RDL>") == "Hello World"


def test_infocard_flag_and_alignment_helpers_normalize_values():
    assert infocard_flags_to_css(3) == "font-weight:700;font-style:italic;"
    assert infocard_normalize_align("Centre") == "center"
    assert infocard_normalize_align("weird") == "left"


def test_infocard_color_normalization_and_tra_state_updates():
    state: dict[str, str | int] = {"flags": 0, "color": "default"}

    infocard_apply_tra_to_state(state, {"bold": "true", "underline": "1", "color": "aa00ff"})

    assert state["flags"] == 5
    assert state["color"] == "#AA00FF"
    assert infocard_normalize_color("none") == "default"


def test_build_infocard_xml_from_fields_builds_expected_rdl():
    xml = build_infocard_xml_from_fields(
        "Title",
        "Line 1\n\nLine 2",
        "center",
        3,
        "aa00ff",
    )

    assert "<JUST loc=\"c\"/>" in xml
    assert "<TRA bold=\"true\" italic=\"true\" underline=\"false\" color=\"#AA00FF\" />" in xml
    assert "<TEXT>Title</TEXT>" in xml
    assert "<TEXT>Line 1</TEXT>" in xml
    assert "<TEXT>Line 2</TEXT>" in xml


def test_build_infocard_xml_from_fields_falls_back_to_default_template():
    assert build_infocard_xml_from_fields("", "", "left", 0, "default") == default_infocard_xml_template()
