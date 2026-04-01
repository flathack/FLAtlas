from __future__ import annotations

from types import SimpleNamespace

from fl_editor.editing_action_state import build_editing_action_state, system_has_tradelanes


def test_system_has_tradelanes_detects_ring_in_archetype_or_nickname():
    objects = [
        SimpleNamespace(data={"archetype": "planet"}, nickname="planet_a"),
        SimpleNamespace(data={"archetype": "trade_lane_ring"}, nickname="lane_a"),
    ]
    assert system_has_tradelanes(objects) is True

    objects = [
        SimpleNamespace(data={"archetype": "planet"}, nickname="tradelane_ring_01"),
    ]
    assert system_has_tradelanes(objects) is True

    objects = [
        SimpleNamespace(data={"archetype": "planet"}, nickname="planet_a"),
    ]
    assert system_has_tradelanes(objects) is False


def test_build_editing_action_state_respects_lock_and_context():
    state = build_editing_action_state(
        locked=False,
        has_system=True,
        has_tradelanes=True,
        is_zone_selected=True,
        has_base_selected=True,
    )

    assert state == {
        "edit_tradelane_enabled": True,
        "edit_zone_pop_enabled": True,
        "edit_ring_enabled": True,
        "edit_base_enabled": True,
        "open_system_ini_enabled": True,
    }

    locked_state = build_editing_action_state(
        locked=True,
        has_system=True,
        has_tradelanes=True,
        is_zone_selected=True,
        has_base_selected=True,
    )

    assert locked_state == {
        "edit_tradelane_enabled": False,
        "edit_zone_pop_enabled": False,
        "edit_ring_enabled": False,
        "edit_base_enabled": False,
        "open_system_ini_enabled": False,
    }
