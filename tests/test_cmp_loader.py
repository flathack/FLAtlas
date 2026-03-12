from __future__ import annotations

from struct import pack, pack_into, unpack_from

import pytest

from fl_editor.cmp_loader import (
    UTF_HEADER,
    _freelancer_model_crc,
    _normalize_model_key,
    _vms_stride_hint_from_source_name,
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
    assert mesh_data.parts[0].cmp_index is None
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


def test_load_native_freelancer_model_accepts_relative_utf_data_offsets(tmp_path):
    cmp_path = tmp_path / "relative_offsets.cmp"
    raw = bytearray(
        _build_fake_utf_with_nodes(
            names=[r"\\", "Part_Core", "File name", "Object name"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("Part_Core", 0x10, 0, 0, 0, 88, 0, None),
                ("File name", 0x80, 0, 11, 11, 132, 0, "mesh0.vms"),
                ("Object name", 0x80, 0, 10, 10, 176, 0, "core_mesh"),
            ],
        )
    )
    header = unpack_from("<4s13I", raw, 0)
    node_block_offset = header[2]
    node_entry_size = header[5]
    data_offset_base = header[9]
    for node_index in (2, 3):
        base = node_block_offset + (node_index * node_entry_size)
        stored_offset = unpack_from("<I", raw, base + 16)[0]
        pack_into("<I", raw, base + 16, stored_offset - data_offset_base)
    cmp_path.write_bytes(bytes(raw))

    mesh_data = load_native_freelancer_model(cmp_path)

    assert mesh_data.parts[0].file_name == "mesh0.vms"
    assert mesh_data.parts[0].object_name == "core_mesh"


def test_normalize_model_key_handles_real_freelancer_lod_suffix_noise():
    assert _normalize_model_key("rings_lod1021001100449.3db") == "rings_lod1"
    assert _normalize_model_key("jump_gate_lod1021001100449.3db") == "jump_gate_lod1"
    assert _normalize_model_key("station_lod10.3db") == "station_lod10"


def test_vms_stride_hint_from_source_name_reads_real_suffix():
    assert _vms_stride_hint_from_source_name("data.solar.dockable.jump_gatel.lod0-112.vms") == 112
    assert _vms_stride_hint_from_source_name("data.solar.dockable.jump_gatel.lod2-212.vms") == 212
    assert _vms_stride_hint_from_source_name("mesh0.vms") is None


def test_freelancer_model_crc_matches_real_jumpgate_references():
    assert _freelancer_model_crc("data.solar.dockable.jump_gatel.lod0-112.vms") == 22204841
    assert _freelancer_model_crc("data.solar.dockable.jump_gatel.lod1-112.vms") == 3961727117
    assert _freelancer_model_crc("data.solar.dockable.jump_gatel.lod2-212.vms") == 4089362221
    assert _freelancer_model_crc("data.solar.dockable.jump_gatel.lod2-112.vms") == 4084736050
    assert _freelancer_model_crc("data.solar.dockable.jump_gatel.lod3-212.vms") == 516902409
    assert _freelancer_model_crc("data.solar.dockable.jump_gatel.lod4-212.vms") == 153558879


def test_load_native_freelancer_model_extracts_material_references(tmp_path):
    cmp_path = tmp_path / "materials.cmp"
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "Texture library", "diffuse.dds", "Material library", "ship.mat", "Texture name"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("Texture library", 0x10, 0, 0, 0, 88, 0, None),
                ("diffuse.dds", 0x10, 0, 0, 0, 132, 0, None),
                ("Material library", 0x10, 0, 0, 0, 176, 0, None),
                ("ship.mat", 0x10, 0, 0, 0, 220, 0, None),
                ("Texture name", 0x80, 0, 12, 12, 264, 0, "normal.tga"),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    assert [ref.value for ref in mesh_data.material_references] == [
        "diffuse.dds",
        "ship.mat",
        "normal.tga",
    ]
    assert [ref.kind for ref in mesh_data.material_references] == [
        "texture",
        "material",
        "texture",
    ]


def test_load_native_freelancer_model_builds_preview_material_bindings(tmp_path):
    cmp_path = tmp_path / "material_binding.cmp"
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[
                r"\\",
                "li_fighter.3db",
                "MultiLevel",
                "Level0",
                "VMeshPart",
                "VMeshRef",
                "fighter_diffuse.dds",
                "VMeshLibrary",
                "mesh0.vms",
                "VMeshData",
            ],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("li_fighter.3db", 0x10, 0, 0, 0, 88, 0, None),
                ("MultiLevel", 0x10, 0, 0, 0, 132, 0, None),
                ("Level0", 0x10, 0, 0, 0, 176, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 220, 0, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob()),
                ("fighter_diffuse.dds", 0x10, 0, 0, 0, 308, 0, None),
                ("VMeshLibrary", 0x10, 0, 0, 0, 352, 440, None),
                ("mesh0.vms", 0x10, 0, 0, 0, 396, 0, None),
                ("VMeshData", 0x80, 0, 16, 16, 0, 0, b"0123456789abcdef"),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    assert len(mesh_data.preview_material_bindings) == 1
    binding = mesh_data.preview_material_bindings[0]
    assert binding.model_name == "li_fighter.3db"
    assert binding.level_name == "Level0"
    assert binding.group_start == 0
    assert binding.group_count == 1
    assert binding.texture_value == "fighter_diffuse.dds"
    assert binding.texture_candidates == ("fighter_diffuse.dds",)
    assert len(mesh_data.preview_material_groups) == 1
    group = mesh_data.preview_material_groups[0]
    assert group.texture_value == "fighter_diffuse.dds"
    assert group.texture_candidates == ("fighter_diffuse.dds",)
    assert group.binding_count == 1
    assert group.group_ranges == ((0, 1),)


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
    assert rows["Resolved preview sources"] == "0/1"
    assert rows["Preview buffer slices"] == "0"
    assert rows["No-fit layouts"] == "0"
    assert rows["Structured VMeshData blocks"] == "0/0"
    assert rows["Vertex-stream VMeshData blocks"] == "0/0"
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
    assert mesh_data.vmesh_data_blocks[0].header_hex.startswith("30313233")
    assert mesh_data.vmesh_data_blocks[0].header_u32
    assert mesh_data.vmesh_data_blocks[0].header_u16
    assert mesh_data.vmesh_data_blocks[0].header_hint is not None
    assert mesh_data.vmesh_data_blocks[0].header_hint.structure_kind == "unknown"
    assert len(mesh_data.vmesh_data_blocks[0].sha1) == 40
    assert mesh_data.vmesh_refs[0].model_name == "mesh0.3db"
    assert mesh_data.vmesh_refs[0].level_name == "Level0"
    assert mesh_data.model_nodes[0].model_name == "mesh0.3db"
    assert mesh_data.model_nodes[0].level_names == ("Level0",)
    assert mesh_data.model_nodes[0].vmesh_ref_count == 1
    assert mesh_data.model_nodes[0].bounds is not None
    assert mesh_data.model_nodes[0].bounds.radius == pytest.approx(6.5)
    assert len(mesh_data.preview_nodes) == 1
    assert mesh_data.preview_nodes[0].vmesh_data_block_count == 1
    assert mesh_data.preview_nodes[0].total_vmesh_data_bytes == 16
    assert len(mesh_data.preview_mesh_bindings) == 1
    assert mesh_data.preview_mesh_bindings[0].level_name == "Level0"
    assert mesh_data.preview_mesh_bindings[0].vertex_count == 10
    assert mesh_data.preview_mesh_bindings[0].index_count == 18
    assert mesh_data.preview_mesh_bindings[0].triangle_count == 6
    assert len(mesh_data.preview_geometry_candidates) == 1
    assert mesh_data.preview_geometry_candidates[0].decode_stage == "single-block-header"
    assert mesh_data.preview_geometry_candidates[0].ready_for_native_render is True
    assert len(mesh_data.preview_submeshes) == 1
    assert mesh_data.preview_submeshes[0].vertex_start == 0
    assert mesh_data.preview_submeshes[0].vertex_count == 10
    assert mesh_data.preview_submeshes[0].index_start == 0
    assert mesh_data.preview_submeshes[0].index_count == 18
    assert len(mesh_data.preview_geometry_sources) == 1
    assert mesh_data.preview_geometry_sources[0].resolved is True
    assert mesh_data.preview_geometry_sources[0].resolution_hint == "single-block-fallback"
    assert mesh_data.preview_geometry_sources[0].matched_block_index == 0
    assert len(mesh_data.preview_layout_guesses) == 1
    assert mesh_data.preview_layout_guesses[0].confidence == "no-fit"
    assert mesh_data.preview_buffer_slices == ()


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
    assert mesh_data.preview_nodes[0].matched_part_name == "Part_ship_lod0"
    assert mesh_data.preview_nodes[0].source_names == ("mesh0.vms",)


def test_load_native_freelancer_model_reads_part_metadata_from_cmpnd_children(tmp_path):
    cmp_path = tmp_path / "cmpnd_parts.cmp"
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "Cmpnd", "Part_ship_lod1", "File name", "Object name", "Index"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("Cmpnd", 0x10, 0, 0, 0, 88, 132, None),
                ("Part_ship_lod1", 0x10, 0, 0, 0, 0, 176, None),
                ("File name", 0x80, 0, 10, 10, 220, 0, "mesh0.vms"),
                ("Object name", 0x80, 0, 10, 10, 264, 0, "ship_root"),
                ("Index", 0x80, 0, 4, 4, 0, 0, pack("<I", 7)),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    assert len(mesh_data.parts) == 1
    assert mesh_data.parts[0].name == "Part_ship_lod1"
    assert mesh_data.parts[0].file_name == "mesh0.vms"
    assert mesh_data.parts[0].object_name == "ship_root"
    assert mesh_data.parts[0].cmp_index == 7


def test_preview_nodes_track_matched_vmesh_blocks(tmp_path):
    cmp_path = tmp_path / "preview.cmp"
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "ship_lod0.3db", "MultiLevel", "Level0", "VMeshPart", "VMeshRef", "mesh0.vms", "VMeshLibrary", "Part_ship_lod0", "File name", "VMeshData"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("ship_lod0.3db", 0x10, 0, 0, 0, 88, 0, None),
                ("MultiLevel", 0x10, 0, 0, 0, 132, 0, None),
                ("Level0", 0x10, 0, 0, 0, 176, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 220, 264, None),
                ("VMeshRef", 0x80, 0, 60, 60, 308, 0, _build_vmesh_ref_blob()),
                ("VMeshLibrary", 0x10, 0, 0, 0, 352, 440, None),
                ("mesh0.vms", 0x10, 0, 0, 0, 396, 0, None),
                ("VMeshData", 0x80, 0, 24, 24, 0, 0, b"0123456789abcdefghijklmn"),
                ("Part_ship_lod0", 0x10, 0, 0, 0, 0, 0, None),
                ("File name", 0x80, 0, 11, 11, 0, 0, "mesh0.vms"),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    assert len(mesh_data.preview_nodes) == 1
    preview = mesh_data.preview_nodes[0]
    assert preview.vmesh_data_block_count == 1
    assert preview.total_vmesh_data_bytes == 24
    assert mesh_data.vmesh_data_blocks[0].header_hex.startswith("30313233")
    binding = mesh_data.preview_mesh_bindings[0]
    assert binding.group_count == 1
    assert binding.vmesh_data_block_count == 1
    assert binding.total_vmesh_data_bytes == 24
    candidate = mesh_data.preview_geometry_candidates[0]
    assert candidate.block_sha1s == (mesh_data.vmesh_data_blocks[0].sha1,)
    assert candidate.total_vmesh_data_bytes == 24
    assert candidate.decode_stage == "single-block-header"
    assert mesh_data.preview_submeshes[0].triangle_count == 6
    assert mesh_data.preview_submeshes[0].group_count == 1
    assert mesh_data.preview_geometry_sources[0].triangle_count == 6


def test_preview_layout_guess_detects_exact_fit(tmp_path):
    cmp_path = tmp_path / "layout.cmp"
    block = (b"H" * 16) + (b"V" * (10 * 12)) + (b"I" * (18 * 2))
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "VMeshLibrary", "mesh0.vms", "VMeshData", "mesh0.3db", "MultiLevel", "Level0", "VMeshPart", "VMeshRef"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("VMeshLibrary", 0x10, 0, 0, 0, 88, 176, None),
                ("mesh0.vms", 0x10, 0, 0, 0, 132, 0, None),
                ("VMeshData", 0x80, 0, len(block), len(block), 0, 0, block),
                ("mesh0.3db", 0x10, 0, 0, 0, 220, 0, None),
                ("MultiLevel", 0x10, 0, 0, 0, 264, 0, None),
                ("Level0", 0x10, 0, 0, 0, 308, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 352, 0, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob()),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    guess = mesh_data.preview_layout_guesses[0]
    assert guess.confidence == "exact"


def test_preview_layout_guess_prefers_vms_stride_hint(tmp_path):
    cmp_path = tmp_path / "layout_hint.cmp"
    block = (b"H" * 128) + (b"V" * (3 * 112)) + (b"I" * (3 * 2))
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "VMeshLibrary", "ship_lod0-112.vms", "VMeshData", "mesh0.3db", "MultiLevel", "Level0", "VMeshPart", "Part_mesh0", "File name", "VMeshRef"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("VMeshLibrary", 0x10, 0, 0, 0, 88, 176, None),
                ("ship_lod0-112.vms", 0x10, 0, 0, 0, 132, 0, None),
                ("VMeshData", 0x80, 0, len(block), len(block), 0, 0, block),
                ("mesh0.3db", 0x10, 0, 0, 0, 220, 0, None),
                ("MultiLevel", 0x10, 0, 0, 0, 264, 0, None),
                ("Level0", 0x10, 0, 0, 0, 308, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 352, 396, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=0, vertex_count=3, index_count=3, group_count=1)),
                ("Part_mesh0", 0x10, 0, 0, 0, 0, 0, None),
                ("File name", 0x80, 0, 18, 18, 0, 0, "ship_lod0-112.vms"),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    guess = mesh_data.preview_layout_guesses[0]
    assert guess.confidence == "exact"
    assert guess.header_size == 128
    assert guess.vertex_stride == 112


