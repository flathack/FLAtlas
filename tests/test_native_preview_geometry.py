from __future__ import annotations

from dataclasses import replace
from struct import pack

import pytest

from fl_editor.cmp_loader import load_native_freelancer_model
from fl_editor.freelancer_mesh_data import FreelancerBounds, FreelancerStructuredDecodePlan
from fl_editor.native_preview_geometry import (
    _rotation_rows_for_geometry,
    _translation_for_geometry,
    decode_native_preview_geometries,
    decode_native_preview_geometry,
)
from tests.test_cmp_loader import _build_fake_utf_with_nodes, _build_vmesh_ref_blob


def test_decode_native_preview_geometry_from_exact_fit(tmp_path):
    cmp_path = tmp_path / "layout.cmp"
    vertex_blob = pack("<9f", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    index_blob = pack("<3H", 0, 1, 2)
    block = (b"H" * 16) + vertex_blob + index_blob
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
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=0, vertex_count=3, index_count=3, group_count=1)),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)
    geometry = decode_native_preview_geometry(mesh_data)

    assert geometry is not None
    assert geometry.positions == ((-0.5, -0.5, 0.0), (0.5, -0.5, 0.0), (-0.5, 0.5, 0.0))
    assert geometry.indices == (0, 1, 2)
    assert geometry.group_start == 0
    assert geometry.group_count == 1
    assert geometry.vertex_stride == 12
    assert geometry.index_size == 2
    assert geometry.bounds.min_xyz == (-0.5, -0.5, 0.0)
    assert geometry.bounds.max_xyz == (0.5, 0.5, 0.0)


def test_decode_native_preview_geometries_can_preserve_original_origin(tmp_path):
    cmp_path = tmp_path / "layout_preserve_origin.cmp"
    vertex_blob = pack("<9f", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    index_blob = pack("<3H", 0, 1, 2)
    block = (b"H" * 16) + vertex_blob + index_blob
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
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=0, vertex_count=3, index_count=3, group_count=1)),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)
    geometries = decode_native_preview_geometries(mesh_data, normalize_to_center=False)

    assert len(geometries) == 1
    assert geometries[0].positions == ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    assert geometries[0].bounds.min_xyz == (0.0, 0.0, 0.0)
    assert geometries[0].bounds.max_xyz == (1.0, 1.0, 0.0)


def test_decode_native_preview_geometry_uses_ready_structured_plan(tmp_path):
    cmp_path = tmp_path / "structured_plan_layout.cmp"
    vertex_blob = pack("<9f", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    index_blob = pack("<3H", 0, 1, 2)
    block = (b"H" * 16) + vertex_blob + index_blob
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
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=0, vertex_count=3, index_count=3, group_count=1)),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)
    weak_slices = tuple(replace(buffer_slice, confidence="weak") for buffer_slice in mesh_data.preview_buffer_slices)
    structured_plan = FreelancerStructuredDecodePlan(
        model_name="mesh0.3db",
        level_name="Level0",
        family_key="mesh0",
        layout_mode="single-block",
        header_block_index=0,
        stream_block_index=0,
        stream_stride_hint=12,
        mesh_header_count=1,
        mesh_header_index_end=3,
        mesh_header_num_ref_vertices=3,
        mesh_header_end_vertex=3,
        source_group_end=1,
        source_index_end=3,
        source_vertex_end=3,
        decode_ready=True,
        decode_hint="ready-for-structured-single-block-decode",
    )
    mesh_data = replace(mesh_data, preview_buffer_slices=weak_slices, structured_decode_plans=(structured_plan,))

    geometry = decode_native_preview_geometry(mesh_data)

    assert geometry is not None
    assert geometry.positions == ((-0.5, -0.5, 0.0), (0.5, -0.5, 0.0), (-0.5, 0.5, 0.0))
    assert geometry.indices == (0, 1, 2)


