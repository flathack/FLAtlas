from __future__ import annotations

from pathlib import Path

from fl_editor.ini_editor_logic import (
    parse_ini_sections,
    scan_ini_tree,
    scan_ini_tree_with_fallback,
    should_skip_ini_tree_entry,
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
