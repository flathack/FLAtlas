from __future__ import annotations

from fl_editor.native_model_path_cache import native_model_path_cache_key
from fl_editor.native_model_path_cache import prune_native_model_path_cache
from fl_editor.native_model_path_cache import touch_native_model_path_cache_order


def test_native_model_path_cache_key_normalizes_input():
    assert native_model_path_cache_key(game_path=" /Game/Root ", archetype=" Li_BattleShip ") == "/game/root::li_battleship"


def test_touch_native_model_path_cache_order_keeps_mru_order():
    order = ["a", "b"]
    touch_native_model_path_cache_order(order, "a")
    touch_native_model_path_cache_order(order, "c")
    assert order == ["b", "a", "c"]


def test_prune_native_model_path_cache_removes_oldest():
    cache = {"a": "A", "b": "B", "c": "C"}
    order = ["a", "b", "c"]
    removed = prune_native_model_path_cache(cache, order, max_entries=2)
    assert removed == ("a",)
    assert cache == {"b": "B", "c": "C"}
    assert order == ["b", "c"]
