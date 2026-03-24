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
    tex_coords: tuple[tuple[float, float], ...] = ()


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
    tex_coords: tuple[tuple[float, float], ...] = ()


def decode_native_preview_geometries(mesh_data: FreelancerMeshData) -> tuple[NativePreviewGeometry, ...]:
    raw_geometries: list[_RawNativePreviewGeometry] = []
    handled_keys: set[tuple[str, str | None, int, int]] = set()
    for plan in mesh_data.structured_decode_plans:
        geometry = _decode_geometry_from_structured_plan(mesh_data, plan)
        if geometry is None:
            continue
        raw_geometries.append(geometry)
        handled_keys.add((geometry.model_name, geometry.level_name, geometry.group_start, geometry.group_count))
    for source in mesh_data.preview_geometry_sources:
        key = (source.model_name, source.level_name, source.group_start, source.group_count)
        if key in handled_keys:
            continue
        geometry = _decode_geometry_from_embedded_vmesh_data(mesh_data, source)
        if geometry is None:
            continue
        raw_geometries.append(geometry)
        handled_keys.add(key)
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
                tex_coords=geometry.tex_coords,
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
        candidates: list[tuple[float, _RawNativePreviewGeometry]] = []
        if matching_slice is not None:
            geometry = _decode_geometry_from_slice(mesh_data, matching_slice)
            if geometry is not None:
                candidates.append((_structured_geometry_score(geometry, source.bounds), geometry))
            structured_geometry = _decode_geometry_from_structured_single_block(mesh_data, plan, matching_slice)
            if structured_geometry is not None:
                candidates.append((_structured_geometry_score(structured_geometry, source.bounds), structured_geometry))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]
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

    exact_geometry = _decode_geometry_from_structured_single_block_mesh_headers(
        mesh_data=mesh_data,
        plan=plan,
        source=source,
        block_bytes=block_bytes,
    )
    if exact_geometry is not None:
        return exact_geometry

    candidates: list[tuple[float, _RawNativePreviewGeometry]] = []

    direct_geometry = _decode_geometry_from_structured_single_block_direct(
        mesh_data=mesh_data,
        source=source,
        block_bytes=block_bytes,
        buffer_slice=buffer_slice,
    )
    if direct_geometry is not None:
        candidates.append((_structured_geometry_score(direct_geometry, source.bounds), direct_geometry))

    index_first_geometry = _decode_geometry_from_structured_single_block_index_first(
        mesh_data=mesh_data,
        plan=plan,
        source=source,
        block_bytes=block_bytes,
        default_stride=buffer_slice.vertex_stride,
    )
    if index_first_geometry is not None:
        candidates.append((_structured_geometry_score(index_first_geometry, source.bounds), index_first_geometry))

    full_pool_geometry = _decode_geometry_from_structured_single_block_full_pool_search(
        mesh_data=mesh_data,
        plan=plan,
        source=source,
        block_bytes=block_bytes,
        default_stride=buffer_slice.vertex_stride,
    )
    if full_pool_geometry is not None:
        candidates.append((_structured_geometry_score(full_pool_geometry, source.bounds), full_pool_geometry))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _decode_geometry_from_structured_single_block_mesh_headers(
    *,
    mesh_data: FreelancerMeshData,
    plan: FreelancerStructuredDecodePlan,
    source,
    block_bytes: bytes,
) -> _RawNativePreviewGeometry | None:
    if len(block_bytes) < 16:
        return None
    if plan.mesh_header_count is None or plan.mesh_header_count <= 0:
        return None
    if source.group_count <= 0 or source.vertex_count <= 0 or source.index_count <= 0:
        return None

    pos = 0
    pos += 8
    mesh_count = struct.unpack_from("<H", block_bytes, pos)[0]
    pos += 2
    num_ref_vertices = struct.unpack_from("<H", block_bytes, pos)[0]
    pos += 2
    flexible_vertex_format = struct.unpack_from("<H", block_bytes, pos)[0]
    pos += 2
    vertex_count = struct.unpack_from("<H", block_bytes, pos)[0]
    pos += 2

    if mesh_count <= 0 or vertex_count <= 0:
        return None
    if mesh_count != int(plan.mesh_header_count):
        return None
    if source.group_start < 0 or source.group_start + source.group_count > mesh_count:
        return None

    mesh_headers: list[tuple[int, int, int, int]] = []
    triangle_start = 0
    for _ in range(mesh_count):
        if pos + 12 > len(block_bytes):
            return None
        pos += 4
        start_vertex, end_vertex, num_ref_indices, _padding = struct.unpack_from("<4H", block_bytes, pos)
        pos += 8
        mesh_headers.append((start_vertex, end_vertex, num_ref_indices, triangle_start))
        triangle_start += int(num_ref_indices)

    triangle_count = num_ref_vertices // 3
    triangles: list[tuple[int, int, int]] = []
    for _ in range(triangle_count):
        if pos + 6 > len(block_bytes):
            return None
        vertex1, vertex3, vertex2 = struct.unpack_from("<3H", block_bytes, pos)
        pos += 6
        triangles.append((int(vertex1), int(vertex2), int(vertex3)))

    vertices, all_uvs = _decode_structured_single_block_vertices(
        block_bytes[pos:],
        vertex_count=vertex_count,
        flexible_vertex_format=flexible_vertex_format,
    )
    if not vertices:
        return None

    positions: list[tuple[float, float, float]] = []
    tex_coords: list[tuple[float, float]] = []
    indices: list[int] = []
    expected_vertex_total = 0
    expected_index_total = 0
    for mesh_index in range(source.group_start, source.group_start + source.group_count):
        start_vertex, end_vertex, num_ref_indices, triangle_start = mesh_headers[mesh_index]
        header_vertex_count = (end_vertex - start_vertex) + 1
        if header_vertex_count <= 0:
            return None
        vertex_begin = int(source.vertex_start) + start_vertex
        vertex_end = int(source.vertex_start) + end_vertex + 1
        if vertex_begin < 0 or vertex_end > len(vertices):
            return None
        mesh_positions = vertices[vertex_begin:vertex_end]
        if all_uvs:
            mesh_uvs = all_uvs[vertex_begin:vertex_end]
        triangle_begin = triangle_start // 3
        triangle_end = (triangle_start + num_ref_indices) // 3
        if triangle_begin < 0 or triangle_end > len(triangles):
            return None
        local_offset = len(positions)
        positions.extend(mesh_positions)
        if all_uvs:
            tex_coords.extend(mesh_uvs)
        for vertex1, vertex2, vertex3 in triangles[triangle_begin:triangle_end]:
            if max(vertex1, vertex2, vertex3) >= header_vertex_count:
                return None
            indices.extend((vertex1 + local_offset, vertex2 + local_offset, vertex3 + local_offset))
        expected_vertex_total += header_vertex_count
        expected_index_total += num_ref_indices

    if expected_vertex_total != int(source.vertex_count):
        return None
    if expected_index_total != int(source.index_count):
        return None

    return _build_raw_geometry(
        mesh_data=mesh_data,
        model_name=source.model_name,
        level_name=source.level_name,
        group_start=source.group_start,
        group_count=source.group_count,
        positions=tuple(positions),
        indices=tuple(indices),
        vertex_stride=_structured_single_block_vertex_stride(flexible_vertex_format),
        index_size=2,
        confidence="structured-single-block",
        tex_coords=tuple(tex_coords),
    )


