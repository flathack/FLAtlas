from __future__ import annotations

from fl_editor.trade_route_market import (
    serialize_ini_sections,
    trade_route_format_multiplier,
    trade_route_remove_marketgood_section,
    trade_route_upsert_marketgood_section,
)


def test_trade_route_format_multiplier_trims_trailing_zeroes():
    assert trade_route_format_multiplier(1.25) == "1.25"
    assert trade_route_format_multiplier(2.0) == "2"


def test_trade_route_upsert_marketgood_section_updates_existing_entry():
    sections = [
        (
            "BaseGood",
            [
                ("base", "li01_01_base"),
                ("MarketGood", "commodity_a, 0, -1, 150, 500, 0, 1.0"),
            ],
        )
    ]

    result = trade_route_upsert_marketgood_section(
        sections,
        base="li01_01_base",
        commodity="commodity_a",
        relation_flag=1,
        multiplier_text="2.5",
    )

    assert result[0][1][1] == ("MarketGood", "commodity_a, 0, -1, 150, 500, 1, 2.5")


def test_trade_route_upsert_marketgood_section_creates_section_and_new_entry():
    result = trade_route_upsert_marketgood_section(
        [],
        base="li01_02_base",
        commodity="commodity_b",
        relation_flag=0,
        multiplier_text="3",
    )

    assert result == [
        (
            "BaseGood",
            [("base", "li01_02_base"), ("MarketGood", "commodity_b, 0, -1, 150, 500, 0, 3")],
        )
    ]


def test_trade_route_remove_marketgood_section_and_serialize():
    sections = [
        (
            "BaseGood",
            [
                ("base", "li01_01_base"),
                ("MarketGood", "commodity_a, 0, -1, 150, 500, 0, 1.0"),
                ("MarketGood", "commodity_b, 0, -1, 150, 500, 0, 1.1"),
            ],
        )
    ]

    result, changed = trade_route_remove_marketgood_section(
        sections,
        base="li01_01_base",
        commodity="commodity_a",
    )

    assert changed
    assert result == [
        (
            "BaseGood",
            [
                ("base", "li01_01_base"),
                ("MarketGood", "commodity_b, 0, -1, 150, 500, 0, 1.1"),
            ],
        )
    ]
    assert serialize_ini_sections(result) == "[BaseGood]\nbase = li01_01_base\nMarketGood = commodity_b, 0, -1, 150, 500, 0, 1.1\n"
