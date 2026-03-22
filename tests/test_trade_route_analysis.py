"""Tests for trade_route_analysis – pure calculation and filtering."""

from __future__ import annotations

from fl_editor.trade_route_analysis import (
    compute_net_profit,
    compute_profit,
    compute_profit_per_jump,
    compute_score,
    enrich_route,
    export_routes_csv,
    filter_routes,
    find_best_buyers,
    find_best_sellers,
    find_commodities_without_sink,
    rank_routes_by_profit,
    system_path_bfs,
    validate_market_good_fields,
    validate_market_sections,
)


def test_compute_profit():
    assert compute_profit(100.0, 350.0) == 250.0
    assert compute_profit(200.0, 100.0) == -100.0


def test_compute_score():
    assert compute_score(200.0, 0) == 2000
    assert compute_score(200.0, 1) == 1000
    assert compute_score(200.0, 3) == 500


def test_compute_profit_per_jump():
    assert compute_profit_per_jump(200.0, 0) == 200.0
    assert compute_profit_per_jump(200.0, 2) == 100.0


def test_system_path_bfs_same():
    adj = {"A": {"B"}, "B": {"A", "C"}, "C": {"B"}}
    assert system_path_bfs(adj, "A", "A") == ["A"]


def test_system_path_bfs_direct():
    adj = {"A": {"B"}, "B": {"A", "C"}, "C": {"B"}}
    assert system_path_bfs(adj, "A", "B") == ["A", "B"]


def test_system_path_bfs_multi_hop():
    adj = {"A": {"B"}, "B": {"A", "C"}, "C": {"B"}}
    assert system_path_bfs(adj, "A", "C") == ["A", "B", "C"]


def test_system_path_bfs_unreachable():
    adj = {"A": {"B"}, "B": {"A"}, "X": {"Y"}, "Y": {"X"}}
    assert system_path_bfs(adj, "A", "X") == []


def test_system_path_bfs_empty():
    assert system_path_bfs({}, "", "") == []


def test_enrich_route():
    base_index = {
        "base_a": {"base_nick": "base_a", "display_name": "Station Alpha", "system": "SYS_A", "pos": (0, 0)},
        "base_b": {"base_nick": "base_b", "display_name": "Station Beta", "system": "SYS_B", "pos": (100, 100)},
    }
    adjacency = {"SYS_A": {"SYS_B"}, "SYS_B": {"SYS_A"}}
    display_map = {"commodity_gold": "Gold"}
    row = {
        "name": "Gold: base_a -> base_b",
        "commodity": "commodity_gold",
        "buy_loc": "base_a",
        "sell_loc": "base_b",
        "buy_price": 100.0,
        "sell_price": 350.0,
        "enabled": True,
    }

    result = enrich_route(
        row,
        base_index=base_index,
        adjacency=adjacency,
        commodity_display_map=display_map,
        system_display_fn=lambda s: s,
    )
    assert result.profit == 250.0
    assert result.jumps == 1
    assert result.buy_system == "SYS_A"
    assert result.sell_system == "SYS_B"
    assert result.buy_label == "Station Alpha"
    assert result.sell_label == "Station Beta"
    assert result.commodity_label == "Gold"
    assert result.route_type == "inter-system"
    assert result.profit_per_jump == 250.0
    assert result.net_profit == 250.0


def test_enrich_route_with_cargo_capacity():
    base_index = {
        "base_a": {"base_nick": "base_a", "display_name": "Station Alpha", "system": "SYS_A", "pos": (0, 0)},
        "base_b": {"base_nick": "base_b", "display_name": "Station Beta", "system": "SYS_B", "pos": (100, 100)},
    }
    row = {
        "commodity": "commodity_gold",
        "buy_loc": "base_a",
        "sell_loc": "base_b",
        "buy_price": 100.0,
        "sell_price": 350.0,
        "enabled": True,
    }

    result = enrich_route(
        row,
        base_index=base_index,
        adjacency={"SYS_A": {"SYS_B"}, "SYS_B": {"SYS_A"}},
        commodity_display_map={},
        system_display_fn=lambda s: s,
        cargo_capacity=40,
    )

    assert result.net_profit == 10000.0


