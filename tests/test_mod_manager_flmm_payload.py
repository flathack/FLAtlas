from __future__ import annotations

from pathlib import Path

import pytest

from fl_editor import config as config_module
from fl_editor.main_window import MainWindow


@pytest.fixture
def main_window(monkeypatch, qapp, tmp_path):
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "config.json")
    window = MainWindow()
    yield window
    window.close()


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


def test_mod_manager_collect_flmm_activation_files_includes_payload_and_skips_sourcefile_only_variants(
    main_window: MainWindow,
    monkeypatch,
    tmp_path: Path,
):
    source = tmp_path / "flmm_mod"
    source.mkdir()
    (source / "script.xml").write_text("<mod/>", encoding="utf-8")

    freelancer_ini = source / "EXE" / "freelancer.ini"
    freelancer_ini.parent.mkdir(parents=True)
    freelancer_ini.write_text("[Resources]\ndll = base_mod.dll\n", encoding="utf-8")

    referenced_target = source / "DATA" / "SHIPS" / "loadouts_special.ini"
    referenced_target.parent.mkdir(parents=True)
    referenced_target.write_text("[Loadout]\nnickname = test\n", encoding="utf-8")

    source_variant = source / "variants" / "universe_alt.ini"
    source_variant.parent.mkdir(parents=True)
    source_variant.write_text("[System]\nnickname = alt\n", encoding="utf-8")

    monkeypatch.setattr(
        main_window,
        "_flmm_collect_script_spec",
        lambda _source: (
            True,
            {
                "operations": [
                    {"file": "DATA/SHIPS/loadouts_special.ini", "method": "append"},
                    {
                        "file": "DATA/UNIVERSE/universe.ini",
                        "method": "copyfile",
                        "sourcefile": "variants/universe_alt.ini",
                    },
                ]
            },
            "",
        ),
    )

    files = main_window._mod_manager_collect_flmm_activation_files(source)
    rels = {path.relative_to(source).as_posix() for path in files}

    assert "EXE/freelancer.ini" in rels
    assert "DATA/SHIPS/loadouts_special.ini" in rels
    assert "variants/universe_alt.ini" not in rels
    assert "script.xml" not in rels
