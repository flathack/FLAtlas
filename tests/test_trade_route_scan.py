"""Tests for trade_route_scan – pure functions on parsed data."""

from __future__ import annotations

from fl_editor.trade_route_models import BaseMarketEntry
from fl_editor.trade_route_scan import (
    build_best_trade_pairs,
    build_commodities,
    commodity_fallback_display_name,
    extract_market_entries,
    scan_commodity_nicknames_from_sections,
)


def test_commodity_fallback_display_name_strips_prefix():
    assert commodity_fallback_display_name("commodity_gold") == "Gold"
    assert commodity_fallback_display_name("commodity_basic_alloy") == "Basic Alloy"


def test_commodity_fallback_display_name_empty():
    assert commodity_fallback_display_name("") == ""


def test_commodity_fallback_display_name_acronym():
    assert commodity_fallback_display_name("commodity_mox_fuel") == "MOX Fuel"


def test_scan_commodity_nicknames_from_sections():
    sections = [
        ("Good", [("nickname", "commodity_gold"), ("price", "200")]),
        ("Good", [("nickname", "commodity_silver"), ("price", "100")]),
        ("Good", [("nickname", "ship_eagle"), ("price", "5000")]),
    ]
    nicks, prices = scan_commodity_nicknames_from_sections(sections)
    assert nicks == ["commodity_gold", "commodity_silver"]
    assert prices == {"commodity_gold": 200, "commodity_silver": 100}


def test_scan_commodity_nicknames_empty():
    nicks, prices = scan_commodity_nicknames_from_sections([])
    assert nicks == []
    assert prices == {}


def test_extract_market_entries():
    sections = [
        (
            "BaseGood",
            [
                ("base", "li01_01_base"),
                ("MarketGood", "commodity_gold, 0, -1, 150, 500, 0, 1.5"),
                ("MarketGood", "commodity_gold, 0, -1, 0, 0, 1, 2.0"),
            ],
        ),
        (
            "BaseGood",
            [
                ("base", "li01_02_base"),
                ("MarketGood", "commodity_gold, 0, -1, 0, 0, 1, 3.0"),
            ],
        ),
    ]
    base_index = {
        "li01_01_base": {"base_nick": "li01_01_base", "display_name": "Manhattan", "system": "LI01", "pos": (0, 0)},
        "li01_02_base": {"base_nick": "li01_02_base", "display_name": "Pittsburgh", "system": "LI01", "pos": (100, 100)},
    }
    prices = {"commodity_gold": 200}

    result = extract_market_entries(sections, base_index, prices)
    assert "commodity_gold" in result
    assert len(result["commodity_gold"]) == 3
    entry = result["commodity_gold"][0]
    assert isinstance(entry, BaseMarketEntry)
    assert entry.base_nick == "li01_01_base"
    assert entry.price == 300.0  # 200 * 1.5
    assert entry.is_source is True


def test_extract_market_entries_skips_unknown_base():
    sections = [
        (
            "BaseGood",
            [
                ("base", "unknown_base"),
                ("MarketGood", "commodity_gold, 0, -1, 150, 500, 0, 1.5"),
            ],
        ),
    ]
    result = extract_market_entries(sections, {}, {"commodity_gold": 200})
    assert result == {}


def test_extract_market_entries_skips_invalid_fields():
    sections = [
        (
            "BaseGood",
            [
                ("base", "li01_01_base"),
                ("MarketGood", "commodity_gold, 0, -1"),  # too few fields
                ("MarketGood", "ship_eagle, 0, -1, 150, 500, 0, 1.5"),  # not a commodity
                ("MarketGood", "commodity_pilot_ammo, 0, -1, 150, 500, 0, 1.5"),  # pilot commodity
            ],
        ),
    ]
    base_index = {"li01_01_base": {"base_nick": "li01_01_base"}}
    result = extract_market_entries(sections, base_index, {"commodity_gold": 200})
    assert result == {}


def test_build_best_trade_pairs():
    by_commodity = {
        "commodity_gold": [
            BaseMarketEntry(base_nick="base_a", commodity="commodity_gold", price=100.0, is_source=True),
            BaseMarketEntry(base_nick="base_b", commodity="commodity_gold", price=300.0, is_source=False),
            BaseMarketEntry(base_nick="base_c", commodity="commodity_gold", price=250.0, is_source=False),
        ],
    }
    display_map = {"commodity_gold": "Gold"}
    routes, commodities = build_best_trade_pairs(by_commodity, display_map)

    assert commodities == ["commodity_gold"]
    assert len(routes) >= 1
    # Best route should be base_a -> base_b (profit 200)
    best = routes[0]
    assert best.buy_loc == "base_a"
    assert best.sell_loc == "base_b"
    assert best.profit == 200.0
    assert best.commodity_label == "Gold"


def test_build_best_trade_pairs_single_entry_skipped():
    by_commodity = {
        "commodity_rare": [
            BaseMarketEntry(base_nick="base_a", commodity="commodity_rare", price=100.0, is_source=True),
        ],
    }
    routes, commodities = build_best_trade_pairs(by_commodity, {})
    assert routes == []
    assert commodities == ["commodity_rare"]


def test_build_commodities():
    nicks = ["commodity_gold", "commodity_silver"]
    prices = {"commodity_gold": 200, "commodity_silver": 100}
    display_map = {"commodity_gold": "Gold"}

    result = build_commodities(nicks, prices, display_map)
    assert len(result) == 2
    assert result[0].nickname == "commodity_gold"
    assert result[0].base_price == 200
    assert result[0].display_name == "Gold"
    assert result[1].display_name == "Silver"  # fallback
