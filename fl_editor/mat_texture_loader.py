"""Extract DDS textures from Freelancer .mat (material library) files.

Freelancer .mat files are UTF containers with:
- "material library" node: material definitions (name → Dt_name mapping)
- "texture library" node: MIPS blobs containing DDS-format texture data

This module extracts the MIPS data as .dds files to a temporary directory.
The DDS decoding is handled at render time in native_preview_qt3d.py.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from .cmp_loader import UtfFileHeader, parse_utf_header, _parse_utf_nodes
from .freelancer_mesh_data import FreelancerUtfNode

_mat_texture_cache: dict[Path, dict[str, Path]] = {}
_mat_temp_dirs: list[tempfile.TemporaryDirectory[str]] = []


def extract_mat_textures(mat_path: Path) -> dict[str, Path]:
    """Parse a .mat file, extract MIPS textures, return {texture_name: dds_path}."""
    resolved = mat_path.resolve()
    if resolved in _mat_texture_cache:
        return _mat_texture_cache[resolved]

    try:
        raw = resolved.read_bytes()
    except OSError:
        _mat_texture_cache[resolved] = {}
        return {}

    try:
        header = parse_utf_header(raw)
        nodes = _parse_utf_nodes(raw, header)
    except (ValueError, Exception):
        _mat_texture_cache[resolved] = {}
        return {}

    # Find all MIPS nodes under "texture library"
    mips_entries: list[tuple[str, int, int]] = []
    for node in nodes:
        if node.name != "MIPS" or node.data_offset is None or not node.used_size:
            continue
        path = node.path or ""
        path_lower = path.lower()
        if "texture library" not in path_lower:
            continue
        # Path looks like: "\texture library/arch_tile1.tga/MIPS"
        parts = path.replace("\\", "/").strip("/").split("/")
        if len(parts) >= 3:
            texture_name = parts[-2]
        else:
            continue
        mips_entries.append((texture_name, node.data_offset, node.used_size))

    if not mips_entries:
        _mat_texture_cache[resolved] = {}
        return {}

    tmp = tempfile.TemporaryDirectory(prefix="flatlas_mat_")
    _mat_temp_dirs.append(tmp)
    tmp_dir = Path(tmp.name)

    result: dict[str, Path] = {}
    for texture_name, data_offset, data_size in mips_entries:
        dds_data = raw[data_offset:data_offset + data_size]
        if len(dds_data) < 4 or dds_data[:4] != b'DDS ':
            continue
        stem = Path(texture_name).stem
        dds_path = tmp_dir / f"{stem}.dds"
        try:
            dds_path.write_bytes(dds_data)
            result[texture_name.lower()] = dds_path
            result[stem.lower()] = dds_path
        except OSError:
            continue

    _mat_texture_cache[resolved] = result
    return result


def extract_all_mat_textures(
    mat_paths: tuple[Path, ...],
) -> dict[str, Path]:
    """Extract textures from multiple .mat files, merged into one dict."""
    merged: dict[str, Path] = {}
    for mat_path in mat_paths:
        merged.update(extract_mat_textures(mat_path))
    return merged


def find_best_mat_texture(mat_textures: dict[str, Path]) -> Path | None:
    """Pick the largest available texture as the 'best' default."""
    if not mat_textures:
        return None
    unique_paths: set[Path] = set(mat_textures.values())
    best: Path | None = None
    best_size = 0
    for path in unique_paths:
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > best_size:
            best_size = size
            best = path
    return best


def _texture_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        from PIL import Image as PILImage

        with PILImage.open(path) as image:
            width, height = image.size
        if width > 0 and height > 0:
            return int(width), int(height)
    except Exception:
        return None
    return None


def _planet_equirectangular_score(path: Path) -> int:
    dims = _texture_dimensions(path)
    if dims is None:
        return 0
    width, height = dims
    if width <= 0 or height <= 0:
        return 0
    ratio = float(width) / float(height)
    delta = abs(ratio - 2.0)
    return max(0, int(round(1000.0 - (delta * 1000.0))))


def find_best_mat_texture_for_planet_surface(mat_textures: dict[str, Path]) -> Path | None:
    """Prefer likely planet-surface textures over clouds, rings, and effect layers."""
    if not mat_textures:
        return None

    exclude_terms = (
        "cloud",
        "cld",
        "ring",
        "atmo",
        "atmos",
        "glow",
        "haze",
        "halo",
        "shine",
        "light",
    )
    prefer_terms = (
        "planet",
        "surface",
        "surf",
        "diffuse",
        "tex",
    )

    ranked: list[tuple[int, int, int, int, int, int, Path]] = []
    seen_paths: set[Path] = set()
    for name, path in mat_textures.items():
        if path in seen_paths:
            continue
        seen_paths.add(path)
        lowered = str(name or "").strip().lower()
        excluded = any(term in lowered for term in exclude_terms)
        is_cap = _is_planet_cap_texture_name(lowered)
        preferred = any(term in lowered for term in prefer_terms)
        try:
            size = int(path.stat().st_size)
        except OSError:
            size = 0
        eq_score = _planet_equirectangular_score(path)
        ranked.append((1 if preferred else 0, 0 if excluded else 1, 0 if is_cap else 1, eq_score, size, path))

    if not ranked:
        return None

    ranked.sort(reverse=True)
    return ranked[0][5]


def _normalize_texture_key(value: str) -> str:
    return "".join(ch for ch in str(value or "").strip().lower() if ch.isalnum())


def _is_planet_cap_texture_name(value: str) -> bool:
    normalized = _normalize_texture_key(value)
    return normalized.endswith("cap") and len(normalized) > 3


def _planet_texture_aliases(archetype: str) -> tuple[str, ...]:
    raw = str(archetype or "").strip().lower()
    if raw.startswith("planet_"):
        raw = raw[len("planet_") :]
    parts = [part for part in raw.split("_") if part]
    while parts and parts[-1].isdigit():
        parts.pop()
    core = "".join(parts)
    if not core:
        return ()

    aliases: list[str] = []
    for candidate in (core,):
        norm = _normalize_texture_key(candidate)
        if norm and norm not in aliases:
            aliases.append(norm)
        trimmed = norm
        for suffix in ("clouds", "cloud", "cld", "rings", "ring", "atmosphere", "atmos", "atmo", "atm"):
            if trimmed.endswith(suffix) and len(trimmed) > len(suffix) + 2:
                trimmed = trimmed[: -len(suffix)]
                if trimmed and trimmed not in aliases:
                    aliases.append(trimmed)
        for suffix in ("grck", "rock", "rck", "moon", "ice", "lava", "molten"):
            if norm.endswith(suffix) and len(norm) > len(suffix) + 2:
                reduced = norm[: -len(suffix)]
                if reduced and reduced not in aliases:
                    aliases.append(reduced)
        if norm.endswith("ed") and len(norm) > 5:
            reduced = norm[:-2]
            if reduced and reduced not in aliases:
                aliases.append(reduced)
    return tuple(sorted(aliases, key=len, reverse=True))


def find_mat_texture_for_planet_archetype(archetype: str, mat_textures: dict[str, Path]) -> Path | None:
    """Choose the original MAT texture that best matches a Freelancer planet archetype."""
    if not mat_textures:
        return None

    aliases = _planet_texture_aliases(archetype)
    exclude_terms = ("cloud", "cld", "ring", "atmo", "atmos", "glow", "haze", "halo", "shine", "light")
    prefer_terms = ("planet", "surface", "surf", "diffuse", "tex")

    ranked: list[tuple[int, int, int, int, int, Path]] = []
    seen_paths: set[Path] = set()
    for name, path in mat_textures.items():
        if path in seen_paths:
            continue
        seen_paths.add(path)
        lowered = str(name or "").strip().lower()
        normalized = _normalize_texture_key(lowered)
        alias_score = 0
        for alias in aliases:
            if not alias:
                continue
            if normalized == alias:
                alias_score = max(alias_score, 300 + len(alias))
            elif alias in normalized:
                alias_score = max(alias_score, 200 + len(alias))
            elif normalized in alias and len(normalized) >= 5:
                alias_score = max(alias_score, 150 + len(normalized))
        excluded = any(term in lowered for term in exclude_terms)
        is_cap = _is_planet_cap_texture_name(lowered)
        preferred = any(term in lowered for term in prefer_terms)
        try:
            size = int(path.stat().st_size)
        except OSError:
            size = 0
        eq_score = _planet_equirectangular_score(path)
        ranked.append((alias_score, 1 if preferred else 0, 0 if excluded else 1, 0 if is_cap else 1, eq_score, size, path))

    if not ranked:
        return None

    ranked.sort(reverse=True)
    if ranked[0][0] > 0:
        return ranked[0][6]
    return find_best_mat_texture_for_planet_surface(mat_textures)


def find_mat_texture_for_planet_clouds(archetype: str, mat_textures: dict[str, Path]) -> Path | None:
    """Choose the original MAT texture that best matches a Freelancer planet cloud layer."""
    if not mat_textures:
        return None

    aliases = _planet_texture_aliases(archetype)
    ranked: list[tuple[int, int, int, int, Path]] = []
    seen_paths: set[Path] = set()
    for name, path in mat_textures.items():
        if path in seen_paths:
            continue
        seen_paths.add(path)
        lowered = str(name or "").strip().lower()
        normalized = _normalize_texture_key(lowered)
        is_cap = _is_planet_cap_texture_name(lowered)
        cloud_score = 0
        if any(term in lowered for term in ("cloud", "cld", "atmo", "atmos")):
            cloud_score += 120
        for alias in aliases:
            if not alias:
                continue
            if normalized == alias:
                cloud_score += 220 + len(alias)
            elif alias in normalized:
                cloud_score += 180 + len(alias)
        try:
            size = int(path.stat().st_size)
        except OSError:
            size = 0
        ranked.append((cloud_score, 0 if is_cap else 1, size, len(lowered), path))

    if not ranked:
        return None
    ranked.sort(reverse=True)
    if ranked[0][0] <= 0:
        return None
    if ranked[0][1] <= 0:
        return None
    return ranked[0][4]


def find_mat_texture_for_planet_ring(mat_textures: dict[str, Path]) -> Path | None:
    """Prefer textures that look like planetary rings."""
    if not mat_textures:
        return None

    ranked: list[tuple[int, int, int, Path]] = []
    seen_paths: set[Path] = set()
    for name, path in mat_textures.items():
        if path in seen_paths:
            continue
        seen_paths.add(path)
        lowered = str(name or "").strip().lower()
        ring_score = 0
        if "ring" in lowered:
            ring_score += 220
        if any(term in lowered for term in ("planet", "saturn", "band", "disk")):
            ring_score += 40
        eq_score = _planet_equirectangular_score(path)
        try:
            size = int(path.stat().st_size)
        except OSError:
            size = 0
        ranked.append((ring_score, eq_score, size, path))

    if not ranked:
        return None
    ranked.sort(reverse=True)
    if ranked[0][0] <= 0:
        return None
    return ranked[0][3]
