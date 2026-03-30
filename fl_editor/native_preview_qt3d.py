from __future__ import annotations

from struct import pack
from typing import Callable
from pathlib import Path

from PySide6.QtCore import QByteArray, QSize, QUrl
from PySide6.QtGui import QColor, QImage

from .native_preview_style import native_preview_rgb
from .qt3d_compat import (
    QAttribute3D,
    QBuffer3D,
    QDiffuseMapMaterial3D,
    QEntity3D,
    QGeometry3D,
    QGeometryRenderer3D,
    QPhongMaterial3D,
    QTextureLoader3D,
    QTextureMaterial3D,
    QTransform3D,
)

try:
    import PySide6.Qt3DRender as _Qt3DRender
    _qt3d_render_ns = getattr(_Qt3DRender, "Qt3DRender", _Qt3DRender)
    QPaintedTextureImage3D = getattr(_qt3d_render_ns, "QPaintedTextureImage", None)
    QTexture2D_3D = getattr(_qt3d_render_ns, "QTexture2D", None)
    QAbstractTexture3D = getattr(_qt3d_render_ns, "QAbstractTexture", None)
    QCullFace3D = getattr(_qt3d_render_ns, "QCullFace", None)
except Exception:
    QPaintedTextureImage3D = None
    QTexture2D_3D = None
    QAbstractTexture3D = None
    QCullFace3D = None


def _disable_backface_culling(material) -> None:
    """Disable back-face culling on a Qt3D material so both sides render."""
    if QCullFace3D is None:
        return
    try:
        effect = material.effect()
        if effect is None:
            return
        for technique in effect.techniques():
            for render_pass in technique.renderPasses():
                cull = QCullFace3D(render_pass)
                mode = getattr(QCullFace3D, "NoCulling", None)
                if mode is None:
                    enum_cls = getattr(QCullFace3D, "CullingMode", None)
                    mode = getattr(enum_cls, "NoCulling", None) if enum_cls is not None else None
                if mode is not None and hasattr(cull, "setMode"):
                    cull.setMode(mode)
                render_pass.addRenderState(cull)
    except Exception:
        pass


def native_preview_qt3d_available() -> bool:
    return all((QGeometryRenderer3D, QGeometry3D, QAttribute3D, QBuffer3D, QPhongMaterial3D, QEntity3D, QTransform3D))


def _build_vertex_normals(native_geometry) -> tuple[tuple[float, float, float], ...]:
    positions = tuple(getattr(native_geometry, "positions", ()) or ())
    if not positions:
        return ()
    accum = [[0.0, 0.0, 0.0] for _ in positions]
    indices = tuple(int(index) for index in (getattr(native_geometry, "indices", ()) or ()))
    for offset in range(0, len(indices) - 2, 3):
        ia, ib, ic = indices[offset], indices[offset + 1], indices[offset + 2]
        if ia < 0 or ib < 0 or ic < 0:
            continue
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
    normals: list[tuple[float, float, float]] = []
    for nx, ny, nz in accum:
        length = float((nx * nx + ny * ny + nz * nz) ** 0.5)
        if length <= 1e-8:
            normals.append((0.0, 1.0, 0.0))
        else:
            normals.append((nx / length, ny / length, nz / length))
    return tuple(normals)