def test_enrich_route_marks_unreachable_system_pairs():
    base_index = {
        "base_a": {"base_nick": "base_a", "display_name": "Station Alpha", "system": "SYS_A", "pos": (0, 0)},
        "base_b": {"base_nick": "base_b", "display_name": "Station Beta", "system": "SYS_B", "pos": (100, 100)},
    }
    row = {
        "commodity": "commodity_gold",
        "buy_loc": "base_a",
        "sell_loc": "base_b",
        "buy_price": 100.0,
        "sell_price": 350.0,
        "enabled": True,
    }

    result = enrich_route(
        row,
        base_index=base_index,
        adjacency={"SYS_A": {"SYS_C"}, "SYS_C": {"SYS_A"}},
        commodity_display_map={},
        system_display_fn=lambda s: s,
    )

    assert result.jumps == 0
    assert result.route_type == "unreachable"


def test_filter_routes_min_profit():
    base_index = {
        "base_a": {"base_nick": "base_a", "display_name": "A", "system": "S1", "pos": (0, 0)},
        "base_b": {"base_nick": "base_b", "display_name": "B", "system": "S1", "pos": (10, 10)},
    }
    rows = [
        {"commodity": "commodity_gold", "buy_loc": "base_a", "sell_loc": "base_b", "buy_price": 100.0, "sell_price": 200.0, "enabled": True},
        {"commodity": "commodity_silver", "buy_loc": "base_a", "sell_loc": "base_b", "buy_price": 100.0, "sell_price": 130.0, "enabled": True},
    ]
    result = filter_routes(
        rows,
        base_index=base_index,
        adjacency={},
        commodity_display_map={},
        system_display_fn=lambda s: s,
        min_profit=50.0,
    )
    assert len(result) == 1
    assert result[0].commodity == "commodity_gold"


def test_filter_routes_skips_unreachable_routes():
    base_index = {
        "base_a": {"base_nick": "base_a", "display_name": "A", "system": "S1", "pos": (0, 0)},
        "base_b": {"base_nick": "base_b", "display_name": "B", "system": "S2", "pos": (10, 10)},
    }
    rows = [
        {"commodity": "commodity_gold", "buy_loc": "base_a", "sell_loc": "base_b", "buy_price": 100.0, "sell_price": 200.0, "enabled": True},
    ]
    result = filter_routes(
        rows,
        base_index=base_index,
        adjacency={"S1": {"S3"}, "S3": {"S1"}},
        commodity_display_map={},
        system_display_fn=lambda s: s,
        min_profit=50.0,
    )
    assert result == []


def test_filter_routes_min_profit_per_jump():
    base_index = {
        "base_a": {"base_nick": "base_a", "display_name": "A", "system": "S1", "pos": (0, 0)},
        "base_b": {"base_nick": "base_b", "display_name": "B", "system": "S2", "pos": (10, 10)},
        "base_c": {"base_nick": "base_c", "display_name": "C", "system": "S3", "pos": (20, 20)},
    }
    adjacency = {"S1": {"S2"}, "S2": {"S1", "S3"}, "S3": {"S2"}}
    rows = [
        {"commodity": "commodity_gold", "buy_loc": "base_a", "sell_loc": "base_b", "buy_price": 100.0, "sell_price": 300.0, "enabled": True},
        {"commodity": "commodity_gold", "buy_loc": "base_a", "sell_loc": "base_c", "buy_price": 100.0, "sell_price": 320.0, "enabled": True},
    ]

    result = filter_routes(
        rows,
        base_index=base_index,
        adjacency=adjacency,
        commodity_display_map={},
        system_display_fn=lambda s: s,
        min_profit_per_jump=150.0,
    )

    assert len(result) == 1
    assert result[0].sell_loc == "base_b"


def test_filter_routes_commodity_filter():
    base_index = {
        "base_a": {"base_nick": "base_a", "display_name": "A", "system": "S1", "pos": (0, 0)},
        "base_b": {"base_nick": "base_b", "display_name": "B", "system": "S1", "pos": (10, 10)},
    }
    rows = [
        {"commodity": "commodity_gold", "buy_loc": "base_a", "sell_loc": "base_b", "buy_price": 100.0, "sell_price": 300.0, "enabled": True},
        {"commodity": "commodity_silver", "buy_loc": "base_a", "sell_loc": "base_b", "buy_price": 100.0, "sell_price": 300.0, "enabled": True},
    ]
    result = filter_routes(
        rows,
        base_index=base_index,
        adjacency={},
        commodity_display_map={},
        system_display_fn=lambda s: s,
        commodity_filter="commodity_gold",
    )
    assert len(result) == 1
    assert result[0].commodity == "commodity_gold"


