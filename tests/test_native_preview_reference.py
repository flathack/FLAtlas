from __future__ import annotations

from struct import pack

from fl_editor.cmp_loader import load_native_freelancer_model
from fl_editor.native_preview_reference import NativePreviewReferenceRow
from fl_editor.native_preview_reference import build_native_preview_reference_rows
from fl_editor.native_preview_reference import build_native_preview_reference_summary
from fl_editor.native_preview_reference import sort_native_preview_reference_rows
from fl_editor.native_preview_scene_data import build_native_preview_scene_data
from tests.test_cmp_loader import _build_fake_utf_with_nodes, _build_vmesh_ref_blob


def test_build_native_preview_reference_rows_collects_geometry_texture_and_translation(tmp_path):
    data_root = tmp_path / "DATA"
    solar_dir = data_root / "SOLAR"
    tex_dir = data_root / "TEXTURES"
    solar_dir.mkdir(parents=True)
    tex_dir.mkdir(parents=True)
    diffuse = tex_dir / "fighter_diffuse.dds"
    diffuse.write_bytes(b"DDS ")

    cmp_path = solar_dir / "ship.cmp"
    vertex_blob = pack("<9f", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    index_blob = pack("<3H", 0, 1, 2)
    block = (b"H" * 16) + vertex_blob + index_blob
    fix_floats = [0.0] * 44
    fix_floats[7:10] = [10.0, 20.0, 30.0]
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
                "fighter_diffuse.dds",
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
                ("fighter_diffuse.dds", 0x10, 0, 0, 0, 396, 0, None),
                ("Cmpnd", 0x10, 0, 0, 0, 440, 0, None),
                ("Part_meshA_lod0", 0x10, 0, 0, 0, 484, 528, None),
                ("Index", 0x80, 0, 4, 4, 0, 0, pack("<I", 0)),
                ("Cons", 0x10, 0, 0, 0, 572, 0, None),
                ("Fix", 0x80, 0, len(fix_blob), len(fix_blob), 0, 0, fix_blob),
            ],
        )
    )

    mesh_data = load_native_freelancer_model(cmp_path)
    scene_data = build_native_preview_scene_data(mesh_data)
    rows = build_native_preview_reference_rows(mesh_data, scene_data)

    assert len(rows) == 1
    row = rows[0]
    assert row.model_name == "meshA_lod0.3db"
    assert row.part_name == "Part_meshA_lod0"
    assert row.raw_center_xyz == (0.0, 0.0, 0.0)
    assert row.center_xyz == (10.0, 20.0, 30.0)
    assert row.has_texture is True
    assert row.texture_name == "fighter_diffuse.dds"
    assert row.has_translation_hint is True
    assert row.translation_xyz == (10.0, 20.0, 30.0)
    assert round(row.translation_delta or 0.0, 3) == 37.417
    assert row.translation_matches_center is False


def test_build_native_preview_reference_summary_reports_translation_match_and_texture_gaps():
    rows = (
        NativePreviewReferenceRow(
            model_name="a",
            part_name="Part_A",
            geometry_index=0,
            raw_center_xyz=(0.0, 0.0, 0.0),
            center_xyz=(0.0, 0.0, 0.0),
            radius=1.0,
            has_texture=True,
            texture_name="a.dds",
            has_translation_hint=True,
            translation_xyz=(0.0, 0.0, 0.0),
            translation_delta=0.0,
            translation_matches_center=True,
        ),
        NativePreviewReferenceRow(
            model_name="b",
            part_name="Part_B",
            geometry_index=1,
            raw_center_xyz=(5.0, 0.0, 0.0),
            center_xyz=(5.0, 0.0, 0.0),
            radius=1.0,
            has_texture=False,
            texture_name=None,
            has_translation_hint=True,
            translation_xyz=(0.0, 0.0, 0.0),
            translation_delta=5.0,
            translation_matches_center=False,
        ),
        NativePreviewReferenceRow(
            model_name="c",
            part_name="Part_C",
            geometry_index=2,
            raw_center_xyz=(1.0, 1.0, 1.0),
            center_xyz=(1.0, 1.0, 1.0),
            radius=1.0,
            has_texture=False,
            texture_name=None,
            has_translation_hint=False,
            translation_xyz=None,
            translation_delta=None,
            translation_matches_center=None,
        ),
    )

    summary = build_native_preview_reference_summary(rows)

    assert summary.total_rows == 3
    assert summary.rows_with_translation_hint == 2
    assert summary.rows_with_matching_translation == 1
    assert summary.rows_with_mismatching_translation == 1
    assert summary.rows_without_texture == 2
    assert summary.max_translation_delta == 5.0


def test_sort_native_preview_reference_rows_prioritizes_mismatch_with_high_delta():
    rows = (
        NativePreviewReferenceRow(
            model_name="a",
            part_name="Part_A",
            geometry_index=0,
            raw_center_xyz=(0.0, 0.0, 0.0),
            center_xyz=(0.0, 0.0, 0.0),
            radius=1.0,
            has_texture=True,
            texture_name="a.dds",
            has_translation_hint=True,
            translation_xyz=(0.0, 0.0, 0.0),
            translation_delta=0.0,
            translation_matches_center=True,
        ),
        NativePreviewReferenceRow(
            model_name="b",
            part_name="Part_B",
            geometry_index=1,
            raw_center_xyz=(6.0, 0.0, 0.0),
            center_xyz=(6.0, 0.0, 0.0),
            radius=1.0,
            has_texture=True,
            texture_name="b.dds",
            has_translation_hint=True,
            translation_xyz=(0.0, 0.0, 0.0),
            translation_delta=6.0,
            translation_matches_center=False,
        ),
        NativePreviewReferenceRow(
            model_name="c",
            part_name="Part_C",
            geometry_index=2,
            raw_center_xyz=(1.0, 1.0, 1.0),
            center_xyz=(1.0, 1.0, 1.0),
            radius=1.0,
            has_texture=False,
            texture_name=None,
            has_translation_hint=False,
            translation_xyz=None,
            translation_delta=None,
            translation_matches_center=None,
        ),
    )

    sorted_rows = sort_native_preview_reference_rows(rows)

    assert sorted_rows[0].model_name == "b"
