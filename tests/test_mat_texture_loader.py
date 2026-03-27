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
