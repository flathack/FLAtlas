from __future__ import annotations

from PySide6.QtGui import QColor

from fl_editor.view_3d_materials import (
    build_torus_mesh,
    make_alpha_material,
    make_phong_material,
    material_always_on_top_refs,
    material_no_alpha_write_refs,
)


class _FakeTorusMesh:
    def __init__(self):
        self.radius = None
        self.minor = None
        self.rings = None
        self.slices = None

    def setRadius(self, value):
        self.radius = value

    def setMinorRadius(self, value):
        self.minor = value

    def setRings(self, value):
        self.rings = value

    def setSlices(self, value):
        self.slices = value


class _FakeMaterial:
    def __init__(self):
        self.diffuse = None
        self.ambient = None
        self.alpha = None

    def setDiffuse(self, value):
        self.diffuse = value

    def setAmbient(self, value):
        self.ambient = value

    def setAlpha(self, value):
        self.alpha = value


class _FakePass:
    def __init__(self):
        self.states = []

    def addRenderState(self, state):
        self.states.append(state)


class _FakeTechnique:
    def __init__(self, passes):
        self._passes = passes

    def renderPasses(self):
        return self._passes


class _FakeEffect:
    def __init__(self, techniques):
        self._techniques = techniques

    def techniques(self):
        return self._techniques


class _FakeDepthTest:
    Always = "always"

    def __init__(self, parent):
        self.parent = parent
        self.fn = None

    def setDepthFunction(self, value):
        self.fn = value


class _FakeNoDepthMask:
    def __init__(self, parent):
        self.parent = parent


class _FakeColorMask:
    def __init__(self, parent):
        self.parent = parent
        self.red = None
        self.green = None
        self.blue = None
        self.alpha = None

    def setRedMasked(self, value):
        self.red = value

    def setGreenMasked(self, value):
        self.green = value

    def setBlueMasked(self, value):
        self.blue = value

    def setAlphaMasked(self, value):
        self.alpha = value


class _FakeRenderNs:
    QDepthTest = _FakeDepthTest
    QNoDepthMask = _FakeNoDepthMask
    QColorMask = _FakeColorMask


class _FakeMatWithEffect:
    def __init__(self, effect):
        self._effect = effect

    def effect(self):
        return self._effect


def test_build_torus_mesh_populates_properties():
    mesh = build_torus_mesh(_FakeTorusMesh, radius=4.2, minor=0.6, rings=8, slices=10)

    assert mesh.radius == 4.2
    assert mesh.minor == 0.6
    assert mesh.rings == 8
    assert mesh.slices == 10


def test_make_phong_and_alpha_materials_populate_fields():
    color = QColor(10, 20, 30)
    phong = make_phong_material(_FakeMaterial, color, ambient_lighter=120)
    alpha = make_alpha_material(_FakeMaterial, color, alpha=0.4)

    assert phong.diffuse == color
    assert phong.ambient is not None
    assert alpha.diffuse == color
    assert alpha.ambient == color
    assert alpha.alpha == 0.4


def test_material_always_on_top_refs_adds_depth_states():
    render_pass = _FakePass()
    effect = _FakeEffect([_FakeTechnique([render_pass])])
    refs = material_always_on_top_refs(_FakeMatWithEffect(effect), _FakeRenderNs)

    assert len(refs) == 2
    assert isinstance(refs[0], _FakeDepthTest)
    assert refs[0].fn == "always"
    assert isinstance(refs[1], _FakeNoDepthMask)
    assert len(render_pass.states) == 2


def test_material_no_alpha_write_refs_keeps_rgb_and_masks_alpha():
    render_pass = _FakePass()
    effect = _FakeEffect([_FakeTechnique([render_pass])])
    refs = material_no_alpha_write_refs(_FakeMatWithEffect(effect), _FakeRenderNs)

    assert len(refs) == 1
    assert refs[0] is render_pass.states[0]
    assert refs[0].red is True
    assert refs[0].green is True
    assert refs[0].blue is True
    assert refs[0].alpha is False
