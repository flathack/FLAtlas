from __future__ import annotations

from pathlib import Path

from fl_editor.main_window import MainWindow


def test_mod_manager_collect_flmm_payload_files_skips_xml(tmp_path: Path):
    source = tmp_path / "flmm_mod"
    source.mkdir()
    (source / "script.xml").write_text("<mod/>", encoding="utf-8")
    (source / "readme.xml").write_text("<meta/>", encoding="utf-8")
    data_dir = source / "DATA" / "SHIPS"
    data_dir.mkdir(parents=True)
    ini_path = data_dir / "shiparch.ini"
    ini_path.write_text("[Ship]\n", encoding="utf-8")

    files = MainWindow._mod_manager_collect_flmm_payload_files(source)

    assert files == [ini_path]
