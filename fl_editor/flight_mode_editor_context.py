"""Editor-Kontext-Helfer fuer Flight-Mode Selection- und Target-State."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtGui import QVector3D


def selected_target_context(
    *,
    selected_item: Any,
    ship_pos: QVector3D,
    item_world_pos: Callable[[Any], QVector3D | None],
) -> dict[str, object]:
    """Liefert Namen und Distanz fuer das aktuell selektierte Objekt."""
    if selected_item is None:
        return {"name": "", "distance": None}
    pos = item_world_pos(selected_item)
    if pos is None:
        return {"name": "", "distance": None}
    return {
        "name": str(getattr(selected_item, "nickname", "Selection")),
        "distance": float((pos - ship_pos).length()),
    }


def autopilot_target_context(
    *,
    mode: str,
    autopilot_mode: str,
    auto_target: Any,
    target_name: str,
    ship_pos: QVector3D,
    item_world_pos: Callable[[Any], QVector3D | None],
) -> dict[str, object]:
    """Liefert Namen und Distanz fuer das aktuelle Autopilot-Ziel."""
    if mode != autopilot_mode or auto_target is None:
        return {"name": target_name, "distance": None}
    pos = item_world_pos(auto_target)
    if pos is None:
        return {"name": target_name, "distance": None}
    return {
        "name": target_name,
        "distance": float((pos - ship_pos).length()),
    }
