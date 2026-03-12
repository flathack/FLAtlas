from __future__ import annotations

import hashlib
from dataclasses import dataclass
from math import isfinite
from math import sqrt
from pathlib import Path
from struct import Struct

from fl_editor.freelancer_mesh_data import (
    FreelancerBounds,
    FreelancerCmpFixRecord,
    FreelancerCmpTransformHint,
    FreelancerMaterialReference,
    FreelancerMeshData,
    FreelancerModelNode,
    FreelancerMeshPart,
    FreelancerPreviewMaterialBinding,
    FreelancerPreviewMaterialGroup,
    FreelancerPreviewBufferSlice,
    FreelancerPreviewGeometryCandidate,
    FreelancerPreviewGeometrySource,
    FreelancerPreviewLayoutGuess,
    FreelancerPreviewMeshBinding,
    FreelancerPreviewMeshNode,
    FreelancerPreviewSubmesh,
    FreelancerUtfNode,
    FreelancerVMeshDataBlock,
    FreelancerVMeshDataHeaderHint,
    FreelancerVMeshRef,
)


UTF_HEADER = Struct("<4s13I")
VMESH_REF = Struct("<IIHHHHHH10f")
UTF_MAGIC = b"UTF "
UTF_NODE_ENTRY_SIZE = 44
COMMON_VERTEX_STRIDES = (12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 56, 64)
COMMON_HEADER_SIZES = tuple(range(0, 257, 4))
PREFERRED_HEADER_SIZES = (16, 32, 12, 20, 24, 8, 28, 36, 40, 48, 0, 4)
TEXTURE_EXTENSIONS = (".dds", ".tga", ".txm", ".mat")
FREELANCER_CRC_TABLE = (
    0, 151466134, 302932268, 453595578, 4285383705, 4134204559, 3982730549, 3831797155,
    4275800114, 4158437540, 3973441822, 3855800712, 28724267, 145849533, 330837255, 448732561,
    4256632932, 4105183474, 4021907784, 3871228382, 47895677, 199091435, 282375505, 433292743,
    57448534, 174827712, 291699066, 409324012, 4227947599, 4110839001, 3993976163, 3876064757,
    4218298568, 4066971742, 3915399652, 3764875634, 67364049, 218420295, 369985021, 520795499,
    95791354, 213031020, 398182870, 515701056, 4208487651, 4091501685, 3906342351, 3788586329,
    114897068, 266207290, 349655424, 500195606, 4189385909, 4038312995, 3954873753, 3804079375,
    4160927902, 4043671560, 3926710706, 3809208612, 124746887, 241716241, 358686123, 476458301,
    4141629840, 4292571398, 3838976188, 3990163498, 162629001, 11973919, 465560741, 314102835,
    134728098, 16841012, 436840590, 319723544, 4150922683, 4268571949, 3848563863, 3965934593,
    191582708, 40657250, 426062040, 274858062, 4094072301, 4244743547, 3859346625, 4010787927,
    4122008006, 4239911248, 3888036074, 4005136508, 182263263, 64630089, 416513267, 299125861,
    229794136, 78991822, 532414580, 381366498, 4074743105, 4225275351, 3771843693, 3923178747,
    4083804522, 4201568764, 3781658694, 3898652880, 201600371, 84090341, 503991391, 386759881,
    4026888508, 4177674666, 3792375824, 3943440518, 258520357, 107972019, 493278217, 341959839,
    249493774, 131713432, 483432482, 366454964, 4055055639, 4172549505, 3820837947, 3938086061,
    3988292384, 3837768630, 4290175500, 4138848922, 315967289, 466778031, 14362133, 165418627,
    325258002, 442776452, 23947838, 141187752, 3960393483, 3842637725, 4261457447, 4144471729,
    269456196, 419996626, 33682024, 184992510, 4016199517, 3865405387, 4251727473, 4100654823,
    4006878070, 3889376224, 4242176602, 4124920524, 297394031, 415166457, 62373443, 179343061,
    383165416, 533828478, 81314500, 232780370, 3921373169, 3770439527, 4222944989, 4071765579,
    3893177306, 3775535948, 4194519798, 4077156960, 392228803, 510123861, 91131631, 208256633,
    3949048716, 3798369050, 4184855200, 4033405494, 336361365, 487278339, 100800185, 251995695,
    364526526, 482151208, 129260178, 246639108, 3940024231, 3822112561, 4175011467, 4057902621,
    459588272, 308539942, 157983644, 7181066, 3825796777, 3977131583, 4127680389, 4278212371,
    3854518914, 3971512852, 4155583406, 4273347384, 450006683, 332774925, 148697015, 31186721,
    3872641748, 4023706178, 4108170232, 4258956142, 431888077, 280569435, 196114401, 45565815,
    403200742, 286222960, 168180682, 50400092, 3882196735, 3999444585, 4117495763, 4234989381,
    3758809720, 3909997294, 4060382036, 4211323842, 526853729, 375396087, 225003341, 74348507,
    517040714, 399923932, 215944038, 98057200, 3787238995, 3904609989, 4088582015, 4206231529,
    498987548, 347783818, 263426864, 112501670, 3805296133, 3956737683, 4041103145, 4191774655,
    3815143982, 3932244664, 4050131714, 4168035220, 470531639, 353144481, 235265819, 117632909,
)


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
    preview_buffer_slices = _build_preview_buffer_slices(
        preview_layout_guesses,
        preview_geometry_sources,
    )
    cmp_fix_records = _parse_cmp_fix_records(nodes, part_names, raw)
    cmp_transform_hints = _build_cmp_transform_hints(cmp_fix_records, part_names)
    material_references = _extract_material_references(nodes, raw)
    preview_material_bindings = _build_preview_material_bindings(
        preview_geometry_sources,
        preview_nodes,
        material_references,
    )
    preview_material_groups = _build_preview_material_groups(preview_material_bindings)
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
    warnings.extend(
        _build_native_preview_warnings(
            preview_geometry_sources=preview_geometry_sources,
            preview_layout_guesses=preview_layout_guesses,
            preview_buffer_slices=preview_buffer_slices,
        )
    )
    vmesh_block_kinds = {
        block.header_hint.structure_kind
        for block in vmesh_data_blocks
        if block.header_hint is not None and block.header_hint.structure_kind != "unknown"
    }
    if {"structured-header", "vertex-stream"}.issubset(vmesh_block_kinds):
        warnings.append(
            "VMeshData blocks show mixed structured-header and vertex-stream patterns; real Freelancer decode likely needs paired stream handling"
        )

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
        cmp_fix_records=cmp_fix_records,
        cmp_transform_hints=cmp_transform_hints,
        material_references=material_references,
        preview_material_bindings=preview_material_bindings,
        preview_material_groups=preview_material_groups,
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
    resolved_sources = sum(1 for source in mesh_data.preview_geometry_sources if source.resolved)
    no_fit_layouts = sum(1 for guess in mesh_data.preview_layout_guesses if guess.confidence == "no-fit")
    structured_blocks = sum(
        1
        for block in mesh_data.vmesh_data_blocks
        if block.header_hint is not None and block.header_hint.structure_kind == "structured-header"
    )
    vertex_stream_blocks = sum(
        1
        for block in mesh_data.vmesh_data_blocks
        if block.header_hint is not None and block.header_hint.structure_kind == "vertex-stream"
    )
    return (
        ("File", str(mesh_data.source_path)),
        ("Format", mesh_data.format),
        ("UTF nodes", str(summary.node_count)),
        ("Named entries", str(summary.names_count)),
        ("Detected parts", str(summary.part_count)),
        ("Referenced VMeshes", str(summary.vmesh_reference_count)),
        ("Model nodes", str(summary.model_node_count)),
        ("Data nodes", str(summary.data_node_count)),
        ("Resolved preview sources", f"{resolved_sources}/{len(mesh_data.preview_geometry_sources)}"),
        ("Preview buffer slices", str(len(mesh_data.preview_buffer_slices))),
        ("No-fit layouts", str(no_fit_layouts)),
        ("Structured VMeshData blocks", f"{structured_blocks}/{len(mesh_data.vmesh_data_blocks)}"),
        ("Vertex-stream VMeshData blocks", f"{vertex_stream_blocks}/{len(mesh_data.vmesh_data_blocks)}"),
        ("Has bounds", "yes" if summary.has_bounds else "no"),
    )


