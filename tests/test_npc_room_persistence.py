from __future__ import annotations

from fl_editor.npc_room_persistence import (
    npc_allowed_roles_for_room,
    npc_canonical_mroom_name,
    npc_fixture_scene_for_role,
    npc_normalize_role_for_room,
    npc_room_density,
    npc_room_key,
    npc_upsert_mrooms_for_base,
)


def _entry_get_value(entries: list[tuple[str, str]], key: str) -> str:
    for entry_key, value in entries:
        if str(entry_key).strip().lower() == str(key).strip().lower():
            return str(value)
    return ""


def test_npc_room_helpers_normalize_keys_roles_and_density():
    assert npc_room_key("ship_dealer") == "shipdealer"
    assert npc_canonical_mroom_name("shipdealer") == "ShipDealer"
    assert npc_allowed_roles_for_room("bar") == ["bartender", "BarFly", "NewsVendor"]
    assert npc_normalize_role_for_room("", "bar") == "bartender"
    assert npc_normalize_role_for_room("newsvendor", "bar") == "NewsVendor"
    assert npc_room_density("bar") == 7


def test_npc_fixture_scene_for_role_maps_known_roles():
    assert npc_fixture_scene_for_role("ShipDealer") == ("scripts\\vendors\\li_shipdealer_fidget.thn", "ShipDealer")
    assert npc_fixture_scene_for_role("bartender") == ("scripts\\vendors\\li_host_fidget.thn", "bartender")
    assert npc_fixture_scene_for_role("unknown") == ("scripts\\vendors\\li_commtrader_fidget.thn", "trader")


def test_npc_upsert_mrooms_for_base_replaces_target_rooms():
    sections = [
        ("MBase", [("nickname", "li01_01_base")]),
        ("BaseFaction", [("faction", "li_n_grp"), ("weight", "10")]),
        ("GF_NPC", [("nickname", "li01_01_npc_001")]),
        ("MRoom", [("nickname", "Bar"), ("fixture", "old_npc, Zs/NPC/trader/01/A/Stand, x, trader")]),
    ]

    changed = npc_upsert_mrooms_for_base(
        sections,
        base_nickname="li01_01_base",
        room_fixtures={"bar": [("li01_01_npc_001", "bartender")]},
        entry_get_value=_entry_get_value,
    )

    assert changed is True
    assert sections[-1][0] == "MRoom"
    assert ("nickname", "bar") in sections[-1][1]
    assert ("character_density", "7") in sections[-1][1]
    assert any(
        key == "fixture"
        and value == "li01_01_npc_001, Zs/NPC/Bartender/01/A/Stand, scripts\\vendors\\li_host_fidget.thn, bartender"
        for key, value in sections[-1][1]
    )
