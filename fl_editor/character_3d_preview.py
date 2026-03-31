from __future__ import annotations

import importlib
from dataclasses import dataclass, replace
import math
from struct import pack, unpack_from
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QByteArray, QEvent, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

_BRIDGE_PACKAGE = __package__ or "fl_editor"
_BRIDGE_MODULES = (
    "freelancer_mesh_data",
    "cmp_orientation_debug",
    "qt3d_compat",
    "native_preview_style",
    "cmp_loader",
    "mat_texture_loader",
    "native_preview_materials",
    "native_preview_geometry",
    "native_preview_scene_data",
    "native_preview_qt3d",
)
_BRIDGE_ERROR = ""
_BRIDGE_READY = False
_EMBEDDED_TEXTURE_CACHE: dict[Path, dict[str, Path]] = {}
_EMBEDDED_TEXTURE_TEMP_DIRS: list[tempfile.TemporaryDirectory[str]] = []
_DEFAULT_PREVIEW_ADJUSTMENTS = {
    "head": {
        "offset": (0.01, -0.01, 0.0),
        "rotation": (1.0, 180.0, 0.0),
    },
    "left": {
        "offset": (-0.63, -0.42, -0.06),
        "rotation": (-1.0, -180.0, 5.0),
    },
    "right": {
        "offset": (0.68, -0.35, -0.06),
        "rotation": (-5.0, -180.0, 1.0),
    },
}


def _ensure_bridge_loaded() -> bool:
    global _BRIDGE_READY, _BRIDGE_ERROR
    if _BRIDGE_READY:
        return True
    try:
        importlib.invalidate_caches()
        for module_name in _BRIDGE_MODULES:
            importlib.import_module(f"{_BRIDGE_PACKAGE}.{module_name}")
    except Exception as exc:
        _BRIDGE_ERROR = str(exc)
        return False
    _BRIDGE_READY = True
    _BRIDGE_ERROR = ""
    return True


def bridge_available() -> bool:
    if not _ensure_bridge_loaded():
        return False
    try:
        qt3d_compat = sys.modules[f"{_BRIDGE_PACKAGE}.qt3d_compat"]
        return bool(getattr(qt3d_compat, "QT3D_AVAILABLE", False))
    except Exception:
        return False


def bridge_error_text() -> str:
    return _BRIDGE_ERROR


@dataclass(frozen=True)
class _SimpleBounds:
    min_xyz: tuple[float, float, float]
    max_xyz: tuple[float, float, float]
    radius: float


@dataclass(frozen=True)
class _SimpleGeometry:
    positions: tuple[tuple[float, float, float], ...]
    tex_coords: tuple[tuple[float, float], ...]
    normals: tuple[tuple[float, float, float], ...]
    indices: tuple[int, ...]
    index_size: int
    material_name: str = ""


def _read_u16_array(raw: bytes) -> tuple[int, ...]:
    if not raw:
        return ()
    return tuple(unpack_from("<H", raw, offset)[0] for offset in range(0, len(raw) - (len(raw) % 2), 2))


def _read_u32_array(raw: bytes) -> tuple[int, ...]:
    if not raw:
        return ()
    return tuple(unpack_from("<I", raw, offset)[0] for offset in range(0, len(raw) - (len(raw) % 4), 4))


def _read_vec3_array(raw: bytes) -> tuple[tuple[float, float, float], ...]:
    if not raw:
        return ()
    return tuple(unpack_from("<3f", raw, offset) for offset in range(0, len(raw) - (len(raw) % 12), 12))


def _read_vec2_array(raw: bytes) -> tuple[tuple[float, float], ...]:
    if not raw:
        return ()
    return tuple(unpack_from("<2f", raw, offset) for offset in range(0, len(raw) - (len(raw) % 8), 8))


def _tristrip_to_triangles(strip_indices: tuple[int, ...]) -> list[tuple[int, int, int]]:
    triangles: list[tuple[int, int, int]] = []
    winding_flip = False
    window: list[int] = []
    for index in strip_indices:
        if index == 0xFFFF:
            window.clear()
            winding_flip = False
            continue
        window.append(int(index))
        if len(window) < 3:
            continue
        if len(window) > 3:
            window.pop(0)
        a, b, c = window
        if a == b or b == c or a == c:
            winding_flip = not winding_flip
            continue
        triangles.append((b, a, c) if winding_flip else (a, b, c))
        winding_flip = not winding_flip
    return triangles


def _build_simple_bounds(positions: list[tuple[float, float, float]]) -> _SimpleBounds | None:
    if not positions:
        return None
    xs = [float(p[0]) for p in positions]
    ys = [float(p[1]) for p in positions]
    zs = [float(p[2]) for p in positions]
    min_xyz = (min(xs), min(ys), min(zs))
    max_xyz = (max(xs), max(ys), max(zs))
    center = (
        (min_xyz[0] + max_xyz[0]) * 0.5,
        (min_xyz[1] + max_xyz[1]) * 0.5,
        (min_xyz[2] + max_xyz[2]) * 0.5,
    )
    radius = max(
        ((px - center[0]) ** 2 + (py - center[1]) ** 2 + (pz - center[2]) ** 2) ** 0.5
        for px, py, pz in positions
    )
    return _SimpleBounds(min_xyz=min_xyz, max_xyz=max_xyz, radius=max(radius, 1.0))


def _compute_vertex_normals(
    positions: list[tuple[float, float, float]],
    indices: list[int],
) -> tuple[tuple[float, float, float], ...]:
    accum = [[0.0, 0.0, 0.0] for _ in positions]
    for offset in range(0, len(indices) - 2, 3):
        ia, ib, ic = indices[offset], indices[offset + 1], indices[offset + 2]
        if ia >= len(positions) or ib >= len(positions) or ic >= len(positions):
            continue
        ax, ay, az = positions[ia]
        bx, by, bz = positions[ib]
        cx, cy, cz = positions[ic]
        abx, aby, abz = bx - ax, by - ay, bz - az
        acx, acy, acz = cx - ax, cy - ay, cz - az
        nx = aby * acz - abz * acy
        ny = abz * acx - abx * acz
        nz = abx * acy - aby * acx
        for idx in (ia, ib, ic):
            accum[idx][0] += nx
            accum[idx][1] += ny
            accum[idx][2] += nz
    out: list[tuple[float, float, float]] = []
    for nx, ny, nz in accum:
        length = (nx * nx + ny * ny + nz * nz) ** 0.5
        if length <= 1e-8:
            out.append((0.0, 1.0, 0.0))
        else:
            out.append((nx / length, ny / length, nz / length))
    return tuple(out)


def _merge_bounds(bounds_list: list[_SimpleBounds | None]) -> _SimpleBounds | None:
    valid = [bounds for bounds in bounds_list if bounds is not None]
    if not valid:
        return None
    min_xyz = (
        min(bounds.min_xyz[0] for bounds in valid),
        min(bounds.min_xyz[1] for bounds in valid),
        min(bounds.min_xyz[2] for bounds in valid),
    )
    max_xyz = (
        max(bounds.max_xyz[0] for bounds in valid),
        max(bounds.max_xyz[1] for bounds in valid),
        max(bounds.max_xyz[2] for bounds in valid),
    )
    return _build_simple_bounds([
        min_xyz,
        max_xyz,
        (min_xyz[0], min_xyz[1], max_xyz[2]),
        (min_xyz[0], max_xyz[1], min_xyz[2]),
        (max_xyz[0], min_xyz[1], min_xyz[2]),
        (max_xyz[0], max_xyz[1], min_xyz[2]),
        (max_xyz[0], min_xyz[1], max_xyz[2]),
        (min_xyz[0], max_xyz[1], max_xyz[2]),
    ])


def _double_sided_native_geometry(geometry):
    indices = tuple(int(index) for index in (getattr(geometry, "indices", ()) or ()))
    if len(indices) < 3:
        return geometry
    doubled: list[int] = list(indices)
    for offset in range(0, len(indices) - 2, 3):
        a, b, c = indices[offset], indices[offset + 1], indices[offset + 2]
        doubled.extend((a, c, b))
    try:
        return replace(geometry, indices=tuple(doubled))
    except Exception:
        try:
            clone = types.SimpleNamespace(**getattr(geometry, "__dict__", {}))
            clone.indices = tuple(doubled)
            return clone
        except Exception:
            return geometry


