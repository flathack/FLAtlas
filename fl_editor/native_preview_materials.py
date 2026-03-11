from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .freelancer_mesh_data import (
    FreelancerMaterialReference,
    FreelancerMeshData,
    FreelancerPreviewMaterialBinding,
)


TEXTURE_FILE_EXTENSIONS = (".dds", ".tga")


def select_native_texture_reference(
    references: tuple[FreelancerMaterialReference, ...],
) -> FreelancerMaterialReference | None:
    preferred: FreelancerMaterialReference | None = None
    for reference in references:
        suffix = Path(reference.value).suffix.lower()
        if reference.kind != "texture":
            continue
        if suffix in TEXTURE_FILE_EXTENSIONS:
            return reference
        if preferred is None:
            preferred = reference
    return preferred


def resolve_native_texture_path(mesh_data: FreelancerMeshData) -> Path | None:
    reference = select_native_texture_reference(mesh_data.material_references)
    if reference is None:
        return None
    return resolve_native_texture_value(mesh_data.source_path.resolve(), reference.value)


def resolve_native_texture_value(source_path: Path, value: str) -> Path | None:
    return _resolve_texture_value(source_path.resolve(), value)


def resolve_native_texture_for_geometry(
    mesh_data: FreelancerMeshData,
    model_name: str,
    level_name: str | None,
) -> Path | None:
    for binding in mesh_data.preview_material_bindings:
        if binding.model_name != model_name:
            continue
        if binding.level_name != level_name:
            continue
        if binding.texture_value:
            return resolve_native_texture_value(mesh_data.source_path, binding.texture_value)
    return resolve_native_texture_path(mesh_data)


def select_preview_material_binding(
    bindings: tuple[FreelancerPreviewMaterialBinding, ...],
    model_name: str,
    level_name: str | None,
) -> FreelancerPreviewMaterialBinding | None:
    for binding in bindings:
        if binding.model_name == model_name and binding.level_name == level_name:
            return binding
    return None


@lru_cache(maxsize=256)
def _resolve_texture_value(source_path: Path, value: str) -> Path | None:
    normalized = value.replace("\\", "/").strip()
    if not normalized:
        return None

    candidate = Path(normalized)
    if candidate.is_absolute() and candidate.exists():
        return candidate

    source_dir = source_path.parent
    direct_candidates = (
        source_dir / normalized,
        source_dir / Path(normalized).name,
    )
    for direct in direct_candidates:
        if direct.exists():
            return direct

    data_root = _find_data_root(source_dir)
    if data_root is None:
        return None

    rooted_candidates = []
    upper_normalized = normalized.upper()
    if upper_normalized.startswith("DATA/"):
        rooted_candidates.append(data_root / normalized.split("/", 1)[1])
    rooted_candidates.append(data_root / normalized)
    rooted_candidates.append(data_root / Path(normalized).name)
    for rooted in rooted_candidates:
        if rooted.exists():
            return rooted

    basename = Path(normalized).name.lower()
    if not basename:
        return None
    try:
        for path in data_root.rglob("*"):
            if path.is_file() and path.name.lower() == basename:
                return path
    except OSError:
        return None
    return None


def _find_data_root(path: Path) -> Path | None:
    for candidate in (path, *path.parents):
        if candidate.name.upper() == "DATA":
            return candidate
    return None
