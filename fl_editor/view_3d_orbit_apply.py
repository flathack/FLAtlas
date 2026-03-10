from __future__ import annotations

from typing import Any

from PySide6.QtGui import QVector3D


def apply_synced_orbit_camera_state(*, view: Any, state: dict[str, object]) -> None:
    view._cam_target = QVector3D(*state["target_xyz"])
    view._cam_distance = float(state["distance"])
    view._cam_yaw = float(state["yaw"])
    view._cam_pitch = float(state["pitch"])
