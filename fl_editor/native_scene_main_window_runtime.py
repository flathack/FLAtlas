from __future__ import annotations

from pathlib import Path
from typing import Any

from .freelancer_model_resolver import resolve_preview_mesh_candidate
from .models import ZoneItem
from .native_model_path_cache import (
    native_model_path_cache_key,
    prune_native_model_path_cache,
    touch_native_model_path_cache_order,
)
from .native_scene_runtime import NativeSceneRuntime, NativeSceneRuntimeEvent


def native_scene_runtime(window: Any) -> NativeSceneRuntime:
    runtime = getattr(window, "_native_scene_runtime_store", None)
    if runtime is None:
        runtime = NativeSceneRuntime(
            parent=window,
            sync_selected_callback=window._sync_view3d_selected_native_scene_data,
            selected_model_path_func=lambda: window._native_model_path_for_object(getattr(window, "_selected", None)),
            debug_event_callback=window._on_native_scene_runtime_event,
        )
        window._native_scene_runtime_store = runtime
    return runtime


def native_scene_debug_events(window: Any) -> list[NativeSceneRuntimeEvent]:
    events = getattr(window, "_native_scene_debug_events_store", None)
    if events is None:
        events = []
        window._native_scene_debug_events_store = events
    return events


def on_native_scene_runtime_event(window: Any, event: NativeSceneRuntimeEvent) -> None:
    events = window._native_scene_debug_events()
    events.append(event)
    if len(events) > 96:
        del events[: len(events) - 96]


def native_scene_debug_state_snapshot(window: Any) -> dict[str, object]:
    runtime = getattr(window, "_native_scene_runtime_store", None)
    selected = getattr(window, "_selected", None)
    selected_model_path = window._native_model_path_for_object(selected)
    if runtime is None:
        return {
            "selected_object_nickname": getattr(selected, "nickname", None),
            "selected_model_path": selected_model_path,
            "runtime_initialized": False,
            "events": tuple(window._native_scene_debug_events()),
            "stats": {},
            "pending_paths": (),
            "cached_paths": (),
            "failed_paths": (),
            "recent_events": (),
        }
    state = runtime.get_debug_state()
    state["selected_object_nickname"] = getattr(selected, "nickname", None)
    state["selected_model_path"] = selected_model_path
    state["runtime_initialized"] = True
    state["events"] = tuple(window._native_scene_debug_events())
    return state


def native_model_path_for_object(window: Any, obj: Any) -> Path | None:
    if obj is None or isinstance(obj, ZoneItem):
        return None
    archetype = str(obj.data.get("archetype", "") or "").strip()
    if not archetype:
        return None
    game_path = window._primary_game_path()
    if not game_path:
        return None
    model_path = window._native_model_path_for_archetype_cached(archetype, game_path)
    if model_path is None:
        return None
    preview_resolution = resolve_preview_mesh_candidate(model_path)
    if not preview_resolution.is_freelancer_native:
        return None
    return model_path


def native_model_path_cache(window: Any) -> dict[str, Path | None]:
    cache = getattr(window, "_native_model_path_cache_store", None)
    if cache is None:
        cache = {}
        window._native_model_path_cache_store = cache
    return cache


def native_model_path_cache_order(window: Any) -> list[str]:
    order = getattr(window, "_native_model_path_cache_order_store", None)
    if order is None:
        order = []
        window._native_model_path_cache_order_store = order
    return order


def native_model_path_for_archetype_cached(window: Any, archetype: str, game_path: str) -> Path | None:
    cache = window._native_model_path_cache()
    order = window._native_model_path_cache_order()
    key = native_model_path_cache_key(game_path=game_path, archetype=archetype)
    if key in cache:
        touch_native_model_path_cache_order(order, key)
        return cache[key]
    model_path, _da_arch = window._resolve_model_for_archetype(archetype, game_path)
    cache[key] = model_path
    touch_native_model_path_cache_order(order, key)
    prune_native_model_path_cache(cache, order, max_entries=512)
    return model_path


def resolve_native_scene_data_for_object(window: Any, obj: Any) -> object | None:
    model_path = window._native_model_path_for_object(obj)
    if model_path is None:
        return None
    return window._native_scene_runtime().resolve_scene_data(model_path)


def sync_view3d_selected_native_scene_data(window: Any) -> None:
    if not hasattr(window, "view3d") or not hasattr(window.view3d, "set_selected_native_scene_data"):
        return
    selected = getattr(window, "_selected", None)
    if selected is None:
        runtime = getattr(window, "_native_scene_runtime_store", None)
        if runtime is not None:
            runtime.discard_pending_requests(reason="no-selection")
        window._on_native_scene_runtime_event(
            NativeSceneRuntimeEvent(kind="sync_cleared_no_selection", model_path=None, detail="")
        )
        window.view3d.set_selected_native_scene_data(None, None)
        return
    if hasattr(window, "view3d_switch") and not window.view3d_switch.isChecked():
        runtime = getattr(window, "_native_scene_runtime_store", None)
        if runtime is not None:
            runtime.discard_pending_requests(reason="3d-disabled")
        window._on_native_scene_runtime_event(
            NativeSceneRuntimeEvent(
                kind="sync_skipped_3d_disabled",
                model_path=window._native_model_path_for_object(selected),
                detail=getattr(selected, "nickname", "") or "",
            )
        )
        window.view3d.set_selected_native_scene_data(selected, None)
        return
    scene_data = window._resolve_native_scene_data_for_object(selected)
    if getattr(window, "_selected", None) is not selected:
        window._on_native_scene_runtime_event(
            NativeSceneRuntimeEvent(
                kind="sync_aborted_selection_changed",
                model_path=window._native_model_path_for_object(selected),
                detail=getattr(selected, "nickname", "") or "",
            )
        )
        return
    window.view3d.set_selected_native_scene_data(selected, scene_data)
