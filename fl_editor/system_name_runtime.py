"""Runtime helpers for system display-name and IDS label handling."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QApplication

from .dll_resources import DllStringResolver
from .i18n import tr
from .models import SolarObject, UniverseSystem


def dll_file_stat_signature(path: Path | None) -> tuple[str, int, int]:
    if path is None:
        return ("", 0, 0)
    try:
        resolved = path.resolve()
    except Exception:
        resolved = Path(path)
    try:
        st = resolved.stat()
        return (str(resolved).lower(), int(getattr(st, "st_mtime_ns", 0)), int(getattr(st, "st_size", 0)))
    except Exception:
        return (str(resolved).lower(), 0, 0)


def current_dll_lookup_signature(window: Any) -> tuple:
    pairs = window._resource_dll_pairs_for_lookup()
    if not pairs:
        return tuple()
    resolver = DllStringResolver()
    sig_items: list[tuple] = []
    for slot, pair in enumerate(pairs, start=1):
        ini_path, dll_name = pair
        ini_sig = dll_file_stat_signature(Path(ini_path))
        dll_txt = str(dll_name or "").strip()
        dll_path = resolver._resolve_dll_path(Path(ini_path), dll_txt)  # noqa: SLF001
        dll_sig = dll_file_stat_signature(dll_path)
        sig_items.append((int(slot), dll_txt.lower(), ini_sig, dll_sig))
    return tuple(sig_items)


def load_dll_html_resources_cached(window: Any, dll_path: Path) -> dict[int, str]:
    key = dll_file_stat_signature(dll_path)
    if key in window._dll_html_cache:
        return dict(window._dll_html_cache.get(key, {}))
    data = window._load_dll_html_resources(dll_path)
    if len(window._dll_html_cache) > 64:
        try:
            first_key = next(iter(window._dll_html_cache.keys()))
            window._dll_html_cache.pop(first_key, None)
        except Exception:
            window._dll_html_cache.clear()
    window._dll_html_cache[key] = dict(data)
    return dict(data)


def reload_dll_name_cache(window: Any, *, force: bool = False) -> None:
    sig = window._current_dll_lookup_signature()
    if not force and sig == window._dll_lookup_cache_sig:
        return
    window._ids_display_cache.clear()
    window._info_editor_cache_sig = None
    window._info_editor_rows_cache = []
    if not sig:
        window._dll_resolver.clear()
        window._dll_lookup_cache_sig = sig
        return
    pairs = window._resource_dll_pairs_for_lookup()
    window._dll_resolver.load_from_resource_pairs(pairs)
    window._dll_lookup_cache_sig = sig


def refresh_system_name_cache(window: Any, game_path: str | None = None) -> None:
    window._system_display_names_by_nick.clear()
    window._system_nick_by_path.clear()
    gp = str(game_path or window._primary_game_path() or "").strip()
    if not gp:
        if hasattr(window, "browser"):
            window.browser.set_system_name_map({}, scan=False)
        return
    window._reload_dll_name_cache()
    systems = window._find_all_systems(gp)
    for system in systems:
        nick = str(system.get("nickname", "") or "").strip().upper()
        if not nick:
            continue
        ids_name = str(system.get("ids_name", "") or "").strip() or str(system.get("strid_name", "") or "").strip()
        display = window._display_name_from_ids_name(ids_name) if (ids_name and window._ids_name_resolution_enabled) else ""
        window._system_display_names_by_nick[nick] = display or nick
        path = str(system.get("path", "") or "")
        if path:
            window._system_nick_by_path[str(Path(path)).lower()] = nick
    if hasattr(window, "browser"):
        window.browser.set_system_name_map(window._system_display_names_by_nick, scan=False)
        window.browser.set_system_name_mode(window._system_name_mode, scan=False)


def system_display_name(window: Any, nickname: str) -> str:
    nick = str(nickname or "").strip().upper()
    if not nick:
        return ""
    if window._system_name_mode == "nickname":
        return nick
    return window._system_display_names_by_nick.get(nick, nick)


def format_system_header_text(window: Any, nickname: str) -> str:
    nick = str(nickname or "").strip()
    title = str(tr("lbl.system") or "System").strip()
    if not nick:
        return title
    code = nick.upper()
    disp = window._system_display_name(code).strip()
    if not disp or disp.lower() == code.lower():
        return f"{title}: {code}"
    return f"{title}: {disp} ({code})"


def system_nickname_for_path(window: Any, path: str) -> str:
    key = str(Path(path)).lower()
    nick = window._system_nick_by_path.get(key, "")
    if nick:
        return nick
    return Path(path).stem.upper()


def base_display_name(window: Any, base_nick: str, ids_name_raw: str | int | None = None) -> str:
    if window._system_name_mode == "nickname":
        return str(base_nick or "").strip()
    name_txt = window._display_name_from_ids_name(ids_name_raw) if (ids_name_raw and window._ids_name_resolution_enabled) else ""
    return name_txt or str(base_nick or "").strip()


def set_system_name_mode(window: Any, mode: str) -> None:
    value = str(mode or "").strip().lower()
    if value not in ("ingame", "nickname"):
        value = "ingame"
    if window._system_name_mode == value:
        return
    window._system_name_mode = value
    window._cfg.set("view.system_name_mode", value)
    for mode_key, action in window._view_system_name_actions.items():
        action.setChecked(mode_key == value)
    if hasattr(window, "browser"):
        window.browser.set_system_name_mode(value, scan=True)
    window._apply_system_name_mode_to_ui()


def set_ids_name_resolution_enabled(window: Any, enabled: bool) -> None:
    on = bool(enabled)
    if window._ids_name_resolution_enabled == on:
        return
    window._ids_name_resolution_enabled = on
    window._cfg.set("view.ids_name_resolution", on)
    if window._view_ids_name_resolution_action is not None:
        window._view_ids_name_resolution_action.setChecked(on)
    window._ids_display_cache.clear()
    window._refresh_system_name_cache(window._primary_game_path())
    window._apply_system_name_mode_to_ui()


def apply_system_name_mode_to_ui(window: Any) -> None:
    live_objects: list[SolarObject] = []
    for obj in list(window._objects):
        if not window._qt_widget_alive(obj):
            continue
        live_objects.append(obj)
        label = getattr(obj, "label", None)
        if not window._qt_widget_alive(label):
            try:
                obj.label = None
            except Exception:
                pass
            continue
        if isinstance(obj, UniverseSystem):
            obj.set_label_text(window._system_display_name(obj.nickname))
        else:
            label.setPlainText(window._object_display_label(obj))
    if len(live_objects) != len(window._objects):
        window._objects = live_objects
    if window._avoid_label_overlap:
        window._reflow_2d_labels()
    else:
        window._reset_2d_label_positions()
    if hasattr(window, "obj_combo"):
        window._rebuild_object_combo()
        window._sync_obj_combo_to_selection()
    if window._uni_selected_nick:
        window.uni_sys_lbl.setText(f"🌐 {window._system_display_name(window._uni_selected_nick)}")
    if window._filepath:
        nick = window._system_nickname_for_path(window._filepath)
        disp = window._system_display_name(nick)
        window.setWindowTitle(window._title_with_version(tr("app.title_system").format(name=disp)))
        window._refresh_system_fields()
    else:
        window._refresh_window_title()
    if isinstance(window._selected, UniverseSystem) and window._qt_widget_alive(window._selected):
        window.statusBar().showMessage(tr("status.system_info").format(nickname=window._system_display_name(window._selected.nickname)))
    if hasattr(window, "trade_routes_table"):
        try:
            window._apply_trade_route_filters()
        except Exception:
            pass
    if hasattr(window, "_center_refresh_tab_titles"):
        try:
            window._center_refresh_tab_titles()
        except Exception:
            pass
    scene = getattr(getattr(window, "view", None), "_scene", None)
    if scene is not None:
        try:
            scene.update()
        except Exception:
            pass
    viewport = getattr(getattr(window, "view", None), "viewport", None)
    if callable(viewport):
        try:
            viewport().update()
        except Exception:
            pass
    QApplication.processEvents()


def extract_ids_name_from_entries(entries: list[tuple[str, str]]) -> str:
    for key, value in entries:
        if str(key).strip().lower() == "ids_name":
            return str(value).strip()
    return ""


def display_name_from_ids_name(window: Any, ids_name_raw: str | int | None) -> str:
    key = str(ids_name_raw or "").strip()
    if not key:
        return ""
    if key in window._ids_display_cache:
        return window._ids_display_cache[key]
    text = window._dll_resolver.resolve_name(key)
    window._ids_display_cache[key] = text
    return text


def display_text_from_ids_value(window: Any, ids_raw: str | int | None) -> str:
    gid = window._safe_int(str(ids_raw or "").strip())
    if gid <= 0:
        return ""
    text = window._display_name_from_ids_name(gid)
    if text:
        return text
    xml = window._resolve_infocard_xml_by_global_id(gid)
    if str(xml).strip():
        return window._xml_to_plain_preview(xml)
    return ""


def build_faction_label_cache(window: Any, groups: list[tuple[str, str]]) -> None:
    labels: list[str] = []
    label_to_nick: dict[str, str] = {}
    nick_to_label: dict[str, str] = {}
    for nick, ids_name in groups:
        nick_clean = str(nick or "").strip()
        if not nick_clean:
            continue
        disp = window._display_name_from_ids_name(ids_name) if ids_name else ""
        disp_clean = str(disp or "").strip() or nick_clean
        label = f"{nick_clean} - {disp_clean}"
        labels.append(label)
        label_to_nick[label.strip().lower()] = nick_clean
        nick_to_label[nick_clean.strip().lower()] = label
        label_to_nick.setdefault(nick_clean.strip().lower(), nick_clean)
        label_to_nick.setdefault(disp_clean.strip().lower(), nick_clean)
    window._cached_factions = [str(n).strip() for n, _ in groups if str(n).strip()]
    window._cached_faction_labels = labels
    window._faction_label_to_nick = label_to_nick
    window._faction_nick_to_label = nick_to_label


def faction_ui_label(window: Any, nick_or_label: str | None) -> str:
    raw = str(nick_or_label or "").strip()
    if not raw:
        return ""
    return window._faction_nick_to_label.get(raw.lower(), raw)


def faction_from_ui(window: Any, nick_or_label: str | None) -> str:
    raw = str(nick_or_label or "").strip()
    if not raw:
        return ""
    key = raw.lower()
    mapped = window._faction_label_to_nick.get(key)
    if mapped:
        return mapped
    match = re.match(r"^(.*)\(([^()]+)\)\s*$", raw)
    if match:
        tail = match.group(2).strip()
        if tail:
            return window._faction_label_to_nick.get(tail.lower(), tail)
    if " - " in raw:
        head = raw.split(" - ", 1)[0].strip()
        if head:
            return window._faction_label_to_nick.get(head.lower(), head)
    return raw


def normalize_reputation_value(window: Any, raw_reputation: str | None) -> str:
    text = str(raw_reputation or "").strip()
    if not text:
        return ""
    mapped = window._faction_from_ui(text)
    if mapped and mapped.lower() != text.lower():
        return mapped
    parts = [part.strip() for part in text.split(",", 1)]
    faction = window._faction_from_ui(parts[0])
    if not faction:
        return ""
    if len(parts) > 1 and parts[1] and parts[0].strip().lower() == faction.lower():
        return f"{faction},{parts[1]}"
    return faction


def object_display_label(window: Any, obj: object) -> str:
    data = getattr(obj, "data", {}) or {}
    nick = str(getattr(obj, "nickname", "") or "")
    if window._system_name_mode == "nickname":
        return nick
    ids_name_raw = data.get("ids_name", "")
    if not ids_name_raw:
        ids_name_raw = window._extract_ids_name_from_entries(data.get("_entries", []))
    display_name = window._display_name_from_ids_name(ids_name_raw) if window._ids_name_resolution_enabled else ""
    return display_name or nick


def default_jump_ids_name(window: Any, arch: str, target_system_display: str) -> str:
    system_name = str(target_system_display or "").strip() or "Unknown"
    lang = window._auto_name_language()
    is_gate = str(arch or "").strip().lower() in ("jumpgate", "nomad_gate")
    if lang == "de":
        kind = "Sprungtor" if is_gate else "Sprungloch"
        return f"{system_name}-{kind}"
    kind = "Jump Gate" if is_gate else "Jump Hole"
    return f"{system_name} {kind}"


def default_gate_connection_name(origin_system_display: str, target_system_display: str) -> str:
    origin = str(origin_system_display or "").strip() or "Unknown"
    target = str(target_system_display or "").strip() or "Unknown"
    return f"{origin} -> {target}"
