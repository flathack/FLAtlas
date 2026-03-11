from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path

from fl_editor.native_scene_loader import NativeSceneLoadResult
from fl_editor.native_scene_runtime import NativeSceneRuntime


class _FakeSceneData:
    def __init__(self, geometries):
        self.geometries = geometries


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

    runtime.shutdown()

    assert timer.deleted is True
    assert executor.shutdown_calls == [(False, True)]
