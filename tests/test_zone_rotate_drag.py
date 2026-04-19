from __future__ import annotations

import pytest

from fl_editor.main_window import MainWindow


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
