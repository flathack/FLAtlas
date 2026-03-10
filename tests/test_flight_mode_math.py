from __future__ import annotations

import math

from fl_editor.flight_mode_math import approach_angle_value, approach_value, wrap_pi


def test_approach_value_caps_step_and_snaps_when_close():
    assert approach_value(cur=0.0, target=10.0, max_step=2.0) == 2.0
    assert approach_value(cur=9.0, target=10.0, max_step=2.0) == 10.0


def test_wrap_pi_normalizes_angle_range():
    assert round(wrap_pi(3.5), 6) == round(3.5 - 2.0 * math.pi, 6)
    assert round(wrap_pi(-3.5), 6) == round(-3.5 + 2.0 * math.pi, 6)


def test_approach_angle_value_uses_wrapped_delta():
    value = approach_angle_value(cur=3.0, target=-3.0, max_step=0.2)
    assert round(value, 6) == round(3.2, 6)
