from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .freelancer_mesh_data import FreelancerBounds, FreelancerCmpTransformHint, FreelancerMeshData
from .cmp_orientation_debug import build_cmp_orientation_debug_snapshot, cmp_orientation_debug_rows
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
    all_geometries: tuple[NativePreviewGeometry, ...] = ()
    all_geometry_texture_paths: tuple[Path | None, ...] = ()
    cmp_orientation_debug_rows: tuple[tuple[str, str], ...] = ()
    cmp_up_correction_euler_deg: tuple[float, float, float] = (0.0, 0.0, 0.0)
    cmp_transform_hints: tuple[FreelancerCmpTransformHint, ...] = ()


def build_native_preview_scene_data(
    native_model: FreelancerMeshData | None,
    *,
    normalize_to_center: bool = True,
) -> NativePreviewSceneData:
    if native_model is None:
        return NativePreviewSceneData(
            geometries=(),
            primary_geometry=None,
            bounds=None,
            part_names=(),
            texture_path=None,
            geometry_texture_paths=(),
            all_geometries=(),
            all_geometry_texture_paths=(),
            cmp_orientation_debug_rows=(),
            cmp_up_correction_euler_deg=(0.0, 0.0, 0.0),
        )
    all_geometries = decode_native_preview_geometries(native_model, normalize_to_center=normalize_to_center)
    geometries = _select_display_geometries(all_geometries, lod_mode=0)
    geometry_bounds = aggregate_native_preview_bounds(geometries)
    all_geometry_texture_paths = tuple(
        resolve_native_texture_for_geometry(
            native_model,
            geometry.model_name,
            geometry.level_name,
            geometry.group_start,
            geometry.group_count,
        )
        for geometry in all_geometries
    )
    geometry_texture_paths = tuple(
        _texture_path_from_all_geometries(
            all_geometries=all_geometries,
            all_geometry_texture_paths=all_geometry_texture_paths,
            geometry=geometry,
            fallback=None,
        )
        for geometry in geometries
    )
    orientation_snapshot = build_cmp_orientation_debug_snapshot(native_model)
    return NativePreviewSceneData(
        geometries=geometries,
        primary_geometry=geometries[0] if geometries else None,
        bounds=geometry_bounds or native_model.bounds,
        part_names=_collect_native_part_names(geometries),
        texture_path=resolve_native_texture_path(native_model),
        geometry_texture_paths=geometry_texture_paths,
        all_geometries=all_geometries,
        all_geometry_texture_paths=all_geometry_texture_paths,
        cmp_orientation_debug_rows=cmp_orientation_debug_rows(orientation_snapshot),
        cmp_up_correction_euler_deg=tuple(
            float(v) for v in orientation_snapshot.get("suggested_up_correction_euler_deg", (0.0, 0.0, 0.0))
        ),
        cmp_transform_hints=native_model.cmp_transform_hints,
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
    for index, candidate in enumerate(scene_data.all_geometries):
        if candidate == geometry:
            if index < len(scene_data.all_geometry_texture_paths):
                return scene_data.all_geometry_texture_paths[index] or scene_data.texture_path
            break
    return scene_data.texture_path


def scene_data_with_lod_mode(
    scene_data: NativePreviewSceneData,
    lod_mode: int,
) -> NativePreviewSceneData:
    mode = max(0, int(lod_mode))
    if mode <= 0 or not scene_data.all_geometries:
        return scene_data
    geometries = _select_display_geometries(scene_data.all_geometries, lod_mode=mode)
    if not geometries:
        return scene_data
    geometry_texture_paths = tuple(
        _texture_path_from_all_geometries(
            all_geometries=scene_data.all_geometries,
            all_geometry_texture_paths=scene_data.all_geometry_texture_paths,
            geometry=geometry,
            fallback=scene_data.texture_path,
        )
        for geometry in geometries
    )
    return NativePreviewSceneData(
        geometries=geometries,
        primary_geometry=geometries[0] if geometries else None,
        bounds=scene_data.bounds,
        part_names=_collect_native_part_names(geometries),
        texture_path=scene_data.texture_path,
        geometry_texture_paths=geometry_texture_paths,
        all_geometries=scene_data.all_geometries,
        all_geometry_texture_paths=scene_data.all_geometry_texture_paths,
        cmp_orientation_debug_rows=scene_data.cmp_orientation_debug_rows,
        cmp_up_correction_euler_deg=scene_data.cmp_up_correction_euler_deg,
        cmp_transform_hints=scene_data.cmp_transform_hints,
    )


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
    *,
    lod_mode: int = 0,
) -> tuple[NativePreviewGeometry, ...]:
    if not native_geometries:
        return ()
    best_by_key: dict[str, NativePreviewGeometry] = {}
    grouped_by_key: dict[str, list[NativePreviewGeometry]] = {}
    ordered_keys: list[str] = []
    for geometry in native_geometries:
        key = geometry.part_name or geometry.model_name
        group = grouped_by_key.setdefault(key, [])
        group.append(geometry)
        if key not in best_by_key:
            best_by_key[key] = geometry
            ordered_keys.append(key)
    for key, group in grouped_by_key.items():
        ordered = sorted(group, key=_geometry_sort_key)
        if int(lod_mode) <= 0:
            best_by_key[key] = ordered[0]
            continue
        preferred = [
            geometry
            for geometry in ordered
            if _level_sort_key(geometry.level_name) >= int(lod_mode)
        ]
        if preferred:
            best_by_key[key] = preferred[0]
            continue
        best_by_key[key] = ordered[-1]
    return tuple(best_by_key[key] for key in ordered_keys)


def _texture_path_from_all_geometries(
    *,
    all_geometries: tuple[NativePreviewGeometry, ...],
    all_geometry_texture_paths: tuple[Path | None, ...],
    geometry: NativePreviewGeometry,
    fallback: Path | None,
) -> Path | None:
    for index, candidate in enumerate(all_geometries):
        if candidate == geometry:
            if index < len(all_geometry_texture_paths):
                return all_geometry_texture_paths[index] or fallback
            break
    return fallback


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
