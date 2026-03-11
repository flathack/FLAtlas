from __future__ import annotations

from pathlib import Path

from fl_editor.native_scene_cache import prune_native_scene_cache
from fl_editor.native_scene_cache import touch_native_scene_cache_order


def test_touch_native_scene_cache_order_moves_path_to_mru(tmp_path: Path):
    a = tmp_path / "a.cmp"
    b = tmp_path / "b.cmp"
    c = tmp_path / "c.cmp"
    order = [a, b]

    touch_native_scene_cache_order(order, a)
    touch_native_scene_cache_order(order, c)

    assert order == [b, a, c]


def test_prune_native_scene_cache_removes_oldest_entries_and_compacts_order(tmp_path: Path):
    a = tmp_path / "a.cmp"
    b = tmp_path / "b.cmp"
    c = tmp_path / "c.cmp"
    d = tmp_path / "d.cmp"
    cache = {a: "scene-a", b: "scene-b", c: "scene-c", d: "scene-d"}
    order = [a, b, c, d, c]

    removed = prune_native_scene_cache(cache, order, max_entries=2)

    assert removed == (a, b)
    assert cache == {c: "scene-c", d: "scene-d"}
    assert order == [c, d]


def test_prune_native_scene_cache_keeps_protected_path(tmp_path: Path):
    a = tmp_path / "a.cmp"
    b = tmp_path / "b.cmp"
    c = tmp_path / "c.cmp"
    cache = {a: "scene-a", b: "scene-b", c: "scene-c"}
    order = [a, b, c]

    removed = prune_native_scene_cache(cache, order, max_entries=1, protected_paths=(a,))

    assert removed == (b, c)
    assert cache == {a: "scene-a"}
    assert order == [a]
