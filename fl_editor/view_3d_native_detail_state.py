from __future__ import annotations

from typing import Any


def selected_native_detail_state(
    *,
    selected_obj: Any,
    requested_obj: Any,
    has_scene_data: bool,
) -> dict[str, object]:
    if selected_obj is None:
        return {
            "clear_detail": True,
            "store_detail": False,
        }
    if requested_obj is not selected_obj:
        return {
            "clear_detail": True,
            "store_detail": False,
        }
    if not has_scene_data:
        return {
            "clear_detail": True,
            "store_detail": False,
        }
    return {
        "clear_detail": False,
        "store_detail": True,
    }
