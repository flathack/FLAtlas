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
