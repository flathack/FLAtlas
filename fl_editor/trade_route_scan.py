"""Scanning and loading helpers for trade route data.

These functions operate on already-parsed INI sections and do not perform I/O.
The caller (typically main_window) is responsible for reading files and passing
parsed sections here.
"""

from __future__ import annotations

from .trade_route_models import BaseMarketEntry, Commodity, TradeRouteCandidate


def commodity_fallback_display_name(nickname: str) -> str:
    """Generate a human-readable display name from a commodity nickname."""
    raw = str(nickname or "").strip()
    if not raw:
        return ""
    low = raw.lower()
    if low.startswith("commodity_"):
        raw = raw[len("commodity_"):]
    parts = [p for p in raw.split("_") if p]
    if not parts:
        return str(nickname or "").strip()
    acronyms = {"wp", "h", "mox", "npc", "gui", "ids"}
    pretty: list[str] = []
    for p in parts:
        pl = p.lower()
        if pl in acronyms:
            pretty.append(pl.upper())
        elif len(pl) <= 2 and pl.isalpha():
            pretty.append(pl.upper())
        else:
            pretty.append(pl[:1].upper() + pl[1:])
    return " ".join(pretty)


def scan_commodity_nicknames_from_sections(
    sections: list[tuple[str, list[tuple[str, str]]]],
) -> tuple[list[str], dict[str, int]]:
    """Extract commodity nicknames and base prices from parsed goods.ini sections.

    Returns ``(nicknames, {nickname: base_price})``.
    """
    nicks: list[str] = []
    prices: dict[str, int] = {}
    for sec_name, entries in sections:
        if sec_name.lower() != "good":
            continue
        nick = ""
        price = 0
        for k, v in entries:
            kl = k.lower()
            if kl == "nickname":
                nick = v.strip()
            elif kl == "price":
                try:
                    price = int(v.strip())
                except ValueError:
                    pass
        if nick and nick.lower().startswith("commodity"):
            nicks.append(nick)
            prices[nick] = price
    return nicks, prices


def extract_market_entries(
    sections: list[tuple[str, list[tuple[str, str]]]],
    base_index: dict[str, dict],
    commodity_base_prices: dict[str, int],
) -> dict[str, list[BaseMarketEntry]]:
    """Extract per-commodity BaseMarketEntry lists from parsed market_commodities.ini.

    *base_index* maps ``base_nick.lower()`` to base info dicts.
    *commodity_base_prices* maps ``commodity_nick`` (original case) to base prices.
    """
    by_commodity: dict[str, list[BaseMarketEntry]] = {}
    for sec_name, entries in sections:
        if sec_name.lower() != "basegood":
            continue
        base_nick = ""
        for k, v in entries:
            if k.lower() == "base":
                base_nick = v.strip().lower()
                break
        if not base_nick or base_nick not in base_index:
            continue
        for k, v in entries:
            if k.lower() != "marketgood":
                continue
            fields = [f.strip() for f in v.split(",")]
            if len(fields) < 7:
                continue
            commodity = fields[0].strip()
            commodity_l = commodity.lower()
            if not commodity_l.startswith("commodity_"):
                continue
            if commodity_l.startswith("commodity_pilot_"):
                continue
            try:
                relation_flag = int(float(fields[5]))
                multiplier = float(fields[6])
            except ValueError:
                continue
            if multiplier <= 0.0:
                continue
            base_price = commodity_base_prices.get(commodity, 0)
            if base_price <= 0:
                continue
            price = float(base_price) * multiplier
            try:
                stock_min = int(float(fields[3])) if fields[3] else 0
                stock_max = int(float(fields[4])) if fields[4] else 0
            except (ValueError, IndexError):
                stock_min, stock_max = 0, 0
            by_commodity.setdefault(commodity, []).append(
                BaseMarketEntry(
                    base_nick=base_nick,
                    commodity=commodity,
                    price=price,
                    is_source=(relation_flag == 0),
                    relation_flag=relation_flag,
                    multiplier=multiplier,
                    stock_min=stock_min,
                    stock_max=stock_max,
                )
            )
    return by_commodity


def build_best_trade_pairs(
    by_commodity: dict[str, list[BaseMarketEntry]],
    commodity_display_map: dict[str, str],
    *,
    max_pairs_per_commodity: int = 6,
    total_limit: int = 3000,
) -> tuple[list[TradeRouteCandidate], list[str]]:
    """Find the most profitable trade route candidates from market entries.

    Returns ``(routes, sorted_commodity_list)``.
    """
    commodities = sorted(by_commodity.keys(), key=str.lower)
    rows: list[TradeRouteCandidate] = []

    for commodity in commodities:
        entries = by_commodity[commodity]
        if len(entries) < 2:
            continue
        sources = [e for e in entries if e.is_source]
        if not sources:
            sources = entries
        cheapest_sources = sorted(sources, key=lambda e: e.price)[:8]
        highest_targets = sorted(entries, key=lambda e: e.price, reverse=True)[:10]

        best_pairs: list[tuple[float, TradeRouteCandidate]] = []
        seen_pairs: set[tuple[str, str]] = set()
        label = commodity_display_map.get(
            commodity.lower(),
            commodity_fallback_display_name(commodity),
        )
        for src in cheapest_sources:
            if src.price <= 0:
                continue
            for dst in highest_targets:
                if dst.base_nick == src.base_nick or dst.price <= src.price:
                    continue
                key = (src.base_nick, dst.base_nick)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                profit = dst.price - src.price
                best_pairs.append(
                    (
                        profit,
                        TradeRouteCandidate(
                            name=f"{label}: {src.base_nick} -> {dst.base_nick}",
                            commodity=commodity,
                            commodity_label=label,
                            buy_loc=src.base_nick,
                            sell_loc=dst.base_nick,
                            buy_price=src.price,
                            sell_price=dst.price,
                        ),
                    )
                )
        best_pairs.sort(key=lambda t: t[0], reverse=True)
        rows.extend(r for _, r in best_pairs[:max_pairs_per_commodity])

    rows.sort(key=lambda r: r.profit, reverse=True)
    return rows[:total_limit], commodities


def build_trade_route_rows_from_market_sections(
    sections: list[tuple[str, list[tuple[str, str]]]],
    *,
    base_index: dict[str, dict],
    commodity_base_prices: dict[str, int],
    commodity_display_map: dict[str, str],
) -> tuple[list[dict], list[str]]:
    by_commodity_entries = extract_market_entries(
        sections,
        base_index,
        commodity_base_prices,
    )
    candidates, commodities = build_best_trade_pairs(
        by_commodity_entries,
        commodity_display_map,
    )
    return [candidate.to_dict() for candidate in candidates], commodities


def build_commodities(
    nicknames: list[str],
    base_prices: dict[str, int],
    display_map: dict[str, str],
) -> list[Commodity]:
    """Build a list of Commodity objects from scan results."""
    result: list[Commodity] = []
    for nick in nicknames:
        key = nick.lower()
        result.append(
            Commodity(
                nickname=nick,
                base_price=base_prices.get(nick, 0),
                display_name=display_map.get(key, commodity_fallback_display_name(nick)),
            )
        )
    return result
