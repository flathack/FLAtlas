from __future__ import annotations

import math
import re

from PySide6.QtGui import QQuaternion, QVector3D


def extract_arch_size(arch: str, default: float) -> float:
    match = re.search(r"_(\d+)(?:\D*$|$)", str(arch))
    if not match:
        return float(default)
    try:
        return float(match.group(1))
    except Exception:
        return float(default)


def scaled_radius_from_arch(
    arch: str,
    *,
    default_size: float,
    base_size: float,
    base_radius: float,
    min_r: float,
    max_r: float,
) -> float:
    size = extract_arch_size(arch, default_size)
    ratio = max(0.25, size / max(1.0, base_size))
    return max(min_r, min(max_r, base_radius * (ratio ** 0.5)))


def parse_triplet(raw: str) -> tuple[float, float, float]:
    parts = [p.strip() for p in str(raw).split(",")]
    values: list[float] = []
    for i in range(3):
        try:
            values.append(float(parts[i]) if i < len(parts) else 0.0)
        except Exception:
            values.append(0.0)
    return values[0], values[1], values[2]


def parse_rotate(raw: str) -> tuple[float, float, float]:
    return parse_triplet(raw)


def parse_pos(raw: str) -> tuple[float, float, float]:
    return parse_triplet(raw)


def is_trade_lane_object(*, nickname: str, archetype: str) -> bool:
    arch = str(archetype or "").lower()
    name = str(nickname or "").lower()
    return any(tag in name or tag in arch for tag in ("trade_lane_ring", "tradelane_ring"))


def rotation_quaternion_from_fl(rx: float, ry: float, rz: float) -> QQuaternion:
    tol = 0.25
    rx_f = float(rx)
    ry_f = float(ry)
    rz_f = float(rz)
    if abs(abs(rx_f) - 180.0) <= tol and abs(abs(rz_f) - 180.0) <= tol:
        # Rx(±180) · Rz(±180) = Ry(180), so the effective rotation is
        # Ry(ry + 180).  Collapse to a pure Y rotation to avoid gimbal-lock
        # artefacts that can differ between Qt3D backends (Linux/Windows).
        rx_f = 0.0
        ry_f = ry_f + 180.0
        rz_f = 0.0
        if ry_f > 180.0:
            ry_f -= 360.0
        elif ry_f < -180.0:
            ry_f += 360.0
    return QQuaternion.fromEulerAngles(rx_f, ry_f, rz_f)


def tradelane_direction_quaternion(
    *,
    current_pos_raw: str,
    prev_pos_raw: str | None,
    next_pos_raw: str | None,
) -> QQuaternion | None:
    if not prev_pos_raw and not next_pos_raw:
        return None

    cur = QVector3D(*parse_pos(current_pos_raw))
    if prev_pos_raw and next_pos_raw:
        prev = QVector3D(*parse_pos(prev_pos_raw))
        nxt = QVector3D(*parse_pos(next_pos_raw))
        direction = nxt - prev
    elif next_pos_raw:
        nxt = QVector3D(*parse_pos(next_pos_raw))
        direction = nxt - cur
    else:
        prev = QVector3D(*parse_pos(prev_pos_raw or "0,0,0"))
        direction = cur - prev

    if direction.length() < 1e-6:
        return None
    direction = direction.normalized()
    yaw_deg = math.degrees(math.atan2(direction.x(), direction.z()))
    flat_len = math.sqrt(direction.x() * direction.x() + direction.z() * direction.z())
    pitch_deg = -math.degrees(math.atan2(direction.y(), flat_len))
    return QQuaternion.fromEulerAngles(float(pitch_deg), float(yaw_deg), 0.0)


def object_rotation_quaternion(
    *,
    nickname: str,
    archetype: str,
    rotate_raw: str,
    current_pos_raw: str,
    prev_pos_raw: str | None,
    next_pos_raw: str | None,
) -> QQuaternion:
    if is_trade_lane_object(nickname=nickname, archetype=archetype):
        quat = tradelane_direction_quaternion(
            current_pos_raw=current_pos_raw,
            prev_pos_raw=prev_pos_raw,
            next_pos_raw=next_pos_raw,
        )
        if quat is not None:
            return quat
    rx, ry, rz = parse_rotate(rotate_raw)
    return rotation_quaternion_from_fl(rx, ry, rz)
