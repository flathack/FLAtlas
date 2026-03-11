from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QTimer

from .native_scene_cache import prune_native_scene_cache, touch_native_scene_cache_order
from .native_scene_loader import (
    collect_completed_native_scene_loads,
    load_native_scene_data,
    reprioritize_native_scene_pending_loads,
)
from .native_scene_retry import prune_failed_native_scene_loads, should_retry_failed_native_scene_load
from .native_scene_sync import should_sync_selected_native_scene_data


class NativeSceneRuntime:
    def __init__(
        self,
        *,
        parent=None,
        sync_selected_callback: Callable[[], None],
        selected_model_path_func: Callable[[], Path | None],
        load_scene_func: Callable[[Path], object] = load_native_scene_data,
        monotonic_func: Callable[[], float] = time.monotonic,
        retry_cooldown_seconds: float = 8.0,
        cache_max_entries: int = 24,
        failed_max_entries: int = 96,
        executor_factory: Callable[[], object] | None = None,
        timer_factory: Callable[[Callable[[], None]], object] | None = None,
    ) -> None:
        self._parent = parent
        self._sync_selected_callback = sync_selected_callback
        self._selected_model_path_func = selected_model_path_func
        self._load_scene_func = load_scene_func
        self._monotonic_func = monotonic_func
        self._retry_cooldown_seconds = float(retry_cooldown_seconds)
        self._cache_max_entries = int(cache_max_entries)
        self._failed_max_entries = int(failed_max_entries)
        self._executor_factory = executor_factory or self._default_executor_factory
        self._timer_factory = timer_factory or self._default_timer_factory
        self._cache_by_path: dict[Path, object | None] = {}
        self._cache_order: list[Path] = []
        self._pending_by_path: dict[Path, object] = {}
        self._failed_by_path: dict[Path, float] = {}
        self._executor = None
        self._timer = None

    def _default_executor_factory(self) -> ThreadPoolExecutor:
        return ThreadPoolExecutor(max_workers=1, thread_name_prefix="fl-native-scene")

    def _default_timer_factory(self, callback: Callable[[], None]) -> QTimer:
        timer = QTimer(self._parent)
        timer.setInterval(30)
        timer.timeout.connect(callback)
        return timer

    def _ensure_executor(self):
        if self._executor is None:
            self._executor = self._executor_factory()
        return self._executor

    def _ensure_timer(self):
        if self._timer is None:
            self._timer = self._timer_factory(self.process_completed_loads)
        return self._timer

    def shutdown(self) -> None:
        timer = self._timer
        self._timer = None
        if timer is not None:
            try:
                timer.stop()
            except Exception:
                pass
            delete_later = getattr(timer, "deleteLater", None)
            if callable(delete_later):
                try:
                    delete_later()
                except Exception:
                    pass

        executor = self._executor
        self._executor = None
        if executor is not None:
            try:
                executor.shutdown(wait=False, cancel_futures=True)
            except TypeError:
                executor.shutdown(wait=False)
            except Exception:
                pass

    def resolve_scene_data(self, model_path: Path) -> object | None:
        if model_path not in self._cache_by_path:
            self.queue_request(model_path)
            return None
        touch_native_scene_cache_order(self._cache_order, model_path)
        scene_data = self._cache_by_path.get(model_path)
        if scene_data is None or not getattr(scene_data, "geometries", ()):
            return None
        return scene_data

    def queue_request(self, model_path: Path) -> bool:
        reprioritize_native_scene_pending_loads(self._pending_by_path, model_path)
        if model_path in self._cache_by_path:
            touch_native_scene_cache_order(self._cache_order, model_path)
            return False
        if model_path in self._pending_by_path:
            return False
        if not should_retry_failed_native_scene_load(
            last_failed_at=self._failed_by_path.get(model_path),
            now_monotonic=self._monotonic_func(),
            retry_cooldown_seconds=self._retry_cooldown_seconds,
        ):
            return False
        self._pending_by_path[model_path] = self._ensure_executor().submit(self._load_scene_func, model_path)
        self._ensure_timer().start()
        return True

    def process_completed_loads(self) -> tuple[object, ...]:
        completed = collect_completed_native_scene_loads(self._pending_by_path)
        if not self._pending_by_path and self._timer is not None:
            try:
                self._timer.stop()
            except Exception:
                pass
        if not completed:
            return ()
        for result in completed:
            if result.scene_data is None:
                self._cache_by_path.pop(result.model_path, None)
                self._failed_by_path[result.model_path] = self._monotonic_func()
                prune_failed_native_scene_loads(self._failed_by_path, max_entries=self._failed_max_entries)
                continue
            self._failed_by_path.pop(result.model_path, None)
            self._cache_by_path[result.model_path] = result.scene_data
            touch_native_scene_cache_order(self._cache_order, result.model_path)
            prune_native_scene_cache(
                cache_by_path=self._cache_by_path,
                order=self._cache_order,
                max_entries=self._cache_max_entries,
                protected_paths=(result.model_path,),
            )
        selected_model_path = self._selected_model_path_func()
        completed_paths = tuple(result.model_path for result in completed)
        if should_sync_selected_native_scene_data(
            selected_model_path=selected_model_path,
            completed_model_paths=completed_paths,
        ):
            self._sync_selected_callback()
        return tuple(completed)
