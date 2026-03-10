"""Helpers for left-sidebar compact width and splitter sizing."""

from __future__ import annotations


def normalized_browser_compact_width(width: object, default: int = 240) -> int:
    try:
        value = int(width)
    except Exception:
        value = int(default)
    return max(210, min(620, value))


def left_sidebar_width_state(
    *,
    is_browser: bool,
    compact_width: object,
    splitter_sizes: list[int] | tuple[int, ...] | None,
) -> dict[str, object]:
    if not is_browser:
        return {
            "min_width": 0,
            "max_width": 16777215,
            "splitter_sizes": None,
        }

    left_width = normalized_browser_compact_width(compact_width)
    if splitter_sizes is None or len(splitter_sizes) < 3:
        return {
            "min_width": left_width,
            "max_width": left_width,
            "splitter_sizes": None,
        }

    total = max(1, sum(int(size) for size in splitter_sizes))
    remaining = max(1, total - left_width)
    prev_center = max(1, int(splitter_sizes[1]))
    prev_right = max(1, int(splitter_sizes[2]))
    denom = prev_center + prev_right
    center = int(remaining * (prev_center / denom))
    right = remaining - center
    return {
        "min_width": left_width,
        "max_width": left_width,
        "splitter_sizes": [left_width, max(300, center), max(200, right)],
    }