def test_decode_native_preview_geometry_falls_back_to_structured_single_block_indices(tmp_path):
    cmp_path = tmp_path / "structured_single_block_indices.cmp"
    index_blob = pack("<3H", 0, 1, 2)
    vertex_blob = pack("<9f", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    block = (b"H" * 16) + index_blob + (b"P" * 42) + vertex_blob
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
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=0, vertex_count=3, index_count=3, group_count=1)),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)
    broken_slice = replace(
        mesh_data.preview_buffer_slices[0],
        header_size=16,
        vertex_offset=64,
        vertex_bytes=36,
        index_offset=88,
        index_bytes=12,
        index_size=4,
        confidence="exact",
    )
    structured_plan = FreelancerStructuredDecodePlan(
        model_name="mesh0.3db",
        level_name="Level0",
        family_key="mesh0",
        layout_mode="single-block",
        header_block_index=0,
        stream_block_index=0,
        stream_stride_hint=12,
        mesh_header_count=1,
        mesh_header_index_end=3,
        mesh_header_num_ref_vertices=3,
        mesh_header_end_vertex=3,
        source_group_end=1,
        source_index_end=3,
        source_vertex_end=3,
        decode_ready=True,
        decode_hint="ready-for-structured-single-block-decode",
    )
    mesh_data = replace(
        mesh_data,
        preview_buffer_slices=(broken_slice,),
        structured_decode_plans=(structured_plan,),
    )

    geometry = decode_native_preview_geometry(mesh_data)

    assert geometry is not None
    assert geometry.positions == ((-0.5, -0.5, 0.0), (0.5, -0.5, 0.0), (-0.5, 0.5, 0.0))
    assert geometry.indices == (0, 1, 2)
    assert geometry.confidence == "structured-single-block"


def test_decode_native_preview_geometry_supports_index_first_single_block_layout(tmp_path):
    cmp_path = tmp_path / "structured_single_block_index_first.cmp"
    header = b"H" * 64
    index_blob = pack("<3H", 0, 1, 2)
    vertex_blob = (
        pack("<3f", 0.0, 0.0, 0.0) + (b"\x00" * 28)
        + pack("<3f", 1.0, 0.0, 0.0) + (b"\x00" * 28)
        + pack("<3f", 0.0, 1.0, 0.0) + (b"\x00" * 28)
    )
    block = header + index_blob + vertex_blob
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
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=0, vertex_count=3, index_count=3, group_count=1)),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)
    weak_slice = replace(
        mesh_data.preview_buffer_slices[0],
        header_size=16,
        vertex_offset=16,
        vertex_bytes=120,
        index_offset=136,
        index_bytes=12,
        index_size=4,
        vertex_stride=40,
        confidence="exact",
    )
    structured_plan = FreelancerStructuredDecodePlan(
        model_name="mesh0.3db",
        level_name="Level0",
        family_key="mesh0",
        layout_mode="single-block",
        header_block_index=0,
        stream_block_index=0,
        stream_stride_hint=40,
        mesh_header_count=4,
        mesh_header_index_end=3,
        mesh_header_num_ref_vertices=3,
        mesh_header_end_vertex=3,
        source_group_end=1,
        source_index_end=3,
        source_vertex_end=3,
        decode_ready=True,
        decode_hint="ready-for-structured-single-block-decode",
    )
    mesh_data = replace(
        mesh_data,
        preview_geometry_sources=(
            replace(
                mesh_data.preview_geometry_sources[0],
                bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(1.0, 1.0, 0.0), radius=1.0),
            ),
        ),
        preview_buffer_slices=(weak_slice,),
        structured_decode_plans=(structured_plan,),
    )

    geometry = decode_native_preview_geometry(mesh_data)

    assert geometry is not None
    assert geometry.positions == ((-0.5, -0.5, 0.0), (0.5, -0.5, 0.0), (-0.5, 0.5, 0.0))
    assert geometry.indices == (0, 1, 2)
    assert geometry.vertex_stride == 40
    assert geometry.index_size == 2


