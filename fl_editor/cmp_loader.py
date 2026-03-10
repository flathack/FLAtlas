from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from struct import Struct

from fl_editor.freelancer_mesh_data import FreelancerMeshData, FreelancerMeshPart, FreelancerUtfNode


UTF_HEADER = Struct("<4s13I")
UTF_MAGIC = b"UTF "
UTF_NODE_ENTRY_SIZE = 44


@dataclass(frozen=True)
class UtfFileHeader:
    magic: bytes
    version: int
    node_block_offset: int
    node_block_size: int
    unknown0: int
    node_entry_size: int
    names_offset: int
    names_allocated_size: int
    names_used_size: int
    data_offset: int
    unknown1: int
    unknown2: int
    timestamp_low: int
    timestamp_high: int

    @property
    def node_count(self) -> int:
        if self.node_entry_size <= 0:
            return 0
        return self.node_block_size // self.node_entry_size


def parse_utf_header(raw: bytes) -> UtfFileHeader:
    if len(raw) < UTF_HEADER.size:
        raise ValueError("UTF header is truncated")
    unpacked = UTF_HEADER.unpack(raw[: UTF_HEADER.size])
    header = UtfFileHeader(*unpacked)
    if header.magic != UTF_MAGIC:
        raise ValueError("Unsupported Freelancer native model header")
    return header


def load_native_freelancer_model(path: str | Path) -> FreelancerMeshData:
    model_path = Path(path)
    ext = model_path.suffix.lower()
    if ext not in {".cmp", ".3db"}:
        raise ValueError(f"Unsupported Freelancer native extension: {ext or '<none>'}")

    raw = model_path.read_bytes()
    header = parse_utf_header(raw)
    names = _decode_string_table(raw, header)
    unique_names = tuple(dict.fromkeys(names))
    nodes = _parse_utf_nodes(raw, header)
    part_names = _build_parts_from_nodes(nodes)
    vmesh_references = tuple(
        node.name for node in nodes if node.name.lower().endswith(".vms")
    )
    warnings: list[str] = []
    if header.node_entry_size != UTF_NODE_ENTRY_SIZE:
        warnings.append(
            f"Unexpected UTF node entry size: {header.node_entry_size} (expected {UTF_NODE_ENTRY_SIZE})"
        )
    if not vmesh_references:
        warnings.append("No VMesh references detected in UTF string table")

    return FreelancerMeshData(
        source_path=model_path,
        format=ext.lstrip("."),
        node_count=header.node_count,
        node_entry_size=header.node_entry_size,
        nodes=nodes,
        parts=part_names,
        node_names=unique_names,
        vmesh_references=vmesh_references,
        warnings=tuple(warnings),
    )


def build_native_model_info_text(mesh_data: FreelancerMeshData) -> str:
    rows = build_native_model_debug_rows(mesh_data)
    lines = [
        f"Freelancer native model detected ({mesh_data.format}). Native Qt3D mesh rendering is still pending."
    ]
    lines.extend(f"{label}: {value}" for label, value in rows[1:])
    if mesh_data.parts:
        lines.append("Part sample: " + ", ".join(part.name for part in mesh_data.parts[:3]))
    if mesh_data.warnings:
        lines.extend(f"Warning: {warning}" for warning in mesh_data.warnings)
    return "\n".join(lines) + "\n\n"


def build_native_model_debug_rows(mesh_data: FreelancerMeshData) -> tuple[tuple[str, str], ...]:
    summary = mesh_data.summary
    return (
        ("File", str(mesh_data.source_path)),
        ("Format", mesh_data.format),
        ("UTF nodes", str(summary.node_count)),
        ("Named entries", str(summary.names_count)),
        ("Detected parts", str(summary.part_count)),
        ("Referenced VMeshes", str(summary.vmesh_reference_count)),
        ("Data nodes", str(summary.data_node_count)),
    )


def _decode_string_table(raw: bytes, header: UtfFileHeader) -> tuple[str, ...]:
    start = header.names_offset
    if start < 0 or start >= len(raw):
        return ()
    names_size = max(header.names_allocated_size, header.names_used_size)
    if names_size <= 0:
        return ()
    chunk = raw[start : min(start + names_size, len(raw))]
    values: list[str] = []
    for piece in chunk.split(b"\x00"):
        if not piece:
            continue
        text = piece.decode("latin-1", errors="ignore").strip()
        if text:
            values.append(text)
    return tuple(values)


def _parse_utf_nodes(raw: bytes, header: UtfFileHeader) -> tuple[FreelancerUtfNode, ...]:
    nodes: list[FreelancerUtfNode] = []
    name_lookup = _string_offset_lookup(raw, header)
    node_struct = Struct("<11I")
    for index in range(header.node_count):
        base = header.node_block_offset + index * header.node_entry_size
        chunk = raw[base : base + UTF_NODE_ENTRY_SIZE]
        if len(chunk) < UTF_NODE_ENTRY_SIZE:
            break
        _child_or_aux_offset, name_offset, flags, _reserved, peer_offset, data_offset, allocated_size, used_size, *_ = (
            node_struct.unpack(chunk)
        )
        name = name_lookup.get(name_offset, f"<name@0x{name_offset:x}>")
        nodes.append(
            FreelancerUtfNode(
                name=name,
                parent_name=None,
                flags=flags,
                peer_offset=peer_offset,
                data_offset=data_offset if (flags & 0x80) else None,
                allocated_size=allocated_size if (flags & 0x80) else None,
                used_size=used_size if (flags & 0x80) else None,
            )
        )
    return tuple(nodes)


def _build_parts_from_nodes(nodes: tuple[FreelancerUtfNode, ...]) -> tuple[FreelancerMeshPart, ...]:
    seen: set[str] = set()
    parts: list[FreelancerMeshPart] = []
    for index, node in enumerate(nodes):
        if not node.name.startswith("Part_") or node.name in seen:
            continue
        seen.add(node.name)
        source_name = None
        for follower in nodes[index + 1 : index + 4]:
            if follower.name.lower().endswith(".vms"):
                source_name = follower.name
                break
            if follower.name.startswith("Part_"):
                break
        parts.append(FreelancerMeshPart(name=node.name, source_name=source_name))
    return tuple(parts)


def _string_offset_lookup(raw: bytes, header: UtfFileHeader) -> dict[int, str]:
    start = header.names_offset
    if start < 0 or start >= len(raw):
        return {}
    names_size = max(header.names_allocated_size, header.names_used_size)
    if names_size <= 0:
        return {}
    chunk = raw[start : min(start + names_size, len(raw))]
    lookup: dict[int, str] = {}
    offset = 0
    for piece in chunk.split(b"\x00"):
        if piece:
            text = piece.decode("latin-1", errors="ignore").strip()
            if text:
                lookup[offset] = text
        offset += len(piece) + 1
    return lookup
