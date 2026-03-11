from __future__ import annotations

from pathlib import Path


def should_retry_failed_native_scene_load(
    *,
    last_failed_at: float | None,
    now_monotonic: float,
    retry_cooldown_seconds: float,
) -> bool:
    if last_failed_at is None:
        return True
    return (now_monotonic - last_failed_at) >= retry_cooldown_seconds


def prune_failed_native_scene_loads(
    failed_by_path: dict[Path, float],
    *,
    max_entries: int,
) -> tuple[Path, ...]:
    if max_entries <= 0:
        removed = tuple(failed_by_path.keys())
        failed_by_path.clear()
        return removed
    if len(failed_by_path) <= max_entries:
        return ()
    to_remove = sorted(failed_by_path.items(), key=lambda item: item[1])[: len(failed_by_path) - max_entries]
    removed_paths: list[Path] = []
    for model_path, _timestamp in to_remove:
        failed_by_path.pop(model_path, None)
        removed_paths.append(model_path)
    return tuple(removed_paths)