def test_decode_native_preview_geometry_uses_single_block_mesh_headers_for_group_range(tmp_path):
    cmp_path = tmp_path / "structured_single_block_group_range.cmp"
    header = pack("<II4H", 1, 4, 2, 6, 0x012, 5)
    mesh_headers = (
        pack("<I4H", 0, 0, 1, 3, 0)
        + pack("<I4H", 0, 2, 4, 3, 0)
    )
    triangle_blob = (
        pack("<3H", 0, 2, 1)
        + pack("<3H", 0, 2, 1)
    )
    vertex_blob = (
        pack("<3f", 0.0, 0.0, 0.0) + (b"\x00" * 12)
        + pack("<3f", 1.0, 0.0, 0.0) + (b"\x00" * 12)
        + pack("<3f", 0.0, 0.0, 1.0) + (b"\x00" * 12)
        + pack("<3f", 1.0, 0.0, 1.0) + (b"\x00" * 12)
        + pack("<3f", 0.0, 0.0, 2.0) + (b"\x00" * 12)
    )
    block = header + mesh_headers + triangle_blob + vertex_blob
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
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=0, vertex_start=0, vertex_count=5, index_start=0, index_count=6, group_start=0, group_count=2)),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)
    weak_slice = replace(
        mesh_data.preview_buffer_slices[0],
        header_size=16,
        vertex_offset=16,
        vertex_bytes=120,
        index_offset=136,
        index_bytes=24,
        index_size=4,
        vertex_stride=24,
        confidence="weak",
    )
    structured_plan = FreelancerStructuredDecodePlan(
        model_name="mesh0.3db",
        level_name="Level0",
        family_key="mesh0",
        layout_mode="single-block",
        header_block_index=0,
        stream_block_index=0,
        stream_stride_hint=24,
        mesh_header_count=2,
        mesh_header_index_end=6,
        mesh_header_num_ref_vertices=6,
        mesh_header_end_vertex=5,
        source_group_end=2,
        source_index_end=6,
        source_vertex_end=5,
        decode_ready=True,
        decode_hint="ready-for-structured-single-block-decode",
    )
    mesh_data = replace(
        mesh_data,
        preview_buffer_slices=(weak_slice,),
        structured_decode_plans=(structured_plan,),
    )

    geometry = decode_native_preview_geometry(mesh_data)

    assert geometry is not None
    assert geometry.positions == (
        (-0.5, 0.0, -1.0),
        (0.5, 0.0, -1.0),
        (-0.5, 0.0, 0.0),
        (0.5, 0.0, 0.0),
        (-0.5, 0.0, 1.0),
    )
    assert geometry.indices == (0, 2, 1, 0, 2, 1)
    assert geometry.vertex_stride == 24
    assert geometry.index_size == 2


def test_decode_native_preview_geometry_uses_structured_family_split_plan(tmp_path):
    cmp_path = tmp_path / "structured_family_layout.cmp"
    vertex_blob = (
        pack("<3f", 0.0, 0.0, 0.0) + (b"\x00" * 4)
        + pack("<3f", 1.0, 0.0, 0.0) + (b"\x00" * 4)
        + pack("<3f", 0.0, 1.0, 0.0) + (b"\x00" * 4)
    )
    header_block = (
        (b"H" * 64)
        + pack("<3H", 0, 1, 2)
        + (b"P" * 26)
        + vertex_blob
    )
    stream_block = b"S" * 64
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[
                r"\\",
                "VMeshLibrary",
                "header.vms",
                "VMeshData",
                "stream.vms",
                "VMeshData",
                "mesh0.3db",
                "MultiLevel",
                "Level0",
                "VMeshPart",
                "VMeshRef",
            ],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("VMeshLibrary", 0x10, 0, 0, 0, 88, 176, None),
                ("header.vms", 0x10, 0, 0, 0, 132, 0, None),
                ("VMeshData", 0x80, 0, len(header_block), len(header_block), 0, 0, header_block),
                ("stream.vms", 0x10, 0, 0, 0, 220, 0, None),
                ("VMeshData", 0x80, 0, len(stream_block), len(stream_block), 0, 0, stream_block),
                ("mesh0.3db", 0x10, 0, 0, 0, 308, 0, None),
                ("MultiLevel", 0x10, 0, 0, 0, 352, 0, None),
                ("Level0", 0x10, 0, 0, 0, 396, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 440, 0, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=0, vertex_count=3, index_count=3, group_count=1)),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)
    preview_source = replace(
        mesh_data.preview_geometry_sources[0],
        model_name="mesh0.3db",
        level_name="Level0",
    )
    mesh_data = replace(
        mesh_data,
        preview_buffer_slices=(),
        preview_geometry_sources=(preview_source,),
    )
    structured_plan = FreelancerStructuredDecodePlan(
        model_name="mesh0.3db",
        level_name="Level0",
        family_key="mesh0",
        layout_mode="family-split-header-stream",
        header_block_index=0,
        stream_block_index=1,
        stream_stride_hint=12,
        mesh_header_count=4,
        mesh_header_index_end=3,
        mesh_header_num_ref_vertices=3,
        mesh_header_end_vertex=3,
        source_group_end=1,
        source_index_end=3,
        source_vertex_end=3,
        decode_ready=True,
        decode_hint="ready-for-structured-family-decode",
    )
    mesh_data = replace(mesh_data, structured_decode_plans=(structured_plan,))

    geometry = decode_native_preview_geometry(mesh_data)

    assert geometry is not None
    assert geometry.positions == ((-0.5, -0.5, 0.0), (0.5, -0.5, 0.0), (-0.5, 0.5, 0.0))
    assert geometry.indices == (0, 1, 2)
    assert geometry.confidence == "structured-family-split"


