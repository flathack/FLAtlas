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
    bounds: FreelancerBounds


@dataclass(frozen=True)
class FreelancerMeshSummary:
    format: str
    node_count: int
    names_count: int
    part_count: int
    vmesh_reference_count: int
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
            data_node_count=sum(1 for node in self.nodes if node.is_data_node),
            has_bounds=self.bounds is not None,
        )
