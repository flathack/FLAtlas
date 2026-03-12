from __future__ import annotations

from pathlib import Path
import tempfile

from PySide6.QtGui import QColor, QImage, QPainter


def ensure_darkened_sky_texture(src_path: Path, *, darken_alpha: int = 150, cache_dir: Path | None = None) -> Path:
    try:
        tmp_dir = cache_dir or (Path(tempfile.gettempdir()) / "fl_atlas")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        dst_path = tmp_dir / f"star-background-dark-a{int(darken_alpha)}.png"
        if dst_path.exists() and dst_path.stat().st_mtime >= src_path.stat().st_mtime:
            return dst_path
        img = QImage(str(src_path))
        if img.isNull():
            return src_path
        out = img.convertToFormat(QImage.Format_ARGB32)
        painter = QPainter(out)
        painter.fillRect(out.rect(), QColor(0, 0, 0, int(darken_alpha)))
        painter.end()
        if out.save(str(dst_path), "PNG"):
            return dst_path
    except Exception:
        pass
    return src_path
