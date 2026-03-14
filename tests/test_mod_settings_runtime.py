from __future__ import annotations

import struct

import pytest

from fl_editor.mod_settings_runtime import (
    ExeOffsetSpec,
    format_exe_offset_value,
    parse_exe_offset_value,
    read_exe_offset_value,
    resolve_exe_offset,
    write_exe_offset_value,
)


def test_read_and_write_float32_offset(tmp_path):
    exe_path = tmp_path / "Freelancer.exe"
    raw = bytearray(b"\x00" * 64)
    struct.pack_into("<f", raw, 16, 2500.0)
    exe_path.write_bytes(raw)
    spec = ExeOffsetSpec(
        key="test",
        label_key="label",
        note_key="note",
        exe_name="Freelancer.exe",
        offset=16,
        value_type="float32",
        default_value=2500.0,
    )

    assert read_exe_offset_value(exe_path, spec) == pytest.approx(2500.0)

    write_exe_offset_value(exe_path, spec, 3333.5)

    assert read_exe_offset_value(exe_path, spec) == pytest.approx(3333.5)
    assert format_exe_offset_value(read_exe_offset_value(exe_path, spec), spec) == "3333.5"


def test_parse_float32_offset_value_accepts_decimal_comma():
    spec = ExeOffsetSpec(
        key="test",
        label_key="label",
        note_key="note",
        exe_name="Freelancer.exe",
        offset=0,
        value_type="float32",
        default_value=0.0,
    )

    assert parse_exe_offset_value("2500,25", spec) == pytest.approx(2500.25)


def test_read_offset_raises_for_out_of_range(tmp_path):
    exe_path = tmp_path / "Freelancer.exe"
    exe_path.write_bytes(b"\x00" * 4)
    spec = ExeOffsetSpec(
        key="test",
        label_key="label",
        note_key="note",
        exe_name="Freelancer.exe",
        offset=8,
        value_type="float32",
        default_value=0.0,
    )

    with pytest.raises(ValueError):
        read_exe_offset_value(exe_path, spec)


def test_resolve_offset_prefers_anchor_bytes(tmp_path):
    exe_path = tmp_path / "Freelancer.exe"
    raw = bytearray(b"\x00" * 64)
    struct.pack_into("<f", raw, 12, 2500.0)
    raw[16:27] = b"HpLeftLane\x00"
    exe_path.write_bytes(raw)
    spec = ExeOffsetSpec(
        key="test",
        label_key="label",
        note_key="note",
        exe_name="Freelancer.exe",
        offset=32,
        value_type="float32",
        default_value=2500.0,
        anchor_bytes=b"HpLeftLane\x00",
        anchor_relative_offset=-4,
    )

    assert resolve_exe_offset(exe_path, spec) == 12
    assert read_exe_offset_value(exe_path, spec) == pytest.approx(2500.0)
