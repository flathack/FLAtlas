from __future__ import annotations

from struct import pack

import pytest

from fl_editor.cmp_loader import (
    UTF_HEADER,
    build_native_model_info_text,
    load_native_freelancer_model,
    parse_utf_header,
)


def test_parse_utf_header_rejects_short_data():
    with pytest.raises(ValueError, match="truncated"):
        parse_utf_header(b"UTF ")


def test_load_native_freelancer_model_extracts_parts_and_vmeshes(tmp_path):
    cmp_path = tmp_path / "sample.cmp"
    cmp_path.write_bytes(_build_fake_utf(names=[r"\\", "Part_Core", "mesh0.vms", "VMeshLibrary"]))

    mesh_data = load_native_freelancer_model(cmp_path)

    assert mesh_data.format == "cmp"
    assert mesh_data.node_count == 2
    assert [part.name for part in mesh_data.parts] == ["Part_Core"]
    assert mesh_data.vmesh_references == ("mesh0.vms",)


def test_load_native_freelancer_model_accepts_3db(tmp_path):
    three_db = tmp_path / "sample.3db"
    three_db.write_bytes(_build_fake_utf(names=[r"\\", "Part_Root"]))

    mesh_data = load_native_freelancer_model(three_db)

    assert mesh_data.format == "3db"
    assert mesh_data.parts[0].name == "Part_Root"


def test_build_native_model_info_text_contains_summary(tmp_path):
    cmp_path = tmp_path / "sample.cmp"
    cmp_path.write_bytes(_build_fake_utf(names=[r"\\", "Part_Core", "mesh0.vms"]))

    info = build_native_model_info_text(load_native_freelancer_model(cmp_path))

    assert "Freelancer native model detected (cmp)." in info
    assert "Detected parts: 1" in info
    assert "Referenced VMeshes: 1" in info


def _build_fake_utf(names: list[str], node_count: int = 2) -> bytes:
    node_block_offset = UTF_HEADER.size
    node_entry_size = 44
    node_block_size = node_count * node_entry_size
    names_blob = b"\x00".join(name.encode("latin-1") for name in names) + b"\x00"
    names_offset = node_block_offset + node_block_size
    data_offset = names_offset + len(names_blob)
    header = pack(
        "<4s13I",
        b"UTF ",
        257,
        node_block_offset,
        node_block_size,
        0,
        node_entry_size,
        names_offset,
        len(names_blob),
        len(names_blob),
        data_offset,
        0,
        0,
        0,
        0,
    )
    node_block = b"\x00" * node_block_size
    return header + node_block + names_blob
