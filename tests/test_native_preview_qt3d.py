from __future__ import annotations

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