def test_filter_routes_same_system_only():
    base_index = {
        "base_a": {"base_nick": "base_a", "display_name": "A", "system": "S1", "pos": (0, 0)},
        "base_b": {"base_nick": "base_b", "display_name": "B", "system": "S1", "pos": (10, 10)},
        "base_c": {"base_nick": "base_c", "display_name": "C", "system": "S2", "pos": (50, 50)},
    }
    rows = [
        {"commodity": "commodity_gold", "buy_loc": "base_a", "sell_loc": "base_b", "buy_price": 100.0, "sell_price": 300.0, "enabled": True},
        {"commodity": "commodity_gold", "buy_loc": "base_a", "sell_loc": "base_c", "buy_price": 100.0, "sell_price": 400.0, "enabled": True},
    ]
    result = filter_routes(
        rows,
        base_index=base_index,
        adjacency={},
        commodity_display_map={},
        system_display_fn=lambda s: s,
        same_system_only=True,
    )
    assert len(result) == 1
    assert result[0].sell_loc == "base_b"
    assert result[0].route_type == "local"


def test_filter_routes_search_text():
    base_index = {
        "base_a": {"base_nick": "base_a", "display_name": "Manhattan", "system": "LI01", "pos": (0, 0)},
        "base_b": {"base_nick": "base_b", "display_name": "Pittsburgh", "system": "LI01", "pos": (10, 10)},
    }
    rows = [
        {"commodity": "commodity_gold", "buy_loc": "base_a", "sell_loc": "base_b", "buy_price": 100.0, "sell_price": 300.0, "enabled": True},
    ]
    # Search for "manhattan" should match
    result = filter_routes(
        rows,
        base_index=base_index,
        adjacency={},
        commodity_display_map={},
        system_display_fn=lambda s: s,
        search_text="manhattan",
    )
    assert len(result) == 1

    # Search for "nonexistent" should not match
    result = filter_routes(
        rows,
        base_index=base_index,
        adjacency={},
        commodity_display_map={},
        system_display_fn=lambda s: s,
        search_text="nonexistent",
    )
    assert len(result) == 0


def test_validate_market_good_fields_valid():
    fields = ["commodity_gold", "0", "-1", "150", "500", "0", "1.5"]
    assert validate_market_good_fields(fields) == []


def test_validate_market_good_fields_too_few():
    fields = ["commodity_gold", "0", "-1"]
    issues = validate_market_good_fields(fields)
    assert len(issues) == 1
    assert "Zu wenige Felder" in issues[0]


def test_validate_market_good_fields_bad_multiplier():
    fields = ["commodity_gold", "0", "-1", "150", "500", "0", "-1.0"]
    issues = validate_market_good_fields(fields)
    assert any("Multiplikator" in i for i in issues)


def test_validate_market_good_fields_invalid_relation():
    fields = ["commodity_gold", "0", "-1", "150", "500", "abc", "1.5"]
    issues = validate_market_good_fields(fields)
    assert any("relation_flag" in i for i in issues)


def test_filter_routes_max_jumps():
    base_index = {
        "base_a": {"base_nick": "base_a", "display_name": "A", "system": "S1", "pos": (0, 0)},
        "base_b": {"base_nick": "base_b", "display_name": "B", "system": "S2", "pos": (10, 10)},
        "base_c": {"base_nick": "base_c", "display_name": "C", "system": "S3", "pos": (50, 50)},
    }
    adjacency = {"S1": {"S2"}, "S2": {"S1", "S3"}, "S3": {"S2"}}
    rows = [
        {"commodity": "commodity_gold", "buy_loc": "base_a", "sell_loc": "base_b", "buy_price": 100.0, "sell_price": 300.0, "enabled": True},
        {"commodity": "commodity_gold", "buy_loc": "base_a", "sell_loc": "base_c", "buy_price": 100.0, "sell_price": 400.0, "enabled": True},
    ]
    # max_jumps=1 should only keep base_a->base_b (1 jump), not base_a->base_c (2 jumps)
    result = filter_routes(
        rows,
        base_index=base_index,
        adjacency=adjacency,
        commodity_display_map={},
        system_display_fn=lambda s: s,
        max_jumps=1,
    )
    assert len(result) == 1
    assert result[0].sell_loc == "base_b"


