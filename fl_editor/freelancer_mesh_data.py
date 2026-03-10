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
    vertex_count: int | None = None
    triangle_count: int | None = None


@dataclass(frozen=True)
class FreelancerMeshSummary:
    format: str
    node_count: int
    names_count: int
    part_count: int
    vmesh_reference_count: int


@dataclass(frozen=True)
class FreelancerMeshData:
    source_path: Path
    format: str
    node_count: int
    node_entry_size: int
    parts: tuple[FreelancerMeshPart, ...]
    node_names: tuple[str, ...]
    vmesh_references: tuple[str, ...]
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
        )
