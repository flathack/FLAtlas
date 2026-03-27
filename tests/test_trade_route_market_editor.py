from __future__ import annotations

from fl_editor.trade_route_market_editor import (
    market_editor_effective_price,
    market_editor_trade_impact_summary,
    market_editor_type_text,
)


def test_market_editor_type_text_defaults():
    assert market_editor_type_text(0) == "Buy (Source)"
    assert market_editor_type_text(1) == "Sell (Sink)"


def test_market_editor_effective_price_handles_zero_base():
    assert market_editor_effective_price(0, 2.5) == 0
    assert market_editor_effective_price(100, 1.5) == 150


def test_market_editor_trade_impact_summary_for_source():
    summary = market_editor_trade_impact_summary(
        entries=[
            {"base": "base_a", "relation_flag": 0, "multiplier": 1.0},
            {"base": "base_b", "relation_flag": 1, "multiplier": 1.8},
            {"base": "base_c", "relation_flag": 1, "multiplier": 1.5},
        ],
        current_base="base_a",
        relation_flag=0,
        multiplier=1.0,
        base_price=100,
        base_index={"base_b": {"display_name": "Beta", "system": "LI02"}},
    )

    assert "Beta (base_b)" in summary
    assert "80" in summary


def test_market_editor_trade_impact_summary_for_sink():
    summary = market_editor_trade_impact_summary(
        entries=[
            {"base": "base_a", "relation_flag": 1, "multiplier": 2.0},
            {"base": "base_b", "relation_flag": 0, "multiplier": 1.2},
            {"base": "base_c", "relation_flag": 0, "multiplier": 1.4},
        ],
        current_base="base_a",
        relation_flag=1,
        multiplier=2.0,
        base_price=100,
        base_index={"base_b": {"display_name": "Beta", "system": "LI02"}},
    )

    assert "Beta (base_b)" in summary
    assert "80" in summary


def test_market_editor_trade_impact_summary_without_counterpart():
    summary = market_editor_trade_impact_summary(
        entries=[{"base": "base_a", "relation_flag": 0, "multiplier": 1.0}],
        current_base="base_a",
        relation_flag=0,
        multiplier=1.0,
        base_price=100,
        base_index={},
    )

    assert "No matching counterpart" in summary
