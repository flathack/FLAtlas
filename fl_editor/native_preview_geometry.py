from __future__ import annotations

import math
import struct
from dataclasses import dataclass

from .freelancer_mesh_data import (
    FreelancerBounds,
    FreelancerMeshData,
    FreelancerPreviewBufferSlice,
    FreelancerStructuredDecodePlan,
)


MAX_PREVIEW_ABS_COORD = 1_000_000.0


@dataclass(frozen=True)
class NativePreviewGeometry:
    model_name: str
    level_name: str | None
    part_name: str | None
    group_start: int
    group_count: int
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
    group_start: int
    group_count: int
    positions: tuple[tuple[float, float, float], ...]
    indices: tuple[int, ...]
    vertex_stride: int
    index_size: int
    confidence: str
    bounds: FreelancerBounds


def decode_native_preview_geometries(mesh_data: FreelancerMeshData) -> tuple[NativePreviewGeometry, ...]:
    raw_geometries: list[_RawNativePreviewGeometry] = []
    handled_keys: set[tuple[str, str | None, int, int]] = set()
    for plan in mesh_data.structured_decode_plans:
        geometry = _decode_geometry_from_structured_plan(mesh_data, plan)
        if geometry is None:
            continue
        raw_geometries.append(geometry)
        handled_keys.add((geometry.model_name, geometry.level_name, geometry.group_start, geometry.group_count))
    for buffer_slice in mesh_data.preview_buffer_slices:
        key = (
            buffer_slice.model_name,
            buffer_slice.level_name,
            buffer_slice.group_start,
            buffer_slice.group_count,
        )
        if key in handled_keys:
            continue
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
                group_start=geometry.group_start,
                group_count=geometry.group_count,
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


def _decode_geometry_from_structured_plan(
    mesh_data: FreelancerMeshData,
    plan: FreelancerStructuredDecodePlan,
) -> _RawNativePreviewGeometry | None:
    if not plan.decode_ready:
        return None
    if plan.layout_mode == "single-block":
        if plan.header_block_index is None:
            return None
        matching_slice = next(
            (
                buffer_slice
                for buffer_slice in mesh_data.preview_buffer_slices
                if buffer_slice.model_name == plan.model_name
                and buffer_slice.level_name == plan.level_name
                and buffer_slice.matched_block_index == plan.header_block_index
                and buffer_slice.header_size > 0
                and buffer_slice.vertex_stride > 0
                and buffer_slice.index_size > 0
            ),
            None,
        )
        if matching_slice is None:
            return None
        geometry = _decode_geometry_from_slice(mesh_data, matching_slice)
        if geometry is not None:
            return geometry
        return _decode_geometry_from_structured_single_block(mesh_data, plan, matching_slice)
    if plan.layout_mode == "family-split-header-stream":
        return _decode_geometry_from_structured_family(mesh_data, plan)
    return None


def _decode_geometry_from_structured_family(
    mesh_data: FreelancerMeshData,
    plan: FreelancerStructuredDecodePlan,
) -> _RawNativePreviewGeometry | None:
    source = next(
        (
            preview_source
            for preview_source in mesh_data.preview_geometry_sources
            if preview_source.model_name == plan.model_name
            and preview_source.level_name == plan.level_name
        ),
        None,
    )
    if source is None:
        return None
    if plan.header_block_index is None:
        return None
    if not (0 <= plan.header_block_index < len(mesh_data.vmesh_data_blocks)):
        return None

    raw = mesh_data.source_path.read_bytes()
    header_block = mesh_data.vmesh_data_blocks[plan.header_block_index]
    header_start = header_block.data_offset
    header_end = header_block.data_offset + header_block.used_size
    if header_start < 0 or header_end > len(raw):
        return None
    header_bytes = raw[header_start:header_end]

    best_indices = _find_structured_family_indices(
        header_bytes=header_bytes,
        expected_index_count=source.index_count,
        expected_index_offset=source.index_start * 2,
        max_vertex_index_hint=plan.source_vertex_end,
    )
    if best_indices is None:
        return None
    _, indices = best_indices
    vertex_count = max(indices) + 1

    best_positions = _find_structured_family_positions(
        header_bytes=header_bytes,
        vertex_count=vertex_count,
        expected_bounds=source.bounds,
    )
    if best_positions is None:
        return None
    _, vertex_stride, positions = best_positions

    return _build_raw_geometry(
        mesh_data=mesh_data,
        model_name=plan.model_name,
        level_name=plan.level_name,
        group_start=source.group_start,
        group_count=source.group_count,
        positions=positions,
        indices=indices,
        vertex_stride=vertex_stride,
        index_size=2,
        confidence="structured-family-split",
    )


