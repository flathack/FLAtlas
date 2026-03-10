from __future__ import annotations

from pathlib import Path

from fl_editor.universe_edit_state import ensure_universe_sections_for_edit, find_universe_system_section_index


def test_ensure_universe_sections_for_edit_reuses_existing_cached_file(tmp_path: Path):
    uni_path = tmp_path / "universe.ini"
    uni_path.write_text("[System]\n", encoding="utf-8")
    sections = [("System", [("nickname", "li01")])]

    ok, path, parsed = ensure_universe_sections_for_edit(
        sections,
        uni_path,
        primary_game_path="/game",
        find_universe_ini_read=lambda _gp: None,
        parse_sections=lambda _path: [],
    )

    assert ok is True
    assert path == uni_path
    assert parsed == sections


def test_ensure_universe_sections_for_edit_loads_when_cache_missing(tmp_path: Path):
    uni_path = tmp_path / "universe.ini"
    uni_path.write_text("[System]\n", encoding="utf-8")
    parsed_sections = [("System", [("nickname", "li02")])]

    ok, path, parsed = ensure_universe_sections_for_edit(
        [],
        None,
        primary_game_path="/game",
        find_universe_ini_read=lambda _gp: uni_path,
        parse_sections=lambda _path: parsed_sections,
    )

    assert ok is True
    assert path == uni_path
    assert parsed == parsed_sections


def test_find_universe_system_section_index_matches_lowercased_nickname():
    sections = [
        ("Base", [("nickname", "li01_01_base")]),
        ("System", [("nickname", "LI01")]),
        ("System", [("nickname", "br01")]),
    ]

    result = find_universe_system_section_index(
        sections,
        "li01",
        entry_get_value=lambda entries, key: next((value for entry_key, value in entries if entry_key == key), ""),
    )

    assert result == 1