def build_native_geometry_renderer(native_geometry, *, owner) -> object:
    geometry = QGeometry3D(owner)

    vertex_blob = QByteArray()
    has_uvs = bool(native_geometry.tex_coords) and len(native_geometry.tex_coords) == len(native_geometry.positions)
    normals = _build_vertex_normals(native_geometry)
    has_normals = len(normals) == len(native_geometry.positions)
    if has_uvs and has_normals:
        # Interleaved: position (3f) + normal (3f) + texcoord (2f) = 32 bytes per vertex
        for (x, y, z), (nx, ny, nz), (u, v) in zip(native_geometry.positions, normals, native_geometry.tex_coords):
            vertex_blob.append(pack("<3f3f2f", x, y, z, nx, ny, nz, u, v))
        byte_stride = 32
        normal_offset = 12
        texcoord_offset = 24
    elif has_normals:
        # Interleaved: position (3f) + normal (3f) = 24 bytes per vertex
        for (x, y, z), (nx, ny, nz) in zip(native_geometry.positions, normals):
            vertex_blob.append(pack("<3f3f", x, y, z, nx, ny, nz))
        byte_stride = 24
        normal_offset = 12
        texcoord_offset = None
    elif has_uvs:
        for (x, y, z), (u, v) in zip(native_geometry.positions, native_geometry.tex_coords):
            vertex_blob.append(pack("<3f2f", x, y, z, u, v))
        byte_stride = 20
        normal_offset = None
        texcoord_offset = 12
    else:
        for x, y, z in native_geometry.positions:
            vertex_blob.append(pack("<3f", x, y, z))
        byte_stride = 12
        normal_offset = None
        texcoord_offset = None
    vertex_buffer = QBuffer3D(geometry)
    vertex_buffer.setData(vertex_blob)

    position_attr = QAttribute3D(geometry)
    position_attr.setName(QAttribute3D.defaultPositionAttributeName())
    position_attr.setAttributeType(QAttribute3D.VertexAttribute)
    position_attr.setVertexBaseType(QAttribute3D.Float)
    position_attr.setVertexSize(3)
    position_attr.setByteStride(byte_stride)
    position_attr.setCount(len(native_geometry.positions))
    position_attr.setBuffer(vertex_buffer)

    geometry.addAttribute(position_attr)

    if has_normals and normal_offset is not None:
        normal_attr = QAttribute3D(geometry)
        normal_attr.setName(QAttribute3D.defaultNormalAttributeName())
        normal_attr.setAttributeType(QAttribute3D.VertexAttribute)
        normal_attr.setVertexBaseType(QAttribute3D.Float)
        normal_attr.setVertexSize(3)
        normal_attr.setByteStride(byte_stride)
        normal_attr.setByteOffset(normal_offset)
        normal_attr.setCount(len(normals))
        normal_attr.setBuffer(vertex_buffer)
        geometry.addAttribute(normal_attr)

    if has_uvs and texcoord_offset is not None:
        texcoord_attr = QAttribute3D(geometry)
        texcoord_attr.setName(QAttribute3D.defaultTextureCoordinateAttributeName())
        texcoord_attr.setAttributeType(QAttribute3D.VertexAttribute)
        texcoord_attr.setVertexBaseType(QAttribute3D.Float)
        texcoord_attr.setVertexSize(2)
        texcoord_attr.setByteStride(byte_stride)
        texcoord_attr.setByteOffset(texcoord_offset)
        texcoord_attr.setCount(len(native_geometry.tex_coords))
        texcoord_attr.setBuffer(vertex_buffer)
        geometry.addAttribute(texcoord_attr)

    index_blob = QByteArray()
    if native_geometry.index_size == 2:
        for index in native_geometry.indices:
            index_blob.append(pack("<H", index))
        index_type = QAttribute3D.UnsignedShort
    else:
        for index in native_geometry.indices:
            index_blob.append(pack("<I", index))
        index_type = QAttribute3D.UnsignedInt
    index_buffer = QBuffer3D(geometry)
    index_buffer.setData(index_blob)

    index_attr = QAttribute3D(geometry)
    index_attr.setAttributeType(QAttribute3D.IndexAttribute)
    index_attr.setVertexBaseType(index_type)
    index_attr.setCount(len(native_geometry.indices))
    index_attr.setBuffer(index_buffer)

    geometry.addAttribute(index_attr)

    renderer = QGeometryRenderer3D(owner)
    renderer.setGeometry(geometry)
    renderer.setPrimitiveType(QGeometryRenderer3D.Triangles)
    renderer.setVertexCount(len(native_geometry.indices))
    return renderer