def _decode_structured_single_block_vertices(
    raw: bytes,
    *,
    vertex_count: int,
    flexible_vertex_format: int,
) -> tuple[tuple[tuple[float, float, float], ...], tuple[tuple[float, float], ...]]:
    """Return (positions, tex_coords).  tex_coords may be empty."""
    stride = _structured_single_block_vertex_stride(flexible_vertex_format)
    if stride <= 0:
        return (), ()
    total_bytes = vertex_count * stride
    if total_bytes > len(raw):
        return (), ()
    positions: list[tuple[float, float, float]] = []
    tex_coords: list[tuple[float, float]] = []
    tex_coord_bits = flexible_vertex_format & 0x700
    has_uvs = tex_coord_bits >= 0x100
    pos = 0
    for _ in range(vertex_count):
        x, y, z = struct.unpack_from("<3f", raw, pos)
        pos += 12
        if not all(math.isfinite(value) for value in (x, y, z)):
            return (), ()
        if max(abs(x), abs(y), abs(z)) > MAX_PREVIEW_ABS_COORD:
            return (), ()
        positions.append((x, y, z))
        uv_offset = pos
        if flexible_vertex_format & 0x10:
            uv_offset += 12
            pos += 12
        if flexible_vertex_format & 0x40:
            uv_offset += 4
            pos += 4
        if has_uvs:
            u, v = struct.unpack_from("<2f", raw, uv_offset)
            tex_coords.append((u, v))
        if tex_coord_bits == 0x500:
            pos += 40
        elif tex_coord_bits == 0x400:
            pos += 32
        elif tex_coord_bits == 0x200:
            pos += 16
        elif tex_coord_bits == 0x100:
            pos += 8
    return tuple(positions), tuple(tex_coords) if has_uvs else ()


