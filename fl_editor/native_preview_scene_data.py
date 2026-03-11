from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .freelancer_mesh_data import FreelancerBounds, FreelancerMeshData
from .native_preview_geometry import NativePreviewGeometry, aggregate_native_preview_bounds, decode_native_preview_geometries
from .native_preview_materials import resolve_native_texture_path


@dataclass(frozen=True)
class NativePreviewSceneData:
    geometries: tuple[NativePreviewGeometry, ...]
    primary_geometry: NativePreviewGeometry | None
    bounds: FreelancerBounds | None
    part_names: tuple[str, ...]
    texture_path: Path | None


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
        )
    geometries = decode_native_preview_geometries(native_model)
    geometry_bounds = aggregate_native_preview_bounds(geometries)
    return NativePreviewSceneData(
        geometries=geometries,
        primary_geometry=geometries[0] if geometries else None,
        bounds=geometry_bounds or native_model.bounds,
        part_names=_collect_native_part_names(geometries),
        texture_path=resolve_native_texture_path(native_model),
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
