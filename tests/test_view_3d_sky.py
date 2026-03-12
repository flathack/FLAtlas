from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QImage

from fl_editor.view_3d_sky import ensure_darkened_sky_texture


def test_ensure_darkened_sky_texture_creates_cached_png(tmp_path: Path):
    src_path = tmp_path / "source.png"
    cache_dir = tmp_path / "cache"
    image = QImage(4, 4, QImage.Format_ARGB32)
    image.fill(QColor(255, 255, 255, 255))
    assert image.save(str(src_path), "PNG")

    result = ensure_darkened_sky_texture(src_path, cache_dir=cache_dir)

    assert result != src_path
    assert result.exists()
    darkened = QImage(str(result))
    assert not darkened.isNull()


def test_ensure_darkened_sky_texture_returns_source_for_invalid_image(tmp_path: Path):
    src_path = tmp_path / "broken.png"
    src_path.write_text("not an image", encoding="utf-8")

    result = ensure_darkened_sky_texture(src_path, cache_dir=tmp_path / "cache")

    assert result == src_path
