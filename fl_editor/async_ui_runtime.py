"""Helpers for non-blocking view loads on the Qt UI thread."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox


def _state(window: Any) -> dict[str, dict[str, Any]]:
    state = getattr(window, "_async_view_loads", None)
    if not isinstance(state, dict):
        state = {}
        setattr(window, "_async_view_loads", state)
    return state


def _ensure_entry(window: Any, key: str) -> dict[str, Any]:
    state = _state(window)
    entry = state.get(key)
    if isinstance(entry, dict):
        return entry
    entry = {
        "serial": 0,
        "future": None,
        "executor": ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"fl-{key}"),
    }
    state[key] = entry
    return entry


def start_async_view_load(
    window: Any,
    *,
    key: str,
    worker: Callable[[], Any],
    apply_result: Callable[[Any], None],
    prepare_ui: Callable[[], None] | None = None,
    loading_message: str | None = None,
    error_title: str = "Load Error",
    poll_interval_ms: int = 40,
) -> int:
    entry = _ensure_entry(window, key)
    future = entry.get("future")
    if isinstance(future, Future) and not future.done():
        future.cancel()

    entry["serial"] = int(entry.get("serial", 0)) + 1
    serial = int(entry["serial"])

    if callable(prepare_ui):
        prepare_ui()
    if hasattr(window, "_set_loading_visible"):
        window._set_loading_visible(True, loading_message)

    if bool(getattr(window, "_startup_blocking_loads", False)):
        entry["future"] = None
        try:
            result = worker()
        except Exception as exc:
            if hasattr(window, "_set_loading_visible"):
                window._set_loading_visible(False)
            QMessageBox.warning(window, error_title, str(exc))
            return serial
        try:
            apply_result(result)
        finally:
            if hasattr(window, "_set_loading_visible"):
                window._set_loading_visible(False)
        return serial

    executor = entry["executor"]
    entry["future"] = executor.submit(worker)
    QTimer.singleShot(poll_interval_ms, lambda key=key, serial=serial: poll_async_view_load(window, key=key, serial=serial, apply_result=apply_result, error_title=error_title, poll_interval_ms=poll_interval_ms))
    return serial


def poll_async_view_load(
    window: Any,
    *,
    key: str,
    serial: int,
    apply_result: Callable[[Any], None],
    error_title: str = "Load Error",
    poll_interval_ms: int = 40,
) -> None:
    entry = _state(window).get(key)
    if not isinstance(entry, dict):
        return
    if int(entry.get("serial", 0)) != int(serial):
        return
    future = entry.get("future")
    if not isinstance(future, Future):
        return
    if not future.done():
        QTimer.singleShot(poll_interval_ms, lambda key=key, serial=serial: poll_async_view_load(window, key=key, serial=serial, apply_result=apply_result, error_title=error_title, poll_interval_ms=poll_interval_ms))
        return

    entry["future"] = None
    try:
        result = future.result()
    except Exception as exc:
        if hasattr(window, "_set_loading_visible"):
            window._set_loading_visible(False)
        QMessageBox.warning(window, error_title, str(exc))
        return

    try:
        apply_result(result)
    finally:
        if hasattr(window, "_set_loading_visible"):
            window._set_loading_visible(False)