def test_decode_native_preview_geometry_decodes_embedded_vmesh_window(tmp_path):
    cmp_path = tmp_path / "embedded_vmesh_window.cmp"
    prefix = b"P" * 32
    header = pack("<II4H", 1, 4, 1, 3, 0x012, 3)
    mesh_headers = pack("<I4H", 0, 0, 2, 3, 0)
    triangle_blob = pack("<3H", 0, 2, 1)
    vertex_blob = (
        pack("<3f", 0.0, 0.0, 0.0) + (b"\x00" * 12)
        + pack("<3f", 1.0, 0.0, 0.0) + (b"\x00" * 12)
        + pack("<3f", 0.0, 0.0, 1.0) + (b"\x00" * 12)
    )
    block = prefix + header + mesh_headers + triangle_blob + vertex_blob
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
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=0, vertex_count=3, index_count=3, group_count=1)),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    geometry = decode_native_preview_geometry(mesh_data)

    assert geometry is not None
    assert geometry.positions == ((-0.5, 0.0, -0.5), (0.5, 0.0, -0.5), (-0.5, 0.0, 0.5))
    assert geometry.indices == (0, 1, 2)
    assert geometry.confidence == "structured-single-block"


def test_decode_native_preview_geometry_rejects_unreasonable_positions(tmp_path):
    cmp_path = tmp_path / "bad_layout.cmp"
    vertex_blob = pack("<9f", 2_000_000.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    index_blob = pack("<3H", 0, 1, 2)
    block = (b"H" * 16) + vertex_blob + index_blob
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
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=1, vertex_count=3, index_count=3, group_count=1)),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    assert decode_native_preview_geometry(mesh_data) is None