def _decode_geometry_from_structured_single_block(
    mesh_data: FreelancerMeshData,
    plan: FreelancerStructuredDecodePlan,
    buffer_slice: FreelancerPreviewBufferSlice,
) -> _RawNativePreviewGeometry | None:
    source = next(
        (
            preview_source
            for preview_source in mesh_data.preview_geometry_sources
            if preview_source.model_name == plan.model_name
            and preview_source.level_name == plan.level_name
        ),
        None,
    )
    if source is None:
        return None
    if buffer_slice.matched_block_index is None:
        return None
    if not (0 <= buffer_slice.matched_block_index < len(mesh_data.vmesh_data_blocks)):
        return None
    if source.vertex_count <= 0 or source.index_count <= 0:
        return None
    if buffer_slice.vertex_stride <= 0:
        return None

    raw = mesh_data.source_path.read_bytes()
    block = mesh_data.vmesh_data_blocks[buffer_slice.matched_block_index]
    start = block.data_offset
    end = block.data_offset + block.used_size
    if start < 0 or end > len(raw):
        return None
    block_bytes = raw[start:end]

    vertex_offset = buffer_slice.vertex_offset
    vertex_end = vertex_offset + (source.vertex_count * buffer_slice.vertex_stride)
    if vertex_end > len(block_bytes):
        return None
    positions = _decode_positions(
        block_bytes[vertex_offset:vertex_end],
        buffer_slice.vertex_stride,
    )
    if not positions:
        return None

    candidate_offsets: list[int] = []
    if plan.mesh_header_count is not None and plan.mesh_header_count > 0:
        candidate_offsets.append(plan.mesh_header_count * 16)
    candidate_offsets.append(source.index_start * 2)
    candidate_offsets.append(source.index_start * 4)
    candidate_offsets.append(buffer_slice.index_offset)

    indices: tuple[int, ...] = ()
    index_size = buffer_slice.index_size
    for candidate_offset in dict.fromkeys(candidate_offsets):
        if candidate_offset < 0:
            continue
        for candidate_index_size in (2, 4):
            index_end = candidate_offset + (source.index_count * candidate_index_size)
            if index_end > len(block_bytes):
                continue
            candidate_indices = _decode_indices(
                block_bytes[candidate_offset:index_end],
                candidate_index_size,
                len(positions),
            )
            if not candidate_indices:
                continue
            indices = candidate_indices
            index_size = candidate_index_size
            break
        if indices:
            break
    if not indices:
        return None

    return _build_raw_geometry(
        mesh_data=mesh_data,
        model_name=buffer_slice.model_name,
        level_name=buffer_slice.level_name,
        group_start=source.group_start,
        group_count=source.group_count,
        positions=positions,
        indices=indices,
        vertex_stride=buffer_slice.vertex_stride,
        index_size=index_size,
        confidence="structured-single-block",
    )