def _configure_line_wireframe_material(material) -> list[object]:
    refs: list[object] = []
    try:
        import PySide6.Qt3DRender as _Qt3DRender

        render_ns = getattr(_Qt3DRender, "Qt3DRender", _Qt3DRender)
        depth_cls = getattr(render_ns, "QDepthTest", None)
        no_depth_mask_cls = getattr(render_ns, "QNoDepthMask", None)
        line_width_cls = getattr(render_ns, "QLineWidth", None)
        effect = material.effect() if hasattr(material, "effect") else None
        if effect is None:
            return refs
        for technique in list(effect.techniques() if hasattr(effect, "techniques") else []):
            for render_pass in list(technique.renderPasses() if hasattr(technique, "renderPasses") else []):
                if depth_cls is not None:
                    depth_state = depth_cls(render_pass)
                    depth_fn = getattr(depth_cls, "Always", None)
                    if depth_fn is None:
                        enum_cls = getattr(depth_cls, "DepthFunction", None)
                        depth_fn = getattr(enum_cls, "Always", None) if enum_cls is not None else None
                    if depth_fn is not None and hasattr(depth_state, "setDepthFunction"):
                        depth_state.setDepthFunction(depth_fn)
                    render_pass.addRenderState(depth_state)
                    refs.append(depth_state)
                if no_depth_mask_cls is not None:
                    no_depth_mask = no_depth_mask_cls(render_pass)
                    render_pass.addRenderState(no_depth_mask)
                    refs.append(no_depth_mask)
                if line_width_cls is not None:
                    line_width = line_width_cls(render_pass)
                    if hasattr(line_width, "setValue"):
                        line_width.setValue(1.5)
                    render_pass.addRenderState(line_width)
                    refs.append(line_width)
    except Exception:
        return refs
    return refs


@dataclass(frozen=True)
class _SimpleTransform:
    translation: tuple[float, float, float]
    rotation: tuple[float, float, float, float, float, float, float, float, float]


def _transform_point(position: tuple[float, float, float], transform: _SimpleTransform) -> tuple[float, float, float]:
    x, y, z = position
    m = transform.rotation
    tx, ty, tz = transform.translation
    return (
        m[0] * x + m[1] * y + m[2] * z + tx,
        m[3] * x + m[4] * y + m[5] * z + ty,
        m[6] * x + m[7] * y + m[8] * z + tz,
    )


def _transform_normal(normal: tuple[float, float, float], transform: _SimpleTransform) -> tuple[float, float, float]:
    x, y, z = normal
    m = transform.rotation
    nx = m[0] * x + m[1] * y + m[2] * z
    ny = m[3] * x + m[4] * y + m[5] * z
    nz = m[6] * x + m[7] * y + m[8] * z
    length = (nx * nx + ny * ny + nz * nz) ** 0.5
    if length <= 1e-8:
        return (0.0, 1.0, 0.0)
    return (nx / length, ny / length, nz / length)


def _apply_transform_to_geometry(geometry: _SimpleGeometry, transform: _SimpleTransform) -> _SimpleGeometry:
    return _SimpleGeometry(
        positions=tuple(_transform_point(pos, transform) for pos in geometry.positions),
        tex_coords=geometry.tex_coords,
        normals=tuple(_transform_normal(normal, transform) for normal in geometry.normals),
        indices=geometry.indices,
        index_size=geometry.index_size,
        material_name=geometry.material_name,
    )


def _matrix_multiply_3x3(
    left: tuple[float, float, float, float, float, float, float, float, float],
    right: tuple[float, float, float, float, float, float, float, float, float],
) -> tuple[float, float, float, float, float, float, float, float, float]:
    return (
        left[0] * right[0] + left[1] * right[3] + left[2] * right[6],
        left[0] * right[1] + left[1] * right[4] + left[2] * right[7],
        left[0] * right[2] + left[1] * right[5] + left[2] * right[8],
        left[3] * right[0] + left[4] * right[3] + left[5] * right[6],
        left[3] * right[1] + left[4] * right[4] + left[5] * right[7],
        left[3] * right[2] + left[4] * right[5] + left[5] * right[8],
        left[6] * right[0] + left[7] * right[3] + left[8] * right[6],
        left[6] * right[1] + left[7] * right[4] + left[8] * right[7],
        left[6] * right[2] + left[7] * right[5] + left[8] * right[8],
    )


def _transpose_3x3(
    matrix: tuple[float, float, float, float, float, float, float, float, float],
) -> tuple[float, float, float, float, float, float, float, float, float]:
    return (
        matrix[0], matrix[3], matrix[6],
        matrix[1], matrix[4], matrix[7],
        matrix[2], matrix[5], matrix[8],
    )


def _compose_transform(left: _SimpleTransform, right: _SimpleTransform) -> _SimpleTransform:
    translated = _transform_point(right.translation, left)
    return _SimpleTransform(
        translation=translated,
        rotation=_matrix_multiply_3x3(left.rotation, right.rotation),
    )


def _invert_rigid_transform(transform: _SimpleTransform) -> _SimpleTransform:
    inv_rotation = _transpose_3x3(transform.rotation)
    tx, ty, tz = transform.translation
    inv_translation = (
        -(inv_rotation[0] * tx + inv_rotation[1] * ty + inv_rotation[2] * tz),
        -(inv_rotation[3] * tx + inv_rotation[4] * ty + inv_rotation[5] * tz),
        -(inv_rotation[6] * tx + inv_rotation[7] * ty + inv_rotation[8] * tz),
    )
    return _SimpleTransform(translation=inv_translation, rotation=inv_rotation)


def _read_hardpoint_transform(path_map: dict[str, object], raw: bytes, hardpoint_name: str) -> _SimpleTransform | None:
    suffix_pos = f"/Hardpoints/Fixed/{hardpoint_name}/Position"
    suffix_ori = f"/Hardpoints/Fixed/{hardpoint_name}/Orientation"
    pos_node = None
    ori_node = None
    for path, node in path_map.items():
        if path.endswith(suffix_pos):
            pos_node = node
        elif path.endswith(suffix_ori):
            ori_node = node
    if pos_node is None or ori_node is None:
        return None
    if pos_node.data_offset is None or ori_node.data_offset is None or not pos_node.used_size or not ori_node.used_size:
        return None
    pdata = raw[int(pos_node.data_offset): int(pos_node.data_offset) + int(pos_node.used_size)]
    odata = raw[int(ori_node.data_offset): int(ori_node.data_offset) + int(ori_node.used_size)]
    if len(pdata) < 12 or len(odata) < 36:
        return None
    return _SimpleTransform(
        translation=tuple(float(v) for v in unpack_from("<3f", pdata, 0)),
        rotation=tuple(float(v) for v in unpack_from("<9f", odata, 0)),
    )


def _material_color(material_name: str) -> QColor:
    raw = str(material_name or "").strip().lower()
    if not raw:
        return QColor(210, 214, 222)
    if any(token in raw for token in ("head", "face", "hand", "skin", "malehand", "femalehand")):
        return QColor(214, 184, 158)
    palette = (
        QColor(179, 190, 204),
        QColor(126, 142, 170),
        QColor(140, 126, 111),
        QColor(98, 109, 126),
        QColor(154, 143, 132),
        QColor(120, 134, 146),
    )
    return palette[sum(ord(ch) for ch in raw) % len(palette)]


