from __future__ import annotations

from typing import Any

from .path_utils import parse_position


def item_world_pos_tuple(item) -> tuple[float, float, float] | None:
    if item is None:
        return None
    try:
        fx, fy, fz = parse_position(getattr(item, "data", {}).get("pos", "0,0,0"))
        return float(fx), float(fy), float(fz)
    except Exception:
        return None


def is_tradelane_item(item) -> bool:
    if item is None:
        return False
    data = getattr(item, "data", {})
    arch = str(data.get("archetype", "")).lower()
    nick = str(getattr(item, "nickname", "")).lower()
    return (
        "trade_lane_ring" in arch
        or "tradelane_ring" in arch
        or "trade_lane_ring" in nick
        or "tradelane_ring" in nick
    )


def build_lane_path_tuples(selected_obj, all_objs: list[Any]) -> list[tuple[float, float, float]]:
    ring_map: dict[str, Any] = {}
    for obj in list(all_objs or []):
        if is_tradelane_item(obj):
            ring_map[str(getattr(obj, "nickname", "")).lower()] = obj
    if not ring_map:
        return []

    cur = selected_obj
    seen: set[str] = set()
    while cur:
        prev = str(getattr(cur, "data", {}).get("prev_ring", "")).strip().lower()
        if not prev or prev in seen or prev not in ring_map:
            break
        seen.add(prev)
        cur = ring_map.get(prev)

    path: list[tuple[float, float, float]] = []
    seen.clear()
    while cur:
        nick = str(getattr(cur, "nickname", "")).lower()
        if nick in seen:
            break
        seen.add(nick)
        pos = item_world_pos_tuple(cur)
        if pos is not None:
            path.append(pos)
        nxt = str(getattr(cur, "data", {}).get("next_ring", "")).strip().lower()
        if not nxt or nxt not in ring_map:
            break
        cur = ring_map.get(nxt)
    return path
