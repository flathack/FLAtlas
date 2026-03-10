from __future__ import annotations

from pathlib import Path

from fl_editor.zone_link_persistence import persist_zone_link_file


def test_persist_zone_link_file_writes_when_visible_and_path_present(tmp_path: Path):
    target = tmp_path / "zone.ini"

    written = persist_zone_link_file(target, visible=True, text="[Zone]\nnickname = zone_a\n")

    assert written is True
    assert target.read_text(encoding="utf-8") == "[Zone]\nnickname = zone_a\n"


def test_persist_zone_link_file_skips_when_hidden(tmp_path: Path):
    target = tmp_path / "zone.ini"

    written = persist_zone_link_file(target, visible=False, text="ignored")

    assert written is False
    assert not target.exists()
