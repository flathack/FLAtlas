from __future__ import annotations

from struct import pack

from fl_editor.cmp_loader import load_native_freelancer_model
from fl_editor.native_preview_geometry import decode_native_preview_geometry
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
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(vertex_count=3, index_count=3, group_count=1)),
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
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(vertex_count=3, index_count=3, group_count=1)),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)

    assert decode_native_preview_geometry(mesh_data) is None
