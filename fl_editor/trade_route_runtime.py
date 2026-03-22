"""Runtime helpers that keep trade-route UI orchestration lightweight."""

from __future__ import annotations


def normalize_trade_route_base_prices(commodity_base_prices: dict[str, object]) -> dict[str, int]:
    result: dict[str, int] = {}
    for key, value in commodity_base_prices.items():
        norm_key = str(key).strip().lower()
        if not norm_key:
            continue
        try:
            result[norm_key] = int(value)
        except Exception:
            continue
    return result


def build_trade_route_payload(
    *,
    commodity_base_prices: dict[str, object],
    commodity_display_map: dict[str, str],
    rows: list[dict],
    commodities: list[str],
    fallback_display_name,
) -> dict[str, object]:
    normalized_prices = normalize_trade_route_base_prices(commodity_base_prices)
    normalized_display_map = {
        str(key).strip().lower(): str(value)
        for key, value in dict(commodity_display_map).items()
        if str(key).strip()
    }
    commodity_options = list(commodities)
    for nick in commodity_options:
        key = str(nick).strip().lower()
        if key:
            normalized_display_map.setdefault(key, fallback_display_name(key))
    return {
        "rows": list(rows),
        "commodities": commodity_options,
        "commodity_display_map": normalized_display_map,
        "commodity_base_prices": normalized_prices,
    }


def build_trade_route_commodity_items(
    commodity_options: list[str],
    commodity_display_map: dict[str, str],
    fallback_display_name,
    *,
    limit: int = 500,
) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for nick in list(commodity_options)[:limit]:
        key = str(nick).lower()
        label = commodity_display_map.get(key, fallback_display_name(str(nick)))
        text = f"{label} ({nick})" if str(label).lower() != str(nick).lower() else str(label)
        items.append((text, str(nick)))
    return items


def build_trade_route_system_items(
    base_index: dict[str, dict],
    system_display_fn,
) -> list[tuple[str, str]]:
    systems = sorted({
        str(info.get("system", "")).strip()
        for info in base_index.values()
        if str(info.get("system", "")).strip()
    })
    items: list[tuple[str, str]] = []
    for sys_nick in systems:
        label = system_display_fn(sys_nick)
        text = f"{label} ({sys_nick})" if label != sys_nick else sys_nick
        items.append((text, sys_nick))
    return items