def test_decode_native_preview_geometries_returns_multiple_exact_submeshes(tmp_path):
    cmp_path = tmp_path / "multi_layout.cmp"
    vertex_blob_a = pack("<9f", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    index_blob_a = pack("<3H", 0, 1, 2)
    block_a = (b"H" * 16) + vertex_blob_a + index_blob_a
    vertex_blob_b = pack("<9f", 0.0, 0.0, 0.0, -1.0, 0.0, 0.0, 0.0, -1.0, 0.0)
    index_blob_b = pack("<3H", 0, 1, 2)
    block_b = (b"J" * 16) + vertex_blob_b + index_blob_b
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "meshA.3db", "meshB.3db", "Level0", "VMeshPart", "VMeshRef", "VMeshLibrary", "mesh0.vms", "VMeshData", "mesh1.vms"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("meshA.3db", 0x10, 0, 0, 0, 88, 0, None),
                ("Level0", 0x10, 0, 0, 0, 132, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 176, 220, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=0, vertex_count=3, index_count=3, group_count=1)),
                ("meshB.3db", 0x10, 0, 0, 0, 264, 0, None),
                ("Level0", 0x10, 0, 0, 0, 308, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 352, 396, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=1, vertex_count=3, index_count=3, group_count=1)),
                ("VMeshLibrary", 0x10, 0, 0, 0, 440, 572, None),
                ("mesh0.vms", 0x10, 0, 0, 0, 484, 0, None),
                ("VMeshData", 0x80, 0, len(block_a), len(block_a), 528, 0, block_a),
                ("mesh1.vms", 0x10, 0, 0, 0, 0, 0, None),
                ("VMeshData", 0x80, 0, len(block_b), len(block_b), 0, 0, block_b),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)
    geometries = decode_native_preview_geometries(mesh_data)

    assert len(geometries) == 2
    assert geometries[0].indices == (0, 1, 2)
    assert geometries[1].indices == (0, 1, 2)
    assert geometries[0].group_start == 0
    assert geometries[0].group_count == 1
    assert geometries[1].group_start == 0
    assert geometries[1].group_count == 1
    assert geometries[0].positions == (
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
    )
    assert geometries[1].positions == (
        (0.0, 0.0, 0.0),
        (-1.0, 0.0, 0.0),
        (0.0, -1.0, 0.0),
    )
    assert geometries[0].bounds.min_xyz == (0.0, 0.0, 0.0)
    assert geometries[0].bounds.max_xyz == (1.0, 1.0, 0.0)
    assert geometries[1].bounds.min_xyz == (-1.0, -1.0, 0.0)
    assert geometries[1].bounds.max_xyz == (0.0, 0.0, 0.0)


def test_decode_native_preview_geometries_applies_cmp_translation_hints(tmp_path):
    cmp_path = tmp_path / "translated_multi_layout.cmp"
    vertex_blob = pack("<9f", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    index_blob = pack("<3H", 0, 1, 2)
    block_a = (b"H" * 16) + vertex_blob + index_blob
    block_b = (b"J" * 16) + vertex_blob + index_blob
    fix_floats = [0.0] * 88
    fix_floats[7:10] = [10.0, 0.0, 0.0]
    fix_floats[44 + 7 : 44 + 10] = [-10.0, 0.0, 0.0]
    fix_blob = pack("<88f", *fix_floats)
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[
                r"\\",
                "meshA_lod0.3db",
                "meshB_lod0.3db",
                "Level0",
                "VMeshPart",
                "VMeshRef",
                "VMeshLibrary",
                "mesh0.vms",
                "VMeshData",
                "mesh1.vms",
                "Part_meshA_lod0",
                "Part_meshB_lod0",
                "File name",
                "Cmpnd",
                "Cons",
                "Fix",
                "Index",
            ],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("meshA_lod0.3db", 0x10, 0, 0, 0, 88, 220, None),
                ("Level0", 0x10, 0, 0, 0, 132, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 176, 0, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=0, vertex_count=3, index_count=3, group_count=1)),
                ("meshB_lod0.3db", 0x10, 0, 0, 0, 264, 396, None),
                ("Level0", 0x10, 0, 0, 0, 308, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 352, 0, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=1, vertex_count=3, index_count=3, group_count=1)),
                ("VMeshLibrary", 0x10, 0, 0, 0, 440, 616, None),
                ("mesh0.vms", 0x10, 0, 0, 0, 484, 528, None),
                ("VMeshData", 0x80, 0, len(block_a), len(block_a), 0, 0, block_a),
                ("mesh1.vms", 0x10, 0, 0, 0, 572, 0, None),
                ("VMeshData", 0x80, 0, len(block_b), len(block_b), 0, 0, block_b),
                ("Cmpnd", 0x10, 0, 0, 0, 660, 0, None),
                ("Part_meshA_lod0", 0x10, 0, 0, 0, 704, 748, None),
                ("Index", 0x80, 0, 4, 4, 0, 0, pack("<I", 0)),
                ("Part_meshB_lod0", 0x10, 0, 0, 0, 792, 836, None),
                ("Index", 0x80, 0, 4, 4, 0, 0, pack("<I", 1)),
                ("Cons", 0x10, 0, 0, 0, 880, 0, None),
                ("Fix", 0x80, 0, len(fix_blob), len(fix_blob), 0, 0, fix_blob),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)
    geometries = decode_native_preview_geometries(mesh_data)

    assert len(geometries) == 2
    assert geometries[0].part_name == "Part_meshA_lod0"
    assert geometries[1].part_name == "Part_meshB_lod0"
    assert geometries[0].bounds.min_xyz == (9.5, -0.5, 0.0)
    assert geometries[0].bounds.max_xyz == (10.5, 0.5, 0.0)
    assert geometries[1].bounds.min_xyz == (-10.5, -0.5, 0.0)
    assert geometries[1].bounds.max_xyz == (-9.5, 0.5, 0.0)


