"""Data models for the trade route domain."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Commodity:
    """A commodity as defined in goods.ini."""

    nickname: str
    base_price: int = 0
    display_name: str = ""


@dataclass
class BaseMarketEntry:
    """A single MarketGood entry for a base, parsed from market_commodities.ini."""

    base_nick: str
    commodity: str
    price: float
    is_source: bool
    relation_flag: int = 0
    multiplier: float = 1.0
    stock_min: int = 0
    stock_max: int = 0


@dataclass
class TradeRouteCandidate:
    """A potential trade route between two bases."""

    name: str
    commodity: str
    commodity_label: str
    buy_loc: str
    sell_loc: str
    buy_price: float
    sell_price: float
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "commodity": self.commodity,
            "commodity_label": self.commodity_label,
            "buy_loc": self.buy_loc,
            "sell_loc": self.sell_loc,
            "buy_price": self.buy_price,
            "sell_price": self.sell_price,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TradeRouteCandidate:
        return cls(
            name=str(d.get("name", "")),
            commodity=str(d.get("commodity", "")),
            commodity_label=str(d.get("commodity_label", "")),
            buy_loc=str(d.get("buy_loc", "")),
            sell_loc=str(d.get("sell_loc", "")),
            buy_price=float(d.get("buy_price", 0.0) or 0.0),
            sell_price=float(d.get("sell_price", 0.0) or 0.0),
            enabled=bool(d.get("enabled", True)),
        )

    @property
    def profit(self) -> float:
        return self.sell_price - self.buy_price


@dataclass
class EnrichedTradeRoute:
    """A trade route with resolved display names, system info, and metrics."""

    name: str = ""
    commodity: str = ""
    commodity_label: str = ""
    buy_loc: str = ""
    sell_loc: str = ""
    buy_price: float = 0.0
    sell_price: float = 0.0
    enabled: bool = True
    buy_system: str = ""
    sell_system: str = ""
    buy_label: str = ""
    sell_label: str = ""
    buy_system_label: str = ""
    sell_system_label: str = ""
    profit: float = 0.0
    jumps: int = 0
    score: int = 0
    profit_per_jump: float = 0.0
    net_profit: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "commodity": self.commodity,
            "commodity_label": self.commodity_label,
            "buy_loc": self.buy_loc,
            "sell_loc": self.sell_loc,
            "buy_price": self.buy_price,
            "sell_price": self.sell_price,
            "enabled": self.enabled,
            "buy_system": self.buy_system,
            "sell_system": self.sell_system,
            "buy_label": self.buy_label,
            "sell_label": self.sell_label,
            "buy_system_label": self.buy_system_label,
            "sell_system_label": self.sell_system_label,
            "profit": self.profit,
            "jumps": self.jumps,
            "score": self.score,
            "profit_per_jump": self.profit_per_jump,
            "net_profit": self.net_profit,
        }
