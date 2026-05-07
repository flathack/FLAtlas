from __future__ import annotations


def selection_state(
    *,
    has_object: bool,
    is_same_selected: bool,
    move_mode: bool,
) -> dict[str, object]:
    if not has_object:
        return {
            "new_selected": None,
            "clear_locked_axis": True,
            "clear_gizmo": True,
            "show_gizmo": False,
            "selection_changed": True,
        }
    if is_same_selected:
        return {
            "selection_changed": False,
        }
    return {
        "selection_changed": True,
        "clear_locked_axis": True,
        "clear_gizmo": not move_mode,
        "show_gizmo": bool(move_mode),
    }


def item_visibility_state(*, is_object: bool, visible: bool, labels_visible: bool) -> dict[str, object]:
    enabled = bool(visible)
    return {
        "entity_enabled": enabled,
        "label_enabled": enabled and bool(labels_visible) if is_object else None,
    }


def label_visibility_state(*, enabled: bool) -> dict[str, object]:
    return {
        "labels_visible": bool(enabled),
        "entity_enabled": bool(enabled),
    }


def move_mode_state(*, enabled: bool, has_selected_obj: bool, has_locked_axis: bool) -> dict[str, object]:
    return {
        "move_mode": bool(enabled),
        "clear_locked_axis": bool(has_locked_axis),
        "show_gizmo": bool(enabled and has_selected_obj),
        "clear_gizmo": bool((not enabled) and has_selected_obj),
    }


def position_update_state(*, is_selected: bool, move_mode: bool, has_label: bool, locked_axis: str | None) -> dict[str, object]:
    return {
        "update_label": bool(has_label),
        "rebuild_gizmo": bool(is_selected and move_mode),
        "restore_locked_axis": locked_axis if is_selected and move_mode and locked_axis else None,
    }
