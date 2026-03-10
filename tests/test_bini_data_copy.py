from __future__ import annotations

from pathlib import Path

from fl_editor.bini_data_copy import (
    copy_data_ini_to_mod_with_bini_decode,
    find_bini_ini_files_under_data,
)


def test_find_bini_ini_files_under_data_filters_bini_files(tmp_path: Path):
    data_dir = tmp_path / "DATA"
    data_dir.mkdir()
    bini_file = data_dir / "bini.ini"
    plain_file = data_dir / "plain.ini"
    bini_file.write_bytes(b"BINIraw")
    plain_file.write_text("[plain]\n", encoding="utf-8")

    result = find_bini_ini_files_under_data(
        str(tmp_path),
        ci_find_func=lambda root, name: root / name if (root / name).exists() else None,
        is_bini_file_func=lambda path: path.read_bytes().startswith(b"BINI"),
    )

    assert result == [bini_file]


def test_copy_data_ini_to_mod_with_bini_decode_copies_and_decodes(tmp_path: Path):
    vanilla_root = tmp_path / "vanilla"
    data_dir = vanilla_root / "DATA"
    data_dir.mkdir(parents=True)
    mod_root = tmp_path / "mod"
    bini_file = data_dir / "convert.ini"
    plain_file = data_dir / "plain.ini"
    bini_file.write_bytes(b"BINIraw")
    plain_file.write_text("[plain]\n", encoding="utf-8")

    ok, written, converted, error = copy_data_ini_to_mod_with_bini_decode(
        str(vanilla_root),
        str(mod_root),
        ci_find_func=lambda root, name: root / name if (root / name).exists() else None,
        decode_bini_to_ini_text=lambda raw: "[decoded]\n",
    )

    assert ok
    assert written == 2
    assert converted == 1
    assert error == ""
    assert (mod_root / "DATA" / "convert.ini").read_text(encoding="cp1252") == "[decoded]\n"
    assert (mod_root / "DATA" / "plain.ini").read_text(encoding="utf-8") == "[plain]\n"


def test_copy_data_ini_to_mod_with_bini_decode_rejects_missing_data_folder(tmp_path: Path):
    ok, written, converted, error = copy_data_ini_to_mod_with_bini_decode(
        str(tmp_path / "missing"),
        str(tmp_path / "mod"),
        ci_find_func=lambda root, name: root / name if (root / name).exists() else None,
        decode_bini_to_ini_text=lambda raw: "",
    )

    assert (ok, written, converted, error) == (False, 0, 0, "Vanilla DATA folder not found")
