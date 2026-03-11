from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from struct import Struct

from fl_editor.freelancer_mesh_data import (
    FreelancerBounds,
    FreelancerMeshData,
    FreelancerModelNode,
    FreelancerMeshPart,
    FreelancerPreviewMeshNode,
    FreelancerUtfNode,
    FreelancerVMeshDataBlock,
    FreelancerVMeshRef,
)


UTF_HEADER = Struct("<4s13I")
VMESH_REF = Struct("<IIHHHHHH10f")
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
    part_names = _build_parts_from_nodes(nodes, raw)
    vmesh_refs = _parse_vmesh_refs(nodes, raw)
    vmesh_data_blocks = _parse_vmesh_data_blocks(nodes)
    model_nodes = _build_model_nodes(vmesh_refs, part_names)
    preview_nodes = _build_preview_nodes(model_nodes, vmesh_data_blocks)
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
        vmesh_refs=vmesh_refs,
        vmesh_data_blocks=vmesh_data_blocks,
        model_nodes=model_nodes,
        preview_nodes=preview_nodes,
        bounds=_aggregate_bounds(tuple(vref.bounds for vref in vmesh_refs)),
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
        ("Model nodes", str(summary.model_node_count)),
        ("Data nodes", str(summary.data_node_count)),
        ("Has bounds", "yes" if summary.has_bounds else "no"),
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
    name_lookup = _string_offset_lookup(raw, header)
    node_struct = Struct("<11I")
    parsed_nodes: list[dict[str, int | str | None]] = []
    for index in range(header.node_count):
        base = header.node_block_offset + index * header.node_entry_size
        chunk = raw[base : base + UTF_NODE_ENTRY_SIZE]
        if len(chunk) < UTF_NODE_ENTRY_SIZE:
            break
        peer_offset, name_offset, flags, _reserved, child_or_data_offset, allocated_size, used_size, _timestamp, *_ = (
            node_struct.unpack(chunk)
        )
        name = name_lookup.get(name_offset, f"<name@0x{name_offset:x}>")
        parsed_nodes.append(
            {
                "name": name,
                "flags": flags,
                "peer_offset": peer_offset,
                "child_offset": child_or_data_offset if not (flags & 0x80) else 0,
                "data_offset": child_or_data_offset if (flags & 0x80) else None,
                "allocated_size": allocated_size if (flags & 0x80) else None,
                "used_size": used_size if (flags & 0x80) else None,
            }
        )
    offset_to_index = {
        index * header.node_entry_size: index
        for index in range(len(parsed_nodes))
    }
    parent_names: list[str | None] = [None] * len(parsed_nodes)
    paths: list[str | None] = [None] * len(parsed_nodes)

    def walk(offset: int, parent_index: int | None, parent_path: str | None, ancestors: frozenset[int] = frozenset()) -> None:
        local_seen: set[int] = set()
        current_offset = offset
        while current_offset in offset_to_index:
            index = offset_to_index[current_offset]
            if index in local_seen or index in ancestors:
                break
            local_seen.add(index)
            node_name = str(parsed_nodes[index]["name"])
            if parent_index is not None and parent_names[index] is None:
                parent_names[index] = str(parsed_nodes[parent_index]["name"])
            current_path = f"{parent_path}/{node_name}" if parent_path else node_name
            if paths[index] is None:
                paths[index] = current_path
            child_offset = int(parsed_nodes[index]["child_offset"] or 0)
            if child_offset in offset_to_index:
                walk(child_offset, index, current_path, ancestors | {index})
            next_offset = int(parsed_nodes[index]["peer_offset"] or 0)
            if next_offset == 0:
                break
            current_offset = next_offset

    walk(0, None, None)

    nodes: list[FreelancerUtfNode] = []
    for index, parsed in enumerate(parsed_nodes):
        nodes.append(
            FreelancerUtfNode(
                name=str(parsed["name"]),
                parent_name=parent_names[index],
                flags=int(parsed["flags"]),
                peer_offset=int(parsed["peer_offset"]),
                child_offset=int(parsed["child_offset"]),
                data_offset=parsed["data_offset"],
                allocated_size=parsed["allocated_size"],
                used_size=parsed["used_size"],
                path=paths[index] or str(parsed["name"]),
            )
        )
    return tuple(nodes)


