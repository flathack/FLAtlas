"""Runtime helpers for writable IDS/resource-DLL workflows."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .dll_resources import DllStringResolver
from .path_utils import ci_find
from .text_write_utils import write_text_with_fallback


def preferred_resource_dll_name(_window: Any) -> str:
    return "FLAtlas_resources.dll"


def active_resource_dll_name(window: Any) -> str:
    override = str(getattr(window, "_ids_resource_dll_override", "") or "").strip()
    return override or preferred_resource_dll_name(window)


def ensure_preferred_resource_dll_registered(window: Any, dll_name: str) -> bool:
    ini_write = window._find_freelancer_ini_write()
    if ini_write is None:
        return False
    try:
        text = window._read_text_best_effort(ini_write)
    except Exception:
        text = ""
    current = window._resource_dlls_from_freelancer_ini(ini_write)
    norm_target = window._normalize_dll_name(dll_name)
    if norm_target in {window._normalize_dll_name(x) for x in current}:
        return True
    text, _added = window._insert_resource_dll_line(text, dll_name)
    if not text.endswith("\n"):
        text += "\n"
    try:
        write_text_with_fallback(ini_write, text, ensure_parent=True)
    except Exception:
        return False
    window._append_dll_change_log(f"Resource DLL registriert in freelancer.ini: {dll_name}")
    return True


def unregister_resource_dll(window: Any, dll_name: str) -> bool:
    ini_write = window._find_freelancer_ini_write()
    if ini_write is None:
        return False
    try:
        text = window._read_text_best_effort(ini_write)
    except Exception:
        text = ""
    text, removed = window._remove_resource_dll_line(text, dll_name)
    if not removed:
        return True
    try:
        write_text_with_fallback(ini_write, text, ensure_parent=True)
    except Exception:
        return False
    window._append_dll_change_log(f"Resource DLL entfernt aus freelancer.ini: {dll_name}")
    return True


def resolve_preferred_resource_dll_path(window: Any, dll_name: str) -> Path | None:
    ini_write = window._find_freelancer_ini_write()
    if ini_write is None:
        return None
    resolver = DllStringResolver()
    resolved = resolver._resolve_dll_path(ini_write, dll_name)  # noqa: SLF001
    if resolved and resolved.is_file():
        return resolved
    rel = str(dll_name or "").strip().strip("\"'").replace("\\", "/")
    if not rel:
        rel = preferred_resource_dll_name(window)
    cand = Path(rel)
    if cand.is_absolute():
        return cand
    return ini_write.parent / cand


def temporary_flmm_resource_dll_name(_window: Any, profile: dict) -> str:
    pid = re.sub(r"[^A-Za-z0-9]+", "", str(profile.get("id", "") or "").strip())[:16] or "mod"
    return f"FLAtlas_FLMM_{pid}.dll"


def cleanup_temporary_flmm_resource_dll(window: Any, target_root: Path, dll_name: str) -> None:
    dll_txt = str(dll_name or "").strip()
    if not dll_txt:
        return
    old_override = str(getattr(window, "_ids_resource_dll_override", "") or "").strip()
    try:
        window._ids_resource_dll_override = dll_txt
        window._flmm_with_target_context(target_root, lambda: window._unregister_resource_dll(dll_txt))
        dll_path = window._flmm_with_target_context(target_root, lambda: window._resolve_preferred_resource_dll_path(dll_txt))
        if isinstance(dll_path, Path) and dll_path.exists():
            try:
                dll_path.unlink()
            except Exception:
                pass
    finally:
        window._ids_resource_dll_override = old_override


def resource_slot_for_dll_name(window: Any, dll_name: str) -> int:
    target = window._normalize_dll_name(dll_name)
    for slot, name in window._dll_resolver.slot_to_dll.items():
        if window._normalize_dll_name(name) == target:
            return int(slot)
    ini_path = window._find_freelancer_ini_read()
    if ini_path and ini_path.is_file():
        dlls = window._resource_dlls_from_freelancer_ini(ini_path)
        for idx, name in enumerate(dlls, start=1):
            if window._normalize_dll_name(name) == target:
                return int(idx)
    return 0


def scan_used_ids_field_values(window: Any, field_name: str, game_path: str | None = None) -> set[int]:
    target = str(field_name or "").strip().lower()
    if not target:
        return set()
    used: set[int] = set()
    systems = window._find_all_systems(str(game_path or window._primary_game_path() or ""))
    for system in systems:
        sys_path = str(system.get("path", "") or "").strip()
        if not sys_path:
            continue
        try:
            sections = window._parser.parse(sys_path)
        except Exception:
            continue
        for _sec, entries in sections:
            raw = window._entry_get_value(entries, target).strip()
            if not raw:
                continue
            try:
                val = int(raw)
            except Exception:
                continue
            if val > 0:
                used.add(val)
    for ini_path in window._iter_equipment_ini_paths_for_usage(str(game_path or window._primary_game_path() or "")):
        try:
            sections = window._parser.parse(str(ini_path))
        except Exception:
            continue
        for _sec, entries in sections:
            raw = window._entry_get_value(entries, target).strip()
            if not raw:
                continue
            try:
                val = int(raw)
            except Exception:
                continue
            if val > 0:
                used.add(val)
    for ini_path in window._iter_missions_ini_paths_for_ids_scan(str(game_path or window._primary_game_path() or "")):
        try:
            sections = window._parser.parse(str(ini_path))
        except Exception:
            continue
        for _sec, entries in sections:
            raw = window._entry_get_value(entries, target).strip()
            if not raw:
                continue
            try:
                val = int(raw)
            except Exception:
                continue
            if val > 0:
                used.add(val)
    return used


def scan_used_ids_info_values(window: Any, game_path: str | None = None) -> set[int]:
    return scan_used_ids_field_values(window, "ids_info", game_path)


def scan_used_ids_name_values(window: Any, game_path: str | None = None) -> set[int]:
    return scan_used_ids_field_values(window, "ids_name", game_path)


def ensure_ids_name_in_user_dll(window: Any, current_ids_name: str | int | None, text: str) -> str:
    new_text = str(text or "").strip()
    if not new_text:
        return str(current_ids_name or "").strip()
    dll_name = window._active_resource_dll_name()
    if not window._ensure_preferred_resource_dll_registered(dll_name):
        raise RuntimeError("Could not register preferred resource DLL in freelancer.ini")
    if not str(getattr(window, "_ids_resource_dll_override", "") or "").strip():
        window._cfg.set("ids.resource_dll_name", dll_name)
    window._reload_dll_name_cache()
    slot = window._resource_slot_for_dll_name(dll_name)
    if slot <= 0:
        raise RuntimeError(f"Could not resolve slot for DLL: {dll_name}")
    local_map = window._dll_resolver.slot_strings(slot)
    dll_path = window._resolve_preferred_resource_dll_path(dll_name)
    if dll_path is None:
        raise RuntimeError(f"Could not resolve writable DLL path for: {dll_name}")
    existing_infos = window._load_dll_html_resources(dll_path)

    ids_val = 0
    try:
        ids_val = int(str(current_ids_name or "").strip() or "0")
    except Exception:
        ids_val = 0
    cur_slot = (ids_val >> 16) & 0xFFFF if ids_val > 0 else 0
    cur_local = ids_val & 0xFFFF if ids_val > 0 else 0
    if cur_slot == slot and cur_local > 0:
        local_id = cur_local
    else:
        used_ids_name = window._scan_used_ids_name_values(window._primary_game_path())
        used_ids_info = window._scan_used_ids_info_values(window._primary_game_path())
        used_global_ids = used_ids_name | used_ids_info
        local_id = 1
        used_locals = set(local_map.keys()) | set(existing_infos.keys())
        if used_locals:
            local_id = max(used_locals) + 1
        while local_id in used_locals or DllStringResolver.make_global_id(slot, int(local_id)) in used_global_ids:
            local_id += 1

    local_map[int(local_id)] = new_text
    ok, err = window._write_resource_dll_entries(dll_path, local_map, existing_infos)
    if not ok:
        raise RuntimeError(err or "Failed to write resource DLL")

    window._reload_dll_name_cache()
    window._ids_display_cache.clear()
    global_id = DllStringResolver.make_global_id(slot, int(local_id))
    window._append_dll_change_log(
        f"ids_name geschrieben: DLL={dll_path.name}, local_id={int(local_id)}, global_id={global_id}"
    )
    return str(global_id)


def relink_ids_info_references(window: Any, old_global_id: int, new_global_id: int, game_path: str | None = None) -> tuple[int, int]:
    old_id = int(old_global_id or 0)
    new_id = int(new_global_id or 0)
    if old_id <= 0 or new_id <= 0 or old_id == new_id:
        return (0, 0)
    gp = str(game_path or window._primary_game_path() or "").strip()
    if not gp:
        return (0, 0)

    file_paths: list[str] = []
    for system in window._find_all_systems(gp):
        path = str(system.get("path", "") or "").strip()
        if path:
            file_paths.append(path)
    file_paths.extend(str(path) for path in window._iter_equipment_ini_paths_for_usage(gp))
    file_paths.extend(str(path) for path in window._iter_missions_ini_paths_for_ids_scan(gp))

    seen: set[str] = set()
    unique_paths: list[str] = []
    for path in file_paths:
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        unique_paths.append(path)

    changed_files = 0
    changed_refs = 0
    for path in unique_paths:
        writable = str(window._ensure_writable_path(path))
        try:
            sections = window._parser.parse(writable)
        except Exception:
            continue
        file_changed = False
        for _sec_name, entries in sections:
            for idx, (key, value) in enumerate(entries):
                if str(key).strip().lower() != "ids_info":
                    continue
                try:
                    cur = int(str(value).strip() or "0")
                except Exception:
                    continue
                if cur != old_id:
                    continue
                entries[idx] = (key, str(new_id))
                file_changed = True
                changed_refs += 1
        if not file_changed:
            continue
        try:
            window._write_sections_to_file(writable, sections)
            changed_files += 1
        except Exception:
            continue
    return changed_files, changed_refs


def ensure_ids_info_in_user_dll(window: Any, current_ids_info: str | int | None, xml_text: str) -> str:
    new_xml = str(xml_text or "").strip()
    if not new_xml:
        return str(current_ids_info or "").strip()
    ET.fromstring(new_xml)
    dll_name = window._active_resource_dll_name()
    if not window._ensure_preferred_resource_dll_registered(dll_name):
        raise RuntimeError("Could not register preferred resource DLL in freelancer.ini")
    if not str(getattr(window, "_ids_resource_dll_override", "") or "").strip():
        window._cfg.set("ids.resource_dll_name", dll_name)
    window._reload_dll_name_cache()
    slot = window._resource_slot_for_dll_name(dll_name)
    if slot <= 0:
        raise RuntimeError(f"Could not resolve slot for DLL: {dll_name}")
    dll_path = window._resolve_preferred_resource_dll_path(dll_name)
    if dll_path is None:
        raise RuntimeError(f"Could not resolve writable DLL path for: {dll_name}")

    local_strings = window._dll_resolver.slot_strings(slot)
    local_infos = window._load_dll_html_resources(dll_path)
    ids_val = 0
    try:
        ids_val = int(str(current_ids_info or "").strip() or "0")
    except Exception:
        ids_val = 0
    cur_slot = (ids_val >> 16) & 0xFFFF if ids_val > 0 else 0
    cur_local = ids_val & 0xFFFF if ids_val > 0 else 0
    if cur_slot == slot and cur_local > 0:
        local_id = cur_local
    else:
        used_ids_info = window._scan_used_ids_info_values(window._primary_game_path())
        used_ids_name = window._scan_used_ids_name_values(window._primary_game_path())
        used_global_ids = used_ids_info | used_ids_name
        local_id = 1
        used_locals = set(local_infos.keys()) | set(local_strings.keys())
        if used_locals:
            local_id = max(used_locals) + 1
        while local_id in used_locals or DllStringResolver.make_global_id(slot, int(local_id)) in used_global_ids:
            local_id += 1
    local_infos[int(local_id)] = new_xml
    ok, err = window._write_resource_dll_entries(dll_path, local_strings, local_infos)
    if not ok:
        raise RuntimeError(err or "Failed to write resource DLL")

    window._reload_dll_name_cache()
    window._ids_display_cache.clear()
    global_id = DllStringResolver.make_global_id(slot, int(local_id))
    window._append_dll_change_log(
        f"ids_info geschrieben: DLL={dll_path.name}, local_id={int(local_id)}, global_id={global_id}"
    )
    return str(global_id)


def iter_missions_ini_paths_for_ids_scan(window: Any, game_path: str | None = None) -> list[Path]:
    paths: list[Path] = []
    seen_rel: set[str] = set()
    roots: list[str] = []
    gp = str(game_path or window._primary_game_path() or "").strip()
    if gp:
        roots.append(gp)
    fallback = str(window._fallback_game_path() or "").strip()
    if fallback:
        try:
            same_root = Path(fallback).resolve() == Path(gp).resolve()
        except Exception:
            same_root = fallback == gp
        if not same_root:
            roots.append(fallback)
    for root in roots:
        data_dir = ci_find(Path(root), "DATA")
        if not data_dir:
            continue
        missions_dir = ci_find(data_dir, "MISSIONS")
        if not missions_dir or not missions_dir.is_dir():
            continue
        try:
            ini_files = sorted(path for path in missions_dir.rglob("*.ini") if path.is_file())
        except Exception:
            ini_files = []
        for ini_path in ini_files:
            try:
                rel_key = str(ini_path.relative_to(missions_dir)).replace("\\", "/").lower()
            except Exception:
                rel_key = str(ini_path).lower()
            if rel_key in seen_rel:
                continue
            seen_rel.add(rel_key)
            paths.append(ini_path)
    return paths


def scan_used_ids_name_in_missions(window: Any, game_path: str | None = None) -> set[int]:
    return scan_used_ids_name_values(window, game_path)
