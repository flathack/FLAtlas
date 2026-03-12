from __future__ import annotations

from fl_editor.view_3d_event_routing import (
    dispatch_widget_flight_event,
    filter_flight_event_state,
    should_capture_locked_axis_wheel,
    should_process_qt3d_interaction,
    widget_flight_event_state,
)


def test_filter_flight_event_state_maps_handlers_and_consume_modes():
    assert filter_flight_event_state(active=False, event_type="key_press") is None
    assert filter_flight_event_state(active=True, event_type="unknown") is None

    assert filter_flight_event_state(active=True, event_type="key_press") == {
        "handler_name": "on_key_press",
        "consume_mode": "handler_result",
    }
    assert filter_flight_event_state(active=True, event_type="mouse_move") == {
        "handler_name": "on_mouse_move",
        "consume_mode": "always_consume",
    }
    assert filter_flight_event_state(active=True, event_type="mouse_release") == {
        "handler_name": "on_mouse_release",
        "consume_mode": "never_consume",
    }


def test_widget_flight_event_state_maps_accept_modes():
    assert widget_flight_event_state(active=False, event_type="wheel") is None
    assert widget_flight_event_state(active=True, event_type="wheel") == {
        "handler_name": "on_wheel",
        "accept_mode": "always_accept",
    }
    assert widget_flight_event_state(active=True, event_type="key_release") == {
        "handler_name": "on_key_release",
        "accept_mode": "handler_result",
    }
    assert widget_flight_event_state(active=True, event_type="mouse_press") == {
        "handler_name": "on_mouse_press",
        "accept_mode": "never_accept",
    }


def test_capture_and_qt3d_interaction_decisions():
    assert should_capture_locked_axis_wheel(event_type="wheel", locked_axis="x", has_selected_obj=True) is True
    assert should_capture_locked_axis_wheel(event_type="wheel", locked_axis=None, has_selected_obj=True) is False
    assert should_capture_locked_axis_wheel(event_type="mouse_move", locked_axis="x", has_selected_obj=True) is False

    assert should_process_qt3d_interaction(qt3d_available=True, target_matches=True) is True
    assert should_process_qt3d_interaction(qt3d_available=False, target_matches=True) is False
    assert should_process_qt3d_interaction(qt3d_available=True, target_matches=False) is False


class _DummyFlight:
    def __init__(self, result: bool):
        self.result = result
        self.calls: list[str] = []

    def on_key_press(self, _event):
        self.calls.append("on_key_press")
        return self.result

    def on_mouse_move(self, _event):
        self.calls.append("on_mouse_move")
        return self.result


def test_dispatch_widget_flight_event_returns_unhandled_when_inactive():
    flight = _DummyFlight(result=True)
    state = dispatch_widget_flight_event(flight=flight, active=False, event_type="key_press", event=object())
    assert state == {
        "handled": False,
        "accepted": False,
    }
    assert flight.calls == []


def test_dispatch_widget_flight_event_uses_handler_result_for_keys():
    accepting = _DummyFlight(result=True)
    state = dispatch_widget_flight_event(flight=accepting, active=True, event_type="key_press", event=object())
    assert state == {
        "handled": True,
        "accepted": True,
    }
    assert accepting.calls == ["on_key_press"]

    rejecting = _DummyFlight(result=False)
    state = dispatch_widget_flight_event(flight=rejecting, active=True, event_type="key_press", event=object())
    assert state == {
        "handled": True,
        "accepted": False,
    }
    assert rejecting.calls == ["on_key_press"]


def test_dispatch_widget_flight_event_always_accepts_mouse_move():
    flight = _DummyFlight(result=False)
    state = dispatch_widget_flight_event(flight=flight, active=True, event_type="mouse_move", event=object())
    assert state == {
        "handled": True,
        "accepted": True,
    }
    assert flight.calls == ["on_mouse_move"]
