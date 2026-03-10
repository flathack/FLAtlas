from __future__ import annotations

from fl_editor.view_3d_orbit_apply import apply_synced_orbit_camera_state


class _FakeView:
    def __init__(self):
        self._cam_target = None
        self._cam_distance = None
        self._cam_yaw = None
        self._cam_pitch = None


def test_apply_synced_orbit_camera_state_updates_view_state():
    view = _FakeView()

    apply_synced_orbit_camera_state(
        view=view,
        state={
            "target_xyz": (1.0, 2.0, 3.0),
            "distance": 50.0,
            "yaw": 0.4,
            "pitch": -0.2,
        },
    )

    assert (view._cam_target.x(), view._cam_target.y(), view._cam_target.z()) == (1.0, 2.0, 3.0)
    assert view._cam_distance == 50.0
    assert view._cam_yaw == 0.4
    assert view._cam_pitch == -0.2
