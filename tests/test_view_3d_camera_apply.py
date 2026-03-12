from __future__ import annotations

from fl_editor.view_3d_camera_apply import apply_camera_update_effects, apply_label_scales, apply_sky_translation


class _FakeCamera:
    def __init__(self):
        self.position_xyz = None
        self.view_center_xyz = None

    def setPosition(self, value):
        self.position_xyz = (value.x(), value.y(), value.z())

    def setViewCenter(self, value):
        self.view_center_xyz = (value.x(), value.y(), value.z())


class _FakeTransform:
    def __init__(self):
        self.translation_xyz = None
        self.scale = None

    def setTranslation(self, value):
        self.translation_xyz = (value.x(), value.y(), value.z())

    def setScale(self, value):
        self.scale = float(value)


def test_apply_sky_translation_updates_transform():
    transform = _FakeTransform()

    apply_sky_translation(sky_transform=transform, sky_translation_xyz=(1.0, 2.0, 3.0))

    assert transform.translation_xyz == (1.0, 2.0, 3.0)


def test_apply_label_scales_updates_all_transforms():
    transforms = [_FakeTransform(), _FakeTransform()]

    apply_label_scales(label_transforms=transforms, label_scales=[0.5, 0.75])

    assert transforms[0].scale == 0.5
    assert transforms[1].scale == 0.75


def test_apply_camera_update_effects_updates_camera_and_callbacks():
    camera = _FakeCamera()
    sky_transform = _FakeTransform()
    label_transform = _FakeTransform()
    calls: list[str] = []

    apply_camera_update_effects(
        camera=camera,
        cam_target_xyz=(4.0, 5.0, 6.0),
        sky_transform=sky_transform,
        label_transforms=[label_transform],
        state={
            "camera_pos_xyz": (1.0, 2.0, 3.0),
            "sky_translation_xyz": (7.0, 8.0, 9.0),
            "label_scales": [1.25],
        },
        update_axis_gizmo=lambda: calls.append("gizmo"),
    )

    assert camera.position_xyz == (1.0, 2.0, 3.0)
    assert camera.view_center_xyz == (4.0, 5.0, 6.0)
    assert sky_transform.translation_xyz == (7.0, 8.0, 9.0)
    assert label_transform.scale == 1.25
    assert calls == ["gizmo"]
