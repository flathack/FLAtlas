from __future__ import annotations

from fl_editor.welcome_logic import welcome_continue_state, welcome_ids_toolchain_notice


def test_welcome_continue_state_detects_language_and_theme_changes():
    state = welcome_continue_state(
        selected_language="de",
        selected_theme="xp",
        current_language="en",
        allowed_themes=["founder", "xp"],
        update_check_enabled=False,
    )

    assert state["language"] == "de"
    assert state["theme"] == "xp"
    assert state["should_change_language"]
    assert state["should_apply_theme"]
    assert not state["update_check_enabled"]


def test_welcome_continue_state_rejects_unknown_theme():
    state = welcome_continue_state(
        selected_language="en",
        selected_theme="unknown",
        current_language="en",
        allowed_themes=["founder", "xp"],
        update_check_enabled=True,
    )

    assert not state["should_change_language"]
    assert not state["should_apply_theme"]


def test_welcome_ids_toolchain_notice_controls_install_button():
    ok_state = welcome_ids_toolchain_notice(
        has_toolchain=True,
        is_windows=True,
        ok_text="ready",
        missing_text="missing",
    )
    missing_state = welcome_ids_toolchain_notice(
        has_toolchain=False,
        is_windows=False,
        ok_text="ready",
        missing_text="missing",
    )

    assert ok_state == {
        "text": "ready",
        "install_button_visible": True,
        "install_button_enabled": False,
    }
    assert missing_state == {
        "text": "missing",
        "install_button_visible": False,
        "install_button_enabled": True,
    }
