from __future__ import annotations

from fl_editor.trade_route_custom_storage import load_custom_trade_routes, save_custom_trade_routes


class _CfgStub:
    def __init__(self, raw=None):
        self.raw = raw
        self.writes: dict[str, object] = {}

    def get(self, key: str, default=None):
        if self.raw is None:
            return default
        return self.raw

    def set(self, key: str, value):
        self.writes[key] = value


def test_load_custom_trade_routes_normalizes_rows():
    cfg = _CfgStub(
        [
            {
                "name": "  ",
                "commodity": " commodity_x ",
                "commodity_label": " Commodity X ",
                "buy_loc": " Li01_01_Base ",
                "sell_loc": " Li01_02_Base ",
                "buy_price": "123",
                "sell_price": 456,
                "enabled": 0,
            },
            "invalid",
        ]
    )

    result = load_custom_trade_routes(cfg)

    assert result == [
        {
            "name": "Route",
            "commodity": "commodity_x",
            "commodity_label": "Commodity X",
            "buy_loc": "li01_01_base",
            "sell_loc": "li01_02_base",
            "buy_price": 123.0,
            "sell_price": 456.0,
            "enabled": False,
        }
    ]


def test_load_custom_trade_routes_ignores_non_list_payload():
    cfg = _CfgStub({"bad": "payload"})

    assert load_custom_trade_routes(cfg) == []


def test_save_custom_trade_routes_persists_rows():
    cfg = _CfgStub()
    rows = [{"name": "Route A"}, {"name": "Route B"}]

    save_custom_trade_routes(cfg, rows)

    assert cfg.writes == {"trade_routes.custom": rows}
