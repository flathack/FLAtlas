from __future__ import annotations

from pathlib import Path

from fl_editor.ini_editor_logic import (
    compare_ini_sections,
    parse_ini_section_details,
    parse_ini_sections,
    scan_ini_tree,
    scan_ini_tree_with_fallback,
    should_skip_ini_tree_entry,
    update_ini_section_field,
)


def test_should_skip_ini_tree_entry_filters_git_metadata():
    assert should_skip_ini_tree_entry(Path(".git"))
    assert should_skip_ini_tree_entry(Path(".gitignore"))
    assert not should_skip_ini_tree_entry(Path("DATA"))


def test_scan_ini_tree_returns_sorted_nested_entries(tmp_path: Path):
    (tmp_path / "DATA").mkdir()
    (tmp_path / "DATA" / "world.ini").write_text("[system]\n", encoding="utf-8")
    (tmp_path / "alpha.ini").write_text("[alpha]\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()

    tree = scan_ini_tree(tmp_path)

    assert tree.entry_type == "dir"
    assert [child.path.name for child in tree.children] == ["DATA", "alpha.ini"]
    assert [child.path.name for child in tree.children[0].children] == ["world.ini"]


def test_parse_ini_sections_returns_titles_and_block_numbers():
    sections = parse_ini_sections("foo\n[system]\nbar\n[object]\n")

    assert sections == [("[system]", 1), ("[object]", 3)]


def test_parse_ini_sections_includes_identifier_detail_for_repeated_sections():
    sections = parse_ini_sections(
        "[BaseGood]\n"
        "base = Br01_01_base\n"
        "marketgood = ge_s_scanner_01, 0, -1, 1, 1, 0, 1\n"
    )

    assert sections == [("[BaseGood]  base = Br01_01_base", 0)]


def test_scan_ini_tree_with_fallback_merges_files_and_prefers_primary(tmp_path: Path):
    primary = tmp_path / "mod"
    fallback = tmp_path / "fl"
    (primary / "DATA").mkdir(parents=True)
    (fallback / "DATA").mkdir(parents=True)
    (primary / "DATA" / "common.ini").write_text("[mod]\n", encoding="utf-8")
    (fallback / "DATA" / "common.ini").write_text("[vanilla]\n", encoding="utf-8")
    (fallback / "DATA" / "missing.ini").write_text("[fallback]\n", encoding="utf-8")

    tree = scan_ini_tree_with_fallback(primary, fallback)

    data = tree.children[0]
    assert data.path == (primary / "DATA")
    assert [child.path.name for child in data.children] == ["common.ini", "missing.ini"]
    assert data.children[0].source == "primary"
    assert data.children[1].source == "fallback"


def test_compare_ini_sections_detects_added_removed_and_changed_sections():
    counterpart_text = (
        "[SystemInfo]\n"
        "space_color = 0, 0, 0\n"
        "\n"
        "[Object]\n"
        "nickname = old_object\n"
        "\n"
        "[EncounterParameters]\n"
        "nickname = test_encounter\n"
    )
    current_text = (
        "[SystemInfo]\n"
        "space_color = 255, 255, 255\n"
        "\n"
        "[Object]\n"
        "nickname = new_object\n"
        "\n"
        "[Zone]\n"
        "nickname = zone_test\n"
    )

    result = compare_ini_sections(current_text, counterpart_text)

    assert result["changed"] == ["[Object]  nickname = new_object", "[SystemInfo]"]
    assert result["added"] == ["[Zone]  nickname = zone_test"]
    assert result["removed"] == ["[EncounterParameters]  nickname = test_encounter"]


def test_compare_ini_sections_handles_duplicate_section_titles_by_occurrence():
    counterpart_text = (
        "[Object]\n"
        "nickname = obj_a\n"
        "\n"
        "[Object]\n"
        "nickname = obj_b\n"
    )
    current_text = (
        "[Object]\n"
        "nickname = obj_a\n"
        "\n"
        "[Object]\n"
        "nickname = obj_c\n"
        "\n"
        "[Object]\n"
        "nickname = obj_d\n"
    )

    result = compare_ini_sections(current_text, counterpart_text)

    assert result["changed"] == ["[Object]  nickname = obj_c (#2)"]
    assert result["added"] == ["[Object]  nickname = obj_d (#3)"]
    assert result["removed"] == []


def test_parse_ini_section_details_returns_editable_fields():
    text = (
        "[BaseGood]\n"
        "base = Li01_01_base\n"
        "; comment\n"
        "MarketGood = commodity_gold, 0, -1, 1, 1, 0, 1\n"
        "MarketGood = commodity_silver, 0, -1, 1, 1, 0, 1\n"
    )

    details = parse_ini_section_details(text, 0)

    assert details is not None
    assert details.title == "[BaseGood]"
    assert [(field.key, field.value, field.occurrence) for field in details.fields] == [
        ("base", "Li01_01_base", 0),
        ("MarketGood", "commodity_gold, 0, -1, 1, 1, 0, 1", 0),
        ("MarketGood", "commodity_silver, 0, -1, 1, 1, 0, 1", 1),
    ]


def test_update_ini_section_field_rewrites_selected_occurrence():
    text = (
        "[BaseGood]\n"
        "MarketGood = commodity_gold, 0, -1, 1, 1, 0, 1\n"
        "MarketGood = commodity_silver, 0, -1, 1, 1, 0, 1\n"
    )

    updated = update_ini_section_field(
        text,
        0,
        "MarketGood",
        1,
        "commodity_silver, 0, -1, 150, 500, 0, 0.05",
    )

    assert "commodity_gold, 0, -1, 1, 1, 0, 1" in updated
    assert "commodity_silver, 0, -1, 150, 500, 0, 0.05" in updated
