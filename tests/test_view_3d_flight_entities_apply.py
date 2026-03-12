from __future__ import annotations

from fl_editor.view_3d_flight_entities_apply import apply_flight_entity_state


class _FlagTarget:
    def __init__(self):
        self.values: list[bool] = []

    def setEnabled(self, value: bool):
        self.values.append(bool(value))

    def setVisible(self, value: bool):
        self.values.append(bool(value))


def test_apply_flight_entity_state_updates_ship_dust_and_charge_bar():
    ship = _FlagTarget()
    dust_a = _FlagTarget()
    dust_b = _FlagTarget()
    charge = _FlagTarget()

    apply_flight_entity_state(
        ship_entity=ship,
        dust_entities=[dust_a, dust_b],
        charge_bar=charge,
        state={
            "ship_enabled": True,
            "dust_enabled": [True, False],
            "charge_bar_visible": False,
        },
    )

    assert ship.values == [True]
    assert dust_a.values == [True]
    assert dust_b.values == [False]
    assert charge.values == [False]
