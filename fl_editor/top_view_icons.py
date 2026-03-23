from __future__ import annotations

import hashlib
import math
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QQuaternion, QVector3D

from .native_preview_scene_data import NativePreviewSceneData


TOP_VIEW_ICON_CACHE_ROOT = Path.home() / ".cache" / "fl_editor" / "top_view_icons"
TOP_VIEW_ICON_RENDER_VERSION = "v3"


def top_view_icon_cache_root() -> Path:
    TOP_VIEW_ICON_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    return TOP_VIEW_ICON_CACHE_ROOT


def top_view_icon_cache_path(*, profile_key: str, archetype: str, model_path: Path) -> Path:
    try:
        stat = model_path.stat()
        stamp = f"{stat.st_size}:{stat.st_mtime_ns}"
    except Exception:
        stamp = "0:0"
    raw_key = "||".join(
        (
            TOP_VIEW_ICON_RENDER_VERSION,
            str(profile_key or "").strip().lower(),
            str(archetype or "").strip().lower(),
            str(model_path).replace("\\", "/").lower(),
            stamp,
        )
    )
    digest = hashlib.sha1(raw_key.encode("utf-8", errors="ignore")).hexdigest()
    return top_view_icon_cache_root() / f"{digest}.png"


def load_cached_top_view_icon(cache_path: Path) -> QPixmap | None:
    if cache_path is None or not cache_path.exists():
        return None
    pixmap = QPixmap(str(cache_path))
    if pixmap.isNull():
        return None
    return pixmap


def save_top_view_icon(cache_path: Path, image: QImage) -> bool:
    if cache_path is None or image is None or image.isNull():
        return False
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        return False
    return bool(image.save(str(cache_path), "PNG"))


def render_native_scene_top_view_icon(
    scene_data: NativePreviewSceneData | None,
    *,
    size: int = 72,
    rotate_euler_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
    fill_color: QColor | None = None,
    outline_color: QColor | None = None,
    background_alpha: int = 0,
) -> QImage | None:
    if scene_data is None or not getattr(scene_data, "geometries", ()):
        return None
    icon_size = max(24, int(size))
    rotation = QQuaternion.fromEulerAngles(
        float(rotate_euler_deg[0]),
        float(rotate_euler_deg[1]),
        float(rotate_euler_deg[2]),
    )
    points: list[tuple[float, float, float]] = []
    for geometry in scene_data.geometries:
        for x_pos, y_pos, z_pos in geometry.positions:
            if math.isfinite(x_pos) and math.isfinite(y_pos) and math.isfinite(z_pos):
                rotated = rotation.rotatedVector(QVector3D(float(x_pos), float(y_pos), float(z_pos)))
                points.append((float(rotated.x()), float(rotated.y()), float(rotated.z())))
    if len(points) < 3:
        return None

    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_z = min(point[2] for point in points)
    max_z = max(point[2] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)
    span_x = max(max_x - min_x, 1e-6)
    span_z = max(max_z - min_z, 1e-6)
    span_y = max(max_y - min_y, 1e-6)
    margin = icon_size * 0.14
    draw_span = max(1.0, float(icon_size) - margin * 2.0)
    scale = draw_span / max(span_x, span_z, 1.0)
    center_x = (min_x + max_x) * 0.5
    center_z = (min_z + max_z) * 0.5

    image = QImage(icon_size, icon_size, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, max(0, min(255, int(background_alpha)))))
    painter = QPainter(image)
    try:
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        base_fill = QColor(fill_color) if fill_color is not None else QColor(185, 215, 245, 220)
        base_outline = QColor(outline_color) if outline_color is not None else QColor(120, 175, 225, 235)
        outline_pen = QPen(base_outline)
        outline_pen.setWidthF(max(1.0, icon_size / 28.0))
        outline_pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(Qt.NoPen)

        triangle_count = 0
        merged_outline = QPainterPath()
        for geometry_index, geometry in enumerate(scene_data.geometries):
            positions = geometry.positions
            indices = geometry.indices
            if len(positions) < 3:
                continue
            step = 3 if len(indices) >= 3 else 0
            if step == 0:
                continue
            for index in range(0, len(indices) - 2, 3):
                try:
                    p0 = _rotate_point(positions[indices[index]], rotation)
                    p1 = _rotate_point(positions[indices[index + 1]], rotation)
                    p2 = _rotate_point(positions[indices[index + 2]], rotation)
                except Exception:
                    continue
                polygon = QPolygonF(
                    (
                        _map_top_view_point(
                            point=p0,
                            center_x=center_x,
                            center_z=center_z,
                            scale=scale,
                            icon_size=icon_size,
                        ),
                        _map_top_view_point(
                            point=p1,
                            center_x=center_x,
                            center_z=center_z,
                            scale=scale,
                            icon_size=icon_size,
                        ),
                        _map_top_view_point(
                            point=p2,
                            center_x=center_x,
                            center_z=center_z,
                            scale=scale,
                            icon_size=icon_size,
                        ),
                    )
                )
                if polygon.boundingRect().width() <= 0.0 and polygon.boundingRect().height() <= 0.0:
                    continue
                avg_height = (float(p0[1]) + float(p1[1]) + float(p2[1])) / 3.0
                shade = 0.70 + 0.30 * ((avg_height - min_y) / span_y)
                fill = _shade_color(base_fill, shade, geometry_index=geometry_index)
                painter.setBrush(fill)
                painter.drawPolygon(polygon)
                path = QPainterPath()
                path.addPolygon(polygon)
                merged_outline = merged_outline.united(path)
                triangle_count += 1
        if triangle_count <= 0:
            return None
        painter.setBrush(Qt.NoBrush)
        painter.setPen(outline_pen)
        painter.drawPath(merged_outline.simplified())
    finally:
        painter.end()
    return image