def _extract_utf_material_texture_map(model_path: Path) -> dict[str, tuple[str, ...]]:
    try:
        cmp_loader = sys.modules[f"{_BRIDGE_PACKAGE}.cmp_loader"]
        raw = model_path.resolve().read_bytes()
        header = cmp_loader.parse_utf_header(raw)
        nodes = cmp_loader._parse_utf_nodes(raw, header)
    except Exception:
        return {}

    material_map: dict[str, list[str]] = {}
    for node in nodes:
        path = str(getattr(node, "path", "") or "")
        lowered_path = path.lower()
        if "material library/" not in lowered_path:
            continue
        if not (lowered_path.endswith("/dt_name") or lowered_path.endswith("/et_name")):
            continue
        if node.data_offset is None or not node.used_size:
            continue
        parts = path.replace("\\", "/").strip("/").split("/")
        if len(parts) < 3:
            continue
        material_name = parts[-2].strip()
        if not material_name:
            continue
        start = int(node.data_offset)
        size = int(node.used_size)
        value = raw[start:start + size].split(b"\x00", 1)[0].decode("ascii", errors="ignore").strip()
        if not value:
            continue
        material_map.setdefault(material_name.lower(), []).append(value)
    return {key: tuple(values) for key, values in material_map.items()}


def _resolve_embedded_texture_path(
    material_name: str,
    embedded_textures: dict[str, Path],
    material_texture_map: dict[str, tuple[str, ...]] | None = None,
) -> Path | None:
    if not embedded_textures:
        return None
    raw_name = str(material_name or "").strip()
    candidates: list[str] = []
    mapped_texture_names = () if material_texture_map is None else material_texture_map.get(raw_name.lower(), ())
    for mapped_name in mapped_texture_names:
        normalized_mapped = mapped_name.replace("\\", "/").split("/")[-1].strip()
        if not normalized_mapped:
            continue
        lowered_mapped = normalized_mapped.lower()
        lowered_mapped_stem = Path(normalized_mapped).stem.lower()
        candidates.extend((lowered_mapped, lowered_mapped_stem))
    if raw_name:
        normalized_name = raw_name.replace("\\", "/").split("/")[-1].strip()
        if normalized_name:
            lowered_name = normalized_name.lower()
            lowered_stem = Path(normalized_name).stem.lower()
            candidates.extend((lowered_name, lowered_stem))
            if "." not in lowered_name:
                candidates.extend((f"{lowered_name}.tga", f"{lowered_name}.dds"))
                if lowered_stem and lowered_stem != lowered_name:
                    candidates.extend((f"{lowered_stem}.tga", f"{lowered_stem}.dds"))
    for candidate in candidates:
        texture_path = embedded_textures.get(candidate)
        if texture_path is not None:
            return texture_path
    unique_paths = tuple(dict.fromkeys(embedded_textures.values()))
    if len(unique_paths) == 1:
        return unique_paths[0]
    return None


def _embedded_texture_extension(texture_blob: bytes) -> str | None:
    if len(texture_blob) >= 4 and texture_blob[:4] == b"DDS ":
        return ".dds"
    if len(texture_blob) >= 18 and texture_blob[1] in {0, 1} and texture_blob[2] in {1, 2, 3, 9, 10, 11}:
        return ".tga"
    return None


def _extract_utf_embedded_textures(model_path: Path) -> dict[str, Path]:
    resolved = model_path.resolve()
    cached = _EMBEDDED_TEXTURE_CACHE.get(resolved)
    if cached is not None:
        return cached
    try:
        cmp_loader = sys.modules[f"{_BRIDGE_PACKAGE}.cmp_loader"]
        raw = resolved.read_bytes()
        header = cmp_loader.parse_utf_header(raw)
        nodes = cmp_loader._parse_utf_nodes(raw, header)
    except Exception:
        _EMBEDDED_TEXTURE_CACHE[resolved] = {}
        return {}

    best_entries: dict[str, tuple[int, bytes]] = {}
    for node in nodes:
        path = str(getattr(node, "path", "") or "")
        if "texture library" not in path.lower():
            continue
        if node.data_offset is None or not node.used_size:
            continue
        parts = path.replace("\\", "/").strip("/").split("/")
        if len(parts) < 3:
            continue
        texture_name = parts[-2].strip()
        mip_name = str(getattr(node, "name", "") or "").strip().lower()
        if not texture_name or not mip_name.startswith("mip"):
            continue
        try:
            mip_level = int(mip_name[3:])
        except ValueError:
            continue
        start = int(node.data_offset)
        size = int(node.used_size)
        texture_blob = raw[start:start + size]
        if not texture_blob:
            continue
        current = best_entries.get(texture_name.lower())
        if current is None or mip_level < current[0]:
            best_entries[texture_name.lower()] = (mip_level, texture_blob)

    if not best_entries:
        _EMBEDDED_TEXTURE_CACHE[resolved] = {}
        return {}

    tmp = tempfile.TemporaryDirectory(prefix="flatlas_dfm_tex_")
    _EMBEDDED_TEXTURE_TEMP_DIRS.append(tmp)
    tmp_dir = Path(tmp.name)
    result: dict[str, Path] = {}
    for texture_name, (_mip_level, texture_blob) in best_entries.items():
        ext = _embedded_texture_extension(texture_blob)
        if ext is None:
            continue
        stem = Path(texture_name).stem
        texture_path = tmp_dir / f"{stem}{ext}"
        try:
            texture_path.write_bytes(texture_blob)
        except OSError:
            continue
        result[texture_name.lower()] = texture_path
        result[stem.lower()] = texture_path
    _EMBEDDED_TEXTURE_CACHE[resolved] = result
    return result


def _character_preview_transform(scale: float = 72.0, *, flip_x: bool = False, flip_z: bool = False) -> _SimpleTransform:
    scaled = float(scale)
    return _SimpleTransform(
        translation=(0.0, 0.0, 0.0),
        rotation=(
            (-scaled if flip_x else scaled), 0.0, 0.0,
            0.0, scaled, 0.0,
            0.0, 0.0, (-scaled if flip_z else scaled),
        ),
    )


def _character_preview_part_transform(part_kind: str) -> _SimpleTransform:
    kind = str(part_kind or "").strip().lower()
    if kind == "body":
        return _SimpleTransform(
            translation=(0.0, 0.0, 0.0),
            rotation=(-1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, -1.0),
        )
    if kind == "head":
        return _SimpleTransform(
            translation=(0.0, 0.0, 0.0),
            rotation=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
        )
    if kind == "left":
        return _SimpleTransform(
            translation=(0.0, 0.0, 0.0),
            rotation=(
                1.0, 0.0, 0.0,
                0.0, -1.0, 0.0,
                0.0, 0.0, -1.0,
            ),
        )
    if kind == "right":
        return _SimpleTransform(
            translation=(0.0, 0.0, 0.0),
            rotation=(
                1.0, 0.0, 0.0,
                0.0, -1.0, 0.0,
                0.0, 0.0, -1.0,
            ),
        )
    return _SimpleTransform(
        translation=(0.0, 0.0, 0.0),
        rotation=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
    )


def _translation_transform(offset_xyz: tuple[float, float, float]) -> _SimpleTransform:
    return _SimpleTransform(
        translation=(float(offset_xyz[0]), float(offset_xyz[1]), float(offset_xyz[2])),
        rotation=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
    )


def _rotation_transform(rotation_deg_xyz: tuple[float, float, float]) -> _SimpleTransform:
    rx_deg, ry_deg, rz_deg = (float(rotation_deg_xyz[0]), float(rotation_deg_xyz[1]), float(rotation_deg_xyz[2]))
    rx = math.radians(rx_deg)
    ry = math.radians(ry_deg)
    rz = math.radians(rz_deg)
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    rot_x = (1.0, 0.0, 0.0, 0.0, cx, -sx, 0.0, sx, cx)
    rot_y = (cy, 0.0, sy, 0.0, 1.0, 0.0, -sy, 0.0, cy)
    rot_z = (cz, -sz, 0.0, sz, cz, 0.0, 0.0, 0.0, 1.0)
    return _SimpleTransform(
        translation=(0.0, 0.0, 0.0),
        rotation=_matrix_multiply_3x3(rot_z, _matrix_multiply_3x3(rot_y, rot_x)),
    )