def test_filter_routes_source_system():
    base_index = {
        "base_a": {"base_nick": "base_a", "display_name": "A", "system": "S1", "pos": (0, 0)},
        "base_b": {"base_nick": "base_b", "display_name": "B", "system": "S2", "pos": (10, 10)},
        "base_c": {"base_nick": "base_c", "display_name": "C", "system": "S2", "pos": (50, 50)},
    }
    rows = [
        {"commodity": "commodity_gold", "buy_loc": "base_a", "sell_loc": "base_b", "buy_price": 100.0, "sell_price": 300.0, "enabled": True},
        {"commodity": "commodity_gold", "buy_loc": "base_c", "sell_loc": "base_a", "buy_price": 100.0, "sell_price": 300.0, "enabled": True},
    ]
    result = filter_routes(
        rows,
        base_index=base_index,
        adjacency={"S1": {"S2"}, "S2": {"S1"}},
        commodity_display_map={},
        system_display_fn=lambda s: s,
        source_system="S1",
    )
    assert len(result) == 1
    assert result[0].buy_loc == "base_a"


def test_filter_routes_target_system():
    base_index = {
        "base_a": {"base_nick": "base_a", "display_name": "A", "system": "S1", "pos": (0, 0)},
        "base_b": {"base_nick": "base_b", "display_name": "B", "system": "S2", "pos": (10, 10)},
    }
    rows = [
        {"commodity": "commodity_gold", "buy_loc": "base_a", "sell_loc": "base_b", "buy_price": 100.0, "sell_price": 300.0, "enabled": True},
        {"commodity": "commodity_gold", "buy_loc": "base_b", "sell_loc": "base_a", "buy_price": 100.0, "sell_price": 300.0, "enabled": True},
    ]
    result = filter_routes(
        rows,
        base_index=base_index,
        adjacency={"S1": {"S2"}, "S2": {"S1"}},
        commodity_display_map={},
        system_display_fn=lambda s: s,
        target_system="S2",
    )
    assert len(result) == 1
    assert result[0].sell_system == "S2"


def test_filter_routes_applies_cargo_capacity_to_net_profit():
    base_index = {
        "base_a": {"base_nick": "base_a", "display_name": "A", "system": "S1", "pos": (0, 0)},
        "base_b": {"base_nick": "base_b", "display_name": "B", "system": "S2", "pos": (10, 10)},
    }
    rows = [
        {"commodity": "commodity_gold", "buy_loc": "base_a", "sell_loc": "base_b", "buy_price": 100.0, "sell_price": 300.0, "enabled": True},
    ]

    result = filter_routes(
        rows,
        base_index=base_index,
        adjacency={"S1": {"S2"}, "S2": {"S1"}},
        commodity_display_map={},
        system_display_fn=lambda s: s,
        cargo_capacity=25,
    )

    assert len(result) == 1
    assert result[0].net_profit == 5000.0


def test_filter_routes_source_system_label_format():
    """Source system filter with 'Label (NICK)' format."""
    base_index = {
        "base_a": {"base_nick": "base_a", "display_name": "A", "system": "LI01", "pos": (0, 0)},
        "base_b": {"base_nick": "base_b", "display_name": "B", "system": "LI02", "pos": (10, 10)},
    }
    rows = [
        {"commodity": "commodity_gold", "buy_loc": "base_a", "sell_loc": "base_b", "buy_price": 100.0, "sell_price": 300.0, "enabled": True},
    ]
    result = filter_routes(
        rows,
        base_index=base_index,
        adjacency={"LI01": {"LI02"}, "LI02": {"LI01"}},
        commodity_display_map={},
        system_display_fn=lambda s: s,
        source_system="New York (LI01)",
    )
    assert len(result) == 1


# ── Phase 4: validate_market_sections ─────────────────────────────

def _market_sections():
    return [
        ("BaseGood", [
            ("base", "li01_01_base"),
            ("MarketGood", "commodity_gold, 0, -1, 150, 500, 0, 1.0"),
            ("MarketGood", "commodity_silver, 0, -1, 100, 300, 1, 0.9"),
        ]),
        ("BaseGood", [
            ("base", "li02_01_base"),
            ("MarketGood", "commodity_gold, 0, -1, 200, 600, 1, 1.2"),
        ]),
    ]


