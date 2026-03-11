from __future__ import annotations

import math
import struct
from dataclasses import dataclass

from .freelancer_mesh_data import (
    FreelancerBounds,
    FreelancerMeshData,
    FreelancerPreviewBufferSlice,
)


MAX_PREVIEW_ABS_COORD = 1_000_000.0


@dataclass(frozen=True)
class NativePreviewGeometry:
    model_name: str
    level_name: str | None
    part_name: str | None
    positions: tuple[tuple[float, float, float], ...]
    indices: tuple[int, ...]
    vertex_stride: int
    index_size: int
    confidence: str
    bounds: FreelancerBounds


@dataclass(frozen=True)
class _RawNativePreviewGeometry:
    model_name: str
    level_name: str | None
    part_name: str | None
    positions: tuple[tuple[float, float, float], ...]
    indices: tuple[int, ...]
    vertex_stride: int
    index_size: int
    confidence: str
    bounds: FreelancerBounds


def decode_native_preview_geometries(mesh_data: FreelancerMeshData) -> tuple[NativePreviewGeometry, ...]:
    raw_geometries: list[_RawNativePreviewGeometry] = []
    for buffer_slice in mesh_data.preview_buffer_slices:
        if buffer_slice.confidence not in {"exact", "tight"}:
            continue
        geometry = _decode_geometry_from_slice(mesh_data, buffer_slice)
        if geometry is not None:
            raw_geometries.append(geometry)
    if not raw_geometries:
        return ()
    common_bounds = _aggregate_bounds(tuple(geometry.bounds for geometry in raw_geometries))
    if common_bounds is None:
        return ()
    center_x = (common_bounds.min_xyz[0] + common_bounds.max_xyz[0]) * 0.5
    center_y = (common_bounds.min_xyz[1] + common_bounds.max_xyz[1]) * 0.5
    center_z = (common_bounds.min_xyz[2] + common_bounds.max_xyz[2]) * 0.5
    geometries: list[NativePreviewGeometry] = []
    for geometry in raw_geometries:
        normalized_positions = tuple(
            (x - center_x, y - center_y, z - center_z)
            for x, y, z in geometry.positions
        )
        bounds = FreelancerBounds(
            min_xyz=(
                geometry.bounds.min_xyz[0] - center_x,
                geometry.bounds.min_xyz[1] - center_y,
                geometry.bounds.min_xyz[2] - center_z,
            ),
            max_xyz=(
                geometry.bounds.max_xyz[0] - center_x,
                geometry.bounds.max_xyz[1] - center_y,
                geometry.bounds.max_xyz[2] - center_z,
            ),
            radius=geometry.bounds.radius,
        )
        geometries.append(
            NativePreviewGeometry(
                model_name=geometry.model_name,
                level_name=geometry.level_name,
                part_name=geometry.part_name,
                positions=normalized_positions,
                indices=geometry.indices,
                vertex_stride=geometry.vertex_stride,
                index_size=geometry.index_size,
                confidence=geometry.confidence,
                bounds=bounds,
            )
        )
    return tuple(geometries)


def decode_native_preview_geometry(mesh_data: FreelancerMeshData) -> NativePreviewGeometry | None:
    geometries = decode_native_preview_geometries(mesh_data)
    if not geometries:
        return None
    return geometries[0]


def _decode_geometry_from_slice(
    mesh_data: FreelancerMeshData,
    buffer_slice: FreelancerPreviewBufferSlice,
) -> _RawNativePreviewGeometry | None:
    if buffer_slice.matched_block_index is None:
        return None
    if not (0 <= buffer_slice.matched_block_index < len(mesh_data.vmesh_data_blocks)):
        return None

    raw = mesh_data.source_path.read_bytes()
    block = mesh_data.vmesh_data_blocks[buffer_slice.matched_block_index]
    start = block.data_offset
    end = block.data_offset + block.used_size
    if start < 0 or end > len(raw):
        return None
    block_bytes = raw[start:end]

    vertex_end = buffer_slice.vertex_offset + buffer_slice.vertex_bytes
    index_end = buffer_slice.index_offset + buffer_slice.index_bytes
    if vertex_end > len(block_bytes) or index_end > len(block_bytes):
        return None

    positions = _decode_positions(
        block_bytes[buffer_slice.vertex_offset:vertex_end],
        buffer_slice.vertex_stride,
    )
    if not positions:
        return None

    indices = _decode_indices(
        block_bytes[buffer_slice.index_offset:index_end],
        buffer_slice.index_size,
        len(positions),
    )
    if not indices:
        return None

    rotation_forward = _forward_vector_for_geometry(mesh_data, buffer_slice.model_name)
    if rotation_forward is not None:
        positions = _rotate_positions_to_forward(positions, rotation_forward)
    bounds = _positions_bounds(positions)
    translation = _translation_for_geometry(mesh_data, buffer_slice.model_name)
    if translation is not None:
        positions = tuple(
            (x + translation[0], y + translation[1], z + translation[2])
            for x, y, z in positions
        )
        bounds = _positions_bounds(positions)

    return _RawNativePreviewGeometry(
        model_name=buffer_slice.model_name,
        level_name=buffer_slice.level_name,
        part_name=_part_name_for_model(mesh_data, buffer_slice.model_name),
        positions=positions,
        indices=indices,
        vertex_stride=buffer_slice.vertex_stride,
        index_size=buffer_slice.index_size,
        confidence=buffer_slice.confidence,
        bounds=bounds,
    )


