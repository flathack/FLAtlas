"""Helpers for reading and applying object rotation values."""

from __future__ import annotations


def normalize_angle_180(value: float) -> float:
    result = (float(value) + 180.0) % 360.0 - 180.0
    if abs(result + 180.0) < 1e-9:
        return 180.0
    return result


def parse_object_rotate(raw_value: str) -> tuple[float, float, float]:
    parts = [part.strip() for part in str(raw_value or "0,0,0").split(",")]

    def _part(index: int) -> float:
        try:
            return float(parts[index]) if len(parts) > index else 0.0
        except ValueError:
            return 0.0

    return (_part(0), _part(1), _part(2))


def apply_object_rotate_entries(entries, rot_xyz: tuple[float, float, float]) -> tuple[list[tuple[str, str]], str]:
    rx = normalize_angle_180(rot_xyz[0])
    ry = normalize_angle_180(rot_xyz[1])
    rz = normalize_angle_180(rot_xyz[2])
    rotate_str = f"{rx:.0f}, {ry:.0f}, {rz:.0f}"
    updated = list(entries)
    for index, (key, _value) in enumerate(updated):
        if str(key).lower() == "rotate":
            updated[index] = (key, rotate_str)
            break
    else:
        updated.append(("rotate", rotate_str))
    return updated, rotate_str