def test_decode_native_preview_geometries_applies_cmp_forward_rotation(tmp_path):
    cmp_path = tmp_path / "rotated_layout.cmp"
    vertex_blob = pack("<9f", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    index_blob = pack("<3H", 0, 1, 2)
    block = (b"H" * 16) + vertex_blob + index_blob
    fix_floats = [0.0] * 44
    fix_floats[0:3] = [0.0, 1.0, 0.0]
    fix_blob = pack("<44f", *fix_floats)
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[
                r"\\",
                "meshA_lod0.3db",
                "Level0",
                "VMeshPart",
                "VMeshRef",
                "VMeshLibrary",
                "mesh0.vms",
                "VMeshData",
                "Cmpnd",
                "Part_meshA_lod0",
                "Index",
                "Cons",
                "Fix",
            ],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("meshA_lod0.3db", 0x10, 0, 0, 0, 88, 0, None),
                ("Level0", 0x10, 0, 0, 0, 132, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 176, 0, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=0, vertex_count=3, index_count=3, group_count=1)),
                ("VMeshLibrary", 0x10, 0, 0, 0, 264, 352, None),
                ("mesh0.vms", 0x10, 0, 0, 0, 308, 0, None),
                ("VMeshData", 0x80, 0, len(block), len(block), 0, 0, block),
                ("Cmpnd", 0x10, 0, 0, 0, 396, 0, None),
                ("Part_meshA_lod0", 0x10, 0, 0, 0, 440, 484, None),
                ("Index", 0x80, 0, 4, 4, 0, 0, pack("<I", 0)),
                ("Cons", 0x10, 0, 0, 0, 528, 0, None),
                ("Fix", 0x80, 0, len(fix_blob), len(fix_blob), 0, 0, fix_blob),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)
    geometries = decode_native_preview_geometries(mesh_data)

    assert len(geometries) == 1
    assert geometries[0].part_name == "Part_meshA_lod0"
    assert geometries[0].bounds.min_xyz == (-0.5, -0.5, 0.0)
    assert geometries[0].bounds.max_xyz == (0.5, 0.5, 0.0)
    expected_positions = (
        (0.5, -0.5, 0.0),
        (0.5, 0.5, 0.0),
        (-0.5, -0.5, 0.0),
    )
    for actual, expected in zip(geometries[0].positions, expected_positions, strict=True):
        assert actual == pytest.approx(expected)


def test_decode_native_preview_geometries_applies_cmp_rotation_rows(tmp_path):
    cmp_path = tmp_path / "rotated_matrix_layout.cmp"
    vertex_blob = pack("<9f", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    index_blob = pack("<3H", 0, 1, 2)
    block = (b"H" * 16) + vertex_blob + index_blob
    fix_floats = [0.0] * 44
    fix_floats[0:3] = [0.0, 1.0, 0.0]
    fix_floats[11:14] = [-1.0, 0.0, 0.0]
    fix_floats[22:25] = [0.0, 0.0, 1.0]
    fix_blob = pack("<44f", *fix_floats)
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[
                r"\\",
                "meshA_lod0.3db",
                "Level0",
                "VMeshPart",
                "VMeshRef",
                "VMeshLibrary",
                "mesh0.vms",
                "VMeshData",
                "Cmpnd",
                "Part_meshA_lod0",
                "Index",
                "Cons",
                "Fix",
            ],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("meshA_lod0.3db", 0x10, 0, 0, 0, 88, 0, None),
                ("Level0", 0x10, 0, 0, 0, 132, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 176, 0, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=0, vertex_count=3, index_count=3, group_count=1)),
                ("VMeshLibrary", 0x10, 0, 0, 0, 264, 352, None),
                ("mesh0.vms", 0x10, 0, 0, 0, 308, 0, None),
                ("VMeshData", 0x80, 0, len(block), len(block), 0, 0, block),
                ("Cmpnd", 0x10, 0, 0, 0, 396, 0, None),
                ("Part_meshA_lod0", 0x10, 0, 0, 0, 440, 484, None),
                ("Index", 0x80, 0, 4, 4, 0, 0, pack("<I", 0)),
                ("Cons", 0x10, 0, 0, 0, 528, 0, None),
                ("Fix", 0x80, 0, len(fix_blob), len(fix_blob), 0, 0, fix_blob),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)
    geometries = decode_native_preview_geometries(mesh_data)

    assert len(geometries) == 1
    expected_positions = (
        (-0.5, 0.5, 0.0),
        (-0.5, -0.5, 0.0),
        (0.5, 0.5, 0.0),
    )
    for actual, expected in zip(geometries[0].positions, expected_positions, strict=True):
        assert actual == pytest.approx(expected)


