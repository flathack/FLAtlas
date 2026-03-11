from __future__ import annotations

from struct import pack
from typing import Callable

from PySide6.QtCore import QByteArray, QUrl
from PySide6.QtGui import QColor

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


def native_preview_qt3d_available() -> bool:
    return all((QGeometryRenderer3D, QGeometry3D, QAttribute3D, QBuffer3D, QPhongMaterial3D, QEntity3D, QTransform3D))


def build_native_geometry_renderer(native_geometry, *, owner) -> object:
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

    geometry.addAttribute(position_attr)
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
            material.setAmbient(QColor(max(red - 48, 24), max(green - 48, 24), max(blue - 48, 24)))
        except Exception:
            pass
    if hasattr(material, "setDiffuse"):
        material.setDiffuse(QColor(red, green, blue))


def build_native_geometry_material(
    *,
    owner,
    native_geometry,
    texture_refs: list[object],
    texture_resolver: Callable[[object], object | None] | None = None,
) -> object:
    texture_path = texture_resolver(native_geometry) if texture_resolver is not None else None
    if texture_path is not None and QTextureLoader3D is not None:
        texture = QTextureLoader3D(owner)
        texture.setSource(QUrl.fromLocalFile(str(texture_path)))
        texture_refs.append(texture)
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
