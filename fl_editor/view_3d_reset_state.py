from __future__ import annotations


def scene_clear_state() -> dict[str, object]:
    return {
        "clear_obj_map": True,
        "clear_obj_by_nick": True,
        "clear_obj_component_refs": True,
        "clear_obj_label_ent": True,
        "clear_obj_label_tr": True,
        "clear_obj_label_yoff": True,
        "clear_zone_map": True,
        "clear_zone_component_refs": True,
        "clear_zone_entities": True,
        "selected_obj": None,
        "locked_axis": None,
        "clear_obj_sphere_ent": True,
        "clear_axis_gizmo": True,
    }


def gizmo_clear_state(*, has_locked_axis: bool) -> dict[str, object]:
    return {
        "clear_entities": True,
        "clear_refs": True,
        "clear_mats": True,
        "clear_nodes": True,
        "axis_gizmo_center": None,
        "clear_locked_axis": bool(has_locked_axis),
    }