def test_load_native_freelancer_model_classifies_vmesh_data_blocks(tmp_path):
    cmp_path = tmp_path / "vmesh_block_hints.cmp"
    structured_block = pack("<IIIHH", 1, 4, 0x00C00004, 530, 146) + (b"\x00" * 20)
    stream_block = pack("<4f", 1.0, -2.5, 3.25, 0.5) + (b"\x00" * 16)
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "VMeshLibrary", "ship_lod4-212.vms", "ship_lod4-112.vms", "VMeshData"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("VMeshLibrary", 0x10, 0, 0, 0, 88, 132, None),
                ("ship_lod4-212.vms", 0x10, 0, 0, 0, 132, 176, None),
                ("VMeshData", 0x80, 0, len(structured_block), len(structured_block), 0, 0, structured_block),
                ("ship_lod4-112.vms", 0x10, 0, 0, 0, 220, 264, None),
                ("VMeshData", 0x80, 0, len(stream_block), len(stream_block), 0, 0, stream_block),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    assert len(mesh_data.vmesh_data_blocks) == 2
    structured_hint = mesh_data.vmesh_data_blocks[0].header_hint
    stream_hint = mesh_data.vmesh_data_blocks[1].header_hint
    assert structured_hint is not None
    assert structured_hint.structure_kind == "structured-header"
    assert structured_hint.mesh_count_hint == 1
    assert structured_hint.referenced_vertex_count_hint == 4
    assert structured_hint.flexible_vertex_format_hint == 0x00C00004
    assert structured_hint.vertex_count_hint == 530
    assert structured_hint.triangle_count_hint == 146
    assert stream_hint is not None
    assert stream_hint.structure_kind == "vertex-stream"
    assert (
        "VMeshData blocks show mixed structured-header and vertex-stream patterns; real Freelancer decode likely needs paired stream handling"
        in mesh_data.warnings
    )
    rows = dict(build_native_model_debug_rows(mesh_data))
    assert rows["Structured VMeshData blocks"] == "1/2"
    assert rows["Vertex-stream VMeshData blocks"] == "1/2"


