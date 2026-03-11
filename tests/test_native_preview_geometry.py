from __future__ import annotations

from struct import pack

import pytest

from fl_editor.cmp_loader import load_native_freelancer_model
from fl_editor.native_preview_geometry import decode_native_preview_geometries, decode_native_preview_geometry
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
    assert geometry.vertex_stride == 12
    assert geometry.index_size == 2
    assert geometry.bounds.min_xyz == (-0.5, -0.5, 0.0)
    assert geometry.bounds.max_xyz == (0.5, 0.5, 0.0)


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
