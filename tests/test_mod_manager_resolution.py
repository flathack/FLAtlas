from __future__ import annotations

from fl_editor.mod_manager_resolution import (
    default_resolution_text,
    parse_resolution,
    ratio_definitions,
    ratio_for_resolution_text,
    ratio_options,
    resolution_options,
    resolution_text,
)


def test_parse_and_format_resolution():
    assert parse_resolution("1920x1080") == (1920, 1080)
    assert parse_resolution(" 1280 X 720 ") == (1280, 720)
    assert parse_resolution("abc") is None
    assert resolution_text(2560, 1440) == "2560x1440"


def test_default_resolution_text_uses_fallback_and_screen_size():
    assert default_resolution_text() == "1920x1080"
    assert default_resolution_text((1366, 768)) == "1366x768"
    assert default_resolution_text((0, 768)) == "1920x1080"


def test_ratio_helpers_return_expected_values():
    assert "16:9" in ratio_options()
    assert ratio_for_resolution_text("1920x1080") == "16:9"
    assert ratio_for_resolution_text("1280x1024") == "5:4"
    assert ratio_definitions()


def test_resolution_options_include_matching_current_and_selected_values():
    options = resolution_options(
        ratio_label="16:9",
        selected_ratio="16:9",
        selected_resolution="1111x625",
        current_resolution="1600x900",
    )

    assert "1600x900" in options
    assert "1111x625" in options
    assert "1280x720" in options
