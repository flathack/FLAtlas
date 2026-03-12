from __future__ import annotations

from pathlib import Path

from fl_editor.freelancer_model_resolver import (
    build_archetype_model_index,
    resolve_model_for_archetype,
    resolve_preview_mesh_candidate,
)


def test_build_archetype_model_index_collects_first_da_archetype(tmp_path):
    solararch = tmp_path / "solararch.ini"
    solararch.write_text(
        "[Solar]\n"
        "nickname = station_a\n"
        "da_archetype = solar\\station_a.cmp\n\n"
        "[Solar]\n"
        "nickname = station_a\n"
        "da_archetype = solar\\station_a_override.cmp\n",
        encoding="utf-8",
    )

    def _resolve(_game_path: str, rel: str):
        if rel == "DATA/SOLAR/solararch.ini":
            return solararch
        return None

    def _parse(path: str):
        assert path == str(solararch)
        return [
            ("Solar", [("nickname", "station_a"), ("da_archetype", r"solar\station_a.cmp")]),
            ("Solar", [("nickname", "station_a"), ("da_archetype", r"solar\station_a_override.cmp")]),
        ]

    arch_map = build_archetype_model_index("game", _resolve, _parse, arch_files=("DATA/SOLAR/solararch.ini",))

    assert arch_map == {"station_a": r"solar\station_a.cmp"}


def test_resolve_model_for_archetype_returns_resolved_path(tmp_path):
    model = tmp_path / "station.cmp"
    model.write_text("cmp", encoding="utf-8")

    resolved = resolve_model_for_archetype(
        archetype="station_a",
        game_path="game",
        arch_map={"station_a": r"solar\station.cmp"},
        resolve_game_path=lambda _game_path, rel: model if rel == r"solar\station.cmp" else None,
    )

    assert resolved.da_archetype == r"solar\station.cmp"
    assert resolved.model_path == model


def test_preview_mesh_resolution_detects_direct_renderable(tmp_path):
    mesh = tmp_path / "station.glb"
    mesh.write_text("mesh", encoding="utf-8")

    resolution = resolve_preview_mesh_candidate(mesh)

    assert resolution.preview_path == mesh
    assert resolution.kind == "direct_renderable"
    assert resolution.directly_renderable is True


def test_preview_mesh_resolution_detects_alternate_renderable(tmp_path):
    cmp_path = tmp_path / "station.cmp"
    glb_path = tmp_path / "station.glb"
    glb_path.write_text("mesh", encoding="utf-8")

    resolution = resolve_preview_mesh_candidate(cmp_path)

    assert resolution.preview_path == glb_path
    assert resolution.kind == "alternate_renderable"
    assert resolution.directly_renderable is True


def test_preview_mesh_resolution_marks_native_freelancer_formats(tmp_path):
    cmp_path = tmp_path / "station.cmp"
    resolution = resolve_preview_mesh_candidate(cmp_path)
    assert resolution.preview_path is None
    assert resolution.kind == "freelancer_native"
    assert resolution.is_freelancer_native is True

    three_db = tmp_path / "station.3db"
    resolution_3db = resolve_preview_mesh_candidate(three_db)
    assert resolution_3db.preview_path is None
    assert resolution_3db.kind == "freelancer_native"


def test_preview_mesh_resolution_marks_sphere_primitive(tmp_path):
    sph_path = tmp_path / "sun.sph"

    resolution = resolve_preview_mesh_candidate(sph_path)

    assert resolution.preview_path is None
    assert resolution.kind == "freelancer_primitive"
