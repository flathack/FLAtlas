from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .freelancer_mesh_data import FreelancerMeshData
from .native_preview_scene_data import NativePreviewSceneData, texture_path_for_geometry


@dataclass(frozen=True)
class NativePreviewReferenceRow:
    model_name: str
    part_name: str | None
    geometry_index: int
    center_xyz: tuple[float, float, float]
    radius: float
    has_texture: bool
    texture_name: str | None
    has_translation_hint: bool
    translation_xyz: tuple[float, float, float] | None


def build_native_preview_reference_rows(
    mesh_data: FreelancerMeshData,
    scene_data: NativePreviewSceneData,
) -> tuple[NativePreviewReferenceRow, ...]:
    rows: list[NativePreviewReferenceRow] = []
    for index, geometry in enumerate(scene_data.geometries):
        texture_path = texture_path_for_geometry(scene_data, geometry)
        translation = _translation_hint_for_part(mesh_data, geometry.part_name)
        rows.append(
            NativePreviewReferenceRow(
                model_name=geometry.model_name,
                part_name=geometry.part_name,
                geometry_index=index,
                center_xyz=_bounds_center(geometry.bounds.min_xyz, geometry.bounds.max_xyz),
                radius=float(geometry.bounds.radius or 0.0),
                has_texture=texture_path is not None,
                texture_name=texture_path.name if isinstance(texture_path, Path) else None,
                has_translation_hint=translation is not None,
                translation_xyz=translation,
            )
        )
    return tuple(rows)


def _translation_hint_for_part(
    mesh_data: FreelancerMeshData,
    part_name: str | None,
) -> tuple[float, float, float] | None:
    if not part_name:
        return None
    for hint in mesh_data.cmp_transform_hints:
        if hint.part_name == part_name:
            return hint.translation_xyz
    return None


def _bounds_center(
    min_xyz: tuple[float, float, float],
    max_xyz: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        (min_xyz[0] + max_xyz[0]) * 0.5,
        (min_xyz[1] + max_xyz[1]) * 0.5,
        (min_xyz[2] + max_xyz[2]) * 0.5,
    )
