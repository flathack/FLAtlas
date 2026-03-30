from __future__ import annotations


def orbit_drag_angles(
    yaw_deg: float,
    pitch_deg: float,
    *,
    delta_x: float,
    delta_y: float,
    yaw_speed: float = 0.35,
    pitch_speed: float = 0.25,
    min_pitch_deg: float = -89.0,
    max_pitch_deg: float = 89.0,
) -> tuple[float, float]:
    next_yaw = float(yaw_deg) - (float(delta_x) * float(yaw_speed))
    next_pitch = float(pitch_deg) + (float(delta_y) * float(pitch_speed))
    return (
        next_yaw,
        max(float(min_pitch_deg), min(float(max_pitch_deg), next_pitch)),
    )