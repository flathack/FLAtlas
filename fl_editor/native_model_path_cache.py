from __future__ import annotations


def native_model_path_cache_key(*, game_path: str, archetype: str) -> str:
    return f"{game_path.strip().lower()}::{archetype.strip().lower()}"


def touch_native_model_path_cache_order(order: list[str], cache_key: str) -> None:
    try:
        order.remove(cache_key)
    except ValueError:
        pass
    order.append(cache_key)


def prune_native_model_path_cache(
    cache_by_key: dict[str, object | None],
    order: list[str],
    *,
    max_entries: int,
) -> tuple[str, ...]:
    if max_entries <= 0:
        removed = tuple(cache_by_key.keys())
        cache_by_key.clear()
        order.clear()
        return removed
    removed_keys: list[str] = []
    while len(cache_by_key) > max_entries and order:
        oldest = order.pop(0)
        if oldest not in cache_by_key:
            continue
        cache_by_key.pop(oldest, None)
        removed_keys.append(oldest)
    _compact_cache_order(order, cache_by_key)
    return tuple(removed_keys)


def _compact_cache_order(order: list[str], cache_by_key: dict[str, object | None]) -> None:
    seen: set[str] = set()
    compacted: list[str] = []
    for key in order:
        if key in seen:
            continue
        seen.add(key)
        if key in cache_by_key:
            compacted.append(key)
    order[:] = compacted