def _structured_single_block_vertex_stride(flexible_vertex_format: int) -> int:
    stride = 12
    if flexible_vertex_format & 0x10:
        stride += 12
    if flexible_vertex_format & 0x40:
        stride += 4
    tex_coord_bits = flexible_vertex_format & 0x700
    if tex_coord_bits == 0x500:
        stride += 40
    elif tex_coord_bits == 0x400:
        stride += 32
    elif tex_coord_bits == 0x200:
        stride += 16
    elif tex_coord_bits == 0x100:
        stride += 8
    return stride


def _decode_geometry_from_structured_single_block_direct(
    *,
    mesh_data: FreelancerMeshData,
    source,
    block_bytes: bytes,
    buffer_slice: FreelancerPreviewBufferSlice,
) -> _RawNativePreviewGeometry | None:
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

    candidate_offsets: list[int] = [buffer_slice.index_offset, buffer_slice.header_size]
    candidate_offsets.append(source.index_start * 2)
    candidate_offsets.append(source.index_start * 4)

    candidates: list[tuple[float, _RawNativePreviewGeometry]] = []
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
            geometry = _build_raw_geometry(
                mesh_data=mesh_data,
                model_name=buffer_slice.model_name,
                level_name=buffer_slice.level_name,
                group_start=source.group_start,
                group_count=source.group_count,
                positions=positions,
                indices=candidate_indices,
                vertex_stride=buffer_slice.vertex_stride,
                index_size=candidate_index_size,
                confidence="structured-single-block",
            )
            candidates.append((_structured_geometry_score(geometry, source.bounds), geometry))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _decode_geometry_from_structured_single_block_index_first(
    *,
    mesh_data: FreelancerMeshData,
    plan: FreelancerStructuredDecodePlan,
    source,
    block_bytes: bytes,
    default_stride: int,
) -> _RawNativePreviewGeometry | None:
    if plan.mesh_header_count is None or plan.mesh_header_count <= 0:
        return None
    header_size = 16 + (int(plan.mesh_header_count) * 12)
    if header_size <= 0 or header_size >= len(block_bytes):
        return None
    if source.index_count <= 0 or source.vertex_count <= 0:
        return None

    candidate_strides: list[int] = []
    for stride in (int(plan.stream_stride_hint or 0), int(default_stride or 0), 40, 36, 32, 24, 20, 16, 12):
        if stride >= 12 and stride not in candidate_strides:
            candidate_strides.append(stride)

    best: tuple[float, _RawNativePreviewGeometry] | None = None
    expected_bounds = source.bounds
    total_vertex_count = int(plan.mesh_header_end_vertex or 0)
    if total_vertex_count <= 0:
        return None
    subset_start = int(source.vertex_start)
    subset_end = subset_start + int(source.vertex_count)
    if subset_start < 0 or subset_end > total_vertex_count:
        return None

    for index_size in (2, 4):
        indices_offset = header_size + (source.index_start * index_size)
        indices_end = indices_offset + (source.index_count * index_size)
        if indices_end > len(block_bytes):
            continue
        raw_indices = _decode_indices(
            block_bytes[indices_offset:indices_end],
            index_size,
            max(total_vertex_count, int(plan.mesh_header_num_ref_vertices or total_vertex_count)),
        )
        if not raw_indices:
            continue
        if min(raw_indices) < subset_start or max(raw_indices) >= subset_end:
            continue
        local_indices = tuple(index - subset_start for index in raw_indices)
        for stride in candidate_strides:
            vertex_offset = header_size + (int(plan.mesh_header_index_end or 0) * index_size)
            vertex_end = vertex_offset + (total_vertex_count * stride)
            if vertex_end > len(block_bytes):
                continue
            for position_offset in range(0, min(stride - 8, 32) + 1, 4):
                all_positions = _decode_positions_with_offset(
                    block_bytes[vertex_offset:vertex_end],
                    stride,
                    position_offset,
                )
                if not all_positions:
                    continue
                positions = all_positions[subset_start:subset_end]
                if len(positions) != int(source.vertex_count):
                    continue
                geometry = _build_raw_geometry(
                    mesh_data=mesh_data,
                    model_name=source.model_name,
                    level_name=source.level_name,
                    group_start=source.group_start,
                    group_count=source.group_count,
                    positions=positions,
                    indices=local_indices,
                    vertex_stride=stride,
                    index_size=index_size,
                    confidence="structured-single-block",
                )
                score = _structured_geometry_score(geometry, expected_bounds)
                if best is None or score < best[0]:
                    best = (score, geometry)
    return best[1] if best is not None else None


