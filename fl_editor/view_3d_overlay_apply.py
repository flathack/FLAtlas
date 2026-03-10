from __future__ import annotations

from typing import Any


def apply_flight_overlay_text(*, overlay: Any, state: dict[str, object]) -> None:
    overlay.setText(str(state["text"]))
    overlay.setVisible(bool(state["visible"]))


def apply_cruise_charge_bar(*, charge_bar: Any, state: dict[str, object]) -> None:
    charge_bar.setVisible(bool(state["visible"]))


def apply_flight_overlay_layout(
    *,
    overlay: Any,
    charge_bar: Any,
    help_overlay: Any,
    state: dict[str, object],
) -> None:
    overlay.move(*state["overlay_pos"])
    charge_bar.setGeometry(*state["charge_bar_geometry"])
    if state.get("help_overlay_pos") is not None:
        help_overlay.move(*state["help_overlay_pos"])
