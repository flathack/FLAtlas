from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


DIRECT_RENDERABLE_EXTENSIONS = (
    ".obj",
    ".stl",
    ".ply",
    ".gltf",
    ".glb",
    ".dae",
    ".fbx",
    ".3ds",
)
FREELANCER_NATIVE_EXTENSIONS = (".cmp", ".3db")
FREELANCER_PRIMITIVE_EXTENSIONS = (".sph",)

DEFAULT_ARCH_FILES = (
    "DATA/SOLAR/solararch.ini",
    "DATA/SHIPS/shiparch.ini",
    "DATA/EQUIPMENT/stationarch.ini",
    "DATA/EQUIPMENT/asteroidarch.ini",
)


@dataclass(frozen=True)
class ResolvedFreelancerModel:
    archetype: str
    da_archetype: str | None
    model_path: Path | None


@dataclass(frozen=True)
class PreviewMeshResolution:
    requested_path: Path
    preview_path: Path | None
    kind: str
    extension: str

    @property
    def directly_renderable(self) -> bool:
        return self.kind in {"direct_renderable", "alternate_renderable"}

    @property
    def is_freelancer_native(self) -> bool:
        return self.kind == "freelancer_native"

    @property
    def is_freelancer_primitive(self) -> bool:
        return self.kind == "freelancer_primitive"


def build_archetype_model_index(
    game_path: str,
    resolve_game_path: Callable[[str, str], Path | None],
    parse_ini: Callable[[str], list[tuple[str, list[tuple[str, str]]]]],
    arch_files: tuple[str, ...] = DEFAULT_ARCH_FILES,
) -> dict[str, str]:
    arch_map: dict[str, str] = {}
    if not game_path:
        return arch_map

    for rel in arch_files:
        ini = resolve_game_path(game_path, rel)
        if not ini or not ini.exists():
            continue
        try:
            sections = parse_ini(str(ini))
        except Exception:
            continue
        for _section_name, entries in sections:
            nickname = ""
            da_archetype = ""
            for key, value in entries:
                key_l = str(key).strip().lower()
                if key_l == "nickname":
                    nickname = str(value).strip()
                elif key_l == "da_archetype":
                    da_archetype = str(value).strip()
            if nickname and da_archetype:
                arch_map.setdefault(nickname.lower(), da_archetype)
    return arch_map


def resolve_model_for_archetype(
    archetype: str,
    game_path: str,
    arch_map: dict[str, str],
    resolve_game_path: Callable[[str, str], Path | None],
) -> ResolvedFreelancerModel:
    archetype_txt = str(archetype or "").strip()
    if not archetype_txt:
        return ResolvedFreelancerModel(archetype="", da_archetype=None, model_path=None)

    da_archetype = arch_map.get(archetype_txt.lower())
    if not da_archetype:
        return ResolvedFreelancerModel(archetype=archetype_txt, da_archetype=None, model_path=None)

    model_path = resolve_game_path(game_path, da_archetype) if game_path else None
    return ResolvedFreelancerModel(
        archetype=archetype_txt,
        da_archetype=da_archetype,
        model_path=model_path,
    )


def resolve_preview_mesh_candidate(model_path: Path) -> PreviewMeshResolution:
    ext = model_path.suffix.lower()
    if ext in DIRECT_RENDERABLE_EXTENSIONS and model_path.exists():
        return PreviewMeshResolution(
            requested_path=model_path,
            preview_path=model_path,
            kind="direct_renderable",
            extension=ext,
        )

    for candidate_ext in DIRECT_RENDERABLE_EXTENSIONS:
        candidate = model_path.with_suffix(candidate_ext)
        if candidate.exists():
            return PreviewMeshResolution(
                requested_path=model_path,
                preview_path=candidate,
                kind="alternate_renderable",
                extension=ext,
            )

    if ext in FREELANCER_NATIVE_EXTENSIONS:
        return PreviewMeshResolution(
            requested_path=model_path,
            preview_path=None,
            kind="freelancer_native",
            extension=ext,
        )

    if ext in FREELANCER_PRIMITIVE_EXTENSIONS:
        return PreviewMeshResolution(
            requested_path=model_path,
            preview_path=None,
            kind="freelancer_primitive",
            extension=ext,
        )

    return PreviewMeshResolution(
        requested_path=model_path,
        preview_path=None,
        kind="unrenderable",
        extension=ext,
    )
