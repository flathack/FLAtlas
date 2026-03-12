from __future__ import annotations

from types import SimpleNamespace

from fl_editor.flight_mode_navigation import build_lane_path_tuples, is_tradelane_item, item_world_pos_tuple


def _obj(nickname: str, pos: str, *, archetype: str = "trade_lane_ring", prev_ring: str = "", next_ring: str = ""):
    return SimpleNamespace(
        nickname=nickname,
        data={
            "pos": pos,
            "archetype": archetype,
            "prev_ring": prev_ring,
            "next_ring": next_ring,
        },
    )


def test_item_world_pos_tuple_parses_position():
    assert item_world_pos_tuple(_obj("a", "1,2,3")) == (1.0, 2.0, 3.0)
    assert item_world_pos_tuple(None) is None


def test_is_tradelane_item_matches_arch_or_nickname():
    assert is_tradelane_item(_obj("ring_01", "0,0,0", archetype="trade_lane_ring"))
    assert is_tradelane_item(_obj("li01_tradelane_ring_01", "0,0,0", archetype="foo"))
    assert not is_tradelane_item(_obj("planet", "0,0,0", archetype="planet_3000"))


def test_build_lane_path_tuples_walks_prev_and_next_chain():
    a = _obj("ring_a", "0,0,0", next_ring="ring_b")
    b = _obj("ring_b", "10,0,0", prev_ring="ring_a", next_ring="ring_c")
    c = _obj("ring_c", "20,0,0", prev_ring="ring_b")

    path = build_lane_path_tuples(b, [c, b, a])

    assert path == [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (20.0, 0.0, 0.0)]
