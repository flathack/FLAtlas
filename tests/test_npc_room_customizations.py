from __future__ import annotations

from fl_editor.npc_room_customizations import normalize_room_npc_customizations


def test_normalize_room_npc_customizations_reuses_existing_rows_when_empty():
    npc_rooms, npc_customizations = normalize_room_npc_customizations(
        existing_rooms=["Bar"],
        selected_rooms=["Bar"],
        room_customizations={"bar": {}},
        room_npcs_existing={"bar": [{"nickname": "npc_bar", "role": "bartender"}]},
    )

    assert npc_rooms == ["Bar"]
    assert npc_customizations["bar"]["npc_rows"] == [{"nickname": "npc_bar", "role": "bartender"}]
    assert npc_customizations["bar"]["npcs"] == ["npc_bar"]


def test_normalize_room_npc_customizations_reinserts_missing_required_roles():
    npc_rooms, npc_customizations = normalize_room_npc_customizations(
        existing_rooms=["Deck"],
        selected_rooms=["Deck"],
        room_customizations={
            "deck": {
                "npc_rows": [{"nickname": "npc_trader", "role": "trader"}],
            }
        },
        room_npcs_existing={
            "deck": [
                {"nickname": "npc_trader", "role": "trader"},
                {"nickname": "npc_equip", "role": "equipment"},
            ]
        },
    )

    assert npc_rooms == ["Deck"]
    assert npc_customizations["deck"]["npc_rows"] == [
        {"nickname": "npc_trader", "role": "trader"},
        {"nickname": "npc_equip", "role": "equipment"},
    ]
    assert npc_customizations["deck"]["npcs"] == ["npc_trader", "npc_equip"]


def test_normalize_room_npc_customizations_restores_existing_bar_role_for_known_npc():
    _rooms, npc_customizations = normalize_room_npc_customizations(
        existing_rooms=["Bar"],
        selected_rooms=["Bar"],
        room_customizations={
            "bar": {
                "npc_rows": [{"nickname": "npc_bar", "role": "mission_vendor"}],
            }
        },
        room_npcs_existing={"bar": [{"nickname": "npc_bar", "role": "bartender"}]},
    )

    assert npc_customizations["bar"]["npc_rows"] == [{"nickname": "npc_bar", "role": "bartender"}]
    assert npc_customizations["bar"]["npcs"] == ["npc_bar"]