def test_load_native_freelancer_model_reports_unresolved_preview_geometry_warning(tmp_path):
    cmp_path = tmp_path / "unresolved_preview.cmp"
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "mesh0.3db", "MultiLevel", "Level0", "VMeshPart", "VMeshRef", "VMeshLibrary", "mesh0.vms", "mesh1.vms", "VMeshData"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("mesh0.3db", 0x10, 0, 0, 0, 88, 0, None),
                ("MultiLevel", 0x10, 0, 0, 0, 132, 0, None),
                ("Level0", 0x10, 0, 0, 0, 176, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 220, 264, None),
                ("VMeshRef", 0x80, 0, 60, 60, 308, 0, _build_vmesh_ref_blob(mesh_data_reference=99)),
                ("VMeshLibrary", 0x10, 0, 0, 0, 352, 440, None),
                ("mesh0.vms", 0x10, 0, 0, 0, 396, 0, None),
                ("VMeshData", 0x80, 0, 24, 24, 484, 0, b"0123456789abcdefghijklmn"),
                ("mesh1.vms", 0x10, 0, 0, 0, 0, 0, None),
                ("VMeshData", 0x80, 0, 24, 24, 0, 0, b"abcdefghijklmnopqrstuvwx"),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    assert "No preview geometry reference could be resolved to a VMeshData block" in mesh_data.warnings