def test_validate_market_sections_no_issues():
    issues = validate_market_sections(_market_sections())
    assert issues == []


def test_validate_market_sections_unknown_base():
    issues = validate_market_sections(
        _market_sections(),
        known_bases={"li01_01_base"},  # li02_01_base missing
    )
    assert len(issues) == 1
    assert issues[0]["base"] == "li02_01_base"
    assert issues[0]["severity"] == "error"
    assert "existiert nicht" in issues[0]["message"]


def test_validate_market_sections_unknown_commodity():
    issues = validate_market_sections(
        _market_sections(),
        known_commodities={"commodity_gold"},  # commodity_silver missing
    )
    assert len(issues) == 1
    assert issues[0]["commodity"] == "commodity_silver"
    assert issues[0]["severity"] == "error"


def test_validate_market_sections_duplicate_entry():
    sections = [
        ("BaseGood", [
            ("base", "li01_01_base"),
            ("MarketGood", "commodity_gold, 0, -1, 150, 500, 0, 1.0"),
            ("MarketGood", "commodity_gold, 0, -1, 200, 600, 1, 1.5"),
        ]),
    ]
    issues = validate_market_sections(sections)
    assert any(i["severity"] == "warning" and "Doppelter" in i["message"] for i in issues)


def test_validate_market_sections_bad_fields():
    sections = [
        ("BaseGood", [
            ("base", "li01_01_base"),
            ("MarketGood", "commodity_gold, 0, -1"),  # only 3 fields
        ]),
    ]
    issues = validate_market_sections(sections)
    assert any("Zu wenige Felder" in i["message"] for i in issues)


def test_validate_market_sections_empty_base():
    sections = [
        ("BaseGood", [
            ("base", "li01_01_base"),
        ]),
    ]
    issues = validate_market_sections(sections)
    assert any("keine MarketGood" in i["message"] for i in issues)


def test_validate_market_sections_missing_base_key():
    sections = [
        ("BaseGood", [
            ("MarketGood", "commodity_gold, 0, -1, 150, 500, 0, 1.0"),
        ]),
    ]
    issues = validate_market_sections(sections)
    assert any("ohne 'base'" in i["message"] for i in issues)


# ── Phase 4: find_best_buyers/sellers ─────────────────────────────

def test_find_best_buyers():
    result = find_best_buyers(
        _market_sections(),
        "commodity_gold",
        commodity_base_prices={"commodity_gold": 1000},
    )
    assert len(result) == 1
    assert result[0]["base"] == "li02_01_base"
    assert result[0]["effective_price"] == 1200


def test_find_best_buyers_includes_implicit_base_price_targets():
    result = find_best_buyers(
        _market_sections(),
        "commodity_gold",
        commodity_base_prices={"commodity_gold": 1000},
        known_bases={"li01_01_base", "li02_01_base", "li03_01_base"},
    )
    assert any(row["base"] == "li03_01_base" and row["effective_price"] == 1000 for row in result)


def test_find_best_sellers():
    result = find_best_sellers(
        _market_sections(),
        "commodity_gold",
        commodity_base_prices={"commodity_gold": 1000},
    )
    assert len(result) == 1
    assert result[0]["base"] == "li01_01_base"
    assert result[0]["effective_price"] == 1000


# ── Phase 4: find_commodities_without_sink ────────────────────────

def test_find_commodities_without_sink():
    sections = [
        ("BaseGood", [
            ("base", "base_a"),
            ("MarketGood", "orphan_commodity, 0, -1, 100, 300, 0, 1.0"),  # source only
            ("MarketGood", "good_commodity, 0, -1, 100, 300, 0, 1.0"),
        ]),
        ("BaseGood", [
            ("base", "base_b"),
            ("MarketGood", "good_commodity, 0, -1, 200, 600, 1, 1.2"),  # sink
        ]),
    ]
    result = find_commodities_without_sink(sections, {"orphan_commodity", "good_commodity"})
    assert result == ["orphan_commodity"]


