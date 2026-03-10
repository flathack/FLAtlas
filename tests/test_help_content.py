from __future__ import annotations

from pathlib import Path

from fl_editor.help_content import help_tree_file_candidates, help_xml_inner_html, load_help_tree_sections


def test_help_tree_file_candidates_prefer_selected_language():
    base_dir = Path("/tmp/help")

    candidates = help_tree_file_candidates(base_dir, "en")

    assert candidates[0] == base_dir / "tree_en.xml"
    assert candidates[1:] == [base_dir / "tree_en.xml", base_dir / "tree_de.xml"]


def test_help_xml_inner_html_preserves_nested_markup():
    import xml.etree.ElementTree as ET

    node = ET.fromstring("<content>Intro <b>bold</b> tail</content>")

    assert help_xml_inner_html(node) == "Intro <b>bold</b> tail"


def test_load_help_tree_sections_reads_first_valid_file(tmp_path: Path):
    (tmp_path / "tree_de.xml").write_text(
        "<help><section title='Universe'><item title='Overview'><content><p>Hallo</p></content></item></section></help>",
        encoding="utf-8",
    )

    sections = load_help_tree_sections(tmp_path, "de")

    assert sections == [
        {
            "title": "Universe",
            "children": [{"title": "Overview", "content": "<p>Hallo</p>"}],
        }
    ]
