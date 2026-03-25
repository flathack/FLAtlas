from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass
from pathlib import Path

from .cmp_loader import load_native_freelancer_model
from .native_preview_scene_data import build_native_preview_scene_data


@dataclass(frozen=True)
class NativeScenePreparedPayload:
    model_path: Path
    scene_data: object
    geometry_count: int
    bounds_radius: float
    normalize_to_center: bool


@dataclass(frozen=True)
class NativeSceneLoadResult:
    model_path: Path
    scene_data: object | None
    prepared_payload: NativeScenePreparedPayload | None = None


def build_native_scene_prepared_payload(
    model_path: Path,
    scene_data: object,
    *,
    normalize_to_center: bool,
) -> NativeScenePreparedPayload:
    geometries = tuple(getattr(scene_data, "geometries", ()) or ())
    bounds = getattr(scene_data, "bounds", None)
    bounds_radius = 0.0
    try:
        bounds_radius = float(getattr(bounds, "radius", 0.0) or 0.0)
    except Exception:
        bounds_radius = 0.0
    return NativeScenePreparedPayload(
        model_path=model_path,
        scene_data=scene_data,
        geometry_count=len(geometries),
        bounds_radius=bounds_radius,
        normalize_to_center=bool(normalize_to_center),
    )


def load_native_scene_data(model_path: Path) -> NativeSceneLoadResult:
    return load_native_scene_data_with_options(model_path)


def load_native_scene_data_with_options(
    model_path: Path,
    *,
    normalize_to_center: bool = True,
) -> NativeSceneLoadResult:
    try:
        native_model = load_native_freelancer_model(model_path)
        scene_data = build_native_preview_scene_data(native_model, normalize_to_center=normalize_to_center)
        if not getattr(scene_data, "geometries", ()):
            scene_data = None
    except Exception:
        scene_data = None
    prepared_payload = None
    if scene_data is not None:
        try:
            prepared_payload = build_native_scene_prepared_payload(
                model_path,
                scene_data,
                normalize_to_center=normalize_to_center,
            )
        except Exception:
            prepared_payload = None
    return NativeSceneLoadResult(model_path=model_path, scene_data=scene_data, prepared_payload=prepared_payload)


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
            result = NativeSceneLoadResult(model_path=model_path, scene_data=None, prepared_payload=None)
        completed.append(result)
    return tuple(completed)


def reprioritize_native_scene_pending_loads(
    pending_by_path: dict[Path, Future],
    prioritized_path: Path,
) -> tuple[Path, ...]:
    removed_paths: list[Path] = []
    for model_path, future in tuple(pending_by_path.items()):
        if model_path == prioritized_path:
            continue
        # Drop finished requests and cancel outdated queued requests so the
        # currently selected model can be loaded next.
        if future.done() or future.cancel():
            pending_by_path.pop(model_path, None)
            removed_paths.append(model_path)
    return tuple(removed_paths)
