from __future__ import annotations

from types import SimpleNamespace

from fl_editor.flight_mode_scene_refs import is_tradelane_scene_item, item_world_pos_vector, lane_path_vectors


def test_item_world_pos_vector_returns_qvector():
    item = SimpleNamespace(data={"pos": "1, 2, 3"})
    pos = item_world_pos_vector(item)
    assert pos is not None
    assert (pos.x(), pos.y(), pos.z()) == (1.0, 2.0, 3.0)


def test_is_tradelane_scene_item_delegates_to_navigation_helper():
    item = SimpleNamespace(nickname="ring_a", data={"archetype": "trade_lane_ring", "pos": "0,0,0"})
    assert is_tradelane_scene_item(item) is True


def test_lane_path_vectors_converts_lane_path_tuples_to_qvectors():
    selected = SimpleNamespace(
        nickname="lane_a",
        data={"archetype": "trade_lane_ring", "pos": "0,0,0", "next_ring": "lane_b"},
    )
    other = SimpleNamespace(
        nickname="lane_b",
        data={"archetype": "trade_lane_ring", "pos": "10,0,0", "prev_ring": "lane_a"},
    )
    path = lane_path_vectors(selected, [selected, other])
    assert [(vec.x(), vec.y(), vec.z()) for vec in path] == [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0)]
