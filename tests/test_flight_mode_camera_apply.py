from __future__ import annotations

from fl_editor.flight_mode_camera_apply import apply_viewport_camera_state


class _FakeCamera:
    def __init__(self):
        self.position_xyz = None
        self.view_center_xyz = None

    def setPosition(self, value):
        self.position_xyz = (value.x(), value.y(), value.z())

    def setViewCenter(self, value):
        self.view_center_xyz = (value.x(), value.y(), value.z())


class _FakeViewport:
    def __init__(self):
        self.sky_sync_calls = 0
        self.label_update_calls = 0

    def _sync_sky_to_camera(self):
        self.sky_sync_calls += 1

    def _update_label_scales(self):
        self.label_update_calls += 1


def test_apply_viewport_camera_state_updates_camera_and_viewport():
    cam = _FakeCamera()
    viewport = _FakeViewport()

    apply_viewport_camera_state(
        cam=cam,
        viewport=viewport,
        state={
            "cam_pos_xyz": (1.0, 2.0, 3.0),
            "view_center_xyz": (4.0, 5.0, 6.0),
            "sync_sky": True,
            "update_labels": True,
        },
    )

    assert cam.position_xyz == (1.0, 2.0, 3.0)
    assert cam.view_center_xyz == (4.0, 5.0, 6.0)
    assert viewport.sky_sync_calls == 1
    assert viewport.label_update_calls == 1


def test_apply_viewport_camera_state_skips_optional_side_effects():
    cam = _FakeCamera()
    viewport = _FakeViewport()

    apply_viewport_camera_state(
        cam=cam,
        viewport=viewport,
        state={
            "cam_pos_xyz": (0.0, 0.0, 0.0),
            "view_center_xyz": (1.0, 1.0, 1.0),
            "sync_sky": False,
            "update_labels": False,
        },
    )

    assert cam.position_xyz == (0.0, 0.0, 0.0)
    assert cam.view_center_xyz == (1.0, 1.0, 1.0)
    assert viewport.sky_sync_calls == 0
    assert viewport.label_update_calls == 0
