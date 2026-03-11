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
            names=[r"\\", "VMeshLibrary", "Part_Core", "File name", "Object name", "mesh0.vms"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("VMeshLibrary", 0x10, 0, 0, 0, 88, 0, None),
                ("Part_Core", 0x10, 0, 0, 0, 132, 0, None),
                ("File name", 0x80, 0, 11, 11, 176, 0, "mesh0.vms"),
                ("Object name", 0x80, 0, 10, 10, 220, 0, "core_mesh"),
                ("mesh0.vms", 0x80, 128, 64, 64, 264, 0, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob()),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    assert mesh_data.format == "cmp"
    assert mesh_data.node_count == 7
    assert [part.name for part in mesh_data.parts] == ["Part_Core"]
    assert mesh_data.vmesh_references == ("mesh0.vms",)
    assert mesh_data.parts[0].source_name == "mesh0.vms"
    assert mesh_data.parts[0].file_name == "mesh0.vms"
    assert mesh_data.parts[0].object_name == "core_mesh"
    assert mesh_data.nodes[2].name == "Part_Core"
    assert mesh_data.nodes[3].name == "File name"
    assert mesh_data.nodes[2].parent_name == "VMeshLibrary"
    assert mesh_data.nodes[3].parent_name == "Part_Core"
    assert mesh_data.nodes[3].path == r"\/VMeshLibrary/Part_Core/File name"
    assert mesh_data.summary.data_node_count == 4
    assert mesh_data.bounds is not None
    assert mesh_data.bounds.min_xyz == (-5.0, -3.0, -2.0)
    assert mesh_data.bounds.max_xyz == (5.0, 3.0, 2.0)


def test_load_native_freelancer_model_accepts_3db(tmp_path):
    three_db = tmp_path / "sample.3db"
    three_db.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "Part_Root"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("Part_Root", 0x10, 0, 0, 0, 0, 0, None),
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
            names=[r"\\", "Part_Core", "File name", "mesh0.vms"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("Part_Core", 0x10, 0, 0, 0, 88, 0, None),
                ("File name", 0x80, 0, 11, 11, 132, 0, "mesh0.vms"),
                ("mesh0.vms", 0x80, 128, 64, 64, 176, 0, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob()),
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
            names=[r"\\", "Part_Core", "File name", "mesh0.vms"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("Part_Core", 0x10, 0, 0, 0, 88, 0, None),
                ("File name", 0x80, 0, 11, 11, 132, 0, "mesh0.vms"),
                ("mesh0.vms", 0x80, 128, 64, 64, 176, 0, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob()),
            ],
        )
    )

    rows = dict(build_native_model_debug_rows(load_native_freelancer_model(cmp_path)))

    assert rows["File"] == str(cmp_path)
    assert rows["Format"] == "cmp"
    assert rows["Detected parts"] == "1"
    assert rows["Referenced VMeshes"] == "1"
    assert rows["Model nodes"] == "1"
    assert rows["Data nodes"] == "3"
    assert rows["Has bounds"] == "yes"


def test_load_native_freelancer_model_extracts_vmesh_data_and_model_context(tmp_path):
    cmp_path = tmp_path / "context.cmp"
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "VMeshLibrary", "mesh0.vms", "VMeshData", "mesh0.3db", "MultiLevel", "Level0", "VMeshPart", "VMeshRef"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("VMeshLibrary", 0x10, 0, 0, 0, 88, 176, None),
                ("mesh0.vms", 0x10, 0, 0, 0, 132, 0, None),
                ("VMeshData", 0x80, 0, 16, 16, 0, 0, b"0123456789abcdef"),
                ("mesh0.3db", 0x10, 0, 0, 0, 220, 0, None),
                ("MultiLevel", 0x10, 0, 0, 0, 264, 0, None),
                ("Level0", 0x10, 0, 0, 0, 308, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 352, 0, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob()),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    assert len(mesh_data.vmesh_data_blocks) == 1
    assert mesh_data.vmesh_data_blocks[0].source_name == "mesh0.vms"
    assert mesh_data.vmesh_refs[0].model_name == "mesh0.3db"
    assert mesh_data.vmesh_refs[0].level_name == "Level0"
    assert mesh_data.model_nodes[0].model_name == "mesh0.3db"
    assert mesh_data.model_nodes[0].level_names == ("Level0",)
    assert mesh_data.model_nodes[0].vmesh_ref_count == 1
    assert mesh_data.model_nodes[0].bounds is not None
    assert mesh_data.model_nodes[0].bounds.radius == pytest.approx(6.5)


