"""Tests for trade_route_models."""

from __future__ import annotations

from fl_editor.trade_route_models import EnrichedTradeRoute, TradeRouteCandidate


def test_trade_route_candidate_profit():
    c = TradeRouteCandidate(
        name="Test",
        commodity="commodity_gold",
        commodity_label="Gold",
        buy_loc="base_a",
        sell_loc="base_b",
        buy_price=100.0,
        sell_price=350.0,
    )
    assert c.profit == 250.0


def test_trade_route_candidate_roundtrip_dict():
    c = TradeRouteCandidate(
        name="Test",
        commodity="commodity_gold",
        commodity_label="Gold",
        buy_loc="base_a",
        sell_loc="base_b",
        buy_price=100.0,
        sell_price=350.0,
    )
    d = c.to_dict()
    c2 = TradeRouteCandidate.from_dict(d)
    assert c2.commodity == c.commodity
    assert c2.buy_price == c.buy_price
    assert c2.sell_price == c.sell_price
    assert c2.profit == c.profit


def test_enriched_trade_route_to_dict():
    e = EnrichedTradeRoute(
        commodity="commodity_gold",
        commodity_label="Gold",
        buy_price=100.0,
        sell_price=350.0,
        profit=250.0,
        jumps=2,
        score=833,
        profit_per_jump=125.0,
    )
    d = e.to_dict()
    assert d["profit"] == 250.0
    assert d["jumps"] == 2
    assert d["profit_per_jump"] == 125.0
