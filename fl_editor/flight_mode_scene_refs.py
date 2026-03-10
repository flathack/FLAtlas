from __future__ import annotations

from PySide6.QtGui import QVector3D

from .flight_mode_navigation import build_lane_path_tuples, is_tradelane_item, item_world_pos_tuple


def item_world_pos_vector(item) -> QVector3D | None:
    pos = item_world_pos_tuple(item)
    if pos is None:
        return None
    return QVector3D(*pos)


def is_tradelane_scene_item(item) -> bool:
    return is_tradelane_item(item)


def lane_path_vectors(selected_obj, objects: list[object]) -> list[QVector3D]:
    return [QVector3D(*pos) for pos in build_lane_path_tuples(selected_obj, objects)]
