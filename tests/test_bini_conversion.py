from __future__ import annotations

from pathlib import Path

from fl_editor.bini_conversion import convert_bini_in_folder_in_place


def test_convert_bini_in_folder_in_place_converts_and_skips_requested_paths(tmp_path: Path):
    data_dir = tmp_path / "DATA"
    data_dir.mkdir()
    convert_me = data_dir / "convert.ini"
    skip_me = data_dir / "skip.ini"
    plain_ini = data_dir / "plain.ini"
    convert_me.write_bytes(b"BINIbinary")
    skip_me.write_bytes(b"BINIbinary")
    plain_ini.write_text("[plain]\n", encoding="utf-8")

    ok, scanned, converted, warning = convert_bini_in_folder_in_place(
        str(tmp_path),
        decode_bini_to_ini_text=lambda raw: "[decoded]\n",
        skip_rel_paths={"DATA/skip.ini"},
    )

    assert ok
    assert scanned == 3
    assert converted == 1
    assert warning == ""
    assert convert_me.read_text(encoding="cp1252") == "[decoded]\n"
    assert skip_me.read_bytes() == b"BINIbinary"


def test_convert_bini_in_folder_in_place_collects_warnings_and_pumps_ui(tmp_path: Path):
    data_dir = tmp_path / "DATA"
    data_dir.mkdir()
    for idx in range(40):
        (data_dir / f"file_{idx}.ini").write_text("[plain]\n", encoding="utf-8")
    broken = data_dir / "broken.ini"
    broken.write_bytes(b"BINIbroken")
    calls: list[str] = []

    ok, scanned, converted, warning = convert_bini_in_folder_in_place(
        str(tmp_path),
        decode_bini_to_ini_text=lambda raw: (_ for _ in ()).throw(ValueError("decode failed")),
        pump_ui=lambda message: calls.append(message),
        loading_message="loading",
    )

    assert ok
    assert scanned == 41
    assert converted == 0
    assert "decode failed" in warning
    assert calls == ["loading"]


def test_convert_bini_in_folder_in_place_rejects_missing_folder(tmp_path: Path):
    ok, scanned, converted, warning = convert_bini_in_folder_in_place(
        str(tmp_path / "missing"),
        decode_bini_to_ini_text=lambda raw: "",
    )

    assert (ok, scanned, converted, warning) == (False, 0, 0, "Folder not found")


def test_convert_bini_in_folder_in_place_can_limit_scan_to_included_paths(tmp_path: Path):
    data_dir = tmp_path / "DATA"
    data_dir.mkdir()
    convert_me = data_dir / "convert.ini"
    untouched = data_dir / "untouched.ini"
    convert_me.write_bytes(b"BINIbinary")
    untouched.write_bytes(b"BINIbinary")

    ok, scanned, converted, warning = convert_bini_in_folder_in_place(
        str(tmp_path),
        decode_bini_to_ini_text=lambda raw: "[decoded]\n",
        include_rel_paths={"DATA/convert.ini"},
    )

    assert ok
    assert scanned == 1
    assert converted == 1
    assert warning == ""
    assert convert_me.read_text(encoding="cp1252") == "[decoded]\n"
    assert untouched.read_bytes() == b"BINIbinary"
