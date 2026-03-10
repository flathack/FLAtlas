"""Viewport-Kamera-Seiteneffekte fuer den Flight-Mode."""

from __future__ import annotations

from typing import Any

from PySide6.QtGui import QVector3D


def apply_viewport_camera_state(*, cam: Any, viewport: Any, state: dict[str, object]) -> None:
    """Wendet eine vorberechnete Kameraansicht auf Kamera und Viewport an."""
    cam.setPosition(QVector3D(*state["cam_pos_xyz"]))
    cam.setViewCenter(QVector3D(*state["view_center_xyz"]))
    if state.get("sync_sky") and hasattr(viewport, "_sync_sky_to_camera"):
        viewport._sync_sky_to_camera()
    if state.get("update_labels") and hasattr(viewport, "_update_label_scales"):
        viewport._update_label_scales()
