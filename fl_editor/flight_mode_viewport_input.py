from __future__ import annotations

from typing import Any, Callable


def viewport_mouse_offset_state(
    *,
    viewport: Any,
    mouse_pos_xy: tuple[float, float],
    mouse_flight_active: bool,
    offset_builder: Callable[..., tuple[float, float, float]],
) -> tuple[float, float, float]:
    viewport_size = None
    if viewport is not None:
        viewport_size = (int(viewport.width()), int(viewport.height()))
    return offset_builder(
        viewport_size=viewport_size,
        mouse_pos_xy=mouse_pos_xy,
        mouse_flight_active=mouse_flight_active,
    )
