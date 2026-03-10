from __future__ import annotations

from fl_editor.global_settings_logic import (
    build_global_settings_state,
    normalized_repo_multi_text,
    resolved_auto_name_language,
)


def test_normalized_repo_multi_text_filters_primary_and_empty_values():
    assert normalized_repo_multi_text("/mods/main", ["/mods/main", "", "/mods/alt"]) == "/mods/alt"


def test_resolved_auto_name_language_falls_back_to_current_language():
    assert resolved_auto_name_language("", "de") == "de"
    assert resolved_auto_name_language("invalid", "en") == "en"
    assert resolved_auto_name_language("en", "de") == "en"


def test_build_global_settings_state_combines_defaults_and_visibility_flags():
    state = build_global_settings_state(
        bini_target_path="",
        primary_game_path="/game/main",
        fallback_game_path="/game/fallback",
        repo_root="/mods/main",
        repo_roots=["/mods/main", "/mods/alt"],
        flmm_install_path="/tools/flmm",
        xml_editor_path="/tools/xml.exe",
        savegame_editor_path="/tools/save.exe",
        current_language="de",
        current_theme="xp",
        auto_name_language="",
        update_check_enabled=True,
        allow_prerelease_toggle=False,
        update_prerelease_enabled=True,
        show_splash_enabled=False,
    )

    assert state == {
        "bini_target_path": "/game/main",
        "repo_root": "/mods/main",
        "repo_multi_text": "/mods/alt",
        "flmm_install_path": "/tools/flmm",
        "xml_editor_path": "/tools/xml.exe",
        "savegame_editor_path": "/tools/save.exe",
        "language": "de",
        "theme": "xp",
        "auto_name_language": "de",
        "update_check_enabled": True,
        "update_prerelease_visible": False,
        "update_prerelease_enabled": False,
        "show_splash_enabled": False,
    }
