from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QWidget


def center_tab_index_for_key(tab_specs: list[dict[str, object]], key: str | None) -> int:
    want = str(key or "").strip()
    if not want:
        return -1
    for index, spec in enumerate(tab_specs):
        if str(spec.get("key", "") or "").strip() == want:
            return index
    return -1


def center_tab_index_for_widget(tab_specs: list[dict[str, object]], widget: QWidget | None) -> int:
    if widget is None:
        return -1
    for index, spec in enumerate(tab_specs):
        if spec.get("widget") is widget:
            return index
    return -1


def center_register_tab(
    tab_specs: list[dict[str, object]],
    *,
    widget: QWidget,
    title: str,
    key: str,
    closable: bool,
) -> int:
    index = center_tab_index_for_key(tab_specs, key)
    if index >= 0:
        spec = tab_specs[index]
        spec["widget"] = widget
        spec["title"] = str(title or "").strip()
        spec["key"] = str(key or "").strip()
        spec["closable"] = bool(closable)
        return index
    tab_specs.append(
        {
            "widget": widget,
            "title": str(title or "").strip(),
            "key": str(key or "").strip(),
            "closable": bool(closable),
        }
    )
    return len(tab_specs) - 1


def center_set_tab_enabled(tab_specs: list[dict[str, object]], key: str, enabled: bool) -> bool:
    index = center_tab_index_for_key(tab_specs, key)
    if index < 0:
        return False
    spec = tab_specs[index]
    if bool(spec.get("enabled", True)) == bool(enabled):
        return False
    spec["enabled"] = bool(enabled)
    return True


def center_fallback_tab_index_after_close(tab_specs: list[dict[str, object]], closed_index: int) -> int:
    if not tab_specs:
        return -1
    if 0 <= closed_index - 1 < len(tab_specs):
        return closed_index - 1
    if 0 <= closed_index < len(tab_specs):
        return closed_index
    return len(tab_specs) - 1


def center_tab_session_payload(tab_specs: list[dict[str, object]], current_key: str | None) -> dict[str, object]:
    tabs: list[dict[str, str]] = []
    for spec in tab_specs:
        key = str(spec.get("key", "") or "").strip()
        if not key or key in {"mods", "universe", "trade", "name"}:
            continue
        row = {"key": key}
        path = str(spec.get("path", "") or "").strip()
        if path:
            row["path"] = path
        tabs.append(row)
    return {
        "current": str(current_key or "").strip(),
        "order": [
            str(spec.get("key", "") or "").strip()
            for spec in tab_specs
            if str(spec.get("key", "") or "").strip()
        ],
        "tabs": tabs,
    }


def center_move_tab(tab_specs: list[dict[str, object]], from_index: int, to_index: int) -> bool:
    if not (0 <= from_index < len(tab_specs) and 0 <= to_index < len(tab_specs)):
        return False
    if from_index == to_index:
        return False
    spec = tab_specs.pop(from_index)
    tab_specs.insert(to_index, spec)
    return True


def center_apply_saved_tab_order(
    tab_specs: list[dict[str, object]],
    ordered_keys: list[str],
) -> list[dict[str, object]]:
    wanted = [str(key or "").strip() for key in ordered_keys if str(key or "").strip()]
    if not wanted:
        return list(tab_specs)
    existing = {str(spec.get("key", "") or "").strip(): spec for spec in tab_specs}
    front: list[dict[str, object]] = []
    seen: set[str] = set()
    for key in wanted:
        spec = existing.get(key)
        if spec is not None:
            front.append(spec)
            seen.add(key)
    tail = [spec for spec in tab_specs if str(spec.get("key", "") or "").strip() not in seen]
    return front + tail