def test_load_native_freelancer_model_resolves_vmesh_data_by_freelancer_crc(tmp_path):
    cmp_path = tmp_path / "crc_resolve.cmp"
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "VMeshLibrary", "data.solar.dockable.jump_gatel.lod4-212.vms", "data.solar.dockable.jump_gatel.lod0-112.vms", "VMeshData", "mesh0.3db", "MultiLevel", "Level0", "VMeshPart", "VMeshRef"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("VMeshLibrary", 0x10, 0, 0, 0, 88, 176, None),
                ("data.solar.dockable.jump_gatel.lod4-212.vms", 0x10, 0, 0, 0, 132, 176, None),
                ("VMeshData", 0x80, 0, 24, 24, 0, 0, b"0123456789abcdefghijklmn"),
                ("data.solar.dockable.jump_gatel.lod0-112.vms", 0x10, 0, 0, 0, 220, 264, None),
                ("VMeshData", 0x80, 0, 24, 24, 0, 0, b"abcdefghijklmnopqrstuvwx"),
                ("mesh0.3db", 0x10, 0, 0, 0, 220, 0, None),
                ("MultiLevel", 0x10, 0, 0, 0, 264, 0, None),
                ("Level0", 0x10, 0, 0, 0, 308, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 352, 0, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=153558879)),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    assert len(mesh_data.preview_geometry_sources) == 1
    source = mesh_data.preview_geometry_sources[0]
    assert source.resolved is True
    assert source.matched_block_index == 0
    assert source.resolution_hint == "flcrc-source-match"