def _find_structured_family_indices(
    header_bytes: bytes,
    expected_index_count: int,
    expected_index_offset: int,
    max_vertex_index_hint: int | None,
) -> tuple[int, tuple[int, ...]] | None:
    if expected_index_count <= 0:
        return None
    best: tuple[int, int, tuple[int, ...]] | None = None
    max_vertex_index = max_vertex_index_hint if max_vertex_index_hint is not None else 4096
    min_unique = max(3, min(32, expected_index_count // 6))
    max_degenerate = max(0, expected_index_count // 6)
    total_bytes = expected_index_count * 2
    for offset in range(0, len(header_bytes) - total_bytes + 1, 2):
        indices = _decode_indices(
            header_bytes[offset:offset + total_bytes],
            2,
            max_vertex_index,
        )
        if not indices:
            continue
        unique_count = len(set(indices))
        if unique_count < min_unique:
            continue
        degenerate_count = sum(
            1
            for index in range(0, len(indices), 3)
            if index + 2 < len(indices)
            and len({indices[index], indices[index + 1], indices[index + 2]}) < 3
        )
        if degenerate_count > max_degenerate:
            continue
        score = (degenerate_count * 1000) - unique_count + abs(offset - expected_index_offset)
        candidate = (score, offset, indices)
        if best is None or candidate < best:
            best = candidate
    if best is None:
        return None
    return best[1], best[2]


def _find_structured_family_positions(
    header_bytes: bytes,
    vertex_count: int,
    expected_bounds: FreelancerBounds | None,
) -> tuple[int, int, tuple[tuple[float, float, float], ...]] | None:
    if vertex_count <= 0:
        return None
    expected_span = None
    if expected_bounds is not None:
        expected_span = (
            expected_bounds.max_xyz[0] - expected_bounds.min_xyz[0],
            expected_bounds.max_xyz[1] - expected_bounds.min_xyz[1],
            expected_bounds.max_xyz[2] - expected_bounds.min_xyz[2],
        )
    stride_candidates = (
        16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60, 64, 68, 72, 76,
        80, 84, 88, 92, 96, 100, 104, 108, 112, 116, 120, 124, 128,
    )
    min_unique = max(3, min(64, vertex_count // 2))
    best: tuple[float, int, int, tuple[tuple[float, float, float], ...]] | None = None
    for offset in range(0, min(320, len(header_bytes)), 4):
        for stride in stride_candidates:
            vertex_end = offset + (vertex_count * stride)
            if vertex_end > len(header_bytes):
                continue
            positions = _decode_positions(
                header_bytes[offset:vertex_end],
                stride,
            )
            if not positions:
                continue
            unique_count = len({tuple(round(value, 2) for value in pos) for pos in positions})
            if unique_count < min_unique:
                continue
            zero_prefix = 0
            for pos in positions:
                if max(abs(value) for value in pos) < 1e-6:
                    zero_prefix += 1
                    continue
                break
            bounds = _positions_bounds(positions)
            span = (
                bounds.max_xyz[0] - bounds.min_xyz[0],
                bounds.max_xyz[1] - bounds.min_xyz[1],
                bounds.max_xyz[2] - bounds.min_xyz[2],
            )
            span_score = 0.0
            if expected_span is not None:
                span_score = sum(abs(span[index] - expected_span[index]) for index in range(3))
            score = span_score + (zero_prefix * 20) + (max(0, stride - 64) * 5) - unique_count
            candidate = (score, offset, stride, positions)
            if best is None or candidate < best:
                best = candidate
    if best is None:
        return None
    return best[1], best[2], best[3]


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

    return _build_raw_geometry(
        mesh_data=mesh_data,
        model_name=buffer_slice.model_name,
        level_name=buffer_slice.level_name,
        group_start=buffer_slice.group_start,
        group_count=buffer_slice.group_count,
        positions=positions,
        indices=indices,
        vertex_stride=buffer_slice.vertex_stride,
        index_size=buffer_slice.index_size,
        confidence=buffer_slice.confidence,
    )


def _build_raw_geometry(
    mesh_data: FreelancerMeshData,
    model_name: str,
    level_name: str | None,
    group_start: int,
    group_count: int,
    positions: tuple[tuple[float, float, float], ...],
    indices: tuple[int, ...],
    vertex_stride: int,
    index_size: int,
    confidence: str,
) -> _RawNativePreviewGeometry:
    rotation_rows = _rotation_rows_for_geometry(mesh_data, model_name)
    if rotation_rows is not None:
        positions = tuple(_apply_rotation_rows(position, rotation_rows) for position in positions)
    else:
        rotation_forward = _forward_vector_for_geometry(mesh_data, model_name)
        if rotation_forward is not None:
            positions = _rotate_positions_to_forward(positions, rotation_forward)
    bounds = _positions_bounds(positions)
    translation = _translation_for_geometry(mesh_data, model_name)
    if translation is not None:
        positions = tuple(
            (x + translation[0], y + translation[1], z + translation[2])
            for x, y, z in positions
        )
        bounds = _positions_bounds(positions)

    return _RawNativePreviewGeometry(
        model_name=model_name,
        level_name=level_name,
        part_name=_part_name_for_model(mesh_data, model_name),
        group_start=group_start,
        group_count=group_count,
        positions=positions,
        indices=indices,
        vertex_stride=vertex_stride,
        index_size=index_size,
        confidence=confidence,
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
        if hint.part_name != part_name:
            continue
        if hint.combined_translation_xyz is not None:
            return hint.combined_translation_xyz
        if hint.translation_xyz is not None:
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


def _rotation_rows_for_geometry(
    mesh_data: FreelancerMeshData,
    model_name: str,
) -> tuple[tuple[float, float, float], ...] | None:
    part_name = _part_name_for_model(mesh_data, model_name)
    if not part_name:
        return None
    for hint in mesh_data.cmp_transform_hints:
        if hint.part_name != part_name:
            continue
        if hint.combined_rotation_rows_xyz is not None:
            return hint.combined_rotation_rows_xyz
        if hint.normalized_rotation_rows_xyz is not None:
            return hint.normalized_rotation_rows_xyz
    return None


def _apply_rotation_rows(
    value: tuple[float, float, float],
    rows: tuple[tuple[float, float, float], ...],
) -> tuple[float, float, float]:
    x, y, z = value
    row0, row1, row2 = rows
    return (
        row0[0] * x + row0[1] * y + row0[2] * z,
        row1[0] * x + row1[1] * y + row1[2] * z,
        row2[0] * x + row2[1] * y + row2[2] * z,
    )


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
