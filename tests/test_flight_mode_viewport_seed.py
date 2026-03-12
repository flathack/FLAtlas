from __future__ import annotations

from types import SimpleNamespace

from fl_editor.flight_mode_viewport_seed import viewport_camera_seed_state


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

    def viewCenter(self):
        return _Vec(40.0, 50.0, 60.0)


def test_viewport_camera_seed_state_passes_viewport_camera_context_to_builder():
    calls: list[tuple[tuple[float, float, float] | None, tuple[float, float, float] | None, float]] = []

    def seed_builder(*, cam_pos_xyz, view_center_xyz, scale):
        calls.append((cam_pos_xyz, view_center_xyz, scale))
        return {"ship_pos_xyz": (1.0, 2.0, 3.0), "yaw": 0.0, "pitch": 0.0, "roll": 0.0}

    viewport = SimpleNamespace(_camera=_Camera(), _scene_scale=2.5)
    state = viewport_camera_seed_state(viewport=viewport, seed_builder=seed_builder)

    assert state["ship_pos_xyz"] == (1.0, 2.0, 3.0)
    assert calls == [((10.0, 20.0, 30.0), (40.0, 50.0, 60.0), 2.5)]


def test_viewport_camera_seed_state_handles_missing_viewport_camera():
    calls: list[tuple[tuple[float, float, float] | None, tuple[float, float, float] | None, float]] = []

    def seed_builder(*, cam_pos_xyz, view_center_xyz, scale):
        calls.append((cam_pos_xyz, view_center_xyz, scale))
        return {"ship_pos_xyz": (0.0, 0.0, 0.0), "yaw": 0.0, "pitch": 0.0, "roll": 0.0}

    state = viewport_camera_seed_state(viewport=None, seed_builder=seed_builder)

    assert state["ship_pos_xyz"] == (0.0, 0.0, 0.0)
    assert calls == [(None, None, 1.0)]
