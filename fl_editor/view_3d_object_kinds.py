from __future__ import annotations

from .view_3d_object_logic import is_trade_lane_object


def classify_object_kind(*, nickname: str, archetype: str) -> dict[str, bool]:
    arch = str(archetype or "").lower()
    name = str(nickname or "").lower()

    return {
        "is_trade_lane": is_trade_lane_object(nickname=name, archetype=arch),
        "is_dock_ring": arch.strip() == "dock_ring",
        "is_sun": any(x in arch for x in ("sun", "star")),
        "is_planet": "planet" in arch,
        "is_jump_gate": any(x in arch for x in ("jumpgate", "jump_gate", "jumppoint_gate", "nomad_gate")),
        "is_jump_hole": any(x in arch for x in ("jumphole", "jump_hole")),
        "is_platform": arch in {"wplatform", "small_wplatform"} or "platform" in arch or arch == "mplatform",
        "is_buoy_like": arch.endswith("buoy") or "buoy" in arch,
        "is_asteroid_like": arch.startswith("ast_"),
        "is_debris_like": "debris" in arch,
        "is_miner_like": "miner" in arch or arch.startswith("miningbase"),
        "is_nomad_structure": arch in {
            "dyson",
            "dyson_airlock",
            "dyson_airlock_inside",
            "dyson_city",
            "fuchu_core",
            "lair",
            "lair_core",
            "lair_platform",
            "co_base_ice_large02",
            "co_base_rock_large01",
            "co_base_rock_large02",
        },
        "is_station_like": arch in {
            "shipyard",
            "space_factory01",
            "space_industrial",
            "space_shipping02",
            "space_port_dmg",
            "smallstation1",
            "largestation1",
            "outpost",
            "ithaca_station",
            "miningbase_badlands",
            "docking_fixture",
        } or arch.startswith("space_") or "station" in arch or arch.endswith("_base"),
        "is_prison": arch == "prison",
        "is_tank_like": (
            arch in {"space_tankl4", "space_tankl4_dmg", "space_habitat_dmg"}
            or arch.startswith("space_tank")
            or arch.startswith("space_tanks")
            or "tank" in arch
            or "habitat" in arch
        ),
        "is_depot_like": arch.startswith("depot"),
        "is_capship": (
            arch in {"l_dreadnought", "l_dreadnought_nodock"}
            or "battleship" in arch
            or "cruiser" in arch
            or "dreadnought" in arch
        ),
        "is_transport": (
            arch == "large_transport"
            or "transport" in arch
            or "freighter" in arch
            or "liner" in arch
            or "train" in arch
            or arch == "hispania_sleeper_ship"
        ),
        "is_surprise_ship": arch.startswith("suprise_"),
        "is_hazard": arch == "blhazard" or "hazard" in arch or arch == "neutron_star",
    }
