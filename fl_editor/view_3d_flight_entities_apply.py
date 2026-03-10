from __future__ import annotations


def apply_flight_entity_state(
    *,
    ship_entity: object | None,
    dust_entities: list[object],
    charge_bar: object,
    state: dict[str, object],
) -> None:
    if ship_entity is not None:
        ship_entity.setEnabled(bool(state.get("ship_enabled")))
    for entity, enabled in zip(dust_entities, list(state.get("dust_enabled", []))):
        entity.setEnabled(bool(enabled))
    charge_bar.setVisible(bool(state.get("charge_bar_visible")))