def _normalized_preview_adjustments(raw_adjustments: dict[str, object] | None) -> dict[str, dict[str, tuple[float, float, float]]]:
    normalized: dict[str, dict[str, tuple[float, float, float]]] = {}
    for part_kind in ("head", "left", "right"):
        default_raw = _DEFAULT_PREVIEW_ADJUSTMENTS.get(part_kind, {})
        raw = raw_adjustments.get(part_kind, default_raw) if isinstance(raw_adjustments, dict) else default_raw
        if not isinstance(raw, dict):
            raw = default_raw
        offset_raw = raw.get("offset", default_raw.get("offset", (0.0, 0.0, 0.0)))
        rotation_raw = raw.get("rotation", default_raw.get("rotation", (0.0, 0.0, 0.0)))
        try:
            offset = (
                float(offset_raw[0]),
                float(offset_raw[1]),
                float(offset_raw[2]),
            )
        except Exception:
            offset = (0.0, 0.0, 0.0)
        try:
            rotation = (
                float(rotation_raw[0]),
                float(rotation_raw[1]),
                float(rotation_raw[2]),
            )
        except Exception:
            rotation = (0.0, 0.0, 0.0)
        normalized[part_kind] = {"offset": offset, "rotation": rotation}
    return normalized


def _preview_part_placement_transform(part_kind: str, body_bounds: _SimpleBounds, part_bounds: _SimpleBounds) -> _SimpleTransform:
    body_min_x, body_min_y, body_min_z = body_bounds.min_xyz
    body_max_x, body_max_y, body_max_z = body_bounds.max_xyz
    part_min_x, part_min_y, part_min_z = part_bounds.min_xyz
    part_max_x, part_max_y, part_max_z = part_bounds.max_xyz
    body_center_x = (body_min_x + body_max_x) * 0.5
    body_center_y = (body_min_y + body_max_y) * 0.5
    body_center_z = (body_min_z + body_max_z) * 0.5
    part_center_x = (part_min_x + part_max_x) * 0.5
    part_center_y = (part_min_y + part_max_y) * 0.5
    part_center_z = (part_min_z + part_max_z) * 0.5
    body_width = body_max_x - body_min_x
    body_height = body_max_y - body_min_y
    body_depth = body_max_z - body_min_z
    part_width = part_max_x - part_min_x
    part_height = part_max_y - part_min_y

    if part_kind == "head":
        target_center = (
            body_center_x,
            body_max_y + part_height * 0.28,
            body_center_z + body_depth * 0.22,
        )
    elif part_kind == "left":
        target_center = (
            body_min_x + part_width * 0.14,
            body_center_y + body_height * 0.27,
            body_center_z + body_depth * 0.30,
        )
    elif part_kind == "right":
        target_center = (
            body_max_x - part_width * 0.14,
            body_center_y + body_height * 0.27,
            body_center_z + body_depth * 0.30,
        )
    else:
        target_center = (part_center_x, part_center_y, part_center_z)
    return _translation_transform(
        (
            target_center[0] - part_center_x,
            target_center[1] - part_center_y,
            target_center[2] - part_center_z,
        )
    )


def _load_dfm_preview_data(model_path: Path) -> tuple[tuple[_SimpleGeometry, ...], _SimpleBounds | None, dict[str, _SimpleTransform]]:
    if not _ensure_bridge_loaded():
        raise RuntimeError(bridge_error_text() or "FLAtlas bridge could not be initialized")
    cmp_loader = sys.modules[f"{_BRIDGE_PACKAGE}.cmp_loader"]
    raw = model_path.read_bytes()
    header = cmp_loader.parse_utf_header(raw)
    nodes = cmp_loader._parse_utf_nodes(raw, header)
    path_map = {str(node.path): node for node in nodes if getattr(node, "path", None)}
    geometries: list[_SimpleGeometry] = []
    all_positions: list[tuple[float, float, float]] = []
    hardpoints = {
        hp_name: transform
        for hp_name in ("hp_head", "hp_left a", "hp_right a", "hp_left b", "hp_right b")
        if (transform := _read_hardpoint_transform(path_map, raw, hp_name)) is not None
    }

    def _node_bytes(path: str) -> bytes:
        node = path_map.get(path)
        if node is None or node.data_offset is None or not node.used_size:
            return b""
        start = int(node.data_offset)
        end = start + int(node.used_size)
        return raw[start:end]

    mesh_prefixes = sorted(
        path for path in path_map if path.startswith("\\/MultiLevel/Mesh") and path.count("/") == 2
    )
    for mesh_prefix in mesh_prefixes:
        points = _read_vec3_array(_node_bytes(f"{mesh_prefix}/Geometry/Points"))
        point_indices = _read_u32_array(_node_bytes(f"{mesh_prefix}/Geometry/Point_indices"))
        uv_indices = _read_u32_array(_node_bytes(f"{mesh_prefix}/Geometry/UV0_indices"))
        uv_coords = _read_vec2_array(_node_bytes(f"{mesh_prefix}/Geometry/UV0"))
        if not points or not point_indices:
            continue
        group_index = 0
        while True:
            strip_blob = _node_bytes(f"{mesh_prefix}/Face_groups/Group{group_index}/Tristrip_indices")
            if not strip_blob:
                break
            material_blob = _node_bytes(f"{mesh_prefix}/Face_groups/Group{group_index}/Material_name")
            material_name = material_blob.split(b"\x00", 1)[0].decode("ascii", errors="ignore").strip()
            strip_indices = _read_u16_array(strip_blob)
            triangles = _tristrip_to_triangles(strip_indices)
            if triangles:
                positions: list[tuple[float, float, float]] = []
                tex_coords: list[tuple[float, float]] = []
                indices: list[int] = []
                vertex_map: dict[tuple[int, int], int] = {}
                has_uvs = bool(uv_coords) and len(uv_indices) == len(point_indices)
                for tri in triangles:
                    for corner_idx in tri:
                        if corner_idx < 0 or corner_idx >= len(point_indices):
                            continue
                        point_idx = int(point_indices[corner_idx])
                        if point_idx < 0 or point_idx >= len(points):
                            continue
                        uv_idx = int(uv_indices[corner_idx]) if has_uvs else -1
                        key = (point_idx, uv_idx)
                        mapped = vertex_map.get(key)
                        if mapped is None:
                            mapped = len(positions)
                            vertex_map[key] = mapped
                            positions.append(points[point_idx])
                            if has_uvs and 0 <= uv_idx < len(uv_coords):
                                tex_coords.append(uv_coords[uv_idx])
                            else:
                                tex_coords.append((0.0, 0.0))
                        indices.append(mapped)
                if len(indices) >= 3 and positions:
                    geometries.append(
                        _SimpleGeometry(
                            positions=tuple(positions),
                            tex_coords=tuple(tex_coords),
                            normals=_compute_vertex_normals(positions, indices),
                            indices=tuple(indices),
                            index_size=2 if len(positions) <= 65535 else 4,
                            material_name=material_name,
                        )
                    )
                    all_positions.extend(positions)
            group_index += 1
    return tuple(geometries), _build_simple_bounds(all_positions), hardpoints


