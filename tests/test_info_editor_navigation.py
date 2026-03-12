from __future__ import annotations

from fl_editor.info_editor_navigation import find_info_editor_row_index, safe_int


def test_safe_int_handles_strings_invalid_values_and_none():
    assert safe_int(" 42 ") == 42
    assert safe_int(None) == 0
    assert safe_int("bad") == 0


def test_find_info_editor_row_index_returns_matching_row():
    rows = [
        {"global_id": "100"},
        {"global_id": 200},
        "invalid",
        {"global_id": "300"},
    ]

    assert find_info_editor_row_index(rows, 200) == 1
    assert find_info_editor_row_index(rows, 999) is None
    assert find_info_editor_row_index(rows, 0) is None
