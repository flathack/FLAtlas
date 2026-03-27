from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QImage

from fl_editor.freelancer_mesh_data import FreelancerBounds
from fl_editor.models import SolarObject
from fl_editor.native_preview_geometry import NativePreviewGeometry
from fl_editor.native_preview_scene_data import NativePreviewSceneData
from fl_editor.top_view_icons import (
    load_cached_top_view_icon,
    render_planet_texture_top_view_icon,
    render_native_scene_top_view_icon,
    save_top_view_icon,
    top_view_icon_cache_path,
)


def _sample_scene_data() -> NativePreviewSceneData:
    geometry = NativePreviewGeometry(
        model_name="sample",
        level_name="Level0",
        part_name="sample",
        group_start=0,
        group_count=1,
        positions=(
            (-2.0, 0.0, -4.0),
            (2.0, 0.0, -4.0),
            (0.0, 0.0, 4.0),
            (0.0, 3.0, 0.0),
        ),
        indices=(0, 1, 3, 1, 2, 3, 2, 0, 3, 0, 2, 1),
        vertex_stride=32,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(-2.0, 0.0, -4.0), max_xyz=(2.0, 3.0, 4.0), radius=4.5),
    )
    return NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("sample",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )


def test_render_native_scene_top_view_icon_returns_image(qapp):
    image = render_native_scene_top_view_icon(_sample_scene_data(), size=64)

    assert image is not None
    assert not image.isNull()
    assert image.width() == 64
    assert image.height() == 64


def test_render_native_scene_top_view_icon_accepts_transform_rotation(qapp):
    image = render_native_scene_top_view_icon(_sample_scene_data(), size=64, rotate_euler_deg=(90.0, 0.0, 0.0))

    assert image is not None
    assert not image.isNull()


def test_top_view_icon_cache_roundtrip(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr("fl_editor.top_view_icons.TOP_VIEW_ICON_CACHE_ROOT", tmp_path / "icons")
    image = render_native_scene_top_view_icon(_sample_scene_data(), size=64)
    assert image is not None and not image.isNull()

    model_path = Path(tmp_path / "sample.cmp")
    model_path.write_bytes(b"cmp")
    cache_path = top_view_icon_cache_path(
        profile_key="vanilla-test",
        archetype="space_station01",
        model_path=model_path,
    )

    assert save_top_view_icon(cache_path, image)

    pixmap = load_cached_top_view_icon(cache_path)

    assert pixmap is not None
    assert not pixmap.isNull()


def test_render_planet_texture_top_view_icon_returns_image(qapp, tmp_path):
    texture_path = tmp_path / "planet.png"
    image = QImage(8, 4, QImage.Format.Format_ARGB32)
    image.fill(QColor(20, 80, 180))
    for x_pos in range(image.width()):
        for y_pos in range(image.height()):
            image.setPixelColor(x_pos, y_pos, QColor(20 + x_pos * 20, 80 + y_pos * 20, 160))
    assert image.save(str(texture_path), "PNG")

    icon = render_planet_texture_top_view_icon(texture_path, size=48)

    assert icon is not None
    assert not icon.isNull()
    assert icon.width() == 48
    assert icon.height() == 48


def test_solar_object_applies_rotate_y_on_init_and_text_update(qapp):
    obj = SolarObject(
        {"nickname": "station", "archetype": "station", "pos": "0,0,0", "rotate": "10, 35, 5", "_entries": []},
        1.0,
    )
    assert obj.rotation() == -35.0
    assert obj.label.rotation() == 35.0

    obj.apply_text("nickname = station\narchetype = station\npos = 0,0,0\nrotate = 0, 90, 0")

    assert obj.rotation() == -90.0
    assert obj.label.rotation() == 90.0
