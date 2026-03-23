from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path

from fl_editor.native_scene_loader import NativeSceneLoadResult
from fl_editor.native_scene_runtime import NativeSceneRuntime


class _FakeSceneData:
    def __init__(self, geometries):
        self.geometries = geometries


class _FakePendingFuture:
    def __init__(self, *, done: bool = False, cancellable: bool = True):
        self._done = done
        self._cancellable = cancellable
        self.cancel_calls = 0

    def done(self):
        return self._done

    def cancel(self):
        self.cancel_calls += 1
        return self._cancellable


class _FakeExecutor:
    def __init__(self, future_map: dict[Path, Future]):
        self.future_map = future_map
        self.submitted: list[Path] = []
        self.shutdown_calls: list[tuple[bool, bool | None]] = []

    def submit(self, _func, model_path: Path):
        self.submitted.append(model_path)
        return self.future_map[model_path]

    def shutdown(self, *, wait: bool = False, cancel_futures: bool | None = None):
        self.shutdown_calls.append((wait, cancel_futures))


class _FakeTimer:
    def __init__(self, callback):
        self.callback = callback
        self.start_calls = 0
        self.stop_calls = 0
        self.deleted = False

    def start(self):
        self.start_calls += 1

    def stop(self):
        self.stop_calls += 1

    def deleteLater(self):
        self.deleted = True


def test_native_scene_runtime_queues_request_and_starts_timer(tmp_path: Path):
    model_path = tmp_path / "ship.cmp"
    future: Future = Future()
    executor = _FakeExecutor({model_path: future})
    timers: list[_FakeTimer] = []

    runtime = NativeSceneRuntime(
        sync_selected_callback=lambda: None,
        selected_model_path_func=lambda: None,
        executor_factory=lambda: executor,
        timer_factory=lambda callback: timers.append(_FakeTimer(callback)) or timers[-1],
        monotonic_func=lambda: 10.0,
    )

    queued = runtime.queue_request(model_path)

    assert queued is True
    assert executor.submitted == [model_path]
    assert len(timers) == 1
    assert timers[0].start_calls == 1
    debug = runtime.get_debug_state()
    assert debug["stats"]["queued_loads"] == 1
    assert debug["recent_events"][-1].kind == "load_queued"


def test_native_scene_runtime_processes_completed_loads_and_syncs_selected(tmp_path: Path):
    selected_path = tmp_path / "selected.cmp"
    selected_future: Future = Future()
    selected_future.set_result(
        NativeSceneLoadResult(
            model_path=selected_path,
            scene_data=_FakeSceneData(geometries=(object(),)),
        )
    )
    executor = _FakeExecutor({selected_path: selected_future})
    timer = _FakeTimer(lambda: None)
    sync_calls: list[str] = []

    runtime = NativeSceneRuntime(
        sync_selected_callback=lambda: sync_calls.append("sync"),
        selected_model_path_func=lambda: selected_path,
        executor_factory=lambda: executor,
        timer_factory=lambda callback: timer,
        monotonic_func=lambda: 20.0,
    )
    runtime.queue_request(selected_path)

    completed = runtime.process_completed_loads()

    assert len(completed) == 1
    assert sync_calls == ["sync"]
    assert timer.stop_calls == 1
    assert runtime.resolve_scene_data(selected_path) is not None
    debug = runtime.get_debug_state()
    assert debug["stats"]["load_successes"] == 1
    assert debug["stats"]["cache_hits"] == 1
    assert debug["stats"]["sync_selected_requests"] == 1


def test_native_scene_runtime_respects_retry_cooldown_and_shutdown(tmp_path: Path):
    model_path = tmp_path / "ship.cmp"
    future: Future = Future()
    future.set_result(NativeSceneLoadResult(model_path=model_path, scene_data=None))
    executor = _FakeExecutor({model_path: future})
    timer = _FakeTimer(lambda: None)

    runtime = NativeSceneRuntime(
        sync_selected_callback=lambda: None,
        selected_model_path_func=lambda: None,
        executor_factory=lambda: executor,
        timer_factory=lambda callback: timer,
        monotonic_func=lambda: 100.0,
    )
    runtime.queue_request(model_path)
    runtime.process_completed_loads()

    assert runtime.queue_request(model_path) is False
    debug = runtime.get_debug_state()
    assert debug["stats"]["load_failures"] == 1
    assert debug["stats"]["queue_skipped_retry_cooldown"] == 1

    runtime.shutdown()

    assert timer.deleted is True
    assert executor.shutdown_calls == [(False, True)]


