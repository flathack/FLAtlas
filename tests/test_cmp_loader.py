from __future__ import annotations

from struct import pack

import pytest

from fl_editor.cmp_loader import (
    UTF_HEADER,
    build_native_model_debug_rows,
    build_native_model_info_text,
    load_native_freelancer_model,
    parse_utf_header,
)


def test_parse_utf_header_rejects_short_data():
    with pytest.raises(ValueError, match="truncated"):
        parse_utf_header(b"UTF ")


def test_load_native_freelancer_model_extracts_parts_and_vmeshes(tmp_path):
    cmp_path = tmp_path / "sample.cmp"
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "VMeshLibrary", "Part_Core", "mesh0.vms"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0),
                ("VMeshLibrary", 0x10, 0, 0, 0, 88, 0),
                ("Part_Core", 0x10, 0, 0, 0, 132, 0),
                ("mesh0.vms", 0x80, 128, 64, 64, 0, 0),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    assert mesh_data.format == "cmp"
    assert mesh_data.node_count == 4
    assert [part.name for part in mesh_data.parts] == ["Part_Core"]
    assert mesh_data.vmesh_references == ("mesh0.vms",)
    assert mesh_data.parts[0].source_name == "mesh0.vms"
    assert mesh_data.nodes[2].name == "Part_Core"
    assert mesh_data.nodes[3].is_data_node is True
    assert mesh_data.summary.data_node_count == 1


def test_load_native_freelancer_model_accepts_3db(tmp_path):
    three_db = tmp_path / "sample.3db"
    three_db.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "Part_Root"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0),
                ("Part_Root", 0x10, 0, 0, 0, 0, 0),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(three_db)

    assert mesh_data.format == "3db"
    assert mesh_data.parts[0].name == "Part_Root"


def test_build_native_model_info_text_contains_summary(tmp_path):
    cmp_path = tmp_path / "sample.cmp"
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "Part_Core", "mesh0.vms"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0),
                ("Part_Core", 0x10, 0, 0, 0, 88, 0),
                ("mesh0.vms", 0x80, 128, 64, 64, 0, 0),
            ],
        )
    )

    info = build_native_model_info_text(load_native_freelancer_model(cmp_path))

    assert "Freelancer native model detected (cmp)." in info
    assert "Detected parts: 1" in info
    assert "Referenced VMeshes: 1" in info


def test_build_native_model_debug_rows_contains_core_fields(tmp_path):
    cmp_path = tmp_path / "sample.cmp"
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "Part_Core", "mesh0.vms"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0),
                ("Part_Core", 0x10, 0, 0, 0, 88, 0),
                ("mesh0.vms", 0x80, 128, 64, 64, 0, 0),
            ],
        )
    )

    rows = dict(build_native_model_debug_rows(load_native_freelancer_model(cmp_path)))

    assert rows["File"] == str(cmp_path)
    assert rows["Format"] == "cmp"
    assert rows["Detected parts"] == "1"
    assert rows["Referenced VMeshes"] == "1"
    assert rows["Data nodes"] == "1"


def _build_fake_utf_with_nodes(
    names: list[str],
    nodes: list[tuple[str, int, int, int, int, int, int]],
) -> bytes:
    node_block_offset = UTF_HEADER.size
    node_entry_size = 44
    node_block_size = len(nodes) * node_entry_size
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
    node_block = bytearray()
    name_offsets: dict[str, int] = {}
    current = 0
    for name in names:
        name_offsets[name] = current
        current += len(name.encode("latin-1")) + 1

    for name, flags, data_off, alloc, used, peer, aux in nodes:
        lookup_name = name
        if lookup_name not in name_offsets and lookup_name == "\\" and "\\\\" in name_offsets:
            lookup_name = "\\\\"
        node_block.extend(
            pack(
                "<11I",
                aux,
                name_offsets[lookup_name],
                flags,
                0,
                peer,
                data_off,
                alloc,
                used,
                0,
                0,
                0,
            )
        )
    return header + bytes(node_block) + names_blob
