from __future__ import annotations

import math
import struct
from dataclasses import dataclass

from .freelancer_mesh_data import (
    FreelancerMeshData,
    FreelancerPreviewBufferSlice,
)


MAX_PREVIEW_ABS_COORD = 1_000_000.0


@dataclass(frozen=True)
class NativePreviewGeometry:
    positions: tuple[tuple[float, float, float], ...]
    indices: tuple[int, ...]
    vertex_stride: int
    index_size: int
    confidence: str


def decode_native_preview_geometry(mesh_data: FreelancerMeshData) -> NativePreviewGeometry | None:
    for buffer_slice in mesh_data.preview_buffer_slices:
        if buffer_slice.confidence not in {"exact", "tight"}:
            continue
        geometry = _decode_geometry_from_slice(mesh_data, buffer_slice)
        if geometry is not None:
            return geometry
    return None


def _decode_geometry_from_slice(
    mesh_data: FreelancerMeshData,
    buffer_slice: FreelancerPreviewBufferSlice,
) -> NativePreviewGeometry | None:
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

    return NativePreviewGeometry(
        positions=positions,
        indices=indices,
        vertex_stride=buffer_slice.vertex_stride,
        index_size=buffer_slice.index_size,
        confidence=buffer_slice.confidence,
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
