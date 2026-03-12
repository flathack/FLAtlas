from __future__ import annotations

from pathlib import Path

from fl_editor.savegame_editor_integration import (
    savegame_editor_configured_path,
    savegame_editor_install_root,
    savegame_editor_installed_tag,
    savegame_editor_launch_path,
    savegame_editor_status_text,
)


def test_savegame_editor_install_root_is_derived_from_module_file():
    module_file = Path("/tmp/project/fl_editor/main_window.py")

    result = savegame_editor_install_root(module_file)

    assert result == Path("/tmp/project/tools/FLAtlas-Savegame-Editor")


def test_savegame_editor_configured_path_prefers_ui_text():
    result = savegame_editor_configured_path("/cfg/path/editor.exe", " /ui/path/editor.exe ")

    assert result == Path("/ui/path/editor.exe")


def test_savegame_editor_launch_path_requires_existing_file(tmp_path):
    exe_path = tmp_path / "editor.exe"
    exe_path.write_text("x", encoding="utf-8")

    assert savegame_editor_launch_path(exe_path) == exe_path
    assert savegame_editor_launch_path(tmp_path / "missing.exe") is None
    assert savegame_editor_launch_path(tmp_path) is None


def test_savegame_editor_installed_tag_trims_value():
    assert savegame_editor_installed_tag(" v1.2.3 ") == "v1.2.3"
    assert savegame_editor_installed_tag(None) == ""


def test_savegame_editor_status_text_uses_installed_or_configured_or_missing(tmp_path):
    exe_path = tmp_path / "editor.exe"
    exe_path.write_text("x", encoding="utf-8")

    assert savegame_editor_status_text(
        exe_path,
        "v1.0.0",
        missing_text="missing",
        configured_template="configured {path}",
        installed_template="installed {version} {path}",
    ) == f"installed v1.0.0 {exe_path}"
    assert savegame_editor_status_text(
        exe_path,
        "",
        missing_text="missing",
        configured_template="configured {path}",
        installed_template="installed {version} {path}",
    ) == f"configured {exe_path}"
    assert savegame_editor_status_text(
        None,
        "",
        missing_text="missing",
        configured_template="configured {path}",
        installed_template="installed {version} {path}",
    ) == "missing"