def _map_top_view_point(
    *,
    point: tuple[float, float, float],
    center_x: float,
    center_z: float,
    scale: float,
    icon_size: int,
) -> QPointF:
    x_pos, _y_pos, z_pos = point
    px = (float(icon_size) * 0.5) + ((float(x_pos) - center_x) * scale)
    # The 2D system editor uses positive Z downward on screen.
    py = (float(icon_size) * 0.5) + ((float(z_pos) - center_z) * scale)
    return QPointF(px, py)


def _shade_color(color: QColor, shade: float, *, geometry_index: int = 0) -> QColor:
    factor = max(0.45, min(1.25, float(shade)))
    drift = 1.0 + (0.025 * float(geometry_index % 5))
    out = QColor(color)
    out.setRed(max(0, min(255, int(out.red() * factor * drift))))
    out.setGreen(max(0, min(255, int(out.green() * factor))))
    out.setBlue(max(0, min(255, int(out.blue() * (factor / drift)))))
    return out


def _rotate_point(
    point: tuple[float, float, float],
    rotation: QQuaternion,
) -> tuple[float, float, float]:
    rotated = rotation.rotatedVector(QVector3D(float(point[0]), float(point[1]), float(point[2])))
    return (float(rotated.x()), float(rotated.y()), float(rotated.z()))