def _decode_geometry_from_structured_single_block_full_pool_search(
    *,
    mesh_data: FreelancerMeshData,
    plan: FreelancerStructuredDecodePlan,
    source,
    block_bytes: bytes,
    default_stride: int,
) -> _RawNativePreviewGeometry | None:
    total_vertex_count = int(plan.mesh_header_end_vertex or 0)
    subset_start = int(source.vertex_start or 0)
    subset_count = int(source.vertex_count or 0)
    subset_end = subset_start + subset_count
    if total_vertex_count <= 0 or subset_count <= 0 or subset_start < 0 or subset_end > total_vertex_count:
        return None

    candidate_strides: list[int] = []
    for stride in (40, int(default_stride or 0), int(plan.stream_stride_hint or 0), 36, 32, 28, 24, 20, 16, 12):
        if stride >= 12 and stride not in candidate_strides:
            candidate_strides.append(stride)

    candidate_headers: list[int] = []
    for header in (
        16,
        16 + (int(plan.mesh_header_count or 0) * 12),
        16 + (int(plan.mesh_header_count or 0) * 16),
        16 + (int(plan.mesh_header_count or 0) * 24),
        60,
        64,
        88,
        112,
    ):
        if 0 <= header < len(block_bytes) and header not in candidate_headers:
            candidate_headers.append(header)

    best: tuple[float, _RawNativePreviewGeometry] | None = None
    for header_size in candidate_headers:
        indices_offset = header_size + (int(source.index_start or 0) * 2)
        indices_end = indices_offset + (int(source.index_count or 0) * 2)
        if indices_end > len(block_bytes):
            continue
        raw_indices = _decode_indices(
            block_bytes[indices_offset:indices_end],
            2,
            subset_count,
        )
        if not raw_indices:
            continue
        for stride in candidate_strides:
            vertex_end = header_size + (total_vertex_count * stride)
            if vertex_end > len(block_bytes):
                continue
            for position_offset in range(0, min(stride - 8, 32) + 1, 4):
                all_positions = _decode_positions_with_offset(
                    block_bytes[header_size:vertex_end],
                    stride,
                    position_offset,
                )
                if not all_positions:
                    continue
                positions = all_positions[subset_start:subset_end]
                if len(positions) != subset_count:
                    continue
                geometry = _build_raw_geometry(
                    mesh_data=mesh_data,
                    model_name=source.model_name,
                    level_name=source.level_name,
                    group_start=source.group_start,
                    group_count=source.group_count,
                    positions=positions,
                    indices=raw_indices,
                    vertex_stride=stride,
                    index_size=2,
                    confidence="structured-single-block",
                )
                score = _structured_geometry_score(geometry, source.bounds)
                if best is None or score < best[0]:
                    best = (score, geometry)
    return best[1] if best is not None else None


def _decode_positions_with_offset(
    raw: bytes,
    stride: int,
    position_offset: int,
) -> tuple[tuple[float, float, float], ...]:
    if position_offset < 0 or position_offset + 12 > stride:
        return ()
    if len(raw) % stride != 0:
        return ()
    positions: list[tuple[float, float, float]] = []
    for offset in range(0, len(raw), stride):
        x, y, z = struct.unpack_from("<3f", raw, offset + position_offset)
        if not all(math.isfinite(value) for value in (x, y, z)):
            return ()
        if max(abs(x), abs(y), abs(z)) > MAX_PREVIEW_ABS_COORD:
            return ()
        positions.append((x, y, z))
    return tuple(positions)