def _load_native_model_any(model_path: Path):
    cmp_loader = sys.modules[f"{_BRIDGE_PACKAGE}.cmp_loader"]
    ext = model_path.suffix.lower()
    if ext in {".cmp", ".3db"}:
        return cmp_loader.load_native_freelancer_model(model_path)
    if ext != ".dfm":
        raise ValueError(f"Unsupported Freelancer native extension: {ext or '<none>'}")

    raw = model_path.read_bytes()
    header = cmp_loader.parse_utf_header(raw)
    names = cmp_loader._decode_string_table(raw, header)
    unique_names = tuple(dict.fromkeys(names))
    nodes = cmp_loader._parse_utf_nodes(raw, header)
    part_names = cmp_loader._build_parts_from_nodes(nodes, raw)
    vmesh_data_blocks = cmp_loader._parse_vmesh_data_blocks(nodes, raw)
    vmesh_refs = cmp_loader._parse_vmesh_refs(nodes, raw, vmesh_data_blocks)
    vmesh_data_families = cmp_loader._build_vmesh_data_families(vmesh_data_blocks)
    model_nodes = cmp_loader._build_model_nodes(vmesh_refs, part_names)
    preview_nodes = cmp_loader._build_preview_nodes(model_nodes, vmesh_data_blocks)
    preview_mesh_bindings = cmp_loader._build_preview_mesh_bindings(vmesh_refs, preview_nodes, vmesh_data_blocks)
    preview_geometry_candidates = cmp_loader._build_preview_geometry_candidates(
        preview_mesh_bindings,
        vmesh_data_blocks,
    )
    preview_submeshes = cmp_loader._build_preview_submeshes(vmesh_refs, preview_mesh_bindings)
    preview_geometry_sources = cmp_loader._build_preview_geometry_sources(
        vmesh_refs,
        preview_mesh_bindings,
        vmesh_data_blocks,
        vmesh_data_families,
    )
    preview_layout_guesses = cmp_loader._build_preview_layout_guesses(
        preview_geometry_sources,
        vmesh_data_blocks,
        vmesh_data_families,
    )
    preview_buffer_slices = cmp_loader._build_preview_buffer_slices(
        preview_layout_guesses,
        preview_geometry_sources,
    )
    preview_family_decode_hints = cmp_loader._build_preview_family_decode_hints(
        preview_geometry_sources,
        preview_layout_guesses,
        vmesh_data_blocks,
    )
    structured_mesh_header_records = cmp_loader._build_structured_mesh_header_records(preview_family_decode_hints)
    structured_decode_plans = cmp_loader._build_structured_decode_plans(preview_family_decode_hints)
    cmp_fix_records = cmp_loader._parse_cmp_fix_records(nodes, part_names, raw)
    cmp_transform_hints = cmp_loader._build_unified_cmp_transform_hints(cmp_fix_records, nodes, part_names, raw)
    material_references = cmp_loader._extract_material_references(nodes, raw)
    preview_material_bindings = cmp_loader._build_preview_material_bindings(
        preview_geometry_sources,
        preview_nodes,
        material_references,
    )
    preview_material_groups = cmp_loader._build_preview_material_groups(preview_material_bindings)
    vmesh_references = tuple(node.name for node in nodes if node.name.lower().endswith(".vms"))
    warnings: list[str] = []
    if header.node_entry_size != cmp_loader.UTF_NODE_ENTRY_SIZE:
        warnings.append(
            f"Unexpected UTF node entry size: {header.node_entry_size} (expected {cmp_loader.UTF_NODE_ENTRY_SIZE})"
        )
    if not vmesh_references:
        warnings.append("No VMesh references detected in UTF string table")
    warnings.extend(
        cmp_loader._build_native_preview_warnings(
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
    multi_block_family_count = sum(1 for family in vmesh_data_families if len(family.block_indices) > 1)
    if multi_block_family_count > 0:
        warnings.append(
            f"{multi_block_family_count}/{len(vmesh_data_families)} VMeshData families contain multiple related blocks; family-aware pairing is likely required"
        )
    family_pairing_mismatch_count = sum(
        1 for hint in preview_family_decode_hints if hint.pairing_status == "header-stream-capacity-mismatch"
    )
    if family_pairing_mismatch_count > 0:
        warnings.append(
            f"{family_pairing_mismatch_count}/{len(preview_family_decode_hints)} preview family decode hints show header/stream capacity mismatches"
        )

    return cmp_loader.FreelancerMeshData(
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
        vmesh_data_families=vmesh_data_families,
        model_nodes=model_nodes,
        preview_nodes=preview_nodes,
        preview_mesh_bindings=preview_mesh_bindings,
        preview_geometry_candidates=preview_geometry_candidates,
        preview_submeshes=preview_submeshes,
        preview_geometry_sources=preview_geometry_sources,
        preview_layout_guesses=preview_layout_guesses,
        preview_buffer_slices=preview_buffer_slices,
        preview_family_decode_hints=preview_family_decode_hints,
        structured_mesh_header_records=structured_mesh_header_records,
        structured_decode_plans=structured_decode_plans,
        cmp_fix_records=cmp_fix_records,
        cmp_transform_hints=cmp_transform_hints,
        material_references=material_references,
        preview_material_bindings=preview_material_bindings,
        preview_material_groups=preview_material_groups,
        bounds=cmp_loader._aggregate_bounds(tuple(vref.bounds for vref in vmesh_refs)),
        warnings=tuple(warnings),
    )


class FreelancerModelPreviewWidget(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._title = str(title or "Model").strip() or "Model"
        self._root = None
        self._camera = None
        self._cam_controller = None
        self._view3d = None
        self._container = None
        self._texture_refs: list[object] = []
        self._scene_entities: list[object] = []
        self._preview_bounds = None
        self._current_model_path: Path | None = None
        self._style_update_in_progress = False
        self._last_style_key: tuple[bool, str, str] | None = None
        self._material_refs: list[object] = []
        self._prefer_front_view = False
        self._preview_adjustments = _normalized_preview_adjustments(None)
        self._last_model_paths: list[Path | None] = []
        self._last_caption = ""
        self._last_meta = ""
        self._force_flat_gray_material = False
        self._show_wireframe_overlay = False
        self._force_light_mode: bool | None = None
        self._compact_mode = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._card = QFrame(self)
        self._card.setObjectName("trentPreviewCard")
        self._card_layout = QVBoxLayout(self._card)
        self._card_layout.setContentsMargins(10, 10, 10, 10)
        self._card_layout.setSpacing(8)
        layout.addWidget(self._card)

        self._eyebrow_label = QLabel(self._title.upper(), self._card)
        self._eyebrow_label.setObjectName("trentPreviewEyebrow")
        self._card_layout.addWidget(self._eyebrow_label)

        self._title_label = QLabel(self._title, self._card)
        self._title_label.setObjectName("trentPreviewTitle")
        self._title_label.setWordWrap(True)
        self._card_layout.addWidget(self._title_label)

        self._meta_label = QLabel("Waiting for selection", self._card)
        self._meta_label.setObjectName("trentPreviewMeta")
        self._meta_label.setWordWrap(True)
        self._card_layout.addWidget(self._meta_label)

        self._status_label = QLabel("", self._card)
        self._status_label.setObjectName("trentPreviewStatus")
        self._status_label.setWordWrap(True)
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setMinimumHeight(180)
        self._card_layout.addWidget(self._status_label, 1)

        self._hint_label = QLabel("Drag to orbit, wheel to zoom.", self._card)
        self._hint_label.setObjectName("trentPreviewHint")
        self._hint_label.setWordWrap(True)
        self._card_layout.addWidget(self._hint_label)

        self._reset_btn = QPushButton("Reset Camera", self._card)
        self._reset_btn.setObjectName("trentPreviewResetButton")
        self._reset_btn.setVisible(False)
        self._reset_btn.clicked.connect(self._reset_camera)
        self._card_layout.addWidget(self._reset_btn, 0, Qt.AlignRight)

        self._apply_styles()

        if not bridge_available():
            self._show_status(
                "3D preview unavailable.\n\n"
                + (bridge_error_text() or "Qt3D or FLAtlas preview modules are missing.")
            )
            self._meta_label.setText("FLAtlas bridge offline")
            return

        qt3d = sys.modules[f"{_BRIDGE_PACKAGE}.qt3d_compat"]
        self._view3d = qt3d.Qt3DWindow3D()
        self._container = QWidget.createWindowContainer(self._view3d, self)
        self._container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._container.setMinimumHeight(220)
        self._container.setFocusPolicy(Qt.StrongFocus)
        self._container.setObjectName("trentPreviewViewport")
        self._card_layout.insertWidget(3, self._container, 1)
        self._status_label.hide()
        self._reset_btn.setVisible(True)

        self._root = qt3d.QEntity3D()
        light_entity = qt3d.QEntity3D(self._root)
        light = qt3d.QDirectionalLight3D(light_entity)
        light.setWorldDirection(qt3d.QVector3D(-0.7, -1.0, -0.5))
        if hasattr(light, "setIntensity"):
            light.setIntensity(1.35)
        light_entity.addComponent(light)
        fill_light_entity = qt3d.QEntity3D(self._root)
        fill_light = qt3d.QDirectionalLight3D(fill_light_entity)
        fill_light.setWorldDirection(qt3d.QVector3D(0.35, -0.25, 1.0))
        if hasattr(fill_light, "setIntensity"):
            fill_light.setIntensity(0.9)
        fill_light_entity.addComponent(fill_light)

        self._camera = self._view3d.camera()
        self._camera.lens().setPerspectiveProjection(45.0, 16.0 / 9.0, 0.1, 50000.0)
        self._camera.setPosition(qt3d.QVector3D(0.0, 0.0, 120.0))
        self._camera.setViewCenter(qt3d.QVector3D(0.0, 0.0, 0.0))

        self._cam_controller = qt3d.QOrbitCameraController3D(self._root)
        self._cam_controller.setLinearSpeed(100.0)
        self._cam_controller.setLookSpeed(180.0)
        self._cam_controller.setCamera(self._camera)
        self._view3d.setRootEntity(self._root)
        self._apply_background_color()
        self._meta_label.setText("Ready for Freelancer model data")

    def set_model_path(self, model_path: Path | None, *, caption: str = "") -> None:
        self.set_model_paths([model_path] if model_path is not None else [], caption=caption)

    def set_preview_adjustments(self, adjustments: dict[str, object] | None) -> None:
        self._preview_adjustments = _normalized_preview_adjustments(adjustments)

    def set_render_style(
        self,
        *,
        flat_gray_material: bool = False,
        wireframe_overlay: bool = False,
        light_mode: bool | None = None,
    ) -> None:
        flat_gray = bool(flat_gray_material)
        wireframe = bool(wireframe_overlay)
        force_light_mode = None if light_mode is None else bool(light_mode)
        if (
            flat_gray == self._force_flat_gray_material
            and wireframe == self._show_wireframe_overlay
            and force_light_mode == self._force_light_mode
        ):
            return
        self._force_flat_gray_material = flat_gray
        self._show_wireframe_overlay = wireframe
        self._force_light_mode = force_light_mode
        self._apply_background_color()
        self._last_style_key = None
        self._apply_styles()
        if self._last_model_paths:
            self.set_model_paths(self._last_model_paths, caption=self._last_caption, meta=self._last_meta)

    def refresh_theme(self) -> None:
        self._apply_background_color()
        self._last_style_key = None
        self._apply_styles()
        if self._force_flat_gray_material and self._last_model_paths:
            self.set_model_paths(self._last_model_paths, caption=self._last_caption, meta=self._last_meta)
        if self._container is not None:
            try:
                self._container.update()
            except Exception:
                pass

    def set_theme_mode(self, light_mode: bool | None) -> None:
        normalized_mode = None if light_mode is None else bool(light_mode)
        if normalized_mode == self._force_light_mode:
            self.refresh_theme()
            return
        self._force_light_mode = normalized_mode
        self.refresh_theme()

    def _theme_is_light(self) -> bool:
        if self._force_light_mode is not None:
            return bool(self._force_light_mode)
        try:
            return self.palette().window().color().lightnessF() >= 0.5
        except Exception:
            return False

    def set_compact_mode(self, compact: bool = True) -> None:
        compact_mode = bool(compact)
        if compact_mode == self._compact_mode:
            return
        self._compact_mode = compact_mode
        self._eyebrow_label.setVisible(not compact_mode)
        self._title_label.setVisible(not compact_mode)
        self._meta_label.setVisible(not compact_mode)
        self._hint_label.setVisible(not compact_mode)
        if compact_mode:
            self._card_layout.setContentsMargins(0, 0, 0, 0)
            self._card_layout.setSpacing(6)
        else:
            self._card_layout.setContentsMargins(10, 10, 10, 10)
            self._card_layout.setSpacing(8)
        self._last_style_key = None
        self._apply_styles()

    def set_model_paths(self, model_paths: list[Path | None], *, caption: str = "", meta: str = "") -> None:
        self._last_model_paths = list(model_paths or [])
        self._last_caption = str(caption or "")
        self._last_meta = str(meta or "")
        valid_paths = [path for path in model_paths if isinstance(path, Path)]
        self._current_model_path = valid_paths[0] if valid_paths else None
        self._title_label.setText(caption or self._title)
        self._prefer_front_view = len(valid_paths) > 1
        if self._view3d is None or self._root is None:
            self._meta_label.setText("3D rendering not active")
            self._show_status("No model selected")
            return
        self._clear_scene_entities()
        if not valid_paths:
            self._meta_label.setText(meta or "Choose body, head and hands to assemble a character")
            self._show_status("No model selected")
            return
        qt3d_mod = sys.modules[f"{_BRIDGE_PACKAGE}.native_preview_qt3d"]
        loaded_names: list[str] = []
        all_bounds: list[_SimpleBounds | None] = []
        total_geometry_count = 0
        body_part_bounds: _SimpleBounds | None = None
        global_preview_transform = _character_preview_transform() if any(path.suffix.lower() == ".dfm" for path in valid_paths) else None
        for model_path in valid_paths:
            if not model_path.exists() or not model_path.is_file():
                continue
            try:
                if model_path.suffix.lower() == ".dfm":
                    geometries, bounds, hardpoints = _load_dfm_preview_data(model_path)
                    scene_data = None
                    embedded_textures = _extract_utf_embedded_textures(model_path)
                    material_texture_map = _extract_utf_material_texture_map(model_path)
                else:
                    scene_mod = sys.modules[f"{_BRIDGE_PACKAGE}.native_preview_scene_data"]
                    native_model = _load_native_model_any(model_path)
                    scene_data = scene_mod.build_native_preview_scene_data(native_model, normalize_to_center=True)
                    geometries = tuple(getattr(scene_data, "geometries", ()) or ())
                    bounds = getattr(scene_data, "bounds", None)
                    hardpoints = {}
                    embedded_textures = {}
                    material_texture_map = {}
            except Exception:
                continue
            if not geometries:
                continue
            lower_name = model_path.name.lower()
            part_kind = "body" if "body" in lower_name else ("head" if "head" in lower_name else ("left" if ("handleft" in lower_name or "left" in lower_name) else ("right" if ("handright" in lower_name or "right" in lower_name) else "")))
            if model_path.suffix.lower() == ".dfm" and part_kind in {"left", "right"}:
                local_preview_transform = _character_preview_part_transform(part_kind)
                geometries = tuple(_apply_transform_to_geometry(geometry, local_preview_transform) for geometry in geometries)
                bounds = _build_simple_bounds([pos for geometry in geometries for pos in geometry.positions])
            if model_path.suffix.lower() == ".dfm" and "body" in lower_name and bounds is not None:
                body_part_bounds = bounds
            if len(valid_paths) > 1 and model_path.suffix.lower() == ".dfm":
                if body_part_bounds is not None and bounds is not None and "body" not in lower_name:
                    placement_transform = _preview_part_placement_transform(part_kind, body_part_bounds, bounds)
                    geometries = tuple(_apply_transform_to_geometry(geometry, placement_transform) for geometry in geometries)
                    bounds = _build_simple_bounds([pos for geometry in geometries for pos in geometry.positions])
            if model_path.suffix.lower() == ".dfm" and part_kind in {"head", "left", "right"}:
                part_adjustment = self._preview_adjustments.get(part_kind, {})
                adjust_rotation = _rotation_transform(part_adjustment.get("rotation", (0.0, 0.0, 0.0)))
                adjust_offset = _translation_transform(part_adjustment.get("offset", (0.0, 0.0, 0.0)))
                geometries = tuple(_apply_transform_to_geometry(geometry, adjust_rotation) for geometry in geometries)
                geometries = tuple(_apply_transform_to_geometry(geometry, adjust_offset) for geometry in geometries)
                bounds = _build_simple_bounds([pos for geometry in geometries for pos in geometry.positions])
            if model_path.suffix.lower() == ".dfm" and global_preview_transform is not None:
                geometries = tuple(_apply_transform_to_geometry(geometry, global_preview_transform) for geometry in geometries)
                bounds = _build_simple_bounds([pos for geometry in geometries for pos in geometry.positions])
            for geometry in geometries:
                if scene_data is None:
                    entity = self._build_dfm_geometry_entity(qt3d_mod, geometry)
                else:
                    scene_mod = sys.modules[f"{_BRIDGE_PACKAGE}.native_preview_scene_data"]
                    entity = self._build_geometry_entity(qt3d_mod, scene_mod, scene_data, geometry)
                if entity is not None:
                    self._scene_entities.append(entity)
                    total_geometry_count += 1
            loaded_names.append(model_path.stem)
            all_bounds.append(bounds)
        if not self._scene_entities:
            self._meta_label.setText(meta or "Character mesh assembly failed")
            self._show_status("No renderable geometry in selected character parts")
            return
        self._preview_bounds = _merge_bounds(all_bounds)
        self._meta_label.setText(meta or f"{len(loaded_names)} parts loaded, {total_geometry_count} geometry batches")
        self._reset_camera()
        self._status_label.hide()
        if self._container is not None:
            self._container.show()

    def _build_geometry_entity(self, qt3d_mod, scene_mod, scene_data, geometry):
        try:
            qt3d = sys.modules[f"{_BRIDGE_PACKAGE}.qt3d_compat"]
            entity = qt3d.QEntity3D(self._root)
            render_geometry = _double_sided_native_geometry(geometry) if self._force_flat_gray_material else geometry
            renderer = qt3d_mod.build_native_geometry_renderer(render_geometry, owner=entity)
            if self._force_flat_gray_material:
                light_mode = self._theme_is_light()
                alpha_material_cls = getattr(qt3d, "QPhongAlphaMaterial3D", None)
                if alpha_material_cls is not None:
                    material = alpha_material_cls(entity)
                    if hasattr(material, "setAlpha"):
                        material.setAlpha(0.72)
                    if light_mode:
                        material.setAmbient(QColor(88, 88, 88))
                        material.setDiffuse(QColor(122, 122, 122))
                        material.setSpecular(QColor(28, 28, 28))
                    else:
                        material.setAmbient(QColor(132, 132, 132))
                        material.setDiffuse(QColor(196, 196, 196))
                        material.setSpecular(QColor(56, 56, 56))
                else:
                    material = qt3d.QPhongMaterial3D(entity)
                    if light_mode:
                        material.setAmbient(QColor(88, 88, 88, 184))
                        material.setDiffuse(QColor(122, 122, 122, 184))
                        material.setSpecular(QColor(28, 28, 28, 184))
                    else:
                        material.setAmbient(QColor(132, 132, 132, 184))
                        material.setDiffuse(QColor(196, 196, 196, 184))
                        material.setSpecular(QColor(56, 56, 56, 184))
                if hasattr(material, "setShininess"):
                    material.setShininess(8.0)
                if hasattr(qt3d_mod, "_disable_backface_culling"):
                    qt3d_mod._disable_backface_culling(material)
            else:
                material = qt3d_mod.build_native_geometry_material(
                    owner=entity,
                    native_geometry=geometry,
                    texture_refs=self._texture_refs,
                    texture_resolver=lambda native_geometry: scene_mod.texture_path_for_geometry(scene_data, native_geometry),
                    allow_textures=True,
                )
                qt3d_mod.apply_native_geometry_material(material, geometry)
            transform = qt3d.QTransform3D(entity)
            entity.addComponent(renderer)
            entity.addComponent(material)
            entity.addComponent(transform)
            self._material_refs.append(material)
            if self._show_wireframe_overlay and hasattr(qt3d_mod, "build_native_wireframe_renderer"):
                wire_entity = qt3d.QEntity3D(self._root)
                wire_renderer = qt3d_mod.build_native_wireframe_renderer(geometry, owner=wire_entity)
                wire_material = qt3d.QPhongMaterial3D(wire_entity)
                wire_material.setAmbient(QColor(0, 0, 0))
                wire_material.setDiffuse(QColor(0, 0, 0))
                wire_material.setSpecular(QColor(0, 0, 0))
                if hasattr(wire_material, "setShininess"):
                    wire_material.setShininess(1.0)
                self._material_refs.extend(_configure_line_wireframe_material(wire_material))
                wire_transform = qt3d.QTransform3D(wire_entity)
                if hasattr(wire_transform, "setScale"):
                    wire_transform.setScale(1.001)
                wire_entity.addComponent(wire_renderer)
                wire_entity.addComponent(wire_material)
                wire_entity.addComponent(wire_transform)
                self._scene_entities.append(wire_entity)
                self._material_refs.append(wire_material)
            return entity
        except Exception:
            return None

    def _clear_scene_entities(self) -> None:
        for entity in self._scene_entities:
            try:
                entity.setParent(None)
                entity.deleteLater()
            except Exception:
                pass
        self._scene_entities.clear()
        self._texture_refs.clear()
        self._material_refs.clear()

    def _build_dfm_geometry_entity(self, qt3d_mod, geometry, *, texture_path: Path | None = None):
        try:
            qt3d = sys.modules[f"{_BRIDGE_PACKAGE}.qt3d_compat"]
            entity = qt3d.QEntity3D(self._root)
            renderer = self._build_dfm_geometry_renderer(qt3d, geometry, owner=entity)
            material = None
            if texture_path is not None and hasattr(qt3d_mod, "build_qt3d_texture_material"):
                material = qt3d_mod.build_qt3d_texture_material(
                    owner=entity,
                    texture_path=texture_path,
                    texture_refs=self._texture_refs,
                )
            if material is None:
                material = qt3d.QPhongMaterial3D(entity)
                diffuse = _material_color(geometry.material_name)
                material.setAmbient(QColor(min(255, int(diffuse.red() * 0.72) + 36), min(255, int(diffuse.green() * 0.72) + 36), min(255, int(diffuse.blue() * 0.72) + 36)))
                material.setDiffuse(diffuse.lighter(118))
                material.setSpecular(QColor(210, 214, 220))
                if hasattr(material, "setShininess"):
                    material.setShininess(28.0)
                if hasattr(qt3d_mod, "_disable_backface_culling"):
                    qt3d_mod._disable_backface_culling(material)
            transform = qt3d.QTransform3D(entity)
            entity.addComponent(renderer)
            entity.addComponent(material)
            entity.addComponent(transform)
            self._material_refs.append(material)
            return entity
        except Exception:
            return None

    def _build_dfm_geometry_renderer(self, qt3d, geometry, *, owner):
        geometry_3d = qt3d.QGeometry3D(owner)
        has_uvs = bool(geometry.tex_coords) and len(geometry.tex_coords) == len(geometry.positions)
        has_normals = bool(geometry.normals) and len(geometry.normals) == len(geometry.positions)
        byte_stride = 12
        if has_normals:
            byte_stride += 12
        if has_uvs:
            byte_stride += 8
        vertex_blob = QByteArray()
        for index, (x, y, z) in enumerate(geometry.positions):
            nx, ny, nz = geometry.normals[index] if has_normals else (0.0, 1.0, 0.0)
            if has_uvs:
                u, v = geometry.tex_coords[index]
                vertex_blob.append(pack("<3f3f2f", x, y, z, nx, ny, nz, u, v))
            elif has_normals:
                vertex_blob.append(pack("<3f3f", x, y, z, nx, ny, nz))
            else:
                vertex_blob.append(pack("<3f", x, y, z))
        vertex_buffer = qt3d.QBuffer3D(geometry_3d)
        vertex_buffer.setData(vertex_blob)

        position_attr = qt3d.QAttribute3D(geometry_3d)
        position_attr.setName(qt3d.QAttribute3D.defaultPositionAttributeName())
        position_attr.setAttributeType(qt3d.QAttribute3D.VertexAttribute)
        position_attr.setVertexBaseType(qt3d.QAttribute3D.Float)
        position_attr.setVertexSize(3)
        position_attr.setByteStride(byte_stride)
        position_attr.setCount(len(geometry.positions))
        position_attr.setBuffer(vertex_buffer)
        geometry_3d.addAttribute(position_attr)

        if has_normals:
            normal_attr = qt3d.QAttribute3D(geometry_3d)
            normal_attr.setName(qt3d.QAttribute3D.defaultNormalAttributeName())
            normal_attr.setAttributeType(qt3d.QAttribute3D.VertexAttribute)
            normal_attr.setVertexBaseType(qt3d.QAttribute3D.Float)
            normal_attr.setVertexSize(3)
            normal_attr.setByteStride(byte_stride)
            normal_attr.setByteOffset(12)
            normal_attr.setCount(len(geometry.normals))
            normal_attr.setBuffer(vertex_buffer)
            geometry_3d.addAttribute(normal_attr)

        if has_uvs:
            tex_offset = 24 if has_normals else 12
            texcoord_attr = qt3d.QAttribute3D(geometry_3d)
            texcoord_attr.setName(qt3d.QAttribute3D.defaultTextureCoordinateAttributeName())
            texcoord_attr.setAttributeType(qt3d.QAttribute3D.VertexAttribute)
            texcoord_attr.setVertexBaseType(qt3d.QAttribute3D.Float)
            texcoord_attr.setVertexSize(2)
            texcoord_attr.setByteStride(byte_stride)
            texcoord_attr.setByteOffset(tex_offset)
            texcoord_attr.setCount(len(geometry.tex_coords))
            texcoord_attr.setBuffer(vertex_buffer)
            geometry_3d.addAttribute(texcoord_attr)

        index_blob = QByteArray()
        if geometry.index_size == 2:
            for index in geometry.indices:
                index_blob.append(pack("<H", index))
            index_type = qt3d.QAttribute3D.UnsignedShort
        else:
            for index in geometry.indices:
                index_blob.append(pack("<I", index))
            index_type = qt3d.QAttribute3D.UnsignedInt
        index_buffer = qt3d.QBuffer3D(geometry_3d)
        index_buffer.setData(index_blob)
        index_attr = qt3d.QAttribute3D(geometry_3d)
        index_attr.setAttributeType(qt3d.QAttribute3D.IndexAttribute)
        index_attr.setVertexBaseType(index_type)
        index_attr.setCount(len(geometry.indices))
        index_attr.setBuffer(index_buffer)
        geometry_3d.addAttribute(index_attr)

        renderer = qt3d.QGeometryRenderer3D(owner)
        renderer.setGeometry(geometry_3d)
        renderer.setPrimitiveType(qt3d.QGeometryRenderer3D.Triangles)
        renderer.setVertexCount(len(geometry.indices))
        return renderer

    def _show_status(self, text: str) -> None:
        if self._container is not None:
            self._container.hide()
        self._status_label.setText(text)
        self._status_label.show()

    def _reset_camera(self) -> None:
        if self._camera is None:
            return
        bounds = self._preview_bounds
        if bounds is None:
            self._camera.setViewCenter(sys.modules[f"{_BRIDGE_PACKAGE}.qt3d_compat"].QVector3D(0.0, 0.0, 0.0))
            self._camera.setPosition(sys.modules[f"{_BRIDGE_PACKAGE}.qt3d_compat"].QVector3D(0.0, 0.0, 120.0))
            return
        qt3d = sys.modules[f"{_BRIDGE_PACKAGE}.qt3d_compat"]
        min_xyz = getattr(bounds, "min_xyz", (0.0, 0.0, 0.0))
        max_xyz = getattr(bounds, "max_xyz", (0.0, 0.0, 0.0))
        radius = float(getattr(bounds, "radius", 0.0) or 0.0)
        radius = max(8.0, radius)
        width = abs(float(max_xyz[0]) - float(min_xyz[0]))
        height = abs(float(max_xyz[1]) - float(min_xyz[1]))
        depth = abs(float(max_xyz[2]) - float(min_xyz[2]))
        center = qt3d.QVector3D(
            (float(min_xyz[0]) + float(max_xyz[0])) * 0.5,
            (float(min_xyz[1]) + float(max_xyz[1])) * 0.5,
            (float(min_xyz[2]) + float(max_xyz[2])) * 0.5,
        )
        if self._prefer_front_view:
            try:
                self._camera.setUpVector(qt3d.QVector3D(0.0, 1.0, 0.0))
            except Exception:
                pass
            focus = qt3d.QVector3D(center.x(), float(min_xyz[1]) + height * 0.54, center.z())
            aspect = 16.0 / 9.0
            fov_rad = 45.0 * 3.141592653589793 / 180.0
            math_mod = __import__("math")
            distance_height = (height * 0.44) / max(0.2, math_mod.tan(fov_rad * 0.5))
            distance_width = (width * 0.52) / max(0.2, aspect * math_mod.tan(fov_rad * 0.5))
            distance = max(distance_height, distance_width, depth * 1.8, radius * 1.18, 18.0)
            self._camera.setViewCenter(focus)
            self._camera.setPosition(qt3d.QVector3D(center.x(), focus.y(), float(min_xyz[2]) - distance))
        else:
            self._camera.setViewCenter(center)
            self._camera.setPosition(center + qt3d.QVector3D(radius * 1.05, radius * 0.7, radius * 2.45))

    def _apply_background_color(self) -> None:
        if self._view3d is None:
            return
        frame_graph = getattr(self._view3d, "defaultFrameGraph", lambda: None)()
        try:
            if self._force_flat_gray_material:
                color = QColor(255, 255, 255) if self._theme_is_light() else QColor(13, 17, 24)
            elif self._theme_is_light():
                color = QColor(241, 244, 247)
            else:
                color = QColor(13, 17, 24)
            if frame_graph is not None and hasattr(frame_graph, "setClearColor"):
                frame_graph.setClearColor(color)
        except Exception:
            pass

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in {QEvent.PaletteChange, QEvent.StyleChange}:
            self._apply_background_color()
            self._apply_styles()

    def _apply_styles(self) -> None:
        if self._style_update_in_progress:
            return
        dark_theme = not self._theme_is_light()
        if self._force_flat_gray_material and self._compact_mode:
            card_bg = "transparent"
            border = "transparent"
            title = "transparent"
            meta = "transparent"
            hint = "transparent"
            status_bg = "#ffffff" if not dark_theme else "rgba(8, 10, 14, 0.96)"
            viewport_border = "transparent"
        elif self._force_flat_gray_material:
            if dark_theme:
                card_bg = "rgba(255, 255, 255, 0.04)"
                border = "#3a4554"
                title = "#eef1f5"
                meta = "#9aa8b7"
                hint = "#91a0af"
                status_bg = "rgba(8, 10, 14, 0.96)"
            else:
                card_bg = "rgba(255, 255, 255, 0.98)"
                border = "#d6d6d6"
                title = "#202020"
                meta = "#5f5f5f"
                hint = "#6b6b6b"
                status_bg = "#ffffff"
            viewport_border = border
        elif self._compact_mode:
            card_bg = "transparent"
            border = "transparent"
            title = "transparent"
            meta = "transparent"
            hint = "transparent"
            status_bg = "rgba(8, 10, 14, 0.96)"
            viewport_border = "transparent"
        elif dark_theme:
            card_bg = "rgba(255, 255, 255, 0.04)"
            border = "#3a4554"
            title = "#eef1f5"
            meta = "#9aa8b7"
            hint = "#91a0af"
            status_bg = "rgba(255, 255, 255, 0.03)"
            viewport_border = border
        else:
            card_bg = "rgba(255, 255, 255, 0.92)"
            border = "#c8d0d9"
            title = "#15202b"
            meta = "#5a6978"
            hint = "#627181"
            status_bg = "rgba(21, 32, 43, 0.035)"
            viewport_border = border
        style_key = (dark_theme, card_bg, border)
        if style_key == self._last_style_key:
            return
        self._style_update_in_progress = True
        try:
            self.setStyleSheet(
                f"""
QFrame#trentPreviewCard {{
    border: 1px solid {border};
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {card_bg}, stop:1 transparent);
}}
QLabel#trentPreviewEyebrow {{
    color: {meta};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QLabel#trentPreviewTitle {{
    color: {title};
    font-size: 15px;
    font-weight: 700;
}}
QLabel#trentPreviewMeta {{
    color: {meta};
    font-size: 11px;
}}
QLabel#trentPreviewHint {{
    color: {hint};
    font-size: 11px;
}}
QLabel#trentPreviewStatus {{
    border: 1px solid {border};
    background: {status_bg};
    color: {meta};
    padding: 14px;
}}
QWidget#trentPreviewViewport {{
    border: 1px solid {viewport_border};
    background: {status_bg};
}}
QPushButton#trentPreviewResetButton {{
    min-width: 110px;
}}
"""
            )
            self._last_style_key = style_key
        finally:
            self._style_update_in_progress = False