def test_load_native_freelancer_model_reports_no_fit_layout_warning(tmp_path):
    cmp_path = tmp_path / "no_fit_layout.cmp"
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

    guess = mesh_data.preview_layout_guesses[0]
    assert "All resolved preview geometry layouts failed the current buffer-fit heuristics" in mesh_data.warnings
    assert guess.confidence == "no-fit"
    assert guess.header_size is None
    assert guess.vertex_stride is None
    assert guess.index_size is None
    assert mesh_data.preview_buffer_slices == ()


def test_load_native_freelancer_model_extracts_cmp_fix_records(tmp_path):
    cmp_path = tmp_path / "fix_records.cmp"
    fix_blob = pack("<88f", *[float(index) for index in range(88)])
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "Cmpnd", "Part_Core", "Part_Wing", "Cons", "Fix", "Index"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("Cmpnd", 0x10, 0, 0, 0, 88, 220, None),
                ("Part_Core", 0x10, 0, 0, 0, 132, 176, None),
                ("Index", 0x80, 0, 4, 4, 220, 0, pack("<I", 1)),
                ("Part_Wing", 0x10, 0, 0, 0, 264, 308, None),
                ("Index", 0x80, 0, 4, 4, 0, 0, pack("<I", 0)),
                ("Cons", 0x10, 0, 0, 0, 352, 396, None),
                ("Fix", 0x80, 0, len(fix_blob), len(fix_blob), 0, 0, fix_blob),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    assert len(mesh_data.cmp_fix_records) == 2
    assert mesh_data.parts[0].cmp_index == 1
    assert mesh_data.parts[1].cmp_index == 0
    assert mesh_data.cmp_fix_records[0].part_name == "Part_Wing"
    assert mesh_data.cmp_fix_records[0].part_index == 0
    assert mesh_data.cmp_fix_records[1].part_name == "Part_Core"
    assert mesh_data.cmp_fix_records[1].part_index == 1
    assert mesh_data.cmp_fix_records[0].record_size == 176
    assert mesh_data.cmp_fix_records[0].float_count == 44
    assert mesh_data.cmp_fix_records[0].row_width == 11
    assert mesh_data.cmp_fix_records[0].row_count == 4
    assert mesh_data.cmp_fix_records[0].rows[0][:4] == (0.0, 1.0, 2.0, 3.0)
    assert mesh_data.cmp_fix_records[1].rows[0][:4] == (44.0, 45.0, 46.0, 47.0)
    assert mesh_data.cmp_fix_records[0].first_f32[:4] == (0.0, 1.0, 2.0, 3.0)
    assert mesh_data.cmp_fix_records[1].first_f32[:4] == (44.0, 45.0, 46.0, 47.0)
    assert len(mesh_data.cmp_transform_hints) == 2
    assert mesh_data.cmp_transform_hints[0].part_name == "Part_Wing"
    assert mesh_data.cmp_transform_hints[0].translation_xyz == (7.0, 8.0, 9.0)
    assert mesh_data.cmp_transform_hints[0].combined_translation_xyz == (7.0, 8.0, 9.0)
    assert mesh_data.cmp_transform_hints[0].leading_vector_xyz == (0.0, 1.0, 2.0)
    assert mesh_data.cmp_transform_hints[0].normalized_forward_xyz is not None
    assert mesh_data.cmp_transform_hints[0].normalized_rotation_rows_xyz is None
    assert mesh_data.cmp_transform_hints[0].combined_rotation_rows_xyz is None
    assert mesh_data.cmp_transform_hints[1].translation_xyz == (51.0, 52.0, 53.0)
    assert mesh_data.cmp_transform_hints[1].combined_translation_xyz == (51.0, 52.0, 53.0)


