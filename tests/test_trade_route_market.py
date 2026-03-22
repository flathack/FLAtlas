from __future__ import annotations

from fl_editor.trade_route_market import (
    extract_base_market_goods,
    list_bases_with_commodity,
    list_bases_with_commodity_including_implicit,
    serialize_ini_sections,
    trade_route_format_multiplier,
    trade_route_patch_marketgood_field,
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


# ── trade_route_patch_marketgood_field ────────────────────────────

def _sample_sections():
    return [
        (
            "BaseGood",
            [
                ("base", "li01_01_base"),
                ("MarketGood", "commodity_a, 0, -1, 150, 500, 0, 1.0"),
                ("MarketGood", "commodity_b, 0, -1, 100, 300, 1, 0.85"),
            ],
        ),
        (
            "BaseGood",
            [
                ("base", "li02_01_base"),
                ("MarketGood", "commodity_a, 0, -1, 200, 600, 1, 1.2"),
            ],
        ),
    ]


def test_patch_marketgood_field_multiplier():
    result, changed = trade_route_patch_marketgood_field(
        _sample_sections(), base="li01_01_base", commodity="commodity_a",
        field_index=6, new_value="2.5",
    )
    assert changed
    mg = [v for k, v in result[0][1] if k == "MarketGood"]
    assert mg[0].startswith("commodity_a")
    assert mg[0].endswith("2.5")


def test_patch_marketgood_field_stock_min():
    result, changed = trade_route_patch_marketgood_field(
        _sample_sections(), base="li01_01_base", commodity="commodity_b",
        field_index=3, new_value="999",
    )
    assert changed
    mg = [v for k, v in result[0][1] if k == "MarketGood" and v.startswith("commodity_b")]
    fields = [f.strip() for f in mg[0].split(",")]
    assert fields[3] == "999"


def test_patch_marketgood_field_no_match():
    result, changed = trade_route_patch_marketgood_field(
        _sample_sections(), base="li01_01_base", commodity="commodity_x",
        field_index=6, new_value="9",
    )
    assert not changed


# ── extract_base_market_goods ─────────────────────────────────────

def test_extract_base_market_goods_returns_entries():
    goods = extract_base_market_goods(_sample_sections(), "li01_01_base")
    assert len(goods) == 2
    assert goods[0]["commodity"] == "commodity_a"
    assert goods[0]["multiplier"] == 1.0
    assert goods[0]["relation_flag"] == 0
    assert goods[1]["commodity"] == "commodity_b"
    assert goods[1]["stock_min"] == 100
    assert goods[1]["stock_max"] == 300


def test_extract_base_market_goods_empty_for_unknown_base():
    goods = extract_base_market_goods(_sample_sections(), "unknown_base")
    assert goods == []


# ── list_bases_with_commodity ─────────────────────────────────────

def test_list_bases_with_commodity_finds_all():
    entries = list_bases_with_commodity(_sample_sections(), "commodity_a")
    assert len(entries) == 2
    bases = {e["base"] for e in entries}
    assert bases == {"li01_01_base", "li02_01_base"}
    # Check detail for li02
    li02 = [e for e in entries if e["base"] == "li02_01_base"][0]
    assert li02["relation_flag"] == 1
    assert li02["multiplier"] == 1.2


def test_list_bases_with_commodity_none_found():
    entries = list_bases_with_commodity(_sample_sections(), "commodity_x")
    assert entries == []


def test_list_bases_with_commodity_including_implicit_adds_base_price_buyers():
    entries = list_bases_with_commodity_including_implicit(
        _sample_sections(),
        "commodity_b",
        known_bases={"li01_01_base", "li02_01_base", "li03_01_base"},
        commodity_base_prices={"commodity_b": 100},
    )
    bases = {e["base"] for e in entries}
    assert bases == {"li01_01_base", "li02_01_base", "li03_01_base"}
    implicit = [e for e in entries if e["base"] == "li03_01_base"][0]
    assert implicit["relation_flag"] == 1
    assert implicit["multiplier"] == 1.0
    assert implicit["implicit"] is True