def _build_native_preview_warnings(
    *,
    preview_geometry_sources: tuple[FreelancerPreviewGeometrySource, ...],
    preview_layout_guesses: tuple[FreelancerPreviewLayoutGuess, ...],
    preview_buffer_slices: tuple[FreelancerPreviewBufferSlice, ...],
) -> tuple[str, ...]:
    warnings: list[str] = []
    if preview_geometry_sources:
        unresolved_count = sum(1 for source in preview_geometry_sources if not source.resolved)
        if unresolved_count == len(preview_geometry_sources):
            warnings.append("No preview geometry reference could be resolved to a VMeshData block")
        elif unresolved_count > 0:
            warnings.append(
                f"{unresolved_count}/{len(preview_geometry_sources)} preview geometry references are unresolved"
            )
    if preview_layout_guesses:
        no_fit_count = sum(1 for guess in preview_layout_guesses if guess.confidence == "no-fit")
        if no_fit_count == len(preview_layout_guesses):
            warnings.append("All resolved preview geometry layouts failed the current buffer-fit heuristics")
        elif no_fit_count > 0:
            warnings.append(
                f"{no_fit_count}/{len(preview_layout_guesses)} preview geometry layouts produced no buffer fit"
            )
    if preview_geometry_sources and not preview_buffer_slices:
        resolved_count = sum(1 for source in preview_geometry_sources if source.resolved)
        if resolved_count > 0:
            warnings.append("Resolved preview geometry references produced no native preview buffer slices")
    return tuple(warnings)


