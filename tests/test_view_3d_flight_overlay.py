from __future__ import annotations

from fl_editor.view_3d_flight_overlay import cruise_charge_bar_state, flight_overlay_layout, flight_overlay_text_state


def test_flight_overlay_layout_positions_help_overlay_on_right():
    state = flight_overlay_layout(
        host_width=1000.0,
        overlay_height=40.0,
        help_overlay_visible=True,
        help_overlay_width=250.0,
    )

    assert state["overlay_pos"] == (8, 8)
    assert state["charge_bar_geometry"] == (8, 54, 260, 20)
    assert state["help_overlay_pos"] == (742, 8)


def test_flight_overlay_text_state_remains_hidden():
    assert flight_overlay_text_state(text="Autopilot active") == {
        "text": "",
        "visible": False,
    }


def test_cruise_charge_bar_state_remains_hidden():
    assert cruise_charge_bar_state(snapshot={"charge_ratio": 0.5}) == {
        "visible": False,
    }
