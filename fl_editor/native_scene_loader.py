from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass
from pathlib import Path

from .cmp_loader import load_native_freelancer_model
from .native_preview_scene_data import build_native_preview_scene_data


@dataclass(frozen=True)
class NativeSceneLoadResult:
    model_path: Path
    scene_data: object | None


def load_native_scene_data(model_path: Path) -> NativeSceneLoadResult:
    try:
        native_model = load_native_freelancer_model(model_path)
        scene_data = build_native_preview_scene_data(native_model)
        if not getattr(scene_data, "geometries", ()):
            scene_data = None
    except Exception:
        scene_data = None
    return NativeSceneLoadResult(model_path=model_path, scene_data=scene_data)


def collect_completed_native_scene_loads(
    pending_by_path: dict[Path, Future],
) -> tuple[NativeSceneLoadResult, ...]:
    completed: list[NativeSceneLoadResult] = []
    for model_path, future in tuple(pending_by_path.items()):
        if not future.done():
            continue
        pending_by_path.pop(model_path, None)
        try:
            result = future.result()
        except Exception:
            result = NativeSceneLoadResult(model_path=model_path, scene_data=None)
        completed.append(result)
    return tuple(completed)
