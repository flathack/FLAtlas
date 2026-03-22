from __future__ import annotations

from fl_editor.trade_route_runtime import (
    build_trade_route_commodity_items,
    build_trade_route_payload,
    build_trade_route_system_items,
    normalize_trade_route_base_prices,
)


def test_normalize_trade_route_base_prices_normalizes_keys_and_values():
    result = normalize_trade_route_base_prices({
        " Commodity_Gold ": "200",
        "commodity_silver": 100,
        "": 999,
        "bad": "x",
    })

    assert result == {
        "commodity_gold": 200,
        "commodity_silver": 100,
    }


def test_build_trade_route_payload_fills_missing_display_names():
    payload = build_trade_route_payload(
        commodity_base_prices={"Commodity_Gold": "200"},
        commodity_display_map={},
        rows=[{"commodity": "commodity_gold"}],
        commodities=["commodity_gold"],
        fallback_display_name=lambda nick: f"pretty:{nick}",
    )

    assert payload["commodity_base_prices"] == {"commodity_gold": 200}
    assert payload["commodity_display_map"] == {"commodity_gold": "pretty:commodity_gold"}
    assert payload["commodities"] == ["commodity_gold"]


def test_build_trade_route_commodity_items_formats_labels():
    items = build_trade_route_commodity_items(
        ["commodity_gold", "commodity_silver"],
        {"commodity_gold": "Gold"},
        lambda nick: nick.replace("commodity_", "").title(),
    )

    assert items == [
        ("Gold (commodity_gold)", "commodity_gold"),
        ("Silver (commodity_silver)", "commodity_silver"),
    ]


def test_build_trade_route_system_items_formats_display_names():
    items = build_trade_route_system_items(
        {
            "base_a": {"system": "LI01"},
            "base_b": {"system": "LI02"},
            "base_c": {"system": "LI01"},
        },
        lambda sys_nick: {"LI01": "New York", "LI02": "California"}.get(sys_nick, sys_nick),
    )

    assert items == [
        ("New York (LI01)", "LI01"),
        ("California (LI02)", "LI02"),
    ]
