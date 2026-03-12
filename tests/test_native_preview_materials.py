from __future__ import annotations

from fl_editor.cmp_loader import load_native_freelancer_model
from fl_editor.native_preview_materials import (
    resolve_native_texture_for_geometry,
    resolve_native_texture_path,
    select_preview_material_binding,
    select_native_texture_reference,
)
from tests.test_cmp_loader import _build_fake_utf_with_nodes, _build_vmesh_ref_blob


def test_select_native_texture_reference_prefers_real_texture_suffixes(tmp_path):
    cmp_path = tmp_path / "materials.cmp"
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "ship.mat", "diffuse.dds", "Texture name"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("ship.mat", 0x10, 0, 0, 0, 88, 0, None),
                ("diffuse.dds", 0x10, 0, 0, 0, 132, 0, None),
                ("Texture name", 0x80, 0, 11, 11, 176, 0, "normal.tga"),
            ],
        )
    )
    mesh_data = load_native_freelancer_model(cmp_path)

    reference = select_native_texture_reference(mesh_data.material_references)

    assert reference is not None
    assert reference.value == "diffuse.dds"


def test_resolve_native_texture_path_finds_texture_below_data_root(tmp_path):
    data_root = tmp_path / "DATA"
    solar_dir = data_root / "SOLAR"
    texture_dir = data_root / "TEXTURES"
    solar_dir.mkdir(parents=True)
    texture_dir.mkdir(parents=True)
    texture_path = texture_dir / "diffuse.dds"
    texture_path.write_bytes(b"DDS ")

    cmp_path = solar_dir / "ship.cmp"
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            names=[r"\\", "diffuse.dds"],
            nodes=[
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("diffuse.dds", 0x10, 0, 0, 0, 0, 0, None),
            ],
        )
    )
    mesh_data = load_native_freelancer_model(cmp_path)

    resolved = resolve_native_texture_path(mesh_data)

    assert resolved == texture_path


def test_resolve_native_texture_for_geometry_prefers_matching_binding(tmp_path):
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
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob()),
                ("fighter_diffuse.dds", 0x10, 0, 0, 0, 308, 0, None),
                ("transport_diffuse.dds", 0x10, 0, 0, 0, 352, 0, None),
                ("VMeshLibrary", 0x10, 0, 0, 0, 396, 484, None),
                ("mesh0.vms", 0x10, 0, 0, 0, 440, 0, None),
                ("VMeshData", 0x80, 0, 16, 16, 0, 0, b"0123456789abcdef"),
            ],
        )
    )
    mesh_data = load_native_freelancer_model(cmp_path)

    binding = select_preview_material_binding(mesh_data.preview_material_bindings, "li_fighter.3db", "Level0", 0, 1)
    resolved = resolve_native_texture_for_geometry(mesh_data, "li_fighter.3db", "Level0", 0, 1)

    assert binding is not None
    assert binding.group_start == 0
    assert binding.group_count == 1
    assert binding.texture_value == "fighter_diffuse.dds"
    assert binding.texture_candidates == ("fighter_diffuse.dds", "transport_diffuse.dds")
    assert binding.match_hint in {"token-match", "first-texture-fallback", "single-texture-fallback"}
    assert resolved == diffuse