def _build_vmesh_data_header_hint(
    block_bytes: bytes,
    source_name: str | None,
    used_size: int,
) -> FreelancerVMeshDataHeaderHint | None:
    if not block_bytes:
        return None
    header_u32 = _decode_u32_words(block_bytes, count=4)
    header_u16 = _decode_u16_words(block_bytes, count=8)
    if len(header_u32) >= 3 and len(header_u16) >= 8:
        mesh_count_hint = header_u32[0]
        referenced_vertex_count_hint = header_u32[1]
        flexible_vertex_format_hint = header_u32[2]
        vertex_count_hint = header_u16[6]
        triangle_count_hint = header_u16[7]
        if _looks_like_structured_vmesh_header(
            mesh_count_hint=mesh_count_hint,
            referenced_vertex_count_hint=referenced_vertex_count_hint,
            flexible_vertex_format_hint=flexible_vertex_format_hint,
            vertex_count_hint=vertex_count_hint,
            triangle_count_hint=triangle_count_hint,
            used_size=used_size,
        ):
            return FreelancerVMeshDataHeaderHint(
                structure_kind="structured-header",
                mesh_count_hint=mesh_count_hint,
                referenced_vertex_count_hint=referenced_vertex_count_hint,
                flexible_vertex_format_hint=flexible_vertex_format_hint,
                vertex_count_hint=vertex_count_hint,
                triangle_count_hint=triangle_count_hint,
            )
    if _looks_like_float_stream(block_bytes, source_name):
        return FreelancerVMeshDataHeaderHint(structure_kind="vertex-stream")
    return FreelancerVMeshDataHeaderHint(structure_kind="unknown")


def _looks_like_structured_vmesh_header(
    *,
    mesh_count_hint: int,
    referenced_vertex_count_hint: int,
    flexible_vertex_format_hint: int,
    vertex_count_hint: int,
    triangle_count_hint: int,
    used_size: int,
) -> bool:
    if mesh_count_hint <= 0 or mesh_count_hint > 4096:
        return False
    if referenced_vertex_count_hint < 0 or referenced_vertex_count_hint > 1_000_000:
        return False
    if flexible_vertex_format_hint <= 0:
        return False
    if vertex_count_hint <= 0 or vertex_count_hint > 65535:
        return False
    if triangle_count_hint <= 0 or triangle_count_hint > 65535:
        return False
    return used_size >= 16


