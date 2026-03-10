"""Editor-Szenenadapter fuer Flight-Mode-Auswahlpfade."""

from __future__ import annotations

from typing import Any

from PySide6.QtGui import QVector3D

from .flight_mode_actions import autopilot_selection_state
from .flight_mode_mode_paths import tradelane_start_state
from .flight_mode_scene_refs import is_tradelane_scene_item, item_world_pos_vector, lane_path_vectors


def autopilot_selection_from_editor(*, editor: Any, autopilot_mode: str) -> dict[str, object] | None:
    """Liefert den Autopilot-Startzustand aus der aktuellen Editor-Selection."""
    target = getattr(editor, "_selected", None) if editor is not None else None
    state = autopilot_selection_state(
        has_editor=editor is not None,
        target_name=getattr(target, "nickname", "Target"),
        target_pos_xyz=item_world_pos_vector(target),
        autopilot_mode=autopilot_mode,
    )
    if state is None:
        return None
    return {
        "target": target,
        "target_name": str(state["auto_target_name"]),
        "mode": str(state["mode"]),
    }


def tradelane_selection_from_editor(
    *,
    editor: Any,
    ship_pos: QVector3D,
    yaw: float,
    pitch: float,
    dock_radius: float,
    tradelane_speed: float,
    forward_xyz: tuple[float, float, float],
) -> dict[str, object] | None:
    """Liefert den Tradelane-Startzustand aus der aktuellen Editor-Selection."""
    if editor is None:
        return None
    selected_obj = getattr(editor, "_selected", None)
    if not is_tradelane_scene_item(selected_obj):
        return None
    lane_path = lane_path_vectors(selected_obj, list(getattr(editor, "_objects", [])))
    state = tradelane_start_state(
        lane_points_xyz=[(point.x(), point.y(), point.z()) for point in lane_path],
        ship_pos_xyz=(ship_pos.x(), ship_pos.y(), ship_pos.z()),
        forward_xyz=forward_xyz,
        dock_radius=dock_radius,
        tradelane_speed=tradelane_speed,
    )
    return {
        "lane_path": lane_path,
        "status": str(state["status"]),
        "lane_index": int(state.get("lane_index", 0)),
        "ship_pos_xyz": state.get("ship_pos_xyz"),
        "speed": state.get("speed"),
        "mode": state.get("mode"),
    }
