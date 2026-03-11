from __future__ import annotations

from pathlib import Path


def center_system_tab_spec(
    tab_specs: list[dict[str, object]],
    *,
    key: str | None = None,
    current_key: str | None = None,
) -> dict[str, object] | None:
    tab_key = str(key or current_key or "").strip()
    if not tab_key.startswith("system:"):
        return None
    for spec in tab_specs:
        if str(spec.get("key", "") or "").strip() == tab_key:
            return spec if isinstance(spec, dict) else None
    return None


def system_tab_key(path: str, normalized_path_key: str) -> str:
    return f"system:{normalized_path_key}"


def system_tab_title(
    path: str,
    *,
    system_display_name_func,
    unknown_title: str,
) -> str:
    path_obj = Path(str(path or "").strip())
    nick = path_obj.stem.upper()
    display_name = str(system_display_name_func(nick) or "").strip()
    if nick and display_name and display_name.lower() != nick.lower():
        return f"{nick} - {display_name}"
    return nick or display_name or path_obj.name or unknown_title


def apply_dirty_system_tab_title(base_title: str, dirty: bool) -> str:
    if not dirty:
        return str(base_title or "").strip()
    title = str(base_title or "").strip()
    return title if title.startswith("* ") else f"* {title}"