def _looks_like_float_stream(block_bytes: bytes, source_name: str | None) -> bool:
    if len(block_bytes) < 16:
        return False
    stride_hint = _vms_stride_hint_from_source_name(source_name)
    if stride_hint is None:
        return False
    values = _decode_f32_words(block_bytes, count=4)
    if len(values) < 4:
        return False
    finite_count = sum(1 for value in values if isfinite(value) and abs(value) <= 1_000_000.0)
    return finite_count >= 3


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
        data_offset = child_or_data_offset if (flags & 0x80) else None
        if data_offset is not None:
            data_offset = _resolve_utf_data_offset(data_offset, header, len(raw))
        parsed_nodes.append(
            {
                "name": name,
                "flags": flags,
                "peer_offset": peer_offset,
                "child_offset": child_or_data_offset if not (flags & 0x80) else 0,
                "data_offset": data_offset,
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


def _resolve_utf_data_offset(
    stored_offset: int,
    header: UtfFileHeader,
    raw_size: int,
) -> int:
    if stored_offset < 0:
        return stored_offset
    if header.data_offset > 0 and stored_offset < header.data_offset:
        relative_offset = header.data_offset + stored_offset
        if 0 <= relative_offset < raw_size:
            return relative_offset
    return stored_offset


def _build_parts_from_nodes(nodes: tuple[FreelancerUtfNode, ...], raw: bytes) -> tuple[FreelancerMeshPart, ...]:
    children_by_parent_path: dict[str, list[FreelancerUtfNode]] = {}
    for node in nodes:
        if not node.path or "/" not in node.path:
            continue
        parent_path = node.path.rsplit("/", 1)[0]
        children_by_parent_path.setdefault(parent_path, []).append(node)

    seen: set[str] = set()
    parts: list[FreelancerMeshPart] = []
    for index, node in enumerate(nodes):
        if not node.name.startswith("Part_") or node.name in seen:
            continue
        seen.add(node.name)
        source_name = None
        file_name = None
        object_name = None
        cmp_index = None
        part_children = children_by_parent_path.get(node.path or "", ())
        for follower in part_children:
            if follower.name.lower().endswith(".vms") and not source_name:
                source_name = follower.name
            elif follower.name == "File name" and follower.data_offset is not None:
                file_name = _read_native_text_node(follower, raw)
            elif follower.name == "Object name" and follower.data_offset is not None:
                object_name = _read_native_text_node(follower, raw)
            elif follower.name == "Index" and follower.data_offset is not None and follower.used_size:
                cmp_index = _read_native_u32_node(follower, raw)
        if source_name is None or file_name is None or object_name is None or cmp_index is None:
            for follower in nodes[index + 1 :]:
                if follower.name.startswith("Part_"):
                    break
                if follower.name.lower().endswith(".vms") and source_name is None:
                    source_name = follower.name
                elif follower.name == "File name" and file_name is None and follower.data_offset is not None:
                    file_name = _read_native_text_node(follower, raw)
                elif follower.name == "Object name" and object_name is None and follower.data_offset is not None:
                    object_name = _read_native_text_node(follower, raw)
                elif follower.name == "Index" and cmp_index is None and follower.data_offset is not None and follower.used_size:
                    cmp_index = _read_native_u32_node(follower, raw)
        parts.append(
            FreelancerMeshPart(
                name=node.name,
                cmp_index=cmp_index,
                parent_part_name=node.parent_name if node.parent_name and node.parent_name.startswith("Part_") else None,
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


def _read_native_u32_node(node: FreelancerUtfNode, raw: bytes) -> int | None:
    if node.data_offset is None or node.used_size is None or node.used_size < 4:
        return None
    if node.data_offset < 0 or node.data_offset + 4 > len(raw):
        return None
    return int.from_bytes(raw[node.data_offset : node.data_offset + 4], "little", signed=False)


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
                header_hint=_build_vmesh_data_header_hint(block_bytes, node.parent_name, node.used_size),
            )
        )
    return tuple(blocks)


def _parse_cmp_fix_records(
    nodes: tuple[FreelancerUtfNode, ...],
    parts: tuple[FreelancerMeshPart, ...],
    raw: bytes,
) -> tuple[FreelancerCmpFixRecord, ...]:
    if not parts:
        return ()
    fix_node = next((node for node in nodes if node.name == "Fix"), None)
    if (
        fix_node is None
        or fix_node.data_offset is None
        or fix_node.used_size is None
        or fix_node.used_size <= 0
    ):
        return ()
    if fix_node.data_offset < 0 or fix_node.data_offset + fix_node.used_size > len(raw):
        return ()
    if fix_node.used_size % len(parts) != 0:
        return ()

    record_size = fix_node.used_size // len(parts)
    if record_size <= 0 or record_size % 4 != 0:
        return ()

    chunk = raw[fix_node.data_offset : fix_node.data_offset + fix_node.used_size]
    parts_by_record = _parts_for_cmp_fix_records(parts, len(parts))
    records: list[FreelancerCmpFixRecord] = []
    for index, part in enumerate(parts_by_record):
        start = index * record_size
        end = start + record_size
        record_bytes = chunk[start:end]
        row_width = _detect_cmp_fix_row_width(record_size)
        row_count = (record_size // 4) // row_width if row_width else 0
        rows = _build_cmp_fix_rows(record_bytes, row_width) if row_width else ()
        records.append(
            FreelancerCmpFixRecord(
                part_name=part.name,
                part_index=part.cmp_index,
                record_index=index,
                record_size=record_size,
                float_count=record_size // 4,
                row_width=row_width,
                row_count=row_count,
                rows=rows,
                first_f32=_decode_f32_words(record_bytes, count=min(8, record_size // 4)),
                first_u32=_decode_u32_words(record_bytes, count=min(8, record_size // 4)),
            )
        )
    return tuple(records)


def _parts_for_cmp_fix_records(
    parts: tuple[FreelancerMeshPart, ...],
    record_count: int,
) -> tuple[FreelancerMeshPart, ...]:
    indexed_parts = [part for part in parts if part.cmp_index is not None and 0 <= part.cmp_index < record_count]
    if len(indexed_parts) == len(parts):
        return tuple(sorted(indexed_parts, key=lambda part: (part.cmp_index or 0, part.name)))
    return parts


def _build_cmp_transform_hints(
    records: tuple[FreelancerCmpFixRecord, ...],
    parts: tuple[FreelancerMeshPart, ...],
) -> tuple[FreelancerCmpTransformHint, ...]:
    hints: list[FreelancerCmpTransformHint] = []
    parent_by_part = {part.name: part.parent_part_name for part in parts}
    local_translations: dict[str, tuple[float, float, float] | None] = {}
    local_rotations: dict[str, tuple[tuple[float, float, float], ...] | None] = {}
    for record in records:
        local_translations[record.part_name] = _cmp_fix_translation_hint(record)
        local_rotations[record.part_name] = _cmp_fix_rotation_rows_hint(record)
    combined_translations: dict[str, tuple[float, float, float] | None] = {}
    combined_rotations: dict[str, tuple[tuple[float, float, float], ...] | None] = {}
    for record in records:
        part_name = record.part_name
        combined_translation, combined_rotation = _combined_cmp_transform_for_part(
            part_name=part_name,
            parent_by_part=parent_by_part,
            local_translations=local_translations,
            local_rotations=local_rotations,
            combined_translations=combined_translations,
            combined_rotations=combined_rotations,
            active_parts=set(),
        )
        leading_vector = _cmp_fix_leading_vector_hint(record)
        base_translation = combined_translation if combined_translation is not None else local_translations.get(part_name)
        magnitude = (
            sqrt(
                base_translation[0] * base_translation[0]
                + base_translation[1] * base_translation[1]
                + base_translation[2] * base_translation[2]
            )
            if base_translation is not None
            else None
        )
        hints.append(
            FreelancerCmpTransformHint(
                part_name=record.part_name,
                part_index=record.part_index,
                record_index=record.record_index,
                row_width=record.row_width,
                row_count=record.row_count,
                translation_xyz=local_translations.get(part_name),
                combined_translation_xyz=combined_translation,
                leading_vector_xyz=leading_vector,
                normalized_forward_xyz=_normalize_cmp_vector(leading_vector),
                normalized_rotation_rows_xyz=local_rotations.get(part_name),
                combined_rotation_rows_xyz=combined_rotation,
                translation_magnitude=magnitude,
            )
        )
    return tuple(hints)


def _combined_cmp_transform_for_part(
    part_name: str,
    parent_by_part: dict[str, str | None],
    local_translations: dict[str, tuple[float, float, float] | None],
    local_rotations: dict[str, tuple[tuple[float, float, float], ...] | None],
    combined_translations: dict[str, tuple[float, float, float] | None],
    combined_rotations: dict[str, tuple[tuple[float, float, float], ...] | None],
    active_parts: set[str],
) -> tuple[tuple[float, float, float] | None, tuple[tuple[float, float, float], ...] | None]:
    if part_name in combined_translations or part_name in combined_rotations:
        return combined_translations.get(part_name), combined_rotations.get(part_name)
    if part_name in active_parts:
        return local_translations.get(part_name), local_rotations.get(part_name)
    active_parts.add(part_name)
    local_translation = local_translations.get(part_name)
    local_rotation = local_rotations.get(part_name)
    parent_name = parent_by_part.get(part_name)
    if parent_name:
        parent_translation, parent_rotation = _combined_cmp_transform_for_part(
            part_name=parent_name,
            parent_by_part=parent_by_part,
            local_translations=local_translations,
            local_rotations=local_rotations,
            combined_translations=combined_translations,
            combined_rotations=combined_rotations,
            active_parts=active_parts,
        )
    else:
        parent_translation, parent_rotation = None, None
    combined_rotation = _combine_rotation_rows(parent_rotation, local_rotation)
    rotated_local_translation = (
        _apply_rotation_rows(parent_rotation, local_translation)
        if parent_rotation is not None and local_translation is not None
        else local_translation
    )
    combined_translation = _add_translation(parent_translation, rotated_local_translation)
    combined_translations[part_name] = combined_translation
    combined_rotations[part_name] = combined_rotation
    active_parts.remove(part_name)
    return combined_translation, combined_rotation


def _combine_rotation_rows(
    parent_rows: tuple[tuple[float, float, float], ...] | None,
    local_rows: tuple[tuple[float, float, float], ...] | None,
) -> tuple[tuple[float, float, float], ...] | None:
    if parent_rows is None:
        return local_rows
    if local_rows is None:
        return parent_rows
    return tuple(_apply_rotation_rows(parent_rows, row) for row in local_rows)


def _add_translation(
    lhs: tuple[float, float, float] | None,
    rhs: tuple[float, float, float] | None,
) -> tuple[float, float, float] | None:
    if lhs is None:
        return rhs
    if rhs is None:
        return lhs
    return (lhs[0] + rhs[0], lhs[1] + rhs[1], lhs[2] + rhs[2])


def _apply_rotation_rows(
    rows: tuple[tuple[float, float, float], ...],
    value: tuple[float, float, float],
) -> tuple[float, float, float]:
    x, y, z = value
    row0, row1, row2 = rows
    return (
        row0[0] * x + row0[1] * y + row0[2] * z,
        row1[0] * x + row1[1] * y + row1[2] * z,
        row2[0] * x + row2[1] * y + row2[2] * z,
    )


def _extract_material_references(
    nodes: tuple[FreelancerUtfNode, ...],
    raw: bytes,
) -> tuple[FreelancerMaterialReference, ...]:
    references: list[FreelancerMaterialReference] = []
    seen: set[tuple[str, str, str | None]] = set()
    for node in nodes:
        for candidate in _node_reference_candidates(node, raw):
            normalized = candidate.strip()
            lowered = normalized.lower()
            if not lowered.endswith(TEXTURE_EXTENSIONS):
                continue
            kind = "texture" if lowered.endswith((".dds", ".tga", ".txm")) else "material"
            key = (kind, lowered, node.path)
            if key in seen:
                continue
            seen.add(key)
            references.append(
                FreelancerMaterialReference(
                    kind=kind,
                    value=normalized,
                    node_name=node.name,
                    node_path=node.path,
                )
            )
    return tuple(references)


def _node_reference_candidates(
    node: FreelancerUtfNode,
    raw: bytes,
) -> tuple[str, ...]:
    values = [node.name]
    text_value = _read_native_text_node(node, raw)
    if text_value:
        values.append(text_value)
    return tuple(values)


def _cmp_fix_translation_hint(
    record: FreelancerCmpFixRecord,
) -> tuple[float, float, float] | None:
    if record.row_width != 11 or not record.rows:
        return None
    row = record.rows[0]
    if len(row) < 10:
        return None
    return (row[7], row[8], row[9])


def _cmp_fix_leading_vector_hint(
    record: FreelancerCmpFixRecord,
) -> tuple[float, float, float] | None:
    if not record.rows:
        return None
    row = record.rows[0]
    if len(row) < 3:
        return None
    return (row[0], row[1], row[2])


def _cmp_fix_rotation_rows_hint(
    record: FreelancerCmpFixRecord,
) -> tuple[tuple[float, float, float], ...] | None:
    if record.row_count < 2 or record.row_width < 3:
        return None
    raw_rows = [
        (row[0], row[1], row[2])
        for row in record.rows[:3]
        if len(row) >= 3
    ]
    nonzero_rows = [
        (index, row)
        for index, row in enumerate(raw_rows)
        if _normalize_cmp_vector(row) is not None
    ]
    if len(nonzero_rows) < 2:
        return None
    if len(nonzero_rows) >= 3:
        rows = []
        for _, candidate in nonzero_rows[:3]:
            normalized = _normalize_cmp_vector(candidate)
            if normalized is None:
                return None
            rows.append(normalized)
        if (
            abs(_dot(rows[0], rows[1])) >= 0.8
            or abs(_dot(rows[0], rows[2])) >= 0.8
            or abs(_dot(rows[1], rows[2])) >= 0.8
        ):
            return None
        determinant = _matrix3_determinant(rows[0], rows[1], rows[2])
        if abs(determinant) <= 1e-5:
            return None
        return tuple(rows)
    rows = _derive_cmp_rotation_rows(tuple(row for _, row in nonzero_rows))
    if rows is None:
        return None
    determinant = _matrix3_determinant(rows[0], rows[1], rows[2])
    if abs(determinant) <= 1e-5:
        return None
    return tuple(rows)


def _normalize_cmp_vector(
    value: tuple[float, float, float] | None,
) -> tuple[float, float, float] | None:
    if value is None:
        return None
    x, y, z = value
    magnitude = sqrt(x * x + y * y + z * z)
    if magnitude <= 1e-6:
        return None
    return (x / magnitude, y / magnitude, z / magnitude)


def _matrix3_determinant(
    row0: tuple[float, float, float],
    row1: tuple[float, float, float],
    row2: tuple[float, float, float],
) -> float:
    return (
        row0[0] * (row1[1] * row2[2] - row1[2] * row2[1])
        - row0[1] * (row1[0] * row2[2] - row1[2] * row2[0])
        + row0[2] * (row1[0] * row2[1] - row1[1] * row2[0])
    )


def _dot(
    lhs: tuple[float, float, float],
    rhs: tuple[float, float, float],
) -> float:
    return lhs[0] * rhs[0] + lhs[1] * rhs[1] + lhs[2] * rhs[2]


def _cross(
    lhs: tuple[float, float, float],
    rhs: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        lhs[1] * rhs[2] - lhs[2] * rhs[1],
        lhs[2] * rhs[0] - lhs[0] * rhs[2],
        lhs[0] * rhs[1] - lhs[1] * rhs[0],
    )


def _subtract_projection(
    value: tuple[float, float, float],
    basis: tuple[float, float, float],
) -> tuple[float, float, float]:
    scale = _dot(value, basis)
    return (
        value[0] - basis[0] * scale,
        value[1] - basis[1] * scale,
        value[2] - basis[2] * scale,
    )


def _derive_cmp_rotation_rows(
    candidate_rows: tuple[tuple[float, float, float], ...],
) -> tuple[tuple[float, float, float], ...] | None:
    primary = _normalize_cmp_vector(candidate_rows[0])
    if primary is None:
        return None
    secondary = None
    for candidate in candidate_rows[1:]:
        candidate_normalized = _normalize_cmp_vector(candidate)
        if candidate_normalized is None:
            continue
        if abs(_dot(primary, candidate_normalized)) >= 0.8:
            continue
        orthogonalized = _normalize_cmp_vector(_subtract_projection(candidate, primary))
        if orthogonalized is not None:
            secondary = orthogonalized
            break
    if secondary is None:
        return None
    tertiary = _normalize_cmp_vector(_cross(primary, secondary))
    if tertiary is None:
        return None
    stabilized_secondary = _normalize_cmp_vector(_cross(tertiary, primary))
    if stabilized_secondary is None:
        return None
    return (primary, stabilized_secondary, tertiary)


def _detect_cmp_fix_row_width(record_size: int) -> int:
    float_count = record_size // 4
    for candidate in (11, 16, 12, 8, 4):
        if float_count % candidate == 0:
            return candidate
    return float_count


def _build_cmp_fix_rows(record_bytes: bytes, row_width: int) -> tuple[tuple[float, ...], ...]:
    if row_width <= 0:
        return ()
    values = _decode_f32_words(record_bytes, count=len(record_bytes) // 4)
    if not values or len(values) % row_width != 0:
        return ()
    return tuple(
        values[offset : offset + row_width]
        for offset in range(0, len(values), row_width)
    )


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
    preview_geometry_sources: tuple[FreelancerPreviewGeometrySource, ...],
) -> tuple[FreelancerPreviewBufferSlice, ...]:
    slices: list[FreelancerPreviewBufferSlice] = []
    for guess, source in zip(preview_layout_guesses, preview_geometry_sources, strict=False):
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
                group_start=source.group_start,
                group_count=source.group_count,
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


def _build_preview_material_bindings(
    preview_geometry_sources: tuple[FreelancerPreviewGeometrySource, ...],
    preview_nodes: tuple[FreelancerPreviewMeshNode, ...],
    material_references: tuple[FreelancerMaterialReference, ...],
) -> tuple[FreelancerPreviewMaterialBinding, ...]:
    if not preview_geometry_sources or not material_references:
        return ()
    nodes_by_model = {node.model_name: node for node in preview_nodes}
    texture_references = tuple(ref for ref in material_references if ref.kind == "texture")
    material_values = tuple(ref.value for ref in material_references if ref.kind == "material")
    bindings: list[FreelancerPreviewMaterialBinding] = []
    for source in preview_geometry_sources:
        node = nodes_by_model.get(source.model_name)
        part_name = node.matched_part_name if node is not None else None
        matched_refs, match_hint = _match_preview_material_references(
            model_name=source.model_name,
            level_name=source.level_name,
            part_name=part_name,
            source_names=source.source_names,
            group_start=source.group_start,
            group_count=source.group_count,
            texture_references=texture_references,
        )
        matched_ref = matched_refs[0] if matched_refs else None
        bindings.append(
            FreelancerPreviewMaterialBinding(
                model_name=source.model_name,
                level_name=source.level_name,
                part_name=part_name,
                group_start=source.group_start,
                group_count=source.group_count,
                source_names=source.source_names,
                texture_value=matched_ref.value if matched_ref is not None else None,
                texture_candidates=tuple(ref.value for ref in matched_refs),
                material_value=material_values[0] if len(material_values) == 1 else None,
                reference_node_path=matched_ref.node_path if matched_ref is not None else None,
                match_hint=match_hint,
            )
        )
    return tuple(bindings)


def _build_preview_material_groups(
    preview_material_bindings: tuple[FreelancerPreviewMaterialBinding, ...],
) -> tuple[FreelancerPreviewMaterialGroup, ...]:
    if not preview_material_bindings:
        return ()
    grouped: dict[
        tuple[str | None, tuple[str, ...], str | None, str],
        list[FreelancerPreviewMaterialBinding],
    ] = {}
    for binding in preview_material_bindings:
        key = (
            binding.texture_value,
            binding.texture_candidates,
            binding.material_value,
            binding.match_hint,
        )
        grouped.setdefault(key, []).append(binding)
    groups: list[FreelancerPreviewMaterialGroup] = []
    for (texture_value, texture_candidates, material_value, match_hint), items in sorted(
        grouped.items(),
        key=lambda item: (
            item[0][0] or "",
            item[0][2] or "",
            item[0][3],
        ),
    ):
        groups.append(
            FreelancerPreviewMaterialGroup(
                texture_value=texture_value,
                texture_candidates=texture_candidates,
                material_value=material_value,
                match_hint=match_hint,
                model_names=tuple(sorted({item.model_name for item in items if item.model_name})),
                level_names=tuple(sorted({item.level_name for item in items if item.level_name})),
                part_names=tuple(sorted({item.part_name for item in items if item.part_name})),
                group_ranges=tuple(sorted({(item.group_start, item.group_count) for item in items})),
                binding_count=len(items),
            )
        )
    return tuple(groups)


def _match_preview_material_references(
    model_name: str,
    level_name: str | None,
    part_name: str | None,
    source_names: tuple[str, ...],
    group_start: int,
    group_count: int,
    texture_references: tuple[FreelancerMaterialReference, ...],
) -> tuple[tuple[FreelancerMaterialReference, ...], str]:
    if not texture_references:
        return (), "no-texture-reference"
    tokens = {
        _normalize_model_key(model_name),
        _normalize_model_key(level_name or ""),
        _normalize_model_key(part_name or ""),
        *(_normalize_model_key(name) for name in source_names),
    }
    tokens = {token for token in tokens if token}
    scored: list[tuple[int, FreelancerMaterialReference]] = []
    for reference in texture_references:
        haystack_parts = [
            _normalize_model_key(reference.value),
            _normalize_model_key(reference.node_name or ""),
            _normalize_model_key(reference.node_path or ""),
            str(group_start),
            str(group_count),
        ]
        score = sum(1 for token in tokens if any(token and token in hay for hay in haystack_parts))
        if score > 0:
            scored.append((score, reference))
    if scored:
        scored.sort(key=lambda item: (-item[0], item[1].value.lower()))
        return tuple(reference for _score, reference in scored), "token-match"
    if len(texture_references) == 1:
        return texture_references, "single-texture-fallback"
    return texture_references, "first-texture-fallback"


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
    # confidence_rank, stride_rank, header_rank, remaining, index_size, header_size
    candidate_strides = _candidate_vertex_strides_for_source(source)
    for index_size in (2, 4):
        index_bytes = source.index_count * index_size
        for vertex_stride in candidate_strides:
            vertex_bytes = source.vertex_count * vertex_stride
            for header_size in COMMON_HEADER_SIZES:
                used = header_size + vertex_bytes + index_bytes
                remaining = block.used_size - used
                if remaining < 0:
                    continue
                confidence_rank = 0 if remaining == 0 else 1 if remaining <= 16 else 2 if remaining <= 64 else 3
                header_rank = _header_preference_rank(header_size)
                stride_rank = candidate_strides.index(vertex_stride)
                candidate = (confidence_rank, stride_rank, header_rank, remaining, index_size, header_size)
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

    confidence_rank, stride_rank, _header_rank, remaining, index_size, header_size = best
    vertex_stride = candidate_strides[stride_rank]
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


def _candidate_vertex_strides_for_source(
    source: FreelancerPreviewGeometrySource,
) -> tuple[int, ...]:
    hinted: list[int] = []
    for name in source.source_names:
        stride_hint = _vms_stride_hint_from_source_name(name)
        if stride_hint is not None and stride_hint not in hinted:
            hinted.append(stride_hint)
    if not hinted:
        return COMMON_VERTEX_STRIDES
    ordered = list(hinted)
    for stride in COMMON_VERTEX_STRIDES:
        if stride not in ordered:
            ordered.append(stride)
    return tuple(ordered)


def _vms_stride_hint_from_source_name(source_name: str | None) -> int | None:
    if not source_name:
        return None
    lowered = source_name.lower()
    marker = lowered.rfind("-")
    dot_index = lowered.rfind(".vms")
    if marker == -1 or dot_index == -1 or marker >= dot_index:
        return None
    suffix = lowered[marker + 1 : dot_index]
    if not suffix.isdigit():
        return None
    value = int(suffix)
    if value <= 0:
        return None
    return value


def _freelancer_model_crc(value: str | None) -> int | None:
    if not value:
        return None
    crc = 0xFFFFFFFF
    for byte in value.lower().encode("ascii", errors="ignore"):
        crc = ((crc >> 8) ^ FREELANCER_CRC_TABLE[(crc ^ byte) & 0xFF]) & 0xFFFFFFFF
    return (~crc) & 0xFFFFFFFF


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
    crc_matches = [
        block
        for block in vmesh_data_blocks
        if block.source_name and _freelancer_model_crc(block.source_name) == mesh_data_reference
    ]
    if len(crc_matches) == 1:
        block = crc_matches[0]
        return vmesh_data_blocks.index(block), block, "flcrc-source-match"
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
            lod_digits = "".join(digits)
            if len(lod_digits) > 2:
                lod_digits = lod_digits[:1]
            lowered = f"{prefix}_lod{lod_digits}"
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


def _decode_f32_words(raw: bytes, count: int) -> tuple[float, ...]:
    usable = min(len(raw) // 4, max(count, 0))
    if usable <= 0:
        return ()
    return tuple(Struct("<f").unpack(raw[idx * 4 : idx * 4 + 4])[0] for idx in range(usable))


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
