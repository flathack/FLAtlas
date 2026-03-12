from __future__ import annotations

import math


def seeded_flight_state_from_selection(*, selected_pos_xyz: tuple[float, float, float] | None, lateral_offset: float = 2000.0) -> dict[str, object] | None:
    if selected_pos_xyz is None:
        return None
    tx, _ty, tz = (float(v) for v in selected_pos_xyz)
    target_xyz = (tx, 0.0, tz)
    ship_pos_xyz = (tx + float(lateral_offset), 0.0, tz)
    to_target_x = target_xyz[0] - ship_pos_xyz[0]
    to_target_z = target_xyz[2] - ship_pos_xyz[2]
    length = math.sqrt(to_target_x * to_target_x + to_target_z * to_target_z)
    if length < 1e-5:
        to_target_x = -1.0
        to_target_z = 0.0
        length = 1.0
    dir_x = to_target_x / length
    dir_z = to_target_z / length
    return {
        "ship_pos_xyz": ship_pos_xyz,
        "yaw": math.atan2(dir_x, dir_z),
        "pitch": 0.0,
        "roll": 0.0,
    }