def _part_name_for_model(mesh_data: FreelancerMeshData, model_name: str) -> str | None:
    for preview_node in mesh_data.preview_nodes:
        if preview_node.model_name == model_name:
            return preview_node.matched_part_name
    return None


def _translation_for_geometry(
    mesh_data: FreelancerMeshData,
    model_name: str,
) -> tuple[float, float, float] | None:
    part_name = _part_name_for_model(mesh_data, model_name)
    if not part_name:
        return None
    for hint in mesh_data.cmp_transform_hints:
        if hint.part_name == part_name and hint.translation_xyz is not None:
            return hint.translation_xyz
    return None


def _forward_vector_for_geometry(
    mesh_data: FreelancerMeshData,
    model_name: str,
) -> tuple[float, float, float] | None:
    part_name = _part_name_for_model(mesh_data, model_name)
    if not part_name:
        return None
    for hint in mesh_data.cmp_transform_hints:
        if hint.part_name == part_name and hint.normalized_forward_xyz is not None:
            return hint.normalized_forward_xyz
    return None


def _rotate_positions_to_forward(
    positions: tuple[tuple[float, float, float], ...],
    forward_xyz: tuple[float, float, float],
) -> tuple[tuple[float, float, float], ...]:
    source = (1.0, 0.0, 0.0)
    target = forward_xyz
    dot = max(-1.0, min(1.0, _dot(source, target)))
    if dot >= 1.0 - 1e-6:
        return positions
    if dot <= -1.0 + 1e-6:
        axis = (0.0, 0.0, 1.0)
        angle = math.pi
    else:
        cross = _cross(source, target)
        cross_length = math.sqrt(_dot(cross, cross))
        if cross_length <= 1e-6:
            return positions
        axis = (cross[0] / cross_length, cross[1] / cross_length, cross[2] / cross_length)
        angle = math.acos(dot)
    return tuple(_rotate_vector(position, axis, angle) for position in positions)


def _rotate_vector(
    value: tuple[float, float, float],
    axis: tuple[float, float, float],
    angle: float,
) -> tuple[float, float, float]:
    x, y, z = value
    kx, ky, kz = axis
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    dot = kx * x + ky * y + kz * z
    cross_x = ky * z - kz * y
    cross_y = kz * x - kx * z
    cross_z = kx * y - ky * x
    return (
        x * cos_a + cross_x * sin_a + kx * dot * (1.0 - cos_a),
        y * cos_a + cross_y * sin_a + ky * dot * (1.0 - cos_a),
        z * cos_a + cross_z * sin_a + kz * dot * (1.0 - cos_a),
    )


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _decode_positions(raw: bytes, stride: int) -> tuple[tuple[float, float, float], ...]:
    if stride < 12 or len(raw) % stride != 0:
        return ()
    positions: list[tuple[float, float, float]] = []
    for offset in range(0, len(raw), stride):
        x, y, z = struct.unpack_from("<3f", raw, offset)
        if not all(math.isfinite(value) for value in (x, y, z)):
            return ()
        if max(abs(x), abs(y), abs(z)) > MAX_PREVIEW_ABS_COORD:
            return ()
        positions.append((x, y, z))
    return tuple(positions)


def _decode_indices(raw: bytes, index_size: int, vertex_count: int) -> tuple[int, ...]:
    if index_size not in (2, 4) or len(raw) % index_size != 0:
        return ()
    indices: list[int] = []
    step = index_size
    for offset in range(0, len(raw), step):
        index = int.from_bytes(raw[offset : offset + step], "little", signed=False)
        if index >= vertex_count:
            return ()
        indices.append(index)
    return tuple(indices)


def aggregate_native_preview_bounds(
    geometries: tuple[NativePreviewGeometry, ...],
) -> FreelancerBounds | None:
    return _aggregate_bounds(tuple(geometry.bounds for geometry in geometries))


def _positions_bounds(
    positions: tuple[tuple[float, float, float], ...],
) -> FreelancerBounds:
    min_x = min(pos[0] for pos in positions)
    min_y = min(pos[1] for pos in positions)
    min_z = min(pos[2] for pos in positions)
    max_x = max(pos[0] for pos in positions)
    max_y = max(pos[1] for pos in positions)
    max_z = max(pos[2] for pos in positions)
    bounds = FreelancerBounds(
        min_xyz=(min_x, min_y, min_z),
        max_xyz=(max_x, max_y, max_z),
        radius=max(
            math.sqrt(x * x + y * y + z * z)
            for x, y, z in positions
        ),
    )
    return bounds


def _aggregate_bounds(bounds_values: tuple[FreelancerBounds, ...]) -> FreelancerBounds | None:
    if not bounds_values:
        return None
    min_x = min(bounds.min_xyz[0] for bounds in bounds_values)
    min_y = min(bounds.min_xyz[1] for bounds in bounds_values)
    min_z = min(bounds.min_xyz[2] for bounds in bounds_values)
    max_x = max(bounds.max_xyz[0] for bounds in bounds_values)
    max_y = max(bounds.max_xyz[1] for bounds in bounds_values)
    max_z = max(bounds.max_xyz[2] for bounds in bounds_values)
    radius_values = [bounds.radius for bounds in bounds_values if bounds.radius is not None]
    radius = max(radius_values) if radius_values else None
    return FreelancerBounds(
        min_xyz=(min_x, min_y, min_z),
        max_xyz=(max_x, max_y, max_z),
        radius=radius,
    )