def test_decode_native_preview_geometries_applies_derived_cmp_rotation_rows(tmp_path):
    cmp_path = tmp_path / "derived_rotation_layout.cmp"
    vertex_blob = pack("<9f", 0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0, 0.0)
    index_blob = pack("<3H", 0, 1, 2)
    block = (b"H" * 16) + vertex_blob + index_blob
    fix_floats = [0.0] * 44
    fix_floats[0:3] = [0.0, 2.0, 0.0]
    fix_floats[11:14] = [-3.0, 1.0, 0.0]
    fix_blob = pack("<44f", *fix_floats)
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[
                r"\\",
                "meshA_lod0.3db",
                "Level0",
                "VMeshPart",
                "VMeshRef",
                "VMeshLibrary",
                "mesh0.vms",
                "VMeshData",
                "Cmpnd",
                "Part_meshA_lod0",
                "Index",
                "Cons",
                "Fix",
            ],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("meshA_lod0.3db", 0x10, 0, 0, 0, 88, 0, None),
                ("Level0", 0x10, 0, 0, 0, 132, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 176, 0, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=0, vertex_count=3, index_count=3, group_count=1)),
                ("VMeshLibrary", 0x10, 0, 0, 0, 264, 352, None),
                ("mesh0.vms", 0x10, 0, 0, 0, 308, 0, None),
                ("VMeshData", 0x80, 0, len(block), len(block), 0, 0, block),
                ("Cmpnd", 0x10, 0, 0, 0, 396, 0, None),
                ("Part_meshA_lod0", 0x10, 0, 0, 0, 440, 484, None),
                ("Index", 0x80, 0, 4, 4, 0, 0, pack("<I", 0)),
                ("Cons", 0x10, 0, 0, 0, 528, 0, None),
                ("Fix", 0x80, 0, len(fix_blob), len(fix_blob), 0, 0, fix_blob),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)
    geometries = decode_native_preview_geometries(mesh_data)

    assert len(geometries) == 1
    expected_positions = (
        (-0.5, 0.5, 0.0),
        (0.5, -0.5, 0.0),
        (0.5, 0.5, 0.0),
    )
    for actual, expected in zip(geometries[0].positions, expected_positions, strict=True):
        assert actual == pytest.approx(expected)


