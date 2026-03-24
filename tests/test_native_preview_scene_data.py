from __future__ import annotations

from struct import pack

from fl_editor.cmp_loader import load_native_freelancer_model
from fl_editor.freelancer_mesh_data import FreelancerBounds
from fl_editor.native_preview_geometry import NativePreviewGeometry
from fl_editor.native_preview_scene_data import (
    NativePreviewSceneData,
    build_native_preview_scene_data,
    scene_data_with_lod_mode,
    texture_path_for_geometry,
)
from tests.test_cmp_loader import _build_fake_utf_with_nodes, _build_vmesh_ref_blob


def test_build_native_preview_scene_data_collects_native_geometry_state(tmp_path):
    cmp_path = tmp_path / "scene_data.cmp"
    vertex_blob = pack("<9f", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    index_blob = pack("<3H", 0, 1, 2)
    block = (b"H" * 16) + vertex_blob + index_blob
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
            ],
        )
    )

    native_model = load_native_freelancer_model(cmp_path)
    scene_data = build_native_preview_scene_data(native_model)

    assert len(scene_data.geometries) == 1
    assert scene_data.primary_geometry is not None
    assert scene_data.primary_geometry.model_name == "meshA_lod0.3db"
    assert scene_data.bounds is not None
    assert scene_data.part_names == ("Part_meshA_lod0",)
    assert scene_data.texture_path is None


def test_build_native_preview_scene_data_handles_missing_native_model():
    scene_data = build_native_preview_scene_data(None)

    assert scene_data.geometries == ()
    assert scene_data.primary_geometry is None
    assert scene_data.bounds is None
    assert scene_data.part_names == ()
    assert scene_data.texture_path is None
    assert scene_data.geometry_texture_paths == ()
    assert scene_data.cmp_up_correction_euler_deg == (0.0, 0.0, 0.0)


def test_build_native_preview_scene_data_collects_per_geometry_texture_paths(tmp_path):
    data_root = tmp_path / "DATA"
    solar_dir = data_root / "SOLAR"
    tex_dir = data_root / "TEXTURES"
    solar_dir.mkdir(parents=True)
    tex_dir.mkdir(parents=True)
    diffuse = tex_dir / "fighter_diffuse.dds"
    diffuse.write_bytes(b"DDS ")
    other = tex_dir / "transport_diffuse.dds"
    other.write_bytes(b"DDS ")

    cmp_path = solar_dir / "ship.cmp"
    vertex_blob = pack("<9f", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    index_blob = pack("<3H", 0, 1, 2)
    block = (b"H" * 16) + vertex_blob + index_blob
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
                "transport_diffuse.dds",
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
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(mesh_data_reference=0, vertex_count=3, index_count=3, group_count=1)),
                ("fighter_diffuse.dds", 0x10, 0, 0, 0, 308, 0, None),
                ("transport_diffuse.dds", 0x10, 0, 0, 0, 352, 0, None),
                ("VMeshLibrary", 0x10, 0, 0, 0, 396, 484, None),
                ("mesh0.vms", 0x10, 0, 0, 0, 440, 0, None),
                ("VMeshData", 0x80, 0, len(block), len(block), 0, 0, block),
            ],
        )
    )

    native_model = load_native_freelancer_model(cmp_path)
    scene_data = build_native_preview_scene_data(native_model)

    assert len(scene_data.geometries) == 1
    assert scene_data.texture_path == diffuse
    assert scene_data.geometry_texture_paths == (diffuse,)
    assert texture_path_for_geometry(scene_data, scene_data.geometries[0]) == diffuse


def test_scene_data_with_lod_mode_prefers_coarser_levels_per_part(tmp_path):
    tex0 = tmp_path / "l0.dds"
    tex1 = tmp_path / "l1.dds"
    tex2 = tmp_path / "l2.dds"
    bounds = FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(1.0, 1.0, 1.0), radius=1.0)
    g0 = NativePreviewGeometry(
        model_name="mesh.3db",
        level_name="Level0",
        part_name="Part_A",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0),),
        indices=(0,),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=bounds,
    )
    g1 = NativePreviewGeometry(
        model_name="mesh.3db",
        level_name="Level1",
        part_name="Part_A",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0),),
        indices=(0,),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=bounds,
    )
    g2 = NativePreviewGeometry(
        model_name="mesh.3db",
        level_name="Level2",
        part_name="Part_A",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0),),
        indices=(0,),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=bounds,
    )
    scene_data = NativePreviewSceneData(
        geometries=(g0,),
        primary_geometry=g0,
        bounds=bounds,
        part_names=("Part_A",),
        texture_path=tex0,
        geometry_texture_paths=(tex0,),
        all_geometries=(g0, g1, g2),
        all_geometry_texture_paths=(tex0, tex1, tex2),
    )

    coarse = scene_data_with_lod_mode(scene_data, 1)
    coarsest = scene_data_with_lod_mode(scene_data, 2)

    assert coarse.geometries[0].level_name == "Level1"
    assert coarse.geometry_texture_paths == (tex1,)
    assert coarsest.geometries[0].level_name == "Level2"
    assert coarsest.geometry_texture_paths == (tex2,)
