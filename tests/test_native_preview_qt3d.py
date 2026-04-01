from __future__ import annotations

from pathlib import Path

import pytest

from fl_editor import native_preview_qt3d


def test_build_native_geometry_material_disables_backface_culling_for_phong_fallback(monkeypatch):
    calls: list[object] = []

    class _FakePhongMaterial:
        def __init__(self, owner):
            self.owner = owner

    monkeypatch.setattr(native_preview_qt3d, "QPhongMaterial3D", _FakePhongMaterial)
    monkeypatch.setattr(native_preview_qt3d, "QTextureMaterial3D", None)
    monkeypatch.setattr(native_preview_qt3d, "QDiffuseMapMaterial3D", None)
    monkeypatch.setattr(native_preview_qt3d, "_disable_backface_culling", lambda material: calls.append(material))

    material = native_preview_qt3d.build_native_geometry_material(
        owner=object(),
        native_geometry=object(),
        texture_refs=[],
        texture_resolver=None,
        allow_textures=False,
    )

    assert isinstance(material, _FakePhongMaterial)
    assert calls == [material]


def test_decode_dds_to_qimage_can_force_opaque_alpha(tmp_path: Path):
    pil = pytest.importorskip("PIL.Image")

    image_path = tmp_path / "planet_surface.png"
    img = pil.new("RGBA", (2, 2), (50, 100, 150, 3))
    img.save(image_path)

    qimage = native_preview_qt3d._decode_dds_to_qimage(image_path, force_opaque=True)

    assert qimage is not None
    assert qimage.isNull() is False
    assert qimage.pixelColor(0, 0).alpha() == 255


def test_build_solid_annulus_renderer_returns_triangle_geometry(qapp):
    renderer = native_preview_qt3d.build_solid_annulus_renderer(
        owner=None,
        inner_radius=8.0,
        outer_radius=12.0,
        height=2.5,
        segments=24,
    )

    assert renderer is not None
    assert renderer.vertexCount() > 0