def test_find_commodities_without_sink_respects_implicit_base_price_targets():
    sections = [
        ("BaseGood", [
            ("base", "base_a"),
            ("MarketGood", "orphan_commodity, 0, -1, 100, 300, 0, 1.0"),
        ]),
    ]
    result = find_commodities_without_sink(
        sections,
        {"orphan_commodity"},
        known_bases={"base_a", "base_b"},
        commodity_base_prices={"orphan_commodity": 100},
    )
    assert result == []


# ── Phase 4: rank_routes_by_profit ────────────────────────────────

def test_rank_routes_top():
    from fl_editor.trade_route_models import EnrichedTradeRoute
    routes = [
        EnrichedTradeRoute(name="r1", commodity="a", commodity_label="A",
            buy_loc="b1", sell_loc="b2", buy_price=100, sell_price=200, enabled=True,
            buy_system="S1", sell_system="S2", buy_label="B1", sell_label="B2",
            buy_system_label="S1", sell_system_label="S2", profit=100, jumps=1, score=500, profit_per_jump=100),
        EnrichedTradeRoute(name="r2", commodity="a", commodity_label="A",
            buy_loc="b1", sell_loc="b3", buy_price=100, sell_price=500, enabled=True,
            buy_system="S1", sell_system="S3", buy_label="B1", sell_label="B3",
            buy_system_label="S1", sell_system_label="S3", profit=400, jumps=2, score=800, profit_per_jump=200),
        EnrichedTradeRoute(name="r3", commodity="b", commodity_label="B",
            buy_loc="b4", sell_loc="b5", buy_price=50, sell_price=300, enabled=True,
            buy_system="S1", sell_system="S2", buy_label="B4", sell_label="B5",
            buy_system_label="S1", sell_system_label="S2", profit=250, jumps=1, score=600, profit_per_jump=250),
    ]
    top2 = rank_routes_by_profit(routes, top_n=2)
    assert len(top2) == 2
    assert top2[0].profit == 400
    assert top2[1].profit == 250


def test_rank_routes_worst():
    from fl_editor.trade_route_models import EnrichedTradeRoute
    routes = [
        EnrichedTradeRoute(name="r1", commodity="a", commodity_label="A",
            buy_loc="b1", sell_loc="b2", buy_price=100, sell_price=200, enabled=True,
            buy_system="S1", sell_system="S2", buy_label="B1", sell_label="B2",
            buy_system_label="S1", sell_system_label="S2", profit=100, jumps=1, score=500, profit_per_jump=100),
        EnrichedTradeRoute(name="r2", commodity="a", commodity_label="A",
            buy_loc="b1", sell_loc="b3", buy_price=100, sell_price=500, enabled=True,
            buy_system="S1", sell_system="S3", buy_label="B1", sell_label="B3",
            buy_system_label="S1", sell_system_label="S3", profit=400, jumps=2, score=800, profit_per_jump=200),
    ]
    worst1 = rank_routes_by_profit(routes, top_n=1, worst=True)
    assert len(worst1) == 1
    assert worst1[0].profit == 100


# ── Phase 6: compute_net_profit ───────────────────────────────────

def test_compute_net_profit():
    assert compute_net_profit(250.0, 100) == 25000.0
    assert compute_net_profit(250.0, 0) == 0.0
    assert compute_net_profit(100.0, -5) == 0.0  # negative cargo clamped to 0


# ── Phase 6: export_routes_csv ────────────────────────────────────

def test_export_routes_csv():
    from fl_editor.trade_route_models import EnrichedTradeRoute
    routes = [
        EnrichedTradeRoute(name="Gold Route", commodity="gold", commodity_label="Gold",
            buy_loc="base_a", sell_loc="base_b", buy_price=100, sell_price=350, enabled=True,
            buy_system="LI01", sell_system="LI02", buy_label="Manhattan", sell_label="Pittsburgh",
            buy_system_label="New York", sell_system_label="Pennsylvania",
            profit=250, jumps=2, score=800, profit_per_jump=125.0, net_profit=8750.0),
    ]
    csv_text = export_routes_csv(routes)
    lines = csv_text.strip().split("\n")
    assert len(lines) == 2  # header + 1 data row
    assert "Gold Route" in lines[1]
    assert "Manhattan" in lines[1]
    assert "Pittsburgh" in lines[1]
    assert "250" in lines[1]
    assert "8750" in lines[1]
