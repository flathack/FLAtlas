"""Analysis, scoring, and filtering for trade routes.

Pure functions that work on data models without UI or I/O dependencies.
"""

from __future__ import annotations

from .trade_route_models import EnrichedTradeRoute
from .trade_route_scan import commodity_fallback_display_name


def compute_profit(buy_price: float, sell_price: float) -> float:
    return sell_price - buy_price


def compute_score(profit: float, jumps: int) -> int:
    return int((profit / max(1, jumps + 1)) * 10)


def compute_profit_per_jump(profit: float, jumps: int) -> float:
    if jumps <= 0:
        return profit
    return profit / jumps


def system_path_bfs(
    adjacency: dict[str, set[str]],
    src: str,
    dst: str,
) -> list[str]:
    """BFS shortest path between two systems. Returns list of system nicks."""
    src_u = str(src).upper()
    dst_u = str(dst).upper()
    if not src_u or not dst_u:
        return []
    if src_u == dst_u:
        return [src_u]
    q = [src_u]
    prev: dict[str, str | None] = {src_u: None}
    while q:
        cur = q.pop(0)
        for nxt in sorted(adjacency.get(cur, set())):
            if nxt in prev:
                continue
            prev[nxt] = cur
            if nxt == dst_u:
                path: list[str] = []
                p: str | None = dst_u
                while p is not None:
                    path.append(p)
                    p = prev.get(p)
                return list(reversed(path))
            q.append(nxt)
    return []


def enrich_route(
    row: dict,
    *,
    base_index: dict[str, dict],
    adjacency: dict[str, set[str]],
    commodity_display_map: dict[str, str],
    system_display_fn,
    cargo_capacity: int = 1,
) -> EnrichedTradeRoute:
    """Enrich a route dict with display names, system info, and metrics."""
    buy_base = base_index.get(str(row.get("buy_loc", "")).lower())
    sell_base = base_index.get(str(row.get("sell_loc", "")).lower())
    buy_system = buy_base.get("system", "?") if buy_base else "?"
    sell_system = sell_base.get("system", "?") if sell_base else "?"
    buy_label = buy_base.get("display_name", row.get("buy_loc", "")) if buy_base else row.get("buy_loc", "")
    sell_label = sell_base.get("display_name", row.get("sell_loc", "")) if sell_base else row.get("sell_loc", "")

    buy_price = float(row.get("buy_price", 0.0) or 0.0)
    sell_price = float(row.get("sell_price", 0.0) or 0.0)
    profit = compute_profit(buy_price, sell_price)

    sys_path = system_path_bfs(adjacency, buy_system, sell_system) if buy_system != "?" and sell_system != "?" else []
    jumps = max(0, len(sys_path) - 1) if sys_path else 0
    score = compute_score(profit, jumps)
    ppj = compute_profit_per_jump(profit, jumps)
    net_profit = compute_net_profit(profit, cargo_capacity)
    if buy_system == sell_system and buy_system not in ("", "?"):
        route_type = "local"
    elif sys_path:
        route_type = "inter-system"
    else:
        route_type = "unreachable"

    commodity_label = str(
        row.get("commodity_label")
        or commodity_display_map.get(
            str(row.get("commodity", "")).lower(),
            commodity_fallback_display_name(str(row.get("commodity", ""))),
        )
    )

    return EnrichedTradeRoute(
        name=row.get("name", ""),
        commodity=row.get("commodity", ""),
        commodity_label=commodity_label,
        buy_loc=row.get("buy_loc", ""),
        sell_loc=row.get("sell_loc", ""),
        buy_price=buy_price,
        sell_price=sell_price,
        enabled=bool(row.get("enabled", True)),
        buy_system=buy_system,
        sell_system=sell_system,
        buy_label=str(buy_label),
        sell_label=str(sell_label),
        buy_system_label=system_display_fn(buy_system),
        sell_system_label=system_display_fn(sell_system),
        route_type=route_type,
        profit=profit,
        jumps=jumps,
        score=score,
        profit_per_jump=ppj,
        net_profit=net_profit,
    )


