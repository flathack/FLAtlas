"""Editor-Kontext-Helfer fuer Flight-Mode Selection- und Target-State."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtGui import QVector3D

from .flight_mode_snapshot import flight_target_context_state


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


def editor_target_context(
    *,
    selected_item: Any,
    mode: str,
    autopilot_mode: str,
    auto_target: Any,
    target_name: str,
    ship_pos: QVector3D,
    item_world_pos: Callable[[Any], QVector3D | None],
) -> dict[str, object]:
    """Kombiniert Selection- und Autopilot-Kontext fuer HUD und Overlay."""
    selection_state = selected_target_context(
        selected_item=selected_item,
        ship_pos=ship_pos,
        item_world_pos=item_world_pos,
    )
    autopilot_state = autopilot_target_context(
        mode=mode,
        autopilot_mode=autopilot_mode,
        auto_target=auto_target,
        target_name=target_name,
        ship_pos=ship_pos,
        item_world_pos=item_world_pos,
    )
    return flight_target_context_state(
        selection_name=str(selection_state["name"]),
        selection_distance=selection_state["distance"],
        mode=mode,
        autopilot_mode=autopilot_mode,
        auto_target_name=str(autopilot_state["name"]),
        auto_target_distance=autopilot_state["distance"],
    )
