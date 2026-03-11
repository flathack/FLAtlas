from __future__ import annotations

import hashlib
from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from struct import Struct

from fl_editor.freelancer_mesh_data import (
    FreelancerBounds,
    FreelancerMeshData,
    FreelancerModelNode,
    FreelancerMeshPart,
    FreelancerPreviewBufferSlice,
    FreelancerPreviewGeometryCandidate,
    FreelancerPreviewGeometrySource,
    FreelancerPreviewLayoutGuess,
    FreelancerPreviewMeshBinding,
    FreelancerPreviewMeshNode,
    FreelancerPreviewSubmesh,
    FreelancerUtfNode,
    FreelancerVMeshDataBlock,
    FreelancerVMeshRef,
)


UTF_HEADER = Struct("<4s13I")
VMESH_REF = Struct("<IIHHHHHH10f")
UTF_MAGIC = b"UTF "
UTF_NODE_ENTRY_SIZE = 44
COMMON_VERTEX_STRIDES = (12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 56, 64)
COMMON_HEADER_SIZES = tuple(range(0, 257, 4))
PREFERRED_HEADER_SIZES = (16, 32, 12, 20, 24, 8, 28, 36, 40, 48, 0, 4)


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
    vmesh_data_blocks = _parse_vmesh_data_blocks(nodes, raw)
    model_nodes = _build_model_nodes(vmesh_refs, part_names)
    preview_nodes = _build_preview_nodes(model_nodes, vmesh_data_blocks)
    preview_mesh_bindings = _build_preview_mesh_bindings(vmesh_refs, preview_nodes, vmesh_data_blocks)
    preview_geometry_candidates = _build_preview_geometry_candidates(
        preview_mesh_bindings,
        vmesh_data_blocks,
    )
    preview_submeshes = _build_preview_submeshes(vmesh_refs, preview_mesh_bindings)
    preview_geometry_sources = _build_preview_geometry_sources(
        vmesh_refs,
        preview_mesh_bindings,
        vmesh_data_blocks,
    )
    preview_layout_guesses = _build_preview_layout_guesses(
        preview_geometry_sources,
        vmesh_data_blocks,
    )
    preview_buffer_slices = _build_preview_buffer_slices(preview_layout_guesses)
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
        preview_mesh_bindings=preview_mesh_bindings,
        preview_geometry_candidates=preview_geometry_candidates,
        preview_submeshes=preview_submeshes,
        preview_geometry_sources=preview_geometry_sources,
        preview_layout_guesses=preview_layout_guesses,
        preview_buffer_slices=preview_buffer_slices,
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