def build_native_wireframe_entity(*, root, native_geometry) -> object:
    entity = QEntity3D(root)
    try:
        entity.setObjectName("flatlas_native_wireframe")
    except Exception:
        pass
    renderer = build_native_wireframe_renderer(native_geometry, owner=entity)
    transform = QTransform3D(entity)
    material = QPhongMaterial3D(entity)
    _disable_backface_culling(material)
    material.setDiffuse(QColor(240, 240, 240))
    entity.addComponent(renderer)
    entity.addComponent(transform)
    entity.addComponent(material)
    entity.setEnabled(False)
    return entity


def build_native_wireframe_renderer(native_geometry, *, owner) -> object:
    geometry = QGeometry3D(owner)

    vertex_blob = QByteArray()
    normals = _build_vertex_normals(native_geometry)
    has_normals = len(normals) == len(native_geometry.positions)
    if has_normals:
        for (x, y, z), (nx, ny, nz) in zip(native_geometry.positions, normals):
            vertex_blob.append(pack("<3f3f", x, y, z, nx, ny, nz))
        byte_stride = 24
        normal_offset = 12
    else:
        for x, y, z in native_geometry.positions:
            vertex_blob.append(pack("<3f", x, y, z))
        byte_stride = 12
        normal_offset = None
    vertex_buffer = QBuffer3D(geometry)
    vertex_buffer.setData(vertex_blob)

    position_attr = QAttribute3D(geometry)
    position_attr.setName(QAttribute3D.defaultPositionAttributeName())
    position_attr.setAttributeType(QAttribute3D.VertexAttribute)
    position_attr.setVertexBaseType(QAttribute3D.Float)
    position_attr.setVertexSize(3)
    position_attr.setByteStride(byte_stride)
    position_attr.setCount(len(native_geometry.positions))
    position_attr.setBuffer(vertex_buffer)

    if has_normals and normal_offset is not None:
        normal_attr = QAttribute3D(geometry)
        normal_attr.setName(QAttribute3D.defaultNormalAttributeName())
        normal_attr.setAttributeType(QAttribute3D.VertexAttribute)
        normal_attr.setVertexBaseType(QAttribute3D.Float)
        normal_attr.setVertexSize(3)
        normal_attr.setByteStride(byte_stride)
        normal_attr.setByteOffset(normal_offset)
        normal_attr.setCount(len(normals))
        normal_attr.setBuffer(vertex_buffer)

    line_indices = []
    for offset in range(0, len(native_geometry.indices) - 2, 3):
        a = native_geometry.indices[offset]
        b = native_geometry.indices[offset + 1]
        c = native_geometry.indices[offset + 2]
        line_indices.extend((a, b, b, c, c, a))

    index_blob = QByteArray()
    if native_geometry.index_size == 2:
        for index in line_indices:
            index_blob.append(pack("<H", index))
        index_type = QAttribute3D.UnsignedShort
    else:
        for index in line_indices:
            index_blob.append(pack("<I", index))
        index_type = QAttribute3D.UnsignedInt
    index_buffer = QBuffer3D(geometry)
    index_buffer.setData(index_blob)

    index_attr = QAttribute3D(geometry)
    index_attr.setAttributeType(QAttribute3D.IndexAttribute)
    index_attr.setVertexBaseType(index_type)
    index_attr.setCount(len(line_indices))
    index_attr.setBuffer(index_buffer)

    geometry.addAttribute(position_attr)
    if has_normals and normal_offset is not None:
        geometry.addAttribute(normal_attr)
    geometry.addAttribute(index_attr)

    renderer = QGeometryRenderer3D(owner)
    renderer.setGeometry(geometry)
    renderer.setPrimitiveType(QGeometryRenderer3D.Lines)
    renderer.setVertexCount(len(line_indices))
    return renderer


