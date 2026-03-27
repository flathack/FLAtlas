from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path

from fl_editor.native_scene_loader import NativeScenePreparedPayload
from fl_editor.native_scene_loader import NativeSceneLoadResult
from fl_editor.native_scene_loader import build_native_scene_prepared_payload
from fl_editor.native_scene_loader import collect_completed_native_scene_loads
from fl_editor.native_scene_loader import load_native_scene_data
from fl_editor.native_scene_loader import reprioritize_native_scene_pending_loads


class _FakeSceneData:
    def __init__(self, geometries):
        self.geometries = geometries
        self.bounds = type("Bounds", (), {"radius": 12.5})()


def test_build_native_scene_prepared_payload_extracts_worker_metadata(tmp_path: Path):
    model_path = tmp_path / "ship.cmp"
    scene_data = _FakeSceneData(geometries=(object(), object(), object()))

    payload = build_native_scene_prepared_payload(model_path, scene_data, normalize_to_center=False)

    assert payload == NativeScenePreparedPayload(
        model_path=model_path,
        scene_data=scene_data,
        geometry_count=3,
        bounds_radius=12.5,
        normalize_to_center=False,
    )


def test_load_native_scene_data_returns_scene_data_with_geometry(monkeypatch, tmp_path: Path):
    model_path = tmp_path / "ship.cmp"
    model_path.write_bytes(b"cmp")
    native_model = object()
    scene_data = _FakeSceneData(geometries=(object(),))

    monkeypatch.setattr("fl_editor.native_scene_loader.load_native_freelancer_model", lambda path: native_model)
    monkeypatch.setattr(
        "fl_editor.native_scene_loader.build_native_preview_scene_data",
        lambda model, **_kwargs: scene_data,
    )

    result = load_native_scene_data(model_path)

    assert result.model_path == model_path
    assert result.scene_data is scene_data
    assert result.prepared_payload is not None
    assert result.prepared_payload.scene_data is scene_data
    assert result.prepared_payload.geometry_count == 1


def test_load_native_scene_data_returns_none_for_empty_or_failed_scene(monkeypatch, tmp_path: Path):
    model_path = tmp_path / "ship.cmp"
    model_path.write_bytes(b"cmp")

    monkeypatch.setattr("fl_editor.native_scene_loader.load_native_freelancer_model", lambda path: object())
    monkeypatch.setattr(
        "fl_editor.native_scene_loader.build_native_preview_scene_data",
        lambda model, **_kwargs: _FakeSceneData(geometries=()),
    )
    empty_result = load_native_scene_data(model_path)

    monkeypatch.setattr(
        "fl_editor.native_scene_loader.load_native_freelancer_model",
        lambda path: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    failed_result = load_native_scene_data(model_path)

    assert empty_result == NativeSceneLoadResult(model_path=model_path, scene_data=None, prepared_payload=None)
    assert failed_result == NativeSceneLoadResult(model_path=model_path, scene_data=None, prepared_payload=None)


def test_collect_completed_native_scene_loads_returns_only_finished_results(tmp_path: Path):
    model_a = tmp_path / "a.cmp"
    model_b = tmp_path / "b.cmp"
    model_c = tmp_path / "c.cmp"
    future_a: Future = Future()
    future_b: Future = Future()
    future_c: Future = Future()
    future_a.set_result(
        NativeSceneLoadResult(
            model_path=model_a,
            scene_data="scene-a",
            prepared_payload=NativeScenePreparedPayload(
                model_path=model_a,
                scene_data="scene-a",
                geometry_count=1,
                bounds_radius=0.0,
                normalize_to_center=True,
            ),
        )
    )
    future_b.set_exception(RuntimeError("broken"))
    pending = {
        model_a: future_a,
        model_b: future_b,
        model_c: future_c,
    }

    completed = collect_completed_native_scene_loads(pending)

    assert completed == (
        NativeSceneLoadResult(
            model_path=model_a,
            scene_data="scene-a",
            prepared_payload=NativeScenePreparedPayload(
                model_path=model_a,
                scene_data="scene-a",
                geometry_count=1,
                bounds_radius=0.0,
                normalize_to_center=True,
            ),
        ),
        NativeSceneLoadResult(model_path=model_b, scene_data=None, prepared_payload=None),
    )
    assert pending == {model_c: future_c}


class _FakePendingFuture:
    def __init__(self, *, done: bool = False, cancel_result: bool = False):
        self._done = done
        self._cancel_result = cancel_result
        self.cancel_calls = 0

    def done(self) -> bool:
        return self._done

    def cancel(self) -> bool:
        self.cancel_calls += 1
        return self._cancel_result


def test_reprioritize_native_scene_pending_loads_keeps_priority_and_drops_outdated(tmp_path: Path):
    keep_path = tmp_path / "selected.cmp"
    cancelable_path = tmp_path / "queued-old.cmp"
    running_path = tmp_path / "running-old.cmp"
    completed_path = tmp_path / "done-old.cmp"
    keep_future = _FakePendingFuture()
    cancelable_future = _FakePendingFuture(cancel_result=True)
    running_future = _FakePendingFuture(cancel_result=False)
    completed_future = _FakePendingFuture(done=True)
    pending = {
        keep_path: keep_future,
        cancelable_path: cancelable_future,
        running_path: running_future,
        completed_path: completed_future,
    }

    removed = reprioritize_native_scene_pending_loads(pending, keep_path)

    assert removed == (cancelable_path, completed_path)
    assert pending == {
        keep_path: keep_future,
        running_path: running_future,
    }
    assert keep_future.cancel_calls == 0
    assert cancelable_future.cancel_calls == 1
    assert running_future.cancel_calls == 1
    assert completed_future.cancel_calls == 0
