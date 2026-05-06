from __future__ import annotations

import warnings

import pytest
from PySide6.QtCore import QPointF

from fl_editor.main_window import MainWindow
from fl_editor.models import ZoneItem


def _zone_data(*, nickname: str = "test_zone", rotate: str = "0,0,0") -> dict:
    entries = [
        ("nickname", nickname),
        ("shape", "ELLIPSOID"),
        ("size", "4000, 1000, 1200"),
        ("rotate", rotate),
        ("pos", "0,0,0"),
    ]
    data = {"_entries": entries}
    for key, value in entries:
        data[key.lower()] = value
    return data


def test_zone_drag_rotation_moving_mouse_up_turns_left():
    angle = MainWindow._zone_rotate_angle_from_vertical_drag(15.0, 200.0, 150.0)

    assert angle == pytest.approx(25.0, abs=0.001)



def test_zone_drag_rotation_moving_mouse_down_turns_right_with_snap():
    angle = MainWindow._zone_rotate_angle_from_vertical_drag(
        0.0,
        100.0,
        140.0,
        snap_mode=True,
    )

    assert angle == pytest.approx(-10.0, abs=0.001)


def test_zone_rotate_wheel_updates_preview_yaw(qapp, monkeypatch):
    window = MainWindow.__new__(MainWindow)
    zone = ZoneItem(_zone_data(), 1.0)
    applied: list[list[tuple[str, str]]] = []
    messages: list[str] = []

    class _StatusBar:
        def showMessage(self, message: str) -> None:
            messages.append(message)

    monkeypatch.setattr(window, "statusBar", lambda: _StatusBar())
    window._zones = [zone]
    window._pending_zone_rotate = {
        "zone": zone,
        "start_scene_y": 0.0,
        "last_scene_y": 0.0,
        "wheel_offset": 0.0,
        "start_rot": (0.0, 0.0, 0.0),
        "preview_rot": (0.0, 0.0, 0.0),
        "old_entries": list(zone.data["_entries"]),
    }
    window._apply_zone_entries_preview = lambda _zone, entries, update_editor=False: applied.append(entries)

    MainWindow._update_zone_rotate_preview_from_wheel(window, QPointF(0.0, 0.0), 120)

    assert window._pending_zone_rotate["preview_rot"] == pytest.approx((0.0, 5.0, 0.0))
    assert ("rotate", "0.00, 5.00, 0.00") in applied[-1]
    assert messages


def test_zone_rotate_preview_signal_disconnect_is_idempotent(qapp):
    window = MainWindow.__new__(MainWindow)

    class _Signal:
        def __init__(self) -> None:
            self.slots = []

        def connect(self, slot) -> None:
            self.slots.append(slot)

        def disconnect(self, slot) -> None:
            if slot not in self.slots:
                warnings.warn("not connected", RuntimeWarning, stacklevel=2)
                return
            self.slots.remove(slot)

    class _View:
        def __init__(self) -> None:
            self.mouse_moved = _Signal()
            self.wheel_scrolled = _Signal()

    first_view = _View()
    second_view = _View()

    window.view = first_view
    assert MainWindow._connect_zone_rotate_preview_signals(window) is True

    window.view = second_view
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert MainWindow._connect_zone_rotate_preview_signals(window) is True
        assert MainWindow._disconnect_zone_rotate_preview_signals(window) is True
        assert MainWindow._disconnect_zone_rotate_preview_signals(window) is False

    assert caught == []
    assert first_view.mouse_moved.slots == []
    assert first_view.wheel_scrolled.slots == []
    assert second_view.mouse_moved.slots == []
    assert second_view.wheel_scrolled.slots == []