def _parse_vmesh_data_blocks(
    nodes: tuple[FreelancerUtfNode, ...],
    raw: bytes,
) -> tuple[FreelancerVMeshDataBlock, ...]:
    blocks: list[FreelancerVMeshDataBlock] = []
    len_raw = len(raw)
    for node in nodes:
        if node.name != "VMeshData" or node.data_offset is None or node.used_size is None:
            continue
        block_bytes = b""
        if node.data_offset >= 0 and node.data_offset < len_raw:
            block_bytes = raw[node.data_offset : min(node.data_offset + node.used_size, len_raw)]
        blocks.append(
            FreelancerVMeshDataBlock(
                source_name=node.parent_name,
                node_path=node.path,
                data_offset=node.data_offset,
                used_size=node.used_size,
                sha1=hashlib.sha1(block_bytes).hexdigest() if block_bytes else "",
                header_hex=block_bytes[:16].hex(),
                header_u32=_decode_u32_words(block_bytes, count=4),
                header_u16=_decode_u16_words(block_bytes, count=8),
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


def _build_preview_mesh_bindings(
    vmesh_refs: tuple[FreelancerVMeshRef, ...],
    preview_nodes: tuple[FreelancerPreviewMeshNode, ...],
    vmesh_data_blocks: tuple[FreelancerVMeshDataBlock, ...],
) -> tuple[FreelancerPreviewMeshBinding, ...]:
    if not vmesh_refs:
        return ()
    preview_by_model = {node.model_name: node for node in preview_nodes}
    refs_by_key: dict[tuple[str, str | None], list[FreelancerVMeshRef]] = {}
    for ref in vmesh_refs:
        if not ref.model_name:
            continue
        refs_by_key.setdefault((ref.model_name, ref.level_name), []).append(ref)

    bindings: list[FreelancerPreviewMeshBinding] = []
    for (model_name, level_name), refs in sorted(refs_by_key.items()):
        preview_node = preview_by_model.get(model_name)
        source_names = preview_node.source_names if preview_node is not None else ()
        matched_blocks = _match_vmesh_data_blocks(source_names, vmesh_data_blocks)
        if not matched_blocks and len(refs_by_key) == 1:
            matched_blocks = list(vmesh_data_blocks)
        index_count = sum(ref.index_count for ref in refs)
        bindings.append(
            FreelancerPreviewMeshBinding(
                model_name=model_name,
                level_name=level_name,
                source_names=source_names,
                vmesh_ref_count=len(refs),
                vertex_count=sum(ref.vertex_count for ref in refs),
                index_count=index_count,
                triangle_count=index_count // 3,
                group_count=sum(ref.group_count for ref in refs),
                vmesh_data_block_count=len(matched_blocks),
                total_vmesh_data_bytes=sum(block.used_size for block in matched_blocks),
                bounds=_aggregate_bounds(tuple(ref.bounds for ref in refs)),
            )
        )
    return tuple(bindings)


def _build_preview_geometry_candidates(
    preview_mesh_bindings: tuple[FreelancerPreviewMeshBinding, ...],
    vmesh_data_blocks: tuple[FreelancerVMeshDataBlock, ...],
) -> tuple[FreelancerPreviewGeometryCandidate, ...]:
    candidates: list[FreelancerPreviewGeometryCandidate] = []
    for binding in preview_mesh_bindings:
        matched_blocks = tuple(_match_vmesh_data_blocks(binding.source_names, vmesh_data_blocks))
        if not matched_blocks and len(preview_mesh_bindings) == 1:
            matched_blocks = vmesh_data_blocks
        candidates.append(
            FreelancerPreviewGeometryCandidate(
                model_name=binding.model_name,
                level_name=binding.level_name,
                source_names=binding.source_names,
                block_sha1s=tuple(block.sha1 for block in matched_blocks if block.sha1),
                vmesh_ref_count=binding.vmesh_ref_count,
                vertex_count=binding.vertex_count,
                index_count=binding.index_count,
                triangle_count=binding.triangle_count,
                group_count=binding.group_count,
                vmesh_data_block_count=len(matched_blocks),
                total_vmesh_data_bytes=sum(block.used_size for block in matched_blocks),
                decode_stage=_geometry_decode_stage(binding, matched_blocks),
                ready_for_native_render=_is_ready_for_native_render(binding, matched_blocks),
                bounds=binding.bounds,
            )
        )
    return tuple(candidates)


def _build_preview_submeshes(
    vmesh_refs: tuple[FreelancerVMeshRef, ...],
    preview_mesh_bindings: tuple[FreelancerPreviewMeshBinding, ...],
) -> tuple[FreelancerPreviewSubmesh, ...]:
    if not vmesh_refs:
        return ()
    bindings_by_key = {
        (binding.model_name, binding.level_name): binding
        for binding in preview_mesh_bindings
    }
    submeshes: list[FreelancerPreviewSubmesh] = []
    for ref in sorted(
        vmesh_refs,
        key=lambda item: (
            item.model_name or "",
            item.level_name or "",
            item.group_start,
            item.index_start,
            item.vertex_start,
        ),
    ):
        if not ref.model_name:
            continue
        binding = bindings_by_key.get((ref.model_name, ref.level_name))
        submeshes.append(
            FreelancerPreviewSubmesh(
                model_name=ref.model_name,
                level_name=ref.level_name,
                source_names=binding.source_names if binding is not None else (),
                vertex_start=ref.vertex_start,
                vertex_count=ref.vertex_count,
                index_start=ref.index_start,
                index_count=ref.index_count,
                group_start=ref.group_start,
                group_count=ref.group_count,
                triangle_count=ref.index_count // 3,
                bounds=ref.bounds,
            )
        )
    return tuple(submeshes)


def _build_preview_geometry_sources(
    vmesh_refs: tuple[FreelancerVMeshRef, ...],
    preview_mesh_bindings: tuple[FreelancerPreviewMeshBinding, ...],
    vmesh_data_blocks: tuple[FreelancerVMeshDataBlock, ...],
) -> tuple[FreelancerPreviewGeometrySource, ...]:
    if not vmesh_refs:
        return ()
    bindings_by_key = {
        (binding.model_name, binding.level_name): binding
        for binding in preview_mesh_bindings
    }
    sources: list[FreelancerPreviewGeometrySource] = []
    for ref in sorted(
        vmesh_refs,
        key=lambda item: (
            item.model_name or "",
            item.level_name or "",
            item.mesh_data_reference,
            item.group_start,
            item.index_start,
            item.vertex_start,
        ),
    ):
        if not ref.model_name:
            continue
        binding = bindings_by_key.get((ref.model_name, ref.level_name))
        matched_index, matched_block, resolution_hint = _resolve_vmesh_data_block(
            ref.mesh_data_reference,
            binding.source_names if binding is not None else (),
            vmesh_data_blocks,
        )
        sources.append(
            FreelancerPreviewGeometrySource(
                model_name=ref.model_name,
                level_name=ref.level_name,
                source_names=binding.source_names if binding is not None else (),
                mesh_data_reference=ref.mesh_data_reference,
                matched_block_index=matched_index,
                matched_block_sha1=matched_block.sha1 if matched_block is not None else None,
                resolved=matched_block is not None,
                resolution_hint=resolution_hint,
                vertex_start=ref.vertex_start,
                vertex_count=ref.vertex_count,
                index_start=ref.index_start,
                index_count=ref.index_count,
                group_start=ref.group_start,
                group_count=ref.group_count,
                triangle_count=ref.index_count // 3,
                bounds=ref.bounds,
            )
        )
    return tuple(sources)


def _build_preview_layout_guesses(
    preview_geometry_sources: tuple[FreelancerPreviewGeometrySource, ...],
    vmesh_data_blocks: tuple[FreelancerVMeshDataBlock, ...],
) -> tuple[FreelancerPreviewLayoutGuess, ...]:
    guesses: list[FreelancerPreviewLayoutGuess] = []
    for source in preview_geometry_sources:
        block = (
            vmesh_data_blocks[source.matched_block_index]
            if source.matched_block_index is not None and 0 <= source.matched_block_index < len(vmesh_data_blocks)
            else None
        )
        guesses.append(_build_preview_layout_guess(source, block))
    return tuple(guesses)


def _build_preview_buffer_slices(
    preview_layout_guesses: tuple[FreelancerPreviewLayoutGuess, ...],
) -> tuple[FreelancerPreviewBufferSlice, ...]:
    slices: list[FreelancerPreviewBufferSlice] = []
    for guess in preview_layout_guesses:
        if (
            not guess.resolved
            or guess.header_size is None
            or guess.vertex_stride is None
            or guess.index_size is None
            or guess.vertex_bytes is None
            or guess.index_bytes is None
            or guess.remaining_bytes is None
        ):
            continue
        header_offset = 0
        vertex_offset = guess.header_size
        index_offset = vertex_offset + guess.vertex_bytes
        remaining_offset = index_offset + guess.index_bytes
        slices.append(
            FreelancerPreviewBufferSlice(
                model_name=guess.model_name,
                level_name=guess.level_name,
                mesh_data_reference=guess.mesh_data_reference,
                matched_block_index=guess.matched_block_index,
                header_offset=header_offset,
                header_size=guess.header_size,
                vertex_offset=vertex_offset,
                vertex_bytes=guess.vertex_bytes,
                index_offset=index_offset,
                index_bytes=guess.index_bytes,
                remaining_offset=remaining_offset,
                remaining_bytes=guess.remaining_bytes,
                vertex_stride=guess.vertex_stride,
                index_size=guess.index_size,
                confidence=guess.confidence,
            )
        )
    return tuple(slices)


def _build_preview_layout_guess(
    source: FreelancerPreviewGeometrySource,
    block: FreelancerVMeshDataBlock | None,
) -> FreelancerPreviewLayoutGuess:
    if not source.resolved or block is None:
        return FreelancerPreviewLayoutGuess(
            model_name=source.model_name,
            level_name=source.level_name,
            mesh_data_reference=source.mesh_data_reference,
            matched_block_index=source.matched_block_index,
            resolved=False,
            header_size=None,
            vertex_stride=None,
            index_size=None,
            vertex_bytes=None,
            index_bytes=None,
            remaining_bytes=None,
            confidence="unresolved",
        )

    best: tuple[int, int, int, int, int, int] | None = None
    # confidence_rank, header_rank, stride_rank, remaining, index_size, header_size
    for index_size in (2, 4):
        index_bytes = source.index_count * index_size
        for vertex_stride in COMMON_VERTEX_STRIDES:
            vertex_bytes = source.vertex_count * vertex_stride
            for header_size in COMMON_HEADER_SIZES:
                used = header_size + vertex_bytes + index_bytes
                remaining = block.used_size - used
                if remaining < 0:
                    continue
                confidence_rank = 0 if remaining == 0 else 1 if remaining <= 16 else 2 if remaining <= 64 else 3
                header_rank = _header_preference_rank(header_size)
                stride_rank = COMMON_VERTEX_STRIDES.index(vertex_stride)
                candidate = (confidence_rank, header_rank, stride_rank, remaining, index_size, header_size)
                if best is None or candidate < best:
                    best = candidate

    if best is None:
        return FreelancerPreviewLayoutGuess(
            model_name=source.model_name,
            level_name=source.level_name,
            mesh_data_reference=source.mesh_data_reference,
            matched_block_index=source.matched_block_index,
            resolved=True,
            header_size=None,
            vertex_stride=None,
            index_size=None,
            vertex_bytes=None,
            index_bytes=None,
            remaining_bytes=None,
            confidence="no-fit",
        )

    confidence_rank, _header_rank, stride_rank, remaining, index_size, header_size = best
    vertex_stride = COMMON_VERTEX_STRIDES[stride_rank]
    confidence = ("exact", "tight", "loose", "weak")[confidence_rank]
    return FreelancerPreviewLayoutGuess(
        model_name=source.model_name,
        level_name=source.level_name,
        mesh_data_reference=source.mesh_data_reference,
        matched_block_index=source.matched_block_index,
        resolved=True,
        header_size=header_size,
        vertex_stride=vertex_stride,
        index_size=index_size,
        vertex_bytes=source.vertex_count * vertex_stride,
        index_bytes=source.index_count * index_size,
        remaining_bytes=remaining,
        confidence=confidence,
    )


def _header_preference_rank(header_size: int) -> int:
    try:
        return PREFERRED_HEADER_SIZES.index(header_size)
    except ValueError:
        return len(PREFERRED_HEADER_SIZES) + header_size


def _resolve_vmesh_data_block(
    mesh_data_reference: int,
    source_names: tuple[str, ...],
    vmesh_data_blocks: tuple[FreelancerVMeshDataBlock, ...],
) -> tuple[int | None, FreelancerVMeshDataBlock | None, str]:
    if not vmesh_data_blocks:
        return None, None, "no-vmeshdata"
    if len(vmesh_data_blocks) == 1:
        return 0, vmesh_data_blocks[0], "single-block-fallback"
    if 0 <= mesh_data_reference < len(vmesh_data_blocks):
        return mesh_data_reference, vmesh_data_blocks[mesh_data_reference], "direct-index"
    matched_blocks = _match_vmesh_data_blocks(source_names, vmesh_data_blocks)
    if len(matched_blocks) == 1:
        block = matched_blocks[0]
        return vmesh_data_blocks.index(block), block, "single-source-match"
    return None, None, "unresolved-reference"


def _geometry_decode_stage(
    binding: FreelancerPreviewMeshBinding,
    matched_blocks: tuple[FreelancerVMeshDataBlock, ...],
) -> str:
    if not matched_blocks:
        return "unmatched"
    if binding.vertex_count <= 0 or binding.index_count <= 0:
        return "ref-only"
    if len(matched_blocks) == 1:
        return "single-block-header"
    return "multi-block-header"


def _is_ready_for_native_render(
    binding: FreelancerPreviewMeshBinding,
    matched_blocks: tuple[FreelancerVMeshDataBlock, ...],
) -> bool:
    return bool(
        matched_blocks
        and binding.vertex_count > 0
        and binding.index_count > 0
        and binding.triangle_count > 0
    )


def _match_vmesh_data_blocks(
    source_names: tuple[str, ...],
    vmesh_data_blocks: tuple[FreelancerVMeshDataBlock, ...],
) -> list[FreelancerVMeshDataBlock]:
    if not source_names:
        return []
    wanted = {source_name.lower() for source_name in source_names}
    return [
        block
        for block in vmesh_data_blocks
        if block.source_name and block.source_name.lower() in wanted
    ]


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


def _decode_u32_words(raw: bytes, count: int) -> tuple[int, ...]:
    usable = min(len(raw) // 4, max(count, 0))
    if usable <= 0:
        return ()
    return tuple(int.from_bytes(raw[idx * 4 : idx * 4 + 4], "little", signed=False) for idx in range(usable))


def _decode_u16_words(raw: bytes, count: int) -> tuple[int, ...]:
    usable = min(len(raw) // 2, max(count, 0))
    if usable <= 0:
        return ()
    return tuple(int.from_bytes(raw[idx * 2 : idx * 2 + 2], "little", signed=False) for idx in range(usable))


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
