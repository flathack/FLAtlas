"""Context and file-state helpers for the INI editor."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

SUPPORTED_TEXT_FILE_SUFFIXES = {
    ".ini",
    ".cfg",
    ".txt",
    ".xml",
    ".lua",
    ".json",
}

SUPPORTED_MODEL_FILE_SUFFIXES = {
    ".cmp",
    ".3db",
    ".sph",
    ".obj",
    ".stl",
    ".ply",
    ".dae",
    ".fbx",
    ".gltf",
    ".glb",
}


def ini_editor_context_root(
    editing_profile: dict | None,
    selected_profile: dict | None,
    profile_source: Callable[[dict | None], Path | None],
) -> Path | None:
    for profile in (editing_profile, selected_profile):
        if not isinstance(profile, dict):
            continue
        source = profile_source(profile)
        if source is not None and source.exists() and source.is_dir():
            return source
    return None


def ini_editor_open_file(
    path: str,
    read_text_best_effort: Callable[[Path], str],
) -> tuple[bool, str, str]:
    clean_path = str(path or "").strip()
    if not clean_path:
        return False, "", ""
    text = read_text_best_effort(Path(clean_path))
    return True, clean_path, text


def ini_editor_is_supported_text_file(path: str | Path) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in SUPPORTED_TEXT_FILE_SUFFIXES


def ini_editor_is_supported_model_file(path: str | Path) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in SUPPORTED_MODEL_FILE_SUFFIXES


def ini_editor_save_file(path: str, text: str) -> tuple[bool, str]:
    clean_path = str(path or "").strip()
    if not clean_path:
        return False, ""
    Path(clean_path).write_text(str(text), encoding="utf-8")
    return True, clean_path