def build_annulus_renderer(*, owner, inner_radius: float, outer_radius: float, segments: int = 96) -> object:
    geometry = QGeometry3D(owner)
    inner = max(0.01, float(inner_radius))
    outer = max(inner + 0.01, float(outer_radius))
    seg_count = max(12, int(segments))

    vertex_blob = QByteArray()
    indices: list[int] = []
    for index in range(seg_count + 1):
        angle = (float(index) / float(seg_count)) * 6.283185307179586
        cos_a = __import__("math").cos(angle)
        sin_a = __import__("math").sin(angle)
        u = float(index) / float(seg_count)
        vertex_blob.append(pack("<3f2f", outer * cos_a, 0.0, outer * sin_a, u, 1.0))
        vertex_blob.append(pack("<3f2f", inner * cos_a, 0.0, inner * sin_a, u, 0.0))
        if index >= seg_count:
            continue
        base = index * 2
        indices.extend((base, base + 1, base + 2, base + 2, base + 1, base + 3))

    vertex_buffer = QBuffer3D(geometry)
    vertex_buffer.setData(vertex_blob)

    position_attr = QAttribute3D(geometry)
    position_attr.setName(QAttribute3D.defaultPositionAttributeName())
    position_attr.setAttributeType(QAttribute3D.VertexAttribute)
    position_attr.setVertexBaseType(QAttribute3D.Float)
    position_attr.setVertexSize(3)
    position_attr.setByteStride(20)
    position_attr.setCount((seg_count + 1) * 2)
    position_attr.setBuffer(vertex_buffer)

    texcoord_attr = QAttribute3D(geometry)
    texcoord_attr.setName(QAttribute3D.defaultTextureCoordinateAttributeName())
    texcoord_attr.setAttributeType(QAttribute3D.VertexAttribute)
    texcoord_attr.setVertexBaseType(QAttribute3D.Float)
    texcoord_attr.setVertexSize(2)
    texcoord_attr.setByteStride(20)
    texcoord_attr.setByteOffset(12)
    texcoord_attr.setCount((seg_count + 1) * 2)
    texcoord_attr.setBuffer(vertex_buffer)

    index_blob = QByteArray()
    for index in indices:
        index_blob.append(pack("<I", index))
    index_buffer = QBuffer3D(geometry)
    index_buffer.setData(index_blob)

    index_attr = QAttribute3D(geometry)
    index_attr.setAttributeType(QAttribute3D.IndexAttribute)
    index_attr.setVertexBaseType(QAttribute3D.UnsignedInt)
    index_attr.setCount(len(indices))
    index_attr.setBuffer(index_buffer)

    geometry.addAttribute(position_attr)
    geometry.addAttribute(texcoord_attr)
    geometry.addAttribute(index_attr)

    renderer = QGeometryRenderer3D(owner)
    renderer.setGeometry(geometry)
    renderer.setPrimitiveType(QGeometryRenderer3D.Triangles)
    renderer.setVertexCount(len(indices))
    return renderer


def apply_native_geometry_material(material, native_geometry) -> None:
    if hasattr(material, "setShininess"):
        try:
            material.setShininess(8.0)
        except Exception:
            pass
    red, green, blue = native_preview_rgb(
        model_name=native_geometry.model_name,
        level_name=native_geometry.level_name,
        part_name=native_geometry.part_name,
        group_start=native_geometry.group_start,
        group_count=native_geometry.group_count,
    )
    if hasattr(material, "setAmbient"):
        try:
            material.setAmbient(QColor(max(red - 20, 80), max(green - 20, 80), max(blue - 20, 80)))
        except Exception:
            pass
    if hasattr(material, "setTexture"):
        return
    if hasattr(material, "setDiffuse"):
        material.setDiffuse(QColor(red, green, blue))


def _decode_dds_to_qimage(texture_path) -> QImage | None:
    """Decode a DDS (or TGA) texture file to QImage via Pillow."""
    try:
        from pathlib import Path
        from PIL import Image as PILImage

        img = PILImage.open(Path(texture_path))
        img = img.convert("RGBA")
        width, height = img.size
        raw_data = img.tobytes("raw", "BGRA")
        qimage = QImage(raw_data, width, height, QImage.Format.Format_ARGB32)
        # Force a deep copy so the QImage owns its data
        return qimage.copy()
    except Exception:
        return None


