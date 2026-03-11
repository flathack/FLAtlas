from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FreelancerBounds:
    min_xyz: tuple[float, float, float]
    max_xyz: tuple[float, float, float]
    radius: float | None = None


@dataclass(frozen=True)
class FreelancerMeshPart:
    name: str
    cmp_index: int | None = None
    source_name: str | None = None
    file_name: str | None = None
    object_name: str | None = None
    vertex_count: int | None = None
    triangle_count: int | None = None


@dataclass(frozen=True)
class FreelancerUtfNode:
    name: str
    parent_name: str | None
    flags: int
    peer_offset: int
    child_offset: int = 0
    data_offset: int | None = None
    allocated_size: int | None = None
    used_size: int | None = None
    path: str | None = None

    @property
    def is_data_node(self) -> bool:
        return bool(self.flags & 0x80)


@dataclass(frozen=True)
class FreelancerVMeshRef:
    mesh_data_reference: int
    vertex_start: int
    vertex_count: int
    index_start: int
    index_count: int
    group_start: int
    group_count: int
    parent_name: str | None
    node_path: str | None
    model_name: str | None
    level_name: str | None
    bounds: FreelancerBounds


@dataclass(frozen=True)
class FreelancerVMeshDataBlock:
    source_name: str | None
    node_path: str | None
    data_offset: int
    used_size: int
    sha1: str
    header_hex: str
    header_u32: tuple[int, ...] = ()
    header_u16: tuple[int, ...] = ()


@dataclass(frozen=True)
class FreelancerModelNode:
    model_name: str
    level_names: tuple[str, ...]
    vmesh_ref_count: int
    matched_part_name: str | None = None
    source_names: tuple[str, ...] = ()
    bounds: FreelancerBounds | None = None


@dataclass(frozen=True)
class FreelancerPreviewMeshNode:
    model_name: str
    matched_part_name: str | None
    level_names: tuple[str, ...]
    source_names: tuple[str, ...]
    vmesh_ref_count: int
    vmesh_data_block_count: int
    total_vmesh_data_bytes: int
    bounds: FreelancerBounds | None = None


@dataclass(frozen=True)
class FreelancerPreviewMeshBinding:
    model_name: str
    level_name: str | None
    source_names: tuple[str, ...]
    vmesh_ref_count: int
    vertex_count: int
    index_count: int
    triangle_count: int
    group_count: int
    vmesh_data_block_count: int
    total_vmesh_data_bytes: int
    bounds: FreelancerBounds | None = None


@dataclass(frozen=True)
class FreelancerPreviewGeometryCandidate:
    model_name: str
    level_name: str | None
    source_names: tuple[str, ...]
    block_sha1s: tuple[str, ...]
    vmesh_ref_count: int
    vertex_count: int
    index_count: int
    triangle_count: int
    group_count: int
    vmesh_data_block_count: int
    total_vmesh_data_bytes: int
    decode_stage: str
    ready_for_native_render: bool
    bounds: FreelancerBounds | None = None


@dataclass(frozen=True)
class FreelancerPreviewSubmesh:
    model_name: str
    level_name: str | None
    source_names: tuple[str, ...]
    vertex_start: int
    vertex_count: int
    index_start: int
    index_count: int
    group_start: int
    group_count: int
    triangle_count: int
    bounds: FreelancerBounds | None = None


@dataclass(frozen=True)
class FreelancerPreviewGeometrySource:
    model_name: str
    level_name: str | None
    source_names: tuple[str, ...]
    mesh_data_reference: int
    matched_block_index: int | None
    matched_block_sha1: str | None
    resolved: bool
    resolution_hint: str
    vertex_start: int
    vertex_count: int
    index_start: int
    index_count: int
    group_start: int
    group_count: int
    triangle_count: int
    bounds: FreelancerBounds | None = None


@dataclass(frozen=True)
class FreelancerPreviewLayoutGuess:
    model_name: str
    level_name: str | None
    mesh_data_reference: int
    matched_block_index: int | None
    resolved: bool
    header_size: int | None
    vertex_stride: int | None
    index_size: int | None
    vertex_bytes: int | None
    index_bytes: int | None
    remaining_bytes: int | None
    confidence: str


