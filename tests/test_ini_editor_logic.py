from __future__ import annotations

from pathlib import Path

from fl_editor.ini_editor_logic import parse_ini_sections, scan_ini_tree, should_skip_ini_tree_entry


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
