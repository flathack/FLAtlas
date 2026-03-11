"""Helpers for welcome-screen state and actions."""

from __future__ import annotations


def welcome_continue_state(
    *,
    selected_language: str,
    selected_theme: str,
    current_language: str,
    allowed_themes: list[str],
    update_check_enabled: bool,
) -> dict[str, object]:
    language = str(selected_language or "").strip() or "en"
    theme = str(selected_theme or "").strip() or "founder"
    return {
        "language": language,
        "theme": theme,
        "should_change_language": language != str(current_language or "").strip(),
        "should_apply_theme": theme in list(allowed_themes or []),
        "update_check_enabled": bool(update_check_enabled),
    }


def welcome_ids_toolchain_notice(
    *,
    has_toolchain: bool,
    is_supported_platform: bool,
    ok_text: str,
    missing_text: str,
) -> dict[str, object]:
    return {
        "text": ok_text if has_toolchain else missing_text,
        "install_button_visible": bool(is_supported_platform),
        "install_button_enabled": not bool(has_toolchain),
    }