class _DdsTextureImage(QPaintedTextureImage3D):
    """QPaintedTextureImage that paints a pre-decoded QImage."""

    def __init__(self, qimage: QImage, parent=None):
        super().__init__(parent)
        self._qimage = qimage
        self.setSize(QSize(qimage.width(), qimage.height()))

    def paint(self, painter):
        painter.drawImage(0, 0, self._qimage)


def _configure_qt3d_texture(texture, qimage: QImage | None = None) -> None:
    if texture is None:
        return
    try:
        if qimage is not None and hasattr(texture, "setWidth"):
            texture.setWidth(int(qimage.width()))
        if qimage is not None and hasattr(texture, "setHeight"):
            texture.setHeight(int(qimage.height()))
        if hasattr(texture, "setDepth"):
            texture.setDepth(1)
        if hasattr(texture, "setLayers"):
            texture.setLayers(1)
        if hasattr(texture, "setMipLevels"):
            texture.setMipLevels(1)
        if hasattr(texture, "setAutoMipMapGenerationEnabled"):
            texture.setAutoMipMapGenerationEnabled(False)
        elif hasattr(texture, "setGenerateMipMaps"):
            texture.setGenerateMipMaps(False)
        if QAbstractTexture3D is not None and hasattr(texture, "setFormat"):
            try:
                texture.setFormat(QAbstractTexture3D.RGBA8_UNorm)
            except Exception:
                pass
    except Exception:
        pass


def _build_texture_object(*, owner, texture_path, texture_refs: list[object]) -> object | None:
    texture = None
    path_obj = Path(texture_path)
    suffix = path_obj.suffix.lower()

    if QTextureLoader3D is not None:
        try:
            texture = QTextureLoader3D(owner)
            texture.setSource(QUrl.fromLocalFile(str(path_obj)))
            _configure_qt3d_texture(texture)
            texture_refs.append(texture)
            if suffix != ".dds":
                return texture
        except Exception:
            texture = None

    if QPaintedTextureImage3D is not None and QTexture2D_3D is not None:
        qimage = _decode_dds_to_qimage(texture_path)
        if qimage is not None and not qimage.isNull():
            texture = QTexture2D_3D(owner)
            _configure_qt3d_texture(texture, qimage)
            tex_image = _DdsTextureImage(qimage, texture)
            texture.addTextureImage(tex_image)
            texture_refs.append(texture)
            texture_refs.append(tex_image)
            return texture

    return texture


def build_qt3d_texture_material(
    *,
    owner,
    texture_path,
    texture_refs: list[object],
) -> object | None:
    if texture_path is None:
        return None
    texture = _build_texture_object(owner=owner, texture_path=texture_path, texture_refs=texture_refs)
    if texture is None:
        return None
    if QTextureMaterial3D is not None:
        material = QTextureMaterial3D(owner)
        if hasattr(material, "setTexture"):
            material.setTexture(texture)
            _disable_backface_culling(material)
            return material
    if QDiffuseMapMaterial3D is not None:
        material = QDiffuseMapMaterial3D(owner)
        if hasattr(material, "setDiffuse"):
            material.setDiffuse(texture)
            _disable_backface_culling(material)
            return material
    return None


def build_native_geometry_material(
    *,
    owner,
    native_geometry,
    texture_refs: list[object],
    texture_resolver: Callable[[object], object | None] | None = None,
    allow_textures: bool = True,
) -> object:
    texture_path = texture_resolver(native_geometry) if allow_textures and texture_resolver is not None else None
    if allow_textures and texture_path is not None:
        texture = _build_texture_object(owner=owner, texture_path=texture_path, texture_refs=texture_refs)
        if texture is not None:
            if QTextureMaterial3D is not None:
                material = QTextureMaterial3D(owner)
                if hasattr(material, "setTexture"):
                    material.setTexture(texture)
                    _disable_backface_culling(material)
                    return material
            if QDiffuseMapMaterial3D is not None:
                material = QDiffuseMapMaterial3D(owner)
                if hasattr(material, "setDiffuse"):
                    material.setDiffuse(texture)
                    _disable_backface_culling(material)
                    return material
    material = QPhongMaterial3D(owner)
    _disable_backface_culling(material)
    return material
