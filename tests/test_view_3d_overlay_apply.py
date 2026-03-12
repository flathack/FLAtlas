from __future__ import annotations

from fl_editor.view_3d_overlay_apply import (
    apply_cruise_charge_bar,
    apply_flight_overlay_layout,
    apply_flight_overlay_text,
)


class _FakeOverlay:
    def __init__(self):
        self.text = None
        self.visible = None
        self.pos = None

    def setText(self, value):
        self.text = value

    def setVisible(self, value):
        self.visible = value

    def move(self, x, y):
        self.pos = (x, y)


class _FakeChargeBar:
    def __init__(self):
        self.visible = None
        self.geometry = None

    def setVisible(self, value):
        self.visible = value

    def setGeometry(self, x, y, w, h):
        self.geometry = (x, y, w, h)


def test_apply_flight_overlay_text_updates_widget():
    overlay = _FakeOverlay()

    apply_flight_overlay_text(overlay=overlay, state={"text": "Docking", "visible": True})

    assert overlay.text == "Docking"
    assert overlay.visible is True


def test_apply_cruise_charge_bar_updates_visibility():
    charge_bar = _FakeChargeBar()

    apply_cruise_charge_bar(charge_bar=charge_bar, state={"visible": False})

    assert charge_bar.visible is False


def test_apply_flight_overlay_layout_updates_all_widgets():
    overlay = _FakeOverlay()
    charge_bar = _FakeChargeBar()
    help_overlay = _FakeOverlay()

    apply_flight_overlay_layout(
        overlay=overlay,
        charge_bar=charge_bar,
        help_overlay=help_overlay,
        state={
            "overlay_pos": (8, 8),
            "charge_bar_geometry": (8, 40, 260, 20),
            "help_overlay_pos": (300, 8),
        },
    )

    assert overlay.pos == (8, 8)
    assert charge_bar.geometry == (8, 40, 260, 20)
    assert help_overlay.pos == (300, 8)
