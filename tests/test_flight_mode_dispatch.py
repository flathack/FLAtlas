from __future__ import annotations

from fl_editor.flight_mode_dispatch import (
    apply_hud_dispatch,
    apply_overlay_dispatch,
    hud_dispatch_state,
    overlay_dispatch_state,
)


def test_hud_dispatch_state_for_inactive_controller():
    assert hud_dispatch_state(active=False, snapshot={"mode": "NORMAL"}) == {
        "hud_snapshot": None,
        "dispatch_to_callback": True,
        "dispatch_to_viewport": True,
    }


def test_hud_dispatch_state_for_active_controller():
    snapshot = {"mode": "AUTOPILOT"}
    assert hud_dispatch_state(active=True, snapshot=snapshot) == {
        "hud_snapshot": snapshot,
        "dispatch_to_callback": True,
        "dispatch_to_viewport": True,
    }


def test_overlay_dispatch_state_reflects_viewport_presence():
    assert overlay_dispatch_state(has_viewport=True, text="overlay") == {
        "dispatch": True,
        "text": "overlay",
    }
    assert overlay_dispatch_state(has_viewport=False, text="overlay") == {
        "dispatch": False,
        "text": "overlay",
    }


class _Viewport:
    def __init__(self):
        self.overlay_calls: list[str] = []
        self.hud_calls: list[object] = []

    def set_flight_overlay_text(self, text: str):
        self.overlay_calls.append(text)

    def update_flight_visuals(self, snapshot):
        self.hud_calls.append(snapshot)


def test_apply_overlay_dispatch_calls_viewport_only_when_enabled():
    viewport = _Viewport()
    apply_overlay_dispatch(viewport=viewport, state={"dispatch": True, "text": "overlay"})
    apply_overlay_dispatch(viewport=viewport, state={"dispatch": False, "text": "ignored"})
    assert viewport.overlay_calls == ["overlay"]


def test_apply_hud_dispatch_calls_callback_and_viewport():
    viewport = _Viewport()
    callback_calls: list[object] = []
    state = {"dispatch_to_callback": True, "dispatch_to_viewport": True, "hud_snapshot": {"mode": "NORMAL"}}
    apply_hud_dispatch(callback=callback_calls.append, viewport=viewport, state=state)
    assert callback_calls == [{"mode": "NORMAL"}]
    assert viewport.hud_calls == [{"mode": "NORMAL"}]