def _structured_geometry_score(
    geometry: _RawNativePreviewGeometry,
    expected_bounds: FreelancerBounds | None,
) -> float:
    unique_positions = len({tuple(round(value, 2) for value in pos) for pos in geometry.positions})
    reused_vertex_ratio = (max(geometry.indices) + 1) / max(len(geometry.positions), 1) if geometry.indices else 0.0
    score = float(len(geometry.positions) - unique_positions)
    score += max(0.0, 0.75 - reused_vertex_ratio) * 100.0
    suspicious_small_vertices = sum(
        1
        for x, y, z in geometry.positions
        if sum(1 for value in (x, y, z) if abs(value) <= 2.0) >= 2
    )
    score += float(suspicious_small_vertices) * 5.0
    degenerate_triangles = sum(
        1
        for index in range(0, len(geometry.indices), 3)
        if index + 2 < len(geometry.indices)
        and len({geometry.indices[index], geometry.indices[index + 1], geometry.indices[index + 2]}) < 3
    )
    score += float(degenerate_triangles) * 50.0
    if expected_bounds is not None:
        expected_span = tuple(
            expected_bounds.max_xyz[index] - expected_bounds.min_xyz[index]
            for index in range(3)
        )
        actual_span = tuple(
            geometry.bounds.max_xyz[index] - geometry.bounds.min_xyz[index]
            for index in range(3)
        )
        expected_center = tuple(
            (expected_bounds.min_xyz[index] + expected_bounds.max_xyz[index]) * 0.5
            for index in range(3)
        )
        actual_center = tuple(
            (geometry.bounds.min_xyz[index] + geometry.bounds.max_xyz[index]) * 0.5
            for index in range(3)
        )
        score += sum(abs(actual_span[index] - expected_span[index]) for index in range(3)) * 0.25
        score += sum(abs(actual_center[index] - expected_center[index]) for index in range(3)) * 0.1
        for index in range(3):
            if expected_span[index] > 50.0 and actual_span[index] < expected_span[index] * 0.1:
                score += 250.0
    return score


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


def _decode_geometry_from_embedded_vmesh_data(
    mesh_data: FreelancerMeshData,
    source,
) -> _RawNativePreviewGeometry | None:
    block_index = source.matched_block_index
    if block_index is None or not (0 <= block_index < len(mesh_data.vmesh_data_blocks)):
        return None
    if source.group_count <= 0 or source.vertex_count <= 0 or source.index_count <= 0:
        return None

    raw = mesh_data.source_path.read_bytes()
    block = mesh_data.vmesh_data_blocks[block_index]
    block_start = block.data_offset
    block_end = block.data_offset + block.used_size
    if block_start < 0 or block_end > len(raw):
        return None
    block_bytes = raw[block_start:block_end]

    candidates: list[tuple[float, _RawNativePreviewGeometry]] = []
    for header_offset, mesh_count, num_ref_vertices, flexible_vertex_format, vertex_count in _find_embedded_vmesh_headers(
        block_bytes=block_bytes,
        source=source,
    ):
        stride = _structured_single_block_vertex_stride(flexible_vertex_format)
        if stride <= 0:
            continue
        total_size = 16 + (mesh_count * 12) + (num_ref_vertices * 2) + (vertex_count * stride)
        absolute_start = block_start + header_offset
        absolute_end = absolute_start + total_size
        if absolute_start < 0 or absolute_end > len(raw):
            continue
        geometry = _decode_geometry_from_vmesh_window(
            mesh_data=mesh_data,
            source=source,
            window_bytes=raw[absolute_start:absolute_end],
            confidence="structured-single-block",
        )
        if geometry is None:
            continue
        candidates.append((_structured_geometry_score(geometry, source.bounds), geometry))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _find_embedded_vmesh_headers(
    *,
    block_bytes: bytes,
    source,
) -> tuple[tuple[int, int, int, int, int], ...]:
    if len(block_bytes) < 16:
        return ()
    min_group_end = int(source.group_start) + int(source.group_count)
    min_index_end = int(source.index_start) + int(source.index_count)
    min_vertex_end = int(source.vertex_start) + int(source.vertex_count)
    matches: list[tuple[int, int, int, int, int]] = []
    seen: set[tuple[int, int, int, int]] = set()
    for offset in range(0, len(block_bytes) - 16 + 1, 2):
        _unknown0, _unknown1, mesh_count, num_ref_vertices, flexible_vertex_format, vertex_count = struct.unpack_from(
            "<II4H",
            block_bytes,
            offset,
        )
        if mesh_count < min_group_end or num_ref_vertices < min_index_end or vertex_count < min_vertex_end:
            continue
        if flexible_vertex_format not in {0x2, 0x12, 0x42, 0x102, 0x112, 0x142, 0x212, 0x412, 0x512}:
            continue
        signature = (mesh_count, num_ref_vertices, flexible_vertex_format, vertex_count)
        if signature in seen:
            continue
        seen.add(signature)
        matches.append((offset, int(mesh_count), int(num_ref_vertices), int(flexible_vertex_format), int(vertex_count)))
    return tuple(matches)