def render_planet_texture_top_view_icon(
    texture_path: Path | None,
    *,
    cloud_texture_path: Path | None = None,
    size: int = 96,
) -> QImage | None:
    base = _load_texture_image(texture_path)
    if base is None or base.isNull():
        return None
    cloud = _load_texture_image(cloud_texture_path)
    icon_size = max(32, int(size))
    image = QImage(icon_size, icon_size, QImage.Format.Format_ARGB32)
    image.fill(Qt.transparent)
    radius = (float(icon_size) * 0.5) - 1.0
    center = float(icon_size) * 0.5
    light_dir = _normalize3(0.35, 0.88, -0.18)

    for py in range(icon_size):
        ny = (center - (py + 0.5)) / radius
        for px in range(icon_size):
            nx = ((px + 0.5) - center) / radius
            rr = (nx * nx) + (ny * ny)
            if rr > 1.0:
                continue
            nz = math.sqrt(max(0.0, 1.0 - rr))
            lon = math.atan2(nx, nz)
            lat = math.asin(max(-1.0, min(1.0, ny)))
            base_color = _sample_equirectangular(base, lon=lon, lat=lat)
            if cloud is not None and not cloud.isNull():
                cloud_color = _sample_equirectangular(cloud, lon=lon + 0.08, lat=lat)
                base_color = _blend_rgba(base_color, cloud_color, alpha_scale=0.55)
            diffuse = max(0.25, min(1.0, _dot3((nx, ny, nz), light_dir)))
            rim = max(0.0, 1.0 - nz)
            shaded = QColor(base_color)
            shaded.setRed(max(0, min(255, int(shaded.red() * (0.58 + diffuse * 0.52) + 28.0 * rim))))
            shaded.setGreen(max(0, min(255, int(shaded.green() * (0.58 + diffuse * 0.52) + 18.0 * rim))))
            shaded.setBlue(max(0, min(255, int(shaded.blue() * (0.62 + diffuse * 0.48) + 42.0 * rim))))
            shaded.setAlpha(255)
            image.setPixelColor(px, py, shaded)

    painter = QPainter(image)
    try:
        painter.setRenderHint(QPainter.Antialiasing, True)
        edge_pen = QPen(QColor(210, 230, 255, 140))
        edge_pen.setWidthF(max(1.0, icon_size / 42.0))
        painter.setPen(edge_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(center, center), radius - 0.5, radius - 0.5)
    finally:
        painter.end()
    return image


def _load_texture_image(texture_path: Path | None) -> QImage | None:
    if texture_path is None:
        return None
    image = QImage(str(texture_path))
    if image.isNull():
        try:
            from PIL import Image as PILImage

            with PILImage.open(texture_path) as pil_image:
                pil_image = pil_image.convert("RGBA")
                width, height = pil_image.size
                raw_data = pil_image.tobytes("raw", "BGRA")
                image = QImage(raw_data, width, height, QImage.Format.Format_ARGB32).copy()
        except Exception:
            return None
    return image


def _sample_equirectangular(image: QImage, *, lon: float, lat: float) -> QColor:
    width = max(1, image.width())
    height = max(1, image.height())
    u = ((lon / (2.0 * math.pi)) + 0.5) % 1.0
    v = 0.5 - (lat / math.pi)
    px = int(round(u * (width - 1)))
    py = int(round(max(0.0, min(1.0, v)) * (height - 1)))
    return image.pixelColor(px, py)


def _normalize3(x_pos: float, y_pos: float, z_pos: float) -> tuple[float, float, float]:
    length = math.sqrt((x_pos * x_pos) + (y_pos * y_pos) + (z_pos * z_pos))
    if length <= 1e-9:
        return (0.0, 0.0, 1.0)
    return (x_pos / length, y_pos / length, z_pos / length)


def _dot3(lhs: tuple[float, float, float], rhs: tuple[float, float, float]) -> float:
    return (lhs[0] * rhs[0]) + (lhs[1] * rhs[1]) + (lhs[2] * rhs[2])


def _blend_rgba(base: QColor, overlay: QColor, *, alpha_scale: float = 1.0) -> QColor:
    alpha = max(0.0, min(1.0, (overlay.alphaF() if overlay.alpha() > 0 else 0.0) * float(alpha_scale)))
    inv = 1.0 - alpha
    return QColor(
        int(base.red() * inv + overlay.red() * alpha),
        int(base.green() * inv + overlay.green() * alpha),
        int(base.blue() * inv + overlay.blue() * alpha),
        255,
    )