def _build_parts_from_nodes(nodes: tuple[FreelancerUtfNode, ...], raw: bytes) -> tuple[FreelancerMeshPart, ...]:
    seen: set[str] = set()
    parts: list[FreelancerMeshPart] = []
    for index, node in enumerate(nodes):
        if not node.name.startswith("Part_") or node.name in seen:
            continue
        seen.add(node.name)
        source_name = None
        file_name = None
        object_name = None
        for follower in nodes[index + 1 :]:
            if follower.name.startswith("Part_"):
                break
            if follower.name.lower().endswith(".vms") and not source_name:
                source_name = follower.name
            elif follower.name == "File name" and follower.data_offset is not None:
                file_name = _read_native_text_node(follower, raw)
            elif follower.name == "Object name" and follower.data_offset is not None:
                object_name = _read_native_text_node(follower, raw)
        parts.append(
            FreelancerMeshPart(
                name=node.name,
                source_name=source_name,
                file_name=file_name,
                object_name=object_name,
            )
        )
    return tuple(parts)


def _read_native_text_node(node: FreelancerUtfNode, raw: bytes) -> str | None:
    if node.data_offset is None or node.used_size is None:
        return None
    if node.data_offset < 0 or node.data_offset >= len(raw):
        return None
    chunk = raw[node.data_offset : min(node.data_offset + node.used_size, len(raw))]
    head = chunk.split(b"\x00", 1)[0]
    text = head.decode("latin-1", errors="ignore").strip()
    if not text:
        return None
    printable_ratio = sum(1 for ch in text if 32 <= ord(ch) <= 126) / max(len(text), 1)
    if printable_ratio < 0.85:
        return None
    return text


def _parse_vmesh_refs(nodes: tuple[FreelancerUtfNode, ...], raw: bytes) -> tuple[FreelancerVMeshRef, ...]:
    refs: list[FreelancerVMeshRef] = []
    for node in nodes:
        if node.name != "VMeshRef" or node.data_offset is None or node.used_size is None:
            continue
        if node.used_size < VMESH_REF.size:
            continue
        start = node.data_offset
        if start < 0 or start + VMESH_REF.size > len(raw):
            continue
        (
            size,
            mesh_data_reference,
            vertex_start,
            vertex_count,
            index_start,
            index_count,
            group_start,
            group_count,
            max_x,
            min_x,
            max_y,
            min_y,
            max_z,
            min_z,
            center_x,
            center_y,
            center_z,
            radius,
        ) = VMESH_REF.unpack(raw[start : start + VMESH_REF.size])
        if size not in {0, VMESH_REF.size}:
            continue
        model_name, level_name = _extract_model_context(node.path)
        refs.append(
            FreelancerVMeshRef(
                mesh_data_reference=mesh_data_reference,
                vertex_start=vertex_start,
                vertex_count=vertex_count,
                index_start=index_start,
                index_count=index_count,
                group_start=group_start,
                group_count=group_count,
                parent_name=node.parent_name,
                node_path=node.path,
                model_name=model_name,
                level_name=level_name,
                bounds=FreelancerBounds(
                    min_xyz=(min_x, min_y, min_z),
                    max_xyz=(max_x, max_y, max_z),
                    radius=radius,
                ),
            )
        )
    return tuple(refs)


def _parse_vmesh_data_blocks(nodes: tuple[FreelancerUtfNode, ...]) -> tuple[FreelancerVMeshDataBlock, ...]:
    blocks: list[FreelancerVMeshDataBlock] = []
    for node in nodes:
        if node.name != "VMeshData" or node.data_offset is None or node.used_size is None:
            continue
        blocks.append(
            FreelancerVMeshDataBlock(
                source_name=node.parent_name,
                node_path=node.path,
                data_offset=node.data_offset,
                used_size=node.used_size,
            )
        )
    return tuple(blocks)


def _build_model_nodes(
    vmesh_refs: tuple[FreelancerVMeshRef, ...],
    parts: tuple[FreelancerMeshPart, ...],
) -> tuple[FreelancerModelNode, ...]:
    grouped: dict[str, list[FreelancerVMeshRef]] = {}
    for ref in vmesh_refs:
        if not ref.model_name:
            continue
        grouped.setdefault(ref.model_name, []).append(ref)
    if not grouped:
        return ()
    parts_by_key = {
        _normalize_model_key(part.name): part.name
        for part in parts
    }
    result: list[FreelancerModelNode] = []
    for model_name in sorted(grouped):
        refs = grouped[model_name]
        levels = tuple(sorted({ref.level_name for ref in refs if ref.level_name}))
        matched_part = parts_by_key.get(_normalize_model_key(model_name))
        source_names = tuple(
            sorted(
                {
                    source_name
                    for part in parts
                    for source_name in (part.source_name, part.file_name)
                    if source_name and _normalize_model_key(part.name) == _normalize_model_key(model_name)
                }
            )
        )
        result.append(
            FreelancerModelNode(
                model_name=model_name,
                level_names=levels,
                vmesh_ref_count=len(refs),
                matched_part_name=matched_part,
                source_names=source_names,
                bounds=_aggregate_bounds(tuple(ref.bounds for ref in refs)),
            )
        )
    return tuple(result)