def test_load_native_freelancer_model_extracts_cmp_rotation_rows(tmp_path):
    cmp_path = tmp_path / "fix_rotation_rows.cmp"
    fix_floats = [0.0] * 44
    fix_floats[0:3] = [0.0, 1.0, 0.0]
    fix_floats[11:14] = [-1.0, 0.0, 0.0]
    fix_floats[22:25] = [0.0, 0.0, 1.0]
    fix_blob = pack("<44f", *fix_floats)
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "Cmpnd", "Part_meshA_lod0", "Cons", "Fix", "Index"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("Cmpnd", 0x10, 0, 0, 0, 88, 132, None),
                ("Part_meshA_lod0", 0x10, 0, 0, 0, 132, 176, None),
                ("Index", 0x80, 0, 4, 4, 220, 0, pack("<I", 0)),
                ("Cons", 0x10, 0, 0, 0, 264, 308, None),
                ("Fix", 0x80, 0, len(fix_blob), len(fix_blob), 0, 0, fix_blob),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    assert len(mesh_data.cmp_transform_hints) == 1
    assert mesh_data.cmp_transform_hints[0].normalized_rotation_rows_xyz == (
        (0.0, 1.0, 0.0),
        (-1.0, 0.0, 0.0),
        (0.0, 0.0, 1.0),
    )


