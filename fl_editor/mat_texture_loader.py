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