def _build_preview_nodes(
    model_nodes: tuple[FreelancerModelNode, ...],
    vmesh_data_blocks: tuple[FreelancerVMeshDataBlock, ...],
) -> tuple[FreelancerPreviewMeshNode, ...]:
    if not model_nodes:
        return ()
    blocks_by_source: dict[str, list[FreelancerVMeshDataBlock]] = {}
    for block in vmesh_data_blocks:
        if not block.source_name:
            continue
        blocks_by_source.setdefault(block.source_name.lower(), []).append(block)
    preview_nodes: list[FreelancerPreviewMeshNode] = []
    for model_node in model_nodes:
        matched_blocks: list[FreelancerVMeshDataBlock] = []
        for source_name in model_node.source_names:
            matched_blocks.extend(blocks_by_source.get(source_name.lower(), []))
        if not matched_blocks and len(model_nodes) == 1:
            matched_blocks = list(vmesh_data_blocks)
        preview_nodes.append(
            FreelancerPreviewMeshNode(
                model_name=model_node.model_name,
                matched_part_name=model_node.matched_part_name,
                level_names=model_node.level_names,
                source_names=model_node.source_names,
                vmesh_ref_count=model_node.vmesh_ref_count,
                vmesh_data_block_count=len(matched_blocks),
                total_vmesh_data_bytes=sum(block.used_size for block in matched_blocks),
                bounds=model_node.bounds,
            )
        )
    return tuple(preview_nodes)


def _extract_model_context(node_path: str | None) -> tuple[str | None, str | None]:
    if not node_path:
        return None, None
    segments = [segment for segment in node_path.split("/") if segment and segment != "\\"]
    if not segments:
        return None, None
    model_name = segments[0] if segments else None
    level_name = next((segment for segment in segments if segment.lower().startswith("level")), None)
    return model_name, level_name


def _normalize_model_key(value: str) -> str:
    lowered = value.lower()
    if lowered.startswith("part_"):
        lowered = lowered[5:]
    if lowered.endswith(".3db"):
        lowered = lowered[:-4]
    lod_index = lowered.find("_lod")
    if lod_index != -1:
        prefix = lowered[:lod_index]
        rest = lowered[lod_index + 4 :]
        digits = []
        for ch in rest:
            if ch.isdigit():
                digits.append(ch)
            else:
                break
        if digits:
            lowered = f"{prefix}_lod{''.join(digits)}"
    return lowered


def _aggregate_bounds(bounds_list: tuple[FreelancerBounds, ...]) -> FreelancerBounds | None:
    valid = [
        bounds for bounds in bounds_list
        if all(value == value for value in (*bounds.min_xyz, *bounds.max_xyz))
        and (
            (bounds.radius is not None and bounds.radius > 0.0)
            or bounds.min_xyz != bounds.max_xyz
        )
    ]
    if not valid:
        return None
    min_x = min(bounds.min_xyz[0] for bounds in valid)
    min_y = min(bounds.min_xyz[1] for bounds in valid)
    min_z = min(bounds.min_xyz[2] for bounds in valid)
    max_x = max(bounds.max_xyz[0] for bounds in valid)
    max_y = max(bounds.max_xyz[1] for bounds in valid)
    max_z = max(bounds.max_xyz[2] for bounds in valid)
    center_x = (min_x + max_x) * 0.5
    center_y = (min_y + max_y) * 0.5
    center_z = (min_z + max_z) * 0.5
    radius = max(
        sqrt((x - center_x) ** 2 + (y - center_y) ** 2 + (z - center_z) ** 2)
        for x in (min_x, max_x)
        for y in (min_y, max_y)
        for z in (min_z, max_z)
    )
    radius = max(radius, max((bounds.radius or 0.0) for bounds in valid))
    return FreelancerBounds(
        min_xyz=(min_x, min_y, min_z),
        max_xyz=(max_x, max_y, max_z),
        radius=radius,
    )


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
