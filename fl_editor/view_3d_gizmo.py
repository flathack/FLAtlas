from __future__ import annotations

from PySide6.QtGui import QColor


def gizmo_transform_state(
    *,
    center_xyz: tuple[float, float, float] | None,
    cam_pos_xyz: tuple[float, float, float] | None,
    axis_dir_xyz: tuple[float, float, float],
) -> dict[str, object] | None:
    if center_xyz is None or cam_pos_xyz is None:
        return None
    cx, cy, cz = (float(v) for v in center_xyz)
    px, py, pz = (float(v) for v in cam_pos_xyz)
    ax, ay, az = (float(v) for v in axis_dir_xyz)

    vx, vy, vz = px - cx, py - cy, pz - cz
    dist = (vx * vx + vy * vy + vz * vz) ** 0.5
    if dist < 1e-6:
        dir_x, dir_y, dir_z = 0.0, 0.0, 1.0
        dist = 1.0
    else:
        dir_x, dir_y, dir_z = vx / dist, vy / dist, vz / dist

    gizmo_scale = max(1.0, min(6.0, dist / 260.0))
    arm_len = 20.0 * gizmo_scale
    bias = 7.0 * gizmo_scale
    return {
        "translation_xyz": (
            cx + dir_x * bias + ax * arm_len,
            cy + dir_y * bias + ay * arm_len,
            cz + dir_z * bias + az * arm_len,
        ),
        "scale": gizmo_scale,
    }


def gizmo_highlight_colors(axis: str) -> dict[str, QColor]:
    bright = {"x": QColor(255, 180, 180), "y": QColor(180, 255, 180), "z": QColor(180, 200, 255)}
    dim = {"x": QColor(100, 40, 40), "y": QColor(40, 90, 40), "z": QColor(40, 60, 100)}
    return {key: bright[key] if key == axis else dim[key] for key in ("x", "y", "z")}


def gizmo_default_colors() -> dict[str, tuple[QColor, QColor]]:
    defaults = {"x": QColor(255, 80, 80), "y": QColor(80, 220, 80), "z": QColor(80, 140, 255)}
    return {key: (color, color.lighter(140)) for key, color in defaults.items()}


def toggled_locked_axis(current_axis: str | None, clicked_axis: str, *, has_selection: bool) -> str | None:
    if not has_selection:
        return current_axis
    if current_axis == clicked_axis:
        return None
    return clicked_axis