def test_load_native_freelancer_model_derives_cmp_rotation_rows_from_partial_basis(tmp_path):
    cmp_path = tmp_path / "fix_partial_rotation_rows.cmp"
    fix_floats = [0.0] * 44
    fix_floats[0:3] = [2.0, 0.0, 0.0]
    fix_floats[11:14] = [1.0, 3.0, 0.0]
    fix_blob = pack("<44f", *fix_floats)
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "Cmpnd", "Part_meshA_lod0", "Cons", "Fix", "Index"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("Cmpnd", 0x10, 0, 0, 0, 88, 132, None),
                ("Part_meshA_lod0", 0x10, 0, 0, 0, 132, 176, None),
                ("Index", 0x80, 0, 4, 4, 220, 0, pack("<I", 0)),
                ("Cons", 0x10, 0, 0, 0, 264, 308, None),
                ("Fix", 0x80, 0, len(fix_blob), len(fix_blob), 0, 0, fix_blob),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    assert len(mesh_data.cmp_transform_hints) == 1
    expected_rows = (
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    )
    for actual, expected in zip(
        mesh_data.cmp_transform_hints[0].normalized_rotation_rows_xyz,
        expected_rows,
        strict=True,
    ):
        assert actual == pytest.approx(expected)


def test_load_native_freelancer_model_builds_combined_cmp_transforms_for_nested_parts(tmp_path):
    cmp_path = tmp_path / "fix_nested_parts.cmp"
    fix_floats = [0.0] * 88
    # parent local rotation (identity rows) + translation (10, 0, 0)
    fix_floats[0:3] = [1.0, 0.0, 0.0]
    fix_floats[11:14] = [0.0, 1.0, 0.0]
    fix_floats[22:25] = [0.0, 0.0, 1.0]
    fix_floats[7:10] = [10.0, 0.0, 0.0]
    # child local rotation (90 deg around z) + translation (0, 5, 0)
    base = 44
    fix_floats[base + 0 : base + 3] = [0.0, 1.0, 0.0]
    fix_floats[base + 11 : base + 14] = [-1.0, 0.0, 0.0]
    fix_floats[base + 22 : base + 25] = [0.0, 0.0, 1.0]
    fix_floats[base + 7 : base + 10] = [0.0, 5.0, 0.0]
    fix_blob = pack("<88f", *fix_floats)
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "Cmpnd", "Part_Parent", "Part_Child", "Cons", "Fix", "Index"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("Cmpnd", 0x10, 0, 0, 0, 88, 0, None),
                ("Part_Parent", 0x10, 0, 0, 0, 176, 264, None),
                ("Index", 0x80, 0, 4, 4, 220, 0, pack("<I", 0)),
                ("Part_Child", 0x10, 0, 0, 0, 0, 264, None),
                ("Index", 0x80, 0, 4, 4, 0, 0, pack("<I", 1)),
                ("Cons", 0x10, 0, 0, 0, 0, 0, None),
                ("Fix", 0x80, 0, len(fix_blob), len(fix_blob), 0, 0, fix_blob),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    assert len(mesh_data.parts) == 2
    parts_by_name = {part.name: part for part in mesh_data.parts}
    assert parts_by_name["Part_Child"].parent_part_name == "Part_Parent"
    hints_by_name = {hint.part_name: hint for hint in mesh_data.cmp_transform_hints}
    assert hints_by_name["Part_Parent"].combined_translation_xyz == (10.0, 0.0, 0.0)
    assert hints_by_name["Part_Child"].translation_xyz == (0.0, 5.0, 0.0)
    assert hints_by_name["Part_Child"].combined_translation_xyz == (10.0, 5.0, 0.0)
    assert hints_by_name["Part_Child"].combined_rotation_rows_xyz == (
        (0.0, 1.0, 0.0),
        (-1.0, 0.0, 0.0),
        (0.0, 0.0, 1.0),
    )


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


def _build_vmesh_ref_blob(
    *,
    mesh_data_reference: int = 0x12345678,
    vertex_start: int = 0,
    vertex_count: int = 10,
    index_start: int = 0,
    index_count: int = 18,
    group_start: int = 0,
    group_count: int = 1,
) -> bytes:
    return pack(
        "<IIHHHHHH10f",
        60,
        mesh_data_reference,
        vertex_start,
        vertex_count,
        index_start,
        index_count,
        group_start,
        group_count,
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