@dataclass(frozen=True)
class FreelancerPreviewBufferSlice:
    model_name: str
    level_name: str | None
    mesh_data_reference: int
    matched_block_index: int | None
    group_start: int
    group_count: int
    header_offset: int
    header_size: int
    vertex_offset: int
    vertex_bytes: int
    index_offset: int
    index_bytes: int
    remaining_offset: int
    remaining_bytes: int
    vertex_stride: int
    index_size: int
    confidence: str


@dataclass(frozen=True)
class FreelancerCmpFixRecord:
    part_name: str
    part_index: int | None
    record_index: int
    record_size: int
    float_count: int
    row_width: int
    row_count: int
    rows: tuple[tuple[float, ...], ...]
    first_f32: tuple[float, ...]
    first_u32: tuple[int, ...]


@dataclass(frozen=True)
class FreelancerCmpTransformHint:
    part_name: str
    part_index: int | None
    record_index: int
    row_width: int
    row_count: int
    translation_xyz: tuple[float, float, float] | None
    leading_vector_xyz: tuple[float, float, float] | None
    normalized_forward_xyz: tuple[float, float, float] | None
    normalized_rotation_rows_xyz: tuple[tuple[float, float, float], ...] | None
    translation_magnitude: float | None


@dataclass(frozen=True)
class FreelancerMaterialReference:
    kind: str
    value: str
    node_name: str | None = None
    node_path: str | None = None


@dataclass(frozen=True)
class FreelancerPreviewMaterialBinding:
    model_name: str
    level_name: str | None
    part_name: str | None
    source_names: tuple[str, ...]
    texture_value: str | None
    material_value: str | None
    reference_node_path: str | None
    match_hint: str


@dataclass(frozen=True)
class FreelancerMeshSummary:
    format: str
    node_count: int
    names_count: int
    part_count: int
    vmesh_reference_count: int
    model_node_count: int
    data_node_count: int
    has_bounds: bool


@dataclass(frozen=True)
class FreelancerMeshData:
    source_path: Path
    format: str
    node_count: int
    node_entry_size: int
    nodes: tuple[FreelancerUtfNode, ...]
    parts: tuple[FreelancerMeshPart, ...]
    node_names: tuple[str, ...]
    vmesh_references: tuple[str, ...]
    vmesh_refs: tuple[FreelancerVMeshRef, ...]
    vmesh_data_blocks: tuple[FreelancerVMeshDataBlock, ...]
    model_nodes: tuple[FreelancerModelNode, ...]
    preview_nodes: tuple[FreelancerPreviewMeshNode, ...]
    preview_mesh_bindings: tuple[FreelancerPreviewMeshBinding, ...]
    preview_geometry_candidates: tuple[FreelancerPreviewGeometryCandidate, ...]
    preview_submeshes: tuple[FreelancerPreviewSubmesh, ...]
    preview_geometry_sources: tuple[FreelancerPreviewGeometrySource, ...]
    preview_layout_guesses: tuple[FreelancerPreviewLayoutGuess, ...]
    preview_buffer_slices: tuple[FreelancerPreviewBufferSlice, ...]
    cmp_fix_records: tuple[FreelancerCmpFixRecord, ...]
    cmp_transform_hints: tuple[FreelancerCmpTransformHint, ...]
    material_references: tuple[FreelancerMaterialReference, ...]
    preview_material_bindings: tuple[FreelancerPreviewMaterialBinding, ...]
    bounds: FreelancerBounds | None = None
    warnings: tuple[str, ...] = ()

    @property
    def summary(self) -> FreelancerMeshSummary:
        return FreelancerMeshSummary(
            format=self.format,
            node_count=self.node_count,
            names_count=len(self.node_names),
            part_count=len(self.parts),
            vmesh_reference_count=len(self.vmesh_references),
            model_node_count=len(self.model_nodes),
            data_node_count=sum(1 for node in self.nodes if node.is_data_node),
            has_bounds=self.bounds is not None,
        )
