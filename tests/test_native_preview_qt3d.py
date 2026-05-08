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


def test_build_texture_object_decodes_dds_without_qtexture_loader(monkeypatch, tmp_path: Path):
    loader_calls: list[object] = []

    class _FakeTextureLoader:
        def __init__(self, owner):
            loader_calls.append(owner)

    class _FakeTexture2D:
        def __init__(self, owner):
            self.owner = owner
            self.images = []

        def addTextureImage(self, image):
            self.images.append(image)

    class _FakeImage:
        def width(self):
            return 4

        def height(self):
            return 4

        def isNull(self):
            return False

    class _FakeTextureImage:
        def __init__(self, qimage, parent):
            self.qimage = qimage
            self.parent = parent

    monkeypatch.setattr(native_preview_qt3d, "QTextureLoader3D", _FakeTextureLoader)
    monkeypatch.setattr(native_preview_qt3d, "QTexture2D_3D", _FakeTexture2D)
    monkeypatch.setattr(native_preview_qt3d, "_DdsTextureImage", _FakeTextureImage)
    monkeypatch.setattr(native_preview_qt3d, "_decode_dds_to_qimage", lambda *_args, **_kwargs: _FakeImage())

    texture_refs: list[object] = []
    texture = native_preview_qt3d._build_texture_object(
        owner=object(),
        texture_path=tmp_path / "planet_surface.dds",
        texture_refs=texture_refs,
    )

    assert isinstance(texture, _FakeTexture2D)
    assert loader_calls == []
    assert texture_refs[0] is texture


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
