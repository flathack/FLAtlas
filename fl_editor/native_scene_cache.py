from __future__ import annotations

from pathlib import Path


def touch_native_scene_cache_order(
    order: list[Path],
    model_path: Path,
) -> None:
    try:
        order.remove(model_path)
    except ValueError:
        pass
    order.append(model_path)


def prune_native_scene_cache(
    cache_by_path: dict[Path, object | None],
    order: list[Path],
    max_entries: int,
    protected_paths: tuple[Path, ...] = (),
) -> tuple[Path, ...]:
    if max_entries <= 0:
        removed = tuple(cache_by_path.keys())
        cache_by_path.clear()
        order.clear()
        return removed

    removed_paths: list[Path] = []
    protected = set(protected_paths)
    while len(cache_by_path) > max_entries:
        candidate = _pop_oldest_unprotected(order, protected)
        if candidate is None:
            break
        if candidate in cache_by_path:
            cache_by_path.pop(candidate, None)
            removed_paths.append(candidate)
    _compact_cache_order(order, cache_by_path)
    return tuple(removed_paths)


def _pop_oldest_unprotected(order: list[Path], protected: set[Path]) -> Path | None:
    while order:
        candidate = order.pop(0)
        if candidate in protected:
            order.append(candidate)
            if all(path in protected for path in order):
                return None
            continue
        return candidate
    return None


def _compact_cache_order(order: list[Path], cache_by_path: dict[Path, object | None]) -> None:
    seen: set[Path] = set()
    compacted: list[Path] = []
    for model_path in order:
        if model_path in seen:
            continue
        seen.add(model_path)
        if model_path in cache_by_path:
            compacted.append(model_path)
    order[:] = compacted
