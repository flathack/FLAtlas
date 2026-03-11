from __future__ import annotations

from fl_editor.cmp_loader import load_native_freelancer_model
from fl_editor.native_preview_materials import (
    resolve_native_texture_path,
    select_native_texture_reference,
)
from tests.test_cmp_loader import _build_fake_utf_with_nodes


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
