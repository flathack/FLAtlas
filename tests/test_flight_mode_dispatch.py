from __future__ import annotations

from fl_editor.flight_mode_dispatch import hud_dispatch_state, overlay_dispatch_state


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