def filter_routes(
    routes: list[dict],
    *,
    base_index: dict[str, dict],
    adjacency: dict[str, set[str]],
    commodity_display_map: dict[str, str],
    system_display_fn,
    commodity_filter: str = "",
    min_profit: float = 0.0,
    same_system_only: bool = False,
    search_text: str = "",
    max_jumps: int | None = None,
    source_system: str = "",
    target_system: str = "",
    cargo_capacity: int = 1,
    min_profit_per_jump: float = 0.0,
) -> list[EnrichedTradeRoute]:
    """Filter and enrich a list of route dicts."""
    commodity_filter_low = commodity_filter.strip().lower()
    search_low = search_text.strip().lower()
    source_system_low = source_system.strip().lower()
    target_system_low = target_system.strip().lower()

    # Extract system nick from "Label (NICK)" format
    if "(" in source_system_low and source_system_low.endswith(")"):
        source_system_low = source_system_low.rsplit("(", 1)[-1].rstrip(")")
    if "(" in target_system_low and target_system_low.endswith(")"):
        target_system_low = target_system_low.rsplit("(", 1)[-1].rstrip(")")

    filtered: list[EnrichedTradeRoute] = []
    for row in routes:
        if not bool(row.get("enabled", True)):
            continue

        enriched = enrich_route(
            row,
            base_index=base_index,
            adjacency=adjacency,
            commodity_display_map=commodity_display_map,
            system_display_fn=system_display_fn,
            cargo_capacity=cargo_capacity,
        )

        if commodity_filter_low and commodity_filter_low not in ("all commodities", "alle commodities"):
            if enriched.commodity.lower() != commodity_filter_low:
                continue
        if enriched.profit < min_profit:
            continue
        if enriched.profit_per_jump < min_profit_per_jump:
            continue
        if max_jumps is not None and enriched.jumps > max_jumps:
            continue
        if enriched.route_type == "unreachable":
            continue
        if same_system_only and enriched.buy_system != enriched.sell_system:
            continue
        if source_system_low and enriched.buy_system.lower() != source_system_low:
            continue
        if target_system_low and enriched.sell_system.lower() != target_system_low:
            continue
        if search_low:
            hay = (
                f"{enriched.name} {enriched.commodity} "
                f"{enriched.commodity_label} "
                f"{enriched.buy_loc} {enriched.sell_loc} {enriched.buy_label} {enriched.sell_label} "
                f"{enriched.buy_system} {enriched.sell_system} {enriched.buy_system_label} {enriched.sell_system_label}"
            ).lower()
            if search_low not in hay:
                continue
        filtered.append(enriched)

    return filtered


def validate_market_good_fields(fields: list[str]) -> list[str]:
    """Validate the fields of a MarketGood entry and return a list of issues."""
    issues: list[str] = []
    if len(fields) < 7:
        issues.append(f"Zu wenige Felder ({len(fields)} statt 7)")
        return issues
    commodity = fields[0].strip()
    if not commodity:
        issues.append("Commodity-Name ist leer")
    try:
        int(float(fields[5]))
    except (ValueError, IndexError):
        issues.append(f"Ungültiger relation_flag: {fields[5]!r}")
    try:
        mult = float(fields[6])
        if mult <= 0:
            issues.append(f"Multiplikator ist <= 0: {fields[6]!r}")
    except (ValueError, IndexError):
        issues.append(f"Ungültiger Multiplikator: {fields[6]!r}")
    return issues


# ── Phase 4: Market validation & analysis ────────────────────────

def validate_market_sections(
    sections: list[tuple[str, list[tuple[str, str]]]],
    *,
    known_bases: set[str] | None = None,
    known_commodities: set[str] | None = None,
) -> list[dict]:
    """Validate all BaseGood/MarketGood entries and return a list of issues.

    Each issue dict has keys: ``base``, ``commodity`` (optional),
    ``severity`` (``"error"`` or ``"warning"``), ``message``.
    """
    issues: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()

    for sec_name, entries in sections:
        if str(sec_name).lower() != "basegood":
            continue
        base_nick = ""
        for key, value in entries:
            if str(key).lower() == "base":
                base_nick = str(value).strip().lower()
                break
        if not base_nick:
            issues.append({
                "base": "(unbekannt)",
                "commodity": "",
                "severity": "error",
                "message": "BaseGood-Sektion ohne 'base'-Schlüssel",
            })
            continue

        # Check base existence
        if known_bases is not None and base_nick not in known_bases:
            issues.append({
                "base": base_nick,
                "commodity": "",
                "severity": "error",
                "message": f"Base '{base_nick}' existiert nicht im Universum",
            })

        mg_count = 0
        for key, value in entries:
            if str(key).lower() != "marketgood":
                continue
            mg_count += 1
            fields = [f.strip() for f in str(value).split(",")]
            field_issues = validate_market_good_fields(fields)
            commodity = fields[0].strip().lower() if fields else ""

            for fi in field_issues:
                issues.append({
                    "base": base_nick,
                    "commodity": commodity,
                    "severity": "error",
                    "message": fi,
                })

            if not commodity:
                continue

            # Duplicate check
            pair = (base_nick, commodity)
            if pair in seen_pairs:
                issues.append({
                    "base": base_nick,
                    "commodity": commodity,
                    "severity": "warning",
                    "message": f"Doppelter MarketGood-Eintrag für '{commodity}'",
                })
            seen_pairs.add(pair)

            # Commodity existence
            if known_commodities is not None and commodity not in known_commodities:
                issues.append({
                    "base": base_nick,
                    "commodity": commodity,
                    "severity": "error",
                    "message": f"Commodity '{commodity}' existiert nicht in goods.ini",
                })

        if mg_count == 0:
            issues.append({
                "base": base_nick,
                "commodity": "",
                "severity": "warning",
                "message": "Base hat keine MarketGood-Einträge",
            })

    return issues


