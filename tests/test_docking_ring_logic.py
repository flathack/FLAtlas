from __future__ import annotations

from fl_editor.docking_ring_logic import build_docking_ring_payload, build_docking_ring_room_state


def test_build_docking_ring_room_state_keeps_only_active_rooms_and_valid_start_room():
    assert build_docking_ring_room_state(
        room_names=["Deck", "", "Bar"],
        preferred_start_room="Trader",
        current_start_room="Bar",
    ) == {
        "rooms": ["Deck", "Bar"],
        "start_room": "Bar",
    }

    assert build_docking_ring_room_state(
        room_names=["Bar", "Trader"],
        preferred_start_room="",
        current_start_room="",
    ) == {
        "rooms": ["Bar", "Trader"],
        "start_room": "Bar",
    }


def test_build_docking_ring_payload_with_new_base_collects_room_data():
    payload = build_docking_ring_payload(
        nickname="Dock_Ring_li01",
        archetype="dock_ring",
        loadout="docking_ring",
        faction="li_n_grp",
        voice="atc_leg_f01a",
        costume="robot_body_A",
        pilot="pilot_solar_easiest",
        difficulty=1,
        ids_name="123",
        ids_info="456",
        needs_base=True,
        base_nickname="li01_01_base",
        strid_name=789,
        room_names=["Deck", "", "Bar"],
        start_room="Trader",
        price_variance=0.2,
        template_base="li01_02_base",
    )

    assert payload == {
        "nickname": "Dock_Ring_li01",
        "archetype": "dock_ring",
        "loadout": "docking_ring",
        "faction": "li_n_grp",
        "voice": "atc_leg_f01a",
        "costume": "robot_body_A",
        "pilot": "pilot_solar_easiest",
        "difficulty": 1,
        "ids_name": "123",
        "ids_info": "456",
        "create_fixture": False,
        "base_nickname": "li01_01_base",
        "strid_name": 789,
        "rooms": ["Deck", "Bar"],
        "start_room": "Deck",
        "price_variance": 0.2,
        "template_base": "li01_02_base",
    }


def test_build_docking_ring_payload_with_existing_base_uses_existing_nickname():
    payload = build_docking_ring_payload(
        nickname="Dock_Ring_li01",
        archetype="dock_ring",
        loadout="docking_ring",
        faction="li_n_grp",
        voice="atc_leg_f01a",
        costume="robot_body_A",
        pilot="pilot_solar_easiest",
        difficulty=1,
        ids_name="123",
        ids_info="456",
        needs_base=False,
        existing_base_nickname="li01_existing_base",
    )

    assert payload["base_nickname"] == "li01_existing_base"
    assert payload["create_fixture"] is False
    assert "rooms" not in payload
