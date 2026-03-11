from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path

from fl_editor.native_scene_loader import NativeSceneLoadResult
from fl_editor.native_scene_loader import collect_completed_native_scene_loads
from fl_editor.native_scene_loader import load_native_scene_data


class _FakeSceneData:
    def __init__(self, geometries):
        self.geometries = geometries


def test_load_native_scene_data_returns_scene_data_with_geometry(monkeypatch, tmp_path: Path):
    model_path = tmp_path / "ship.cmp"
    model_path.write_bytes(b"cmp")
    native_model = object()
    scene_data = _FakeSceneData(geometries=(object(),))

    monkeypatch.setattr("fl_editor.native_scene_loader.load_native_freelancer_model", lambda path: native_model)
    monkeypatch.setattr("fl_editor.native_scene_loader.build_native_preview_scene_data", lambda model: scene_data)

    result = load_native_scene_data(model_path)

    assert result == NativeSceneLoadResult(model_path=model_path, scene_data=scene_data)


def test_load_native_scene_data_returns_none_for_empty_or_failed_scene(monkeypatch, tmp_path: Path):
    model_path = tmp_path / "ship.cmp"
    model_path.write_bytes(b"cmp")

    monkeypatch.setattr("fl_editor.native_scene_loader.load_native_freelancer_model", lambda path: object())
    monkeypatch.setattr(
        "fl_editor.native_scene_loader.build_native_preview_scene_data",
        lambda model: _FakeSceneData(geometries=()),
    )
    empty_result = load_native_scene_data(model_path)

    monkeypatch.setattr(
        "fl_editor.native_scene_loader.load_native_freelancer_model",
        lambda path: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    failed_result = load_native_scene_data(model_path)

    assert empty_result == NativeSceneLoadResult(model_path=model_path, scene_data=None)
    assert failed_result == NativeSceneLoadResult(model_path=model_path, scene_data=None)


def test_collect_completed_native_scene_loads_returns_only_finished_results(tmp_path: Path):
    model_a = tmp_path / "a.cmp"
    model_b = tmp_path / "b.cmp"
    model_c = tmp_path / "c.cmp"
    future_a: Future = Future()
    future_b: Future = Future()
    future_c: Future = Future()
    future_a.set_result(NativeSceneLoadResult(model_path=model_a, scene_data="scene-a"))
    future_b.set_exception(RuntimeError("broken"))
    pending = {
        model_a: future_a,
        model_b: future_b,
        model_c: future_c,
    }

    completed = collect_completed_native_scene_loads(pending)

    assert completed == (
        NativeSceneLoadResult(model_path=model_a, scene_data="scene-a"),
        NativeSceneLoadResult(model_path=model_b, scene_data=None),
    )
    assert pending == {model_c: future_c}
