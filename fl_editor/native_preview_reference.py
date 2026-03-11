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
    translation_delta: float | None
    translation_matches_center: bool | None


@dataclass(frozen=True)
class NativePreviewReferenceSummary:
    total_rows: int
    rows_with_translation_hint: int
    rows_with_matching_translation: int
    rows_with_mismatching_translation: int
    rows_without_texture: int
    max_translation_delta: float


def build_native_preview_reference_rows(
    mesh_data: FreelancerMeshData,
    scene_data: NativePreviewSceneData,
    translation_match_tolerance: float = 1.0,
) -> tuple[NativePreviewReferenceRow, ...]:
    rows: list[NativePreviewReferenceRow] = []
    for index, geometry in enumerate(scene_data.geometries):
        texture_path = texture_path_for_geometry(scene_data, geometry)
        translation = _translation_hint_for_part(mesh_data, geometry.part_name)
        center_xyz = _bounds_center(geometry.bounds.min_xyz, geometry.bounds.max_xyz)
        translation_delta = _distance_xyz(center_xyz, translation) if translation is not None else None
        rows.append(
            NativePreviewReferenceRow(
                model_name=geometry.model_name,
                part_name=geometry.part_name,
                geometry_index=index,
                center_xyz=center_xyz,
                radius=float(geometry.bounds.radius or 0.0),
                has_texture=texture_path is not None,
                texture_name=texture_path.name if isinstance(texture_path, Path) else None,
                has_translation_hint=translation is not None,
                translation_xyz=translation,
                translation_delta=translation_delta,
                translation_matches_center=(
                    translation_delta <= translation_match_tolerance if translation_delta is not None else None
                ),
            )
        )
    return tuple(rows)


def build_native_preview_reference_summary(
    rows: tuple[NativePreviewReferenceRow, ...],
) -> NativePreviewReferenceSummary:
    with_hint = 0
    matching_translation = 0
    mismatching_translation = 0
    without_texture = 0
    max_delta = 0.0

    for row in rows:
        if not row.has_texture:
            without_texture += 1
        if row.translation_delta is None:
            continue
        with_hint += 1
        max_delta = max(max_delta, row.translation_delta)
        if row.translation_matches_center:
            matching_translation += 1
        else:
            mismatching_translation += 1

    return NativePreviewReferenceSummary(
        total_rows=len(rows),
        rows_with_translation_hint=with_hint,
        rows_with_matching_translation=matching_translation,
        rows_with_mismatching_translation=mismatching_translation,
        rows_without_texture=without_texture,
        max_translation_delta=max_delta,
    )


def sort_native_preview_reference_rows(
    rows: tuple[NativePreviewReferenceRow, ...],
) -> tuple[NativePreviewReferenceRow, ...]:
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                row.translation_matches_center is not False,
                -(row.translation_delta or -1.0),
                row.geometry_index,
            ),
        )
    )


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


def _distance_xyz(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return (dx * dx + dy * dy + dz * dz) ** 0.5
