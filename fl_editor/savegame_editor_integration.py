"""Helpers for external savegame editor path and status handling."""

from __future__ import annotations

from pathlib import Path


def savegame_editor_install_root(module_file: str | Path) -> Path:
    return Path(module_file).resolve().parent.parent / "tools" / "FLAtlas-Savegame-Editor"


def savegame_editor_configured_path(configured_text: str, ui_text: str = "") -> Path | None:
    text = str(ui_text).strip() or str(configured_text).strip()
    if not text:
        return None
    return Path(text)


def savegame_editor_launch_path(configured_path: Path | None) -> Path | None:
    if configured_path is None or not configured_path.exists() or not configured_path.is_file():
        return None
    return configured_path


def savegame_editor_installed_tag(raw_tag: str | None) -> str:
    return str(raw_tag or "").strip()


def savegame_editor_status_text(
    exe_path: Path | None,
    installed_tag: str,
    *,
    missing_text: str,
    configured_template: str,
    installed_template: str,
) -> str:
    if exe_path is not None and exe_path.exists():
        if installed_tag:
            return installed_template.format(path=str(exe_path), version=installed_tag)
        return configured_template.format(path=str(exe_path))
    return missing_text
