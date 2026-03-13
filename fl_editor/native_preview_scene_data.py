from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .freelancer_mesh_data import FreelancerBounds, FreelancerMeshData
from .native_preview_geometry import NativePreviewGeometry, aggregate_native_preview_bounds, decode_native_preview_geometries
from .native_preview_materials import resolve_native_texture_for_geometry, resolve_native_texture_path


@dataclass(frozen=True)
class NativePreviewSceneData:
    geometries: tuple[NativePreviewGeometry, ...]
    primary_geometry: NativePreviewGeometry | None
    bounds: FreelancerBounds | None
    part_names: tuple[str, ...]
    texture_path: Path | None
    geometry_texture_paths: tuple[Path | None, ...]


def build_native_preview_scene_data(
    native_model: FreelancerMeshData | None,
) -> NativePreviewSceneData:
    if native_model is None:
        return NativePreviewSceneData(
            geometries=(),
            primary_geometry=None,
            bounds=None,
            part_names=(),
            texture_path=None,
            geometry_texture_paths=(),
        )
    geometries = _select_display_geometries(decode_native_preview_geometries(native_model))
    geometry_bounds = aggregate_native_preview_bounds(geometries)
    geometry_texture_paths = tuple(
        resolve_native_texture_for_geometry(
            native_model,
            geometry.model_name,
            geometry.level_name,
            geometry.group_start,
            geometry.group_count,
        )
        for geometry in geometries
    )
    return NativePreviewSceneData(
        geometries=geometries,
        primary_geometry=geometries[0] if geometries else None,
        bounds=geometry_bounds or native_model.bounds,
        part_names=_collect_native_part_names(geometries),
        texture_path=resolve_native_texture_path(native_model),
        geometry_texture_paths=geometry_texture_paths,
    )


def texture_path_for_geometry(
    scene_data: NativePreviewSceneData,
    geometry: NativePreviewGeometry | None,
) -> Path | None:
    if geometry is None:
        return scene_data.texture_path
    for index, candidate in enumerate(scene_data.geometries):
        if candidate == geometry:
            if index < len(scene_data.geometry_texture_paths):
                return scene_data.geometry_texture_paths[index] or scene_data.texture_path
            break
    return scene_data.texture_path


def _collect_native_part_names(
    native_geometries: tuple[NativePreviewGeometry, ...],
) -> tuple[str, ...]:
    names: list[str] = []
    seen: set[str] = set()
    for geometry in native_geometries:
        label = geometry.part_name or geometry.model_name
        if label and label not in seen:
            seen.add(label)
            names.append(label)
    return tuple(names)


def _select_display_geometries(
    native_geometries: tuple[NativePreviewGeometry, ...],
) -> tuple[NativePreviewGeometry, ...]:
    if not native_geometries:
        return ()
    best_by_key: dict[str, NativePreviewGeometry] = {}
    ordered_keys: list[str] = []
    for geometry in native_geometries:
        key = geometry.part_name or geometry.model_name
        current = best_by_key.get(key)
        if current is None:
            best_by_key[key] = geometry
            ordered_keys.append(key)
            continue
        if _geometry_sort_key(geometry) < _geometry_sort_key(current):
            best_by_key[key] = geometry
    return tuple(best_by_key[key] for key in ordered_keys)


def _geometry_sort_key(geometry: NativePreviewGeometry) -> tuple[int, int, int]:
    return (
        _level_sort_key(geometry.level_name),
        -len(geometry.positions),
        -len(geometry.indices),
    )


def _level_sort_key(level_name: str | None) -> int:
    if not level_name:
        return 1_000_000
    lowered = level_name.lower()
    if lowered.startswith("level"):
        try:
            return int(lowered[5:])
        except ValueError:
            return 1_000_000
    return 1_000_000
