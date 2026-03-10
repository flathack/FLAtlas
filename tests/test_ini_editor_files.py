from __future__ import annotations

from pathlib import Path

from fl_editor.ini_editor_files import (
    ini_editor_context_root,
    ini_editor_open_file,
    ini_editor_save_file,
)


def test_ini_editor_context_root_prefers_editing_profile(tmp_path: Path):
    editing_root = tmp_path / "editing"
    selected_root = tmp_path / "selected"
    editing_root.mkdir()
    selected_root.mkdir()

    result = ini_editor_context_root(
        {"id": "edit"},
        {"id": "selected"},
        lambda profile: editing_root if profile and profile.get("id") == "edit" else selected_root,
    )

    assert result == editing_root


def test_ini_editor_open_file_reads_text(tmp_path: Path):
    ini_path = tmp_path / "test.ini"
    ini_path.write_text("[test]\n", encoding="utf-8")

    ok, opened_path, text = ini_editor_open_file(str(ini_path), lambda path: path.read_text(encoding="utf-8"))

    assert ok
    assert opened_path == str(ini_path)
    assert text == "[test]\n"


def test_ini_editor_save_file_writes_text(tmp_path: Path):
    ini_path = tmp_path / "save.ini"

    ok, saved_path = ini_editor_save_file(str(ini_path), "[saved]\n")

    assert ok
    assert saved_path == str(ini_path)
    assert ini_path.read_text(encoding="utf-8") == "[saved]\n"
