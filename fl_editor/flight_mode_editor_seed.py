"""Editor-Seed-Helfer fuer den Flight-Mode-Startzustand."""

from __future__ import annotations

from typing import Any, Callable


def selection_seed_state(
    *,
    selected_item: Any,
    parse_position: Callable[[str], tuple[float, float, float] | None],
    seed_builder: Callable[[tuple[float, float, float] | None], dict[str, object] | None],
) -> dict[str, object] | None:
    """Leitet einen Flight-Seed aus dem aktuell selektierten Objekt ab."""
    if selected_item is None or hasattr(selected_item, "sys_path"):
        return None
    try:
        data = getattr(selected_item, "data", {})
        raw_pos = data.get("pos", "0,0,0") if isinstance(data, dict) else "0,0,0"
        return seed_builder(parse_position(raw_pos))
    except Exception:
        return None
