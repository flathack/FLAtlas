from __future__ import annotations

from types import SimpleNamespace

from fl_editor.flight_mode_viewport_context import viewport_camera_pose_context, viewport_orbit_toggle_context


class _Vec:
    def __init__(self, x: float, y: float, z: float):
        self._x = x
        self._y = y
        self._z = z

    def x(self):
        return self._x

    def y(self):
        return self._y

    def z(self):
        return self._z


class _Camera:
    def position(self):
        return _Vec(10.0, 20.0, 30.0)


def test_viewport_camera_pose_context_collects_camera_and_scale():
    calls: list[tuple] = []

    def pose_builder(**kwargs):
        calls.append(kwargs)
        return {"cam_pos_xyz": (1.0, 2.0, 3.0), "view_center_xyz": (4.0, 5.0, 6.0)}

    viewport = SimpleNamespace(_camera=_Camera(), _scene_scale=2.5)
    cam, state = viewport_camera_pose_context(
        viewport=viewport,
        pose_builder=pose_builder,
        orbit_cam_active=True,
        ship_pos_xyz=(7.0, 8.0, 9.0),
        forward_xyz=(0.0, 0.0, 1.0),
        chase_distance_ship_lengths=1.8,
        orbit_yaw=0.1,
        orbit_pitch=0.2,
        orbit_distance=95.0,
    )

    assert cam is viewport._camera
    assert state == {"cam_pos_xyz": (1.0, 2.0, 3.0), "view_center_xyz": (4.0, 5.0, 6.0)}
    assert calls[0]["scale"] == 2.5


def test_viewport_camera_pose_context_returns_none_without_camera():
    cam, state = viewport_camera_pose_context(
        viewport=SimpleNamespace(_scene_scale=2.5),
        pose_builder=lambda **kwargs: kwargs,
        orbit_cam_active=False,
        ship_pos_xyz=(0.0, 0.0, 0.0),
        forward_xyz=(0.0, 0.0, 1.0),
        chase_distance_ship_lengths=1.8,
        orbit_yaw=0.0,
        orbit_pitch=0.0,
        orbit_distance=95.0,
    )
    assert cam is None
    assert state is None


def test_viewport_orbit_toggle_context_collects_camera_position():
    calls: list[tuple] = []

    def orbit_toggle_builder(**kwargs):
        calls.append(kwargs)
        return {"orbit_active": True}

    viewport = SimpleNamespace(_camera=_Camera(), _scene_scale=2.5)
    state = viewport_orbit_toggle_context(
        viewport=viewport,
        orbit_toggle_builder=orbit_toggle_builder,
        orbit_active=False,
        ship_pos_xyz=(7.0, 8.0, 9.0),
    )

    assert state == {"orbit_active": True}
    assert calls[0]["cam_pos_xyz"] == (10.0, 20.0, 30.0)
    assert calls[0]["scale"] == 2.5
