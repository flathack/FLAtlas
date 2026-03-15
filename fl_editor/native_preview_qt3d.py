from __future__ import annotations

from struct import pack
from typing import Callable

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
except Exception:
    QPaintedTextureImage3D = None
    QTexture2D_3D = None


def native_preview_qt3d_available() -> bool:
    return all((QGeometryRenderer3D, QGeometry3D, QAttribute3D, QBuffer3D, QPhongMaterial3D, QEntity3D, QTransform3D))


def build_native_geometry_renderer(native_geometry, *, owner) -> object:
    geometry = QGeometry3D(owner)

    vertex_blob = QByteArray()
    has_uvs = bool(native_geometry.tex_coords) and len(native_geometry.tex_coords) == len(native_geometry.positions)
    if has_uvs:
        # Interleaved: position (3f) + texcoord (2f) = 20 bytes per vertex
        for (x, y, z), (u, v) in zip(native_geometry.positions, native_geometry.tex_coords):
            vertex_blob.append(pack("<3f2f", x, y, z, u, v))
        byte_stride = 20
    else:
        for x, y, z in native_geometry.positions:
            vertex_blob.append(pack("<3f", x, y, z))
        byte_stride = 12
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

    if has_uvs:
        texcoord_attr = QAttribute3D(geometry)
        texcoord_attr.setName(QAttribute3D.defaultTextureCoordinateAttributeName())
        texcoord_attr.setAttributeType(QAttribute3D.VertexAttribute)
        texcoord_attr.setVertexBaseType(QAttribute3D.Float)
        texcoord_attr.setVertexSize(2)
        texcoord_attr.setByteStride(byte_stride)
        texcoord_attr.setByteOffset(12)
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
    renderer = build_native_wireframe_renderer(native_geometry, owner=entity)
    transform = QTransform3D(entity)
    material = QPhongMaterial3D(entity)
    material.setDiffuse(QColor(240, 240, 240))
    entity.addComponent(renderer)
    entity.addComponent(transform)
    entity.addComponent(material)
    entity.setEnabled(False)
    return entity


def build_native_wireframe_renderer(native_geometry, *, owner) -> object:
    geometry = QGeometry3D(owner)

    vertex_blob = QByteArray()
    for x, y, z in native_geometry.positions:
        vertex_blob.append(pack("<3f", x, y, z))
    vertex_buffer = QBuffer3D(geometry)
    vertex_buffer.setData(vertex_blob)

    position_attr = QAttribute3D(geometry)
    position_attr.setName(QAttribute3D.defaultPositionAttributeName())
    position_attr.setAttributeType(QAttribute3D.VertexAttribute)
    position_attr.setVertexBaseType(QAttribute3D.Float)
    position_attr.setVertexSize(3)
    position_attr.setByteStride(12)
    position_attr.setCount(len(native_geometry.positions))
    position_attr.setBuffer(vertex_buffer)

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
    geometry.addAttribute(index_attr)

    renderer = QGeometryRenderer3D(owner)
    renderer.setGeometry(geometry)
    renderer.setPrimitiveType(QGeometryRenderer3D.Lines)
    renderer.setVertexCount(len(line_indices))
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


def build_native_geometry_material(
    *,
    owner,
    native_geometry,
    texture_refs: list[object],
    texture_resolver: Callable[[object], object | None] | None = None,
) -> object:
    texture_path = texture_resolver(native_geometry) if texture_resolver is not None else None
    if texture_path is not None:
        # Decode DDS/TGA via Pillow → QImage → QPaintedTextureImage (no file conversion)
        if QPaintedTextureImage3D is not None and QTexture2D_3D is not None:
            qimage = _decode_dds_to_qimage(texture_path)
            if qimage is not None and not qimage.isNull():
                texture = QTexture2D_3D(owner)
                tex_image = _DdsTextureImage(qimage, texture)
                texture.addTextureImage(tex_image)
                texture_refs.append(texture)
                texture_refs.append(tex_image)
                if QTextureMaterial3D is not None:
                    material = QTextureMaterial3D(owner)
                    if hasattr(material, "setTexture"):
                        material.setTexture(texture)
                        return material
                if QDiffuseMapMaterial3D is not None:
                    material = QDiffuseMapMaterial3D(owner)
                    if hasattr(material, "setDiffuse"):
                        material.setDiffuse(texture)
                        return material
    return QPhongMaterial3D(owner)
