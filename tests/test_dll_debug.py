from __future__ import annotations

from pathlib import Path

from fl_editor.dll_debug import build_dll_debug_lines, classify_dll_source


def test_classify_dll_source_prefers_mod_when_under_mod_root(tmp_path: Path):
    mod_root = tmp_path / "mod"
    vanilla_root = tmp_path / "vanilla"
    probe = mod_root / "EXE" / "resources.dll"
    probe.parent.mkdir(parents=True)
    probe.write_text("", encoding="utf-8")

    assert classify_dll_source(probe, mod_root=mod_root, vanilla_root=vanilla_root) == "mod"


def test_classify_dll_source_marks_vanilla_when_only_under_vanilla_root(tmp_path: Path):
    vanilla_root = tmp_path / "vanilla"
    probe = vanilla_root / "EXE" / "resources.dll"
    probe.parent.mkdir(parents=True)
    probe.write_text("", encoding="utf-8")

    assert classify_dll_source(probe, mod_root=None, vanilla_root=vanilla_root) == "vanilla"


def test_build_dll_debug_lines_formats_entries_and_empty_state(tmp_path: Path):
    ini_path = tmp_path / "EXE" / "freelancer.ini"
    resolved = tmp_path / "EXE" / "resources.dll"
    ini_path.parent.mkdir(parents=True)
    ini_path.write_text("", encoding="utf-8")
    resolved.write_text("", encoding="utf-8")

    empty_lines = build_dll_debug_lines(
        [],
        resolve_dll_path=lambda ini, dll: None,
        mod_root=None,
        vanilla_root=None,
        empty_text="Empty",
        mod_label="Mod",
        vanilla_label="Vanilla",
    )
    lines = build_dll_debug_lines(
        [(str(ini_path), "resources.dll")],
        resolve_dll_path=lambda ini, dll: resolved,
        mod_root=tmp_path,
        vanilla_root=None,
        empty_text="Empty",
        mod_label="Mod",
        vanilla_label="Vanilla",
    )

    assert empty_lines == ["Empty"]
    assert lines == [
        "[01] resources.dll",
        "     source: Mod",
        f"     ini:    {ini_path}",
        f"     file:   {resolved}",
    ]