def test_native_scene_runtime_reprioritizes_outdated_pending_requests(tmp_path: Path):
    selected_path = tmp_path / "selected.cmp"
    outdated_path = tmp_path / "outdated.cmp"
    selected_future: Future = Future()
    executor = _FakeExecutor({selected_path: selected_future})

    runtime = NativeSceneRuntime(
        sync_selected_callback=lambda: None,
        selected_model_path_func=lambda: selected_path,
        executor_factory=lambda: executor,
        timer_factory=lambda callback: _FakeTimer(callback),
        monotonic_func=lambda: 5.0,
    )
    outdated_future = _FakePendingFuture(done=False, cancellable=True)
    runtime._pending_by_path[outdated_path] = outdated_future

    queued = runtime.queue_request(selected_path)

    assert queued is True
    assert outdated_path not in runtime._pending_by_path
    assert outdated_future.cancel_calls == 1
    debug = runtime.get_debug_state()
    assert debug["stats"]["reprioritized_pending"] == 1
    assert any(event.kind == "pending_discarded" and event.model_path == outdated_path for event in debug["recent_events"])


def test_native_scene_runtime_keeps_pending_preview_requests_for_non_selected_path(tmp_path: Path):
    selected_path = tmp_path / "selected.cmp"
    preview_path = tmp_path / "preview.cmp"
    outdated_path = tmp_path / "outdated.cmp"
    preview_future: Future = Future()
    executor = _FakeExecutor({preview_path: preview_future})

    runtime = NativeSceneRuntime(
        sync_selected_callback=lambda: None,
        selected_model_path_func=lambda: selected_path,
        executor_factory=lambda: executor,
        timer_factory=lambda callback: _FakeTimer(callback),
        monotonic_func=lambda: 5.0,
    )
    outdated_future = _FakePendingFuture(done=False, cancellable=True)
    runtime._pending_by_path[outdated_path] = outdated_future

    queued = runtime.queue_request(preview_path)

    assert queued is True
    assert outdated_path in runtime._pending_by_path
    assert outdated_future.cancel_calls == 0
    debug = runtime.get_debug_state()
    assert debug["stats"]["reprioritized_pending"] == 0


def test_native_scene_runtime_skips_sync_for_non_selected_completed_path(tmp_path: Path):
    selected_path = tmp_path / "selected.cmp"
    other_path = tmp_path / "other.cmp"
    other_future: Future = Future()
    other_future.set_result(
        NativeSceneLoadResult(
            model_path=other_path,
            scene_data=_FakeSceneData(geometries=(object(),)),
        )
    )
    executor = _FakeExecutor({other_path: other_future})
    sync_calls: list[str] = []

    runtime = NativeSceneRuntime(
        sync_selected_callback=lambda: sync_calls.append("sync"),
        selected_model_path_func=lambda: selected_path,
        executor_factory=lambda: executor,
        timer_factory=lambda callback: _FakeTimer(callback),
        monotonic_func=lambda: 25.0,
    )
    runtime.queue_request(other_path)

    completed = runtime.process_completed_loads()

    assert len(completed) == 1
    assert sync_calls == []
    debug = runtime.get_debug_state()
    assert debug["stats"]["sync_selected_skipped"] == 1
    assert any(event.kind == "sync_selected_skipped" and event.model_path == selected_path for event in debug["recent_events"])


def test_native_scene_runtime_discards_pending_requests_and_stops_timer(tmp_path: Path):
    path_a = tmp_path / "a.cmp"
    path_b = tmp_path / "b.cmp"
    timer = _FakeTimer(lambda: None)

    runtime = NativeSceneRuntime(
        sync_selected_callback=lambda: None,
        selected_model_path_func=lambda: None,
        executor_factory=lambda: _FakeExecutor({}),
        timer_factory=lambda callback: timer,
        monotonic_func=lambda: 1.0,
    )
    runtime._timer = timer
    future_a = _FakePendingFuture(done=False, cancellable=True)
    future_b = _FakePendingFuture(done=True, cancellable=False)
    runtime._pending_by_path[path_a] = future_a
    runtime._pending_by_path[path_b] = future_b

    removed = runtime.discard_pending_requests(reason="no-selection")

    assert removed == (path_a, path_b)
    assert runtime.get_debug_state()["pending_paths"] == ()
    assert timer.stop_calls == 1
    debug = runtime.get_debug_state()
    assert debug["stats"]["reprioritized_pending"] == 2
    assert any(event.kind == "pending_discarded" and event.detail == "no-selection" for event in debug["recent_events"])
