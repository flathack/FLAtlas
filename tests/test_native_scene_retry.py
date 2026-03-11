from __future__ import annotations

from pathlib import Path

from fl_editor.native_scene_retry import prune_failed_native_scene_loads
from fl_editor.native_scene_retry import should_retry_failed_native_scene_load


def test_should_retry_failed_native_scene_load_respects_cooldown():
    assert should_retry_failed_native_scene_load(
        last_failed_at=None,
        now_monotonic=10.0,
        retry_cooldown_seconds=8.0,
    ) is True
    assert should_retry_failed_native_scene_load(
        last_failed_at=4.5,
        now_monotonic=10.0,
        retry_cooldown_seconds=8.0,
    ) is False
    assert should_retry_failed_native_scene_load(
        last_failed_at=2.0,
        now_monotonic=10.0,
        retry_cooldown_seconds=8.0,
    ) is True


def test_prune_failed_native_scene_loads_keeps_newest_entries(tmp_path: Path):
    a = tmp_path / "a.cmp"
    b = tmp_path / "b.cmp"
    c = tmp_path / "c.cmp"
    failed = {a: 1.0, b: 2.0, c: 3.0}

    removed = prune_failed_native_scene_loads(failed, max_entries=2)

    assert removed == (a,)
    assert failed == {b: 2.0, c: 3.0}
