from __future__ import annotations

import math


def approach_value(*, cur: float, target: float, max_step: float) -> float:
    delta = float(target) - float(cur)
    if abs(delta) <= float(max_step):
        return float(target)
    return float(cur) + float(max_step) * (1.0 if delta > 0.0 else -1.0)


def wrap_pi(value: float) -> float:
    return (float(value) + math.pi) % (2.0 * math.pi) - math.pi


def approach_angle_value(*, cur: float, target: float, max_step: float) -> float:
    delta = wrap_pi(float(target) - float(cur))
    if abs(delta) <= float(max_step):
        return float(target)
    return float(cur) + float(max_step) * (1.0 if delta > 0.0 else -1.0)