def find_best_buyers(
    sections: list[tuple[str, list[tuple[str, str]]]],
    commodity: str,
    *,
    commodity_base_prices: dict[str, int],
) -> list[dict]:
    """Find bases that sell a commodity (relation_flag=1) sorted by effective price desc.

    Returns list of dicts: base, multiplier, effective_price.
    """
    from .trade_route_market import list_bases_with_commodity

    commodity_low = str(commodity).strip().lower()
    base_price = commodity_base_prices.get(commodity_low, 0)
    entries = list_bases_with_commodity(sections, commodity)
    result: list[dict] = []
    for e in entries:
        if e["relation_flag"] != 1:
            continue
        effective = int(base_price * e["multiplier"]) if base_price > 0 else 0
        result.append({
            "base": e["base"],
            "multiplier": e["multiplier"],
            "effective_price": effective,
        })
    result.sort(key=lambda x: x["effective_price"], reverse=True)
    return result


def find_best_sellers(
    sections: list[tuple[str, list[tuple[str, str]]]],
    commodity: str,
    *,
    commodity_base_prices: dict[str, int],
) -> list[dict]:
    """Find bases that buy a commodity (relation_flag=0) sorted by effective price asc.

    Returns list of dicts: base, multiplier, effective_price.
    """
    from .trade_route_market import list_bases_with_commodity

    commodity_low = str(commodity).strip().lower()
    base_price = commodity_base_prices.get(commodity_low, 0)
    entries = list_bases_with_commodity(sections, commodity)
    result: list[dict] = []
    for e in entries:
        if e["relation_flag"] != 0:
            continue
        effective = int(base_price * e["multiplier"]) if base_price > 0 else 0
        result.append({
            "base": e["base"],
            "multiplier": e["multiplier"],
            "effective_price": effective,
        })
    result.sort(key=lambda x: x["effective_price"])
    return result


def find_commodities_without_sink(
    sections: list[tuple[str, list[tuple[str, str]]]],
    known_commodities: set[str],
) -> list[str]:
    """Find commodities that have sources (buy) but no sinks (sell).

    Returns list of commodity nicknames without a selling base.
    """
    from .trade_route_market import list_bases_with_commodity

    result: list[str] = []
    for commodity in sorted(known_commodities):
        entries = list_bases_with_commodity(sections, commodity)
        has_source = any(e["relation_flag"] == 0 for e in entries)
        has_sink = any(e["relation_flag"] == 1 for e in entries)
        if has_source and not has_sink:
            result.append(commodity)
    return result


def rank_routes_by_profit(
    enriched_routes: list[EnrichedTradeRoute],
    *,
    top_n: int = 10,
    worst: bool = False,
) -> list[EnrichedTradeRoute]:
    """Return top-N (or worst-N) routes by profit."""
    sorted_routes = sorted(enriched_routes, key=lambda r: r.profit, reverse=not worst)
    return sorted_routes[:top_n]


# ── Phase 6: Comfort functions ───────────────────────────────────

def compute_net_profit(
    profit_per_unit: float,
    cargo_capacity: int,
) -> float:
    """Compute net profit for a full cargo load."""
    return profit_per_unit * max(0, cargo_capacity)


def export_routes_csv(
    routes: list[EnrichedTradeRoute],
) -> str:
    """Export enriched routes to CSV text."""
    import csv
    import io

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Name", "Commodity", "Buy At", "Buy Price", "Sell At", "Sell Price",
        "Source System", "Target System", "Profit", "Net Profit", "Jumps", "Profit/Jump", "Score",
    ])
    for r in routes:
        writer.writerow([
            r.name, r.commodity_label, r.buy_label, int(r.buy_price),
            r.sell_label, int(r.sell_price),
            r.buy_system_label, r.sell_system_label,
            int(r.profit), int(r.net_profit), r.jumps,
            f"{r.profit_per_jump:.1f}", r.score,
        ])
    return buf.getvalue()