def _decode_geometry_from_vmesh_window(
    *,
    mesh_data: FreelancerMeshData,
    source,
    window_bytes: bytes,
    confidence: str,
) -> _RawNativePreviewGeometry | None:
    if len(window_bytes) < 16:
        return None

    pos = 0
    pos += 8
    mesh_count = struct.unpack_from("<H", window_bytes, pos)[0]
    pos += 2
    num_ref_vertices = struct.unpack_from("<H", window_bytes, pos)[0]
    pos += 2
    flexible_vertex_format = struct.unpack_from("<H", window_bytes, pos)[0]
    pos += 2
    vertex_count = struct.unpack_from("<H", window_bytes, pos)[0]
    pos += 2

    if (
        mesh_count <= 0
        or vertex_count <= 0
        or source.group_start < 0
        or source.group_start + source.group_count > mesh_count
        or source.vertex_start < 0
        or source.vertex_start + source.vertex_count > vertex_count
        or source.index_start < 0
        or source.index_start + source.index_count > num_ref_vertices
    ):
        return None

    mesh_headers: list[tuple[int, int, int, int]] = []
    triangle_start = 0
    for _ in range(mesh_count):
        if pos + 12 > len(window_bytes):
            return None
        pos += 4
        start_vertex, end_vertex, num_ref_indices, _padding = struct.unpack_from("<4H", window_bytes, pos)
        pos += 8
        mesh_headers.append((int(start_vertex), int(end_vertex), int(num_ref_indices), triangle_start))
        triangle_start += int(num_ref_indices)

    triangle_count = num_ref_vertices // 3
    triangles: list[tuple[int, int, int]] = []
    for _ in range(triangle_count):
        if pos + 6 > len(window_bytes):
            return None
        vertex1, vertex3, vertex2 = struct.unpack_from("<3H", window_bytes, pos)
        pos += 6
        triangles.append((int(vertex1), int(vertex2), int(vertex3)))

    vertices, all_uvs = _decode_structured_single_block_vertices(
        window_bytes[pos:],
        vertex_count=vertex_count,
        flexible_vertex_format=flexible_vertex_format,
    )
    if not vertices:
        return None

    positions: list[tuple[float, float, float]] = []
    tex_coords: list[tuple[float, float]] = []
    indices: list[int] = []
    expected_vertex_total = 0
    expected_index_total = 0
    for mesh_index in range(source.group_start, source.group_start + source.group_count):
        start_vertex, end_vertex, num_ref_indices, triangle_start = mesh_headers[mesh_index]
        header_vertex_count = (end_vertex - start_vertex) + 1
        if header_vertex_count <= 0:
            return None
        vertex_begin = int(source.vertex_start) + start_vertex
        vertex_end = int(source.vertex_start) + end_vertex + 1
        if vertex_begin < 0 or vertex_end > len(vertices):
            return None
        mesh_positions = vertices[vertex_begin:vertex_end]
        if all_uvs:
            mesh_uvs = all_uvs[vertex_begin:vertex_end]
        triangle_begin = triangle_start // 3
        triangle_end = (triangle_start + num_ref_indices) // 3
        if triangle_begin < 0 or triangle_end > len(triangles):
            return None
        local_offset = len(positions)
        positions.extend(mesh_positions)
        if all_uvs:
            tex_coords.extend(mesh_uvs)
        for vertex1, vertex2, vertex3 in triangles[triangle_begin:triangle_end]:
            if max(vertex1, vertex2, vertex3) >= header_vertex_count:
                return None
            indices.extend((vertex1 + local_offset, vertex2 + local_offset, vertex3 + local_offset))
        expected_vertex_total += header_vertex_count
        expected_index_total += num_ref_indices

    if expected_vertex_total != int(source.vertex_count):
        return None
    if expected_index_total != int(source.index_count):
        return None

    return _build_raw_geometry(
        mesh_data=mesh_data,
        model_name=source.model_name,
        level_name=source.level_name,
        group_start=source.group_start,
        group_count=source.group_count,
        positions=tuple(positions),
        indices=tuple(indices),
        vertex_stride=_structured_single_block_vertex_stride(flexible_vertex_format),
        index_size=2,
        confidence=confidence,
        tex_coords=tuple(tex_coords),
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
    tex_coords: tuple[tuple[float, float], ...] = (),
) -> _RawNativePreviewGeometry:
    rotation_rows = _rotation_rows_override_for_geometry(mesh_data, model_name, positions)
    if rotation_rows is None:
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
        tex_coords=tex_coords,
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


