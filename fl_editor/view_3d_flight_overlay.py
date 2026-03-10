from __future__ import annotations


def flight_overlay_layout(
    *,
    host_width: float,
    overlay_height: float,
    help_overlay_visible: bool,
    help_overlay_width: float,
) -> dict[str, object]:
    y = 8
    overlay_pos = (8, y)
    charge_bar_geometry = (8, y + int(float(overlay_height)) + 6, 260, 20)
    help_overlay_pos = None
    if help_overlay_visible:
        help_overlay_pos = (max(8, int(float(host_width) - float(help_overlay_width) - 8)), y)
    return {
        "overlay_pos": overlay_pos,
        "charge_bar_geometry": charge_bar_geometry,
        "help_overlay_pos": help_overlay_pos,
    }


def flight_overlay_text_state(*, text: str) -> dict[str, object]:
    _ = text
    return {
        "text": "",
        "visible": False,
    }


def cruise_charge_bar_state(*, snapshot: dict[str, object]) -> dict[str, object]:
    _ = snapshot
    return {
        "visible": False,
    }
