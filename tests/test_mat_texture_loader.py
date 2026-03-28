from pathlib import Path

from fl_editor import mat_texture_loader


def test_find_best_mat_texture_for_planet_surface_prefers_equirectangular_projection(monkeypatch, tmp_path: Path):
    wide = tmp_path / "wide_surface.dds"
    square = tmp_path / "square_surface.dds"
    wide.write_text("wide", encoding="utf-8")
    square.write_text("square", encoding="utf-8")

    monkeypatch.setattr(
        mat_texture_loader,
        "_texture_dimensions",
        lambda path: (2048, 1024) if Path(path) == wide else (1024, 1024),
    )

    chosen = mat_texture_loader.find_best_mat_texture_for_planet_surface(
        {
            "planet_surface_large": square,
            "planet_surface": wide,
        }
    )

    assert chosen == wide


def test_find_best_mat_texture_for_planet_surface_avoids_cap_textures(monkeypatch, tmp_path: Path):
    surface = tmp_path / "earthcity01.dds"
    cap = tmp_path / "earthcitycap.dds"
    surface.write_text("surface", encoding="utf-8")
    cap.write_text("cap", encoding="utf-8")

    monkeypatch.setattr(mat_texture_loader, "_texture_dimensions", lambda _path: (2048, 1024))

    chosen = mat_texture_loader.find_best_mat_texture_for_planet_surface(
        {
            "earthcity01": surface,
            "earthcitycap": cap,
        }
    )

    assert chosen == surface


def test_find_mat_texture_for_planet_archetype_avoids_cap_textures(tmp_path: Path):
    surface = tmp_path / "earthcity01.dds"
    cap = tmp_path / "earthcitycap.dds"
    surface.write_text("surface", encoding="utf-8")
    cap.write_text("cap", encoding="utf-8")

    chosen = mat_texture_loader.find_mat_texture_for_planet_archetype(
        "planet_earthcity_3000",
        {
            "earthcity01": surface,
            "earthcitycap": cap,
        },
    )

    assert chosen == surface
