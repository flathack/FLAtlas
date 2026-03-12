"""Helpers for persisting custom trade routes in config storage."""

from __future__ import annotations


def load_custom_trade_routes(cfg) -> list[dict]:
    raw = cfg.get("trade_routes.custom", [])
    out: list[dict] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "name": str(item.get("name", "")).strip() or "Route",
                "commodity": str(item.get("commodity", "")).strip(),
                "commodity_label": str(item.get("commodity_label", "")).strip(),
                "buy_loc": str(item.get("buy_loc", "")).strip().lower(),
                "sell_loc": str(item.get("sell_loc", "")).strip().lower(),
                "buy_price": float(item.get("buy_price", 0.0) or 0.0),
                "sell_price": float(item.get("sell_price", 0.0) or 0.0),
                "enabled": bool(item.get("enabled", True)),
            }
        )
    return out


def save_custom_trade_routes(cfg, rows: list[dict]) -> None:
    cfg.set("trade_routes.custom", list(rows))
