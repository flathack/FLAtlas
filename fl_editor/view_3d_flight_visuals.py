from __future__ import annotations

import math
import random


def initial_dust_positions(count: int, rng: random.Random | random.Random = random) -> list[tuple[float, float, float]]:
    return [
        (
            float(rng.uniform(-26.0, 26.0)),
            float(rng.uniform(-14.0, 12.0)),
            float(rng.uniform(8.0, 180.0)),
        )
        for _ in range(max(0, int(count)))
    ]


def flight_ship_render_pose(
    *,
    snapshot: dict[str, object],
    scene_scale: float,
    camera_pos_xyz: tuple[float, float, float] | None,
    camera_view_center_xyz: tuple[float, float, float] | None,
) -> dict[str, object]:
    x, y, z = snapshot.get("pos", (0.0, 0.0, 0.0))
    yaw_deg = float(snapshot.get("yaw_deg", 0.0))
    pitch_deg = float(snapshot.get("pitch_deg", 0.0))
    tilt_deg = float(snapshot.get("ship_tilt_deg", 0.0))

    pos_xyz: tuple[float, float, float] | None = None
    if camera_pos_xyz is not None and camera_view_center_xyz is not None:
        fx = float(camera_view_center_xyz[0]) - float(camera_pos_xyz[0])
        fy = float(camera_view_center_xyz[1]) - float(camera_pos_xyz[1])
        fz = float(camera_view_center_xyz[2]) - float(camera_pos_xyz[2])
        length = math.sqrt(fx * fx + fy * fy + fz * fz)
        if length > 1e-5:
            pos_xyz = (
                float(camera_pos_xyz[0]) + fx / length * 2.1,
                float(camera_pos_xyz[1]) + fy / length * 2.1,
                float(camera_pos_xyz[2]) + fz / length * 2.1,
            )
    if pos_xyz is None:
        scale = float(scene_scale or 1.0)
        pos_xyz = (float(x) * scale, float(y) * scale, float(z) * scale)

    return {
        "pos_xyz": pos_xyz,
        "rotation_euler_deg": (pitch_deg + tilt_deg, yaw_deg, 0.0),
    }


def dust_update_state(
    *,
    snapshot: dict[str, object],
    local_positions_xyz: list[tuple[float, float, float]],
    scene_scale: float,
    dt: float = 0.016,
    rng: random.Random | random.Random = random,
) -> dict[str, object]:
    x, y, z = snapshot.get("pos", (0.0, 0.0, 0.0))
    f = snapshot.get("forward", (0.0, 0.0, 1.0))
    fx = float(f[0])
    fy = float(f[1])
    fz = float(f[2])
    fwd_len = math.sqrt(fx * fx + fy * fy + fz * fz)
    if fwd_len < 1e-5:
        fx, fy, fz = 0.0, 0.0, 1.0
        fwd_len = 1.0
    fx, fy, fz = fx / fwd_len, fy / fwd_len, fz / fwd_len

    rx = -fz
    ry = 0.0
    rz = fx
    right_len = math.sqrt(rx * rx + ry * ry + rz * rz)
    if right_len < 1e-5:
        rx, ry, rz = 1.0, 0.0, 0.0
        right_len = 1.0
    rx, ry, rz = rx / right_len, ry / right_len, rz / right_len

    ux = ry * fz - rz * fy
    uy = rz * fx - rx * fz
    uz = rx * fy - ry * fx
    up_len = math.sqrt(ux * ux + uy * uy + uz * uz)
    if up_len < 1e-5:
        ux, uy, uz = 0.0, 1.0, 0.0
    else:
        ux, uy, uz = ux / up_len, uy / up_len, uz / up_len

    scale = float(scene_scale or 1.0)
    ship_world = (float(x) * scale, float(y) * scale, float(z) * scale)
    speed = float(snapshot.get("speed", 0.0))
    flow = max(8.0, speed * 0.22)

    next_local_positions: list[tuple[float, float, float]] = []
    world_positions: list[tuple[float, float, float]] = []
    for local_x, local_y, local_z in list(local_positions_xyz or []):
        next_z = float(local_z) - flow * float(dt)
        next_x = float(local_x)
        next_y = float(local_y)
        if next_z < 2.0:
            next_x = float(rng.uniform(-26.0, 26.0))
            next_y = float(rng.uniform(-14.0, 12.0))
            next_z = float(rng.uniform(130.0, 220.0))
        next_local_positions.append((next_x, next_y, next_z))
        world_positions.append(
            (
                ship_world[0] + rx * next_x + ux * next_y + fx * next_z,
                ship_world[1] + ry * next_x + uy * next_y + fy * next_z,
                ship_world[2] + rz * next_x + uz * next_y + fz * next_z,
            )
        )

    return {
        "local_positions_xyz": next_local_positions,
        "world_positions_xyz": world_positions,
        "enabled": True,
    }
