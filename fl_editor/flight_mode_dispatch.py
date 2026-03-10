from __future__ import annotations


def hud_dispatch_state(*, active: bool, snapshot: dict[str, object] | None) -> dict[str, object]:
    if not active:
        return {
            "hud_snapshot": None,
            "dispatch_to_callback": True,
            "dispatch_to_viewport": True,
        }
    return {
        "hud_snapshot": snapshot,
        "dispatch_to_callback": True,
        "dispatch_to_viewport": True,
    }


def overlay_dispatch_state(*, has_viewport: bool, text: str) -> dict[str, object]:
    return {
        "dispatch": bool(has_viewport),
        "text": str(text),
    }


def apply_overlay_dispatch(*, viewport: object | None, state: dict[str, object]) -> None:
    if not bool(state.get("dispatch")):
        return
    if viewport is not None and hasattr(viewport, "set_flight_overlay_text"):
        viewport.set_flight_overlay_text(str(state.get("text", "")))


def apply_hud_dispatch(
    *,
    callback: object | None,
    viewport: object | None,
    state: dict[str, object],
) -> None:
    if bool(state.get("dispatch_to_callback")) and callable(callback):
        callback(state.get("hud_snapshot"))
    if bool(state.get("dispatch_to_viewport")) and viewport is not None and hasattr(viewport, "update_flight_visuals"):
        viewport.update_flight_visuals(state.get("hud_snapshot"))