def test_translation_and_rotation_helpers_prefer_combined_cmp_hints(tmp_path):
    cmp_path = tmp_path / "combined_hint_precedence_layout.cmp"
    vertex_blob = pack("<9f", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    index_blob = pack("<3H", 0, 1, 2)
    block = (b"H" * 16) + vertex_blob + index_blob
    fix_floats = [0.0] * 44
    fix_floats[0:3] = [1.0, 0.0, 0.0]
    fix_floats[11:14] = [0.0, 1.0, 0.0]
    fix_floats[22:25] = [0.0, 0.0, 1.0]
    fix_floats[7:10] = [0.0, 5.0, 0.0]
    fix_blob = pack("<44f", *fix_floats)
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[
                r"\\",
                "meshA_lod0.3db",
                "Level0",
                "VMeshPart",
                "VMeshRef",
                "VMeshLibrary",
                "mesh0.vms",
                "VMeshData",
                "Cmpnd",
                "Part_meshA_lod0",
                "Index",
                "Cons",
                "Fix",
            ],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("meshA_lod0.3db", 0x10, 0, 0, 0, 88, 0, None),
                ("Level0", 0x10, 0, 0, 0, 132, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 176, 0, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=0, vertex_count=3, index_count=3, group_count=1)),
                ("VMeshLibrary", 0x10, 0, 0, 0, 264, 352, None),
                ("mesh0.vms", 0x10, 0, 0, 0, 308, 0, None),
                ("VMeshData", 0x80, 0, len(block), len(block), 0, 0, block),
                ("Cmpnd", 0x10, 0, 0, 0, 396, 0, None),
                ("Part_meshA_lod0", 0x10, 0, 0, 0, 440, 484, None),
                ("Index", 0x80, 0, 4, 4, 0, 0, pack("<I", 0)),
                ("Cons", 0x10, 0, 0, 0, 528, 0, None),
                ("Fix", 0x80, 0, len(fix_blob), len(fix_blob), 0, 0, fix_blob),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)
    hints = [replace(
        mesh_data.cmp_transform_hints[0],
        combined_translation_xyz=(10.0, 5.0, 0.0),
        combined_rotation_rows_xyz=((0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    )]
    mesh_data = replace(mesh_data, cmp_transform_hints=tuple(hints))
    assert _translation_for_geometry(mesh_data, "meshA_lod0.3db") == (10.0, 5.0, 0.0)
    assert _rotation_rows_for_geometry(mesh_data, "meshA_lod0.3db") == (
        (0.0, 1.0, 0.0),
        (-1.0, 0.0, 0.0),
        (0.0, 0.0, 1.0),
    )


def test_decode_native_preview_geometry_applies_cmp_rotation_rows(tmp_path):
    cmp_path = tmp_path / "combined_hint_rotation_apply_layout.cmp"
    vertex_blob = pack("<9f", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    index_blob = pack("<3H", 0, 1, 2)
    block = (b"H" * 16) + vertex_blob + index_blob
    fix_floats = [0.0] * 44
    fix_floats[0:3] = [1.0, 0.0, 0.0]
    fix_floats[11:14] = [0.0, 1.0, 0.0]
    fix_floats[22:25] = [0.0, 0.0, 1.0]
    fix_blob = pack("<44f", *fix_floats)
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[
                r"\\",
                "meshA_lod0.3db",
                "Level0",
                "VMeshPart",
                "VMeshRef",
                "VMeshLibrary",
                "mesh0.vms",
                "VMeshData",
                "Cmpnd",
                "Part_meshA_lod0",
                "Index",
                "Cons",
                "Fix",
            ],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("meshA_lod0.3db", 0x10, 0, 0, 0, 88, 0, None),
                ("Level0", 0x10, 0, 0, 0, 132, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 176, 0, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=0, vertex_count=3, index_count=3, group_count=1)),
                ("VMeshLibrary", 0x10, 0, 0, 0, 264, 352, None),
                ("mesh0.vms", 0x10, 0, 0, 0, 308, 0, None),
                ("VMeshData", 0x80, 0, len(block), len(block), 0, 0, block),
                ("Cmpnd", 0x10, 0, 0, 0, 396, 0, None),
                ("Part_meshA_lod0", 0x10, 0, 0, 0, 440, 484, None),
                ("Index", 0x80, 0, 4, 4, 0, 0, pack("<I", 0)),
                ("Cons", 0x10, 0, 0, 0, 528, 0, None),
                ("Fix", 0x80, 0, len(fix_blob), len(fix_blob), 0, 0, fix_blob),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)
    mesh_data = replace(
        mesh_data,
        cmp_transform_hints=(
            replace(
                mesh_data.cmp_transform_hints[0],
                combined_rotation_rows_xyz=((0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
            ),
        ),
    )

    geometry = decode_native_preview_geometry(mesh_data)

    assert geometry is not None
    assert geometry.positions == ((-0.5, 0.5, 0.0), (-0.5, -0.5, 0.0), (0.5, 0.5, 0.0))
