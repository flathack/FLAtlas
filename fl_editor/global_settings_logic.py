"""Helpers for preparing global settings form state."""

from __future__ import annotations


def normalized_repo_multi_text(repo_root: str, repo_roots: list[str] | tuple[str, ...]) -> str:
    primary = str(repo_root or "").strip()
    lines = [
        str(item).strip()
        for item in list(repo_roots or [])
        if str(item).strip() and str(item).strip() != primary
    ]
    return "\n".join(lines)


def resolved_auto_name_language(configured_language: str, current_language: str) -> str:
    value = str(configured_language or "").strip().lower()
    if value in ("de", "en"):
        return value
    return "de" if str(current_language or "").strip().lower().startswith("de") else "en"


def build_global_settings_state(
    *,
    bini_target_path: str,
    ids_toolchain_dir: str,
    primary_game_path: str,
    fallback_game_path: str,
    repo_root: str,
    repo_roots: list[str] | tuple[str, ...],
    flmm_install_path: str,
    xml_editor_path: str,
    savegame_editor_path: str,
    current_language: str,
    current_theme: str,
    auto_name_language: str,
    update_check_enabled: bool,
    allow_prerelease_toggle: bool,
    update_prerelease_enabled: bool,
    show_splash_enabled: bool,
    restore_tabs_enabled: bool,
    search_debounce_ms: int,
) -> dict[str, object]:
    bini_target = str(bini_target_path or "").strip()
    if not bini_target:
        bini_target = str(primary_game_path or "").strip() or str(fallback_game_path or "").strip() or ""
    resolved_auto_name = resolved_auto_name_language(auto_name_language, current_language)
    return {
        "bini_target_path": bini_target,
        "ids_toolchain_dir": str(ids_toolchain_dir or "").strip(),
        "repo_root": str(repo_root or "").strip(),
        "repo_multi_text": normalized_repo_multi_text(repo_root, repo_roots),
        "flmm_install_path": str(flmm_install_path or "").strip(),
        "xml_editor_path": str(xml_editor_path or "").strip(),
        "savegame_editor_path": str(savegame_editor_path or "").strip(),
        "language": str(current_language or "").strip(),
        "theme": str(current_theme or "").strip(),
        "auto_name_language": resolved_auto_name,
        "update_check_enabled": bool(update_check_enabled),
        "update_prerelease_visible": bool(allow_prerelease_toggle),
        "update_prerelease_enabled": bool(update_prerelease_enabled) if allow_prerelease_toggle else False,
        "show_splash_enabled": bool(show_splash_enabled),
        "restore_tabs_enabled": bool(restore_tabs_enabled),
        "search_debounce_ms": max(0, min(2000, int(search_debounce_ms))),
    }