def test_model_nodes_include_part_sources_and_bounds(tmp_path):
    cmp_path = tmp_path / "sample.cmp"
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "ship_lod0.3db", "MultiLevel", "Level0", "VMeshPart", "Part_ship_lod0", "File name", "mesh0.vms", "VMeshRef"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("ship_lod0.3db", 0x10, 0, 0, 0, 88, 0, None),
                ("MultiLevel", 0x10, 0, 0, 0, 132, 0, None),
                ("Level0", 0x10, 0, 0, 0, 176, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 220, 264, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob()),
                ("Part_ship_lod0", 0x10, 0, 0, 0, 308, 0, None),
                ("File name", 0x80, 0, 11, 11, 0, 0, "mesh0.vms"),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    assert len(mesh_data.model_nodes) == 1
    model_node = mesh_data.model_nodes[0]
    assert model_node.model_name == "ship_lod0.3db"
    assert model_node.matched_part_name == "Part_ship_lod0"
    assert model_node.source_names == ("mesh0.vms",)
    assert model_node.bounds is not None
    assert model_node.bounds.min_xyz == (-5.0, -3.0, -2.0)


def _build_fake_utf_with_nodes(
    names: list[str],
    nodes: list[tuple[str, int, int, int, int, int, int, str | bytes | None]],
) -> bytes:
    for name, *_ in nodes:
        if name not in names:
            names.append(name)
    node_block_offset = UTF_HEADER.size
    node_entry_size = 44
    node_block_size = len(nodes) * node_entry_size
    names_blob = b"\x00".join(name.encode("latin-1") for name in names) + b"\x00"
    names_offset = node_block_offset + node_block_size
    data_offset = names_offset + len(names_blob)
    data_chunks: list[bytes] = []
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

    for name, flags, data_off, alloc, used, peer, aux, text_data in nodes:
        actual_data_off = data_off
        actual_alloc = alloc
        actual_used = used
        if text_data is not None:
            if isinstance(text_data, bytes):
                encoded = text_data
            else:
                encoded = text_data.encode("latin-1") + b"\x00"
            actual_data_off = data_offset + sum(len(chunk) for chunk in data_chunks)
            actual_alloc = len(encoded)
            actual_used = len(encoded)
            data_chunks.append(encoded)
        lookup_name = name
        if lookup_name not in name_offsets and lookup_name == "\\" and "\\\\" in name_offsets:
            lookup_name = "\\\\"
        entry_or_peer = actual_data_off if (flags & 0x80) else peer
        entry_alloc = actual_alloc if (flags & 0x80) else actual_data_off
        entry_used = actual_used if (flags & 0x80) else actual_alloc
        node_block.extend(
            pack(
                "<11I",
                aux,
                name_offsets[lookup_name],
                flags,
                0,
                entry_or_peer,
                entry_alloc,
                entry_used,
                0,
                0,
                0,
                0,
            )
        )
    return header + bytes(node_block) + names_blob + b"".join(data_chunks)


def _build_vmesh_ref_blob() -> bytes:
    return pack(
        "<IIHHHHHH10f",
        60,
        0x12345678,
        0,
        10,
        0,
        18,
        0,
        1,
        5.0,
        -5.0,
        3.0,
        -3.0,
        2.0,
        -2.0,
        0.0,
        0.0,
        0.0,
        6.5,
    )