def _rotation_rows_override_for_geometry(
    mesh_data: FreelancerMeshData,
    model_name: str,
    positions: tuple[tuple[float, float, float], ...],
) -> tuple[tuple[float, float, float], ...] | None:
    part_name = _part_name_for_model(mesh_data, model_name)
    if not part_name:
        return None
    lowered = part_name.lower()
    if "door" not in lowered:
        return None
    hint_by_name = {hint.part_name: hint for hint in mesh_data.cmp_transform_hints}
    door_hint = hint_by_name.get(part_name)
    if door_hint is None or door_hint.combined_translation_xyz is None:
        return None
    dock_part_name = part_name.replace("door", "dock").replace("Door", "Dock")
    dock_hint = hint_by_name.get(dock_part_name)
    if dock_hint is None or dock_hint.combined_translation_xyz is None:
        return None
    local_axis = _thinnest_local_axis(positions)
    if local_axis is None:
        return None
    dock_to_door = _normalize_vector(
        (
            float(door_hint.combined_translation_xyz[0] - dock_hint.combined_translation_xyz[0]),
            float(door_hint.combined_translation_xyz[1] - dock_hint.combined_translation_xyz[1]),
            float(door_hint.combined_translation_xyz[2] - dock_hint.combined_translation_xyz[2]),
        )
    )
    if dock_to_door is None:
        return None

    candidates: list[tuple[int, tuple[tuple[float, float, float], ...]]] = []
    if door_hint.combined_rotation_rows_xyz is not None:
        combined = tuple(tuple(float(v) for v in row) for row in door_hint.combined_rotation_rows_xyz)
        candidates.append((0, combined))
        candidates.append((1, tuple(zip(*combined))))
    if door_hint.normalized_rotation_rows_xyz is not None:
        local = tuple(tuple(float(v) for v in row) for row in door_hint.normalized_rotation_rows_xyz)
        candidates.append((2, local))
        candidates.append((3, tuple(zip(*local))))
    if not candidates:
        return None

    best_rows: tuple[tuple[float, float, float], ...] | None = None
    best_score: tuple[float, int] | None = None
    for rank, rows in candidates:
        normal = _normalize_vector(_apply_rotation_rows(local_axis, rows))
        if normal is None:
            continue
        score = (abs(_dot(normal, dock_to_door)), -rank)
        if best_score is None or score > best_score:
            best_score = score
            best_rows = rows
    return best_rows


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


def _thinnest_local_axis(
    positions: tuple[tuple[float, float, float], ...],
) -> tuple[float, float, float] | None:
    if not positions:
        return None
    spans = []
    for index in range(3):
        values = [pos[index] for pos in positions]
        spans.append(max(values) - min(values))
    axis_index = min(range(3), key=lambda idx: spans[idx])
    if spans[axis_index] <= 1e-9:
        axis_index = min(range(3), key=lambda idx: (spans[idx], idx))
    if axis_index == 0:
        return (1.0, 0.0, 0.0)
    if axis_index == 1:
        return (0.0, 1.0, 0.0)
    return (0.0, 0.0, 1.0)


def _normalize_vector(
    value: tuple[float, float, float],
) -> tuple[float, float, float] | None:
    length = math.sqrt(_dot(value, value))
    if length <= 1e-9:
        return None
    return (value[0] / length, value[1] / length, value[2] / length)


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
