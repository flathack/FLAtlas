from __future__ import annotations

from fl_editor.name_editor_logic import (
    filter_name_editor_rows,
    name_from_nickname_guess,
    usage_location_line,
)


def test_filter_name_editor_rows_matches_id_text_and_dll():
    rows = [
        {"global_id": 100, "text": "Alpha", "dll": "resources.dll"},
        {"global_id": 200, "text": "Beta", "dll": "mod.dll"},
    ]

    assert filter_name_editor_rows(rows, "100") == [rows[0]]
    assert filter_name_editor_rows(rows, "beta") == [rows[1]]
    assert filter_name_editor_rows(rows, "resources") == [rows[0]]
    assert filter_name_editor_rows(rows, "") == rows


def test_name_from_nickname_guess_and_usage_location_line():
    assert name_from_nickname_guess("li01_trade_lane") == "Li01 Trade Lane"
    assert name_from_nickname_guess("") == ""
    assert usage_location_line({"section": "object", "nickname": "lane_a", "path": "/tmp/test.ini"}) == (
        "[object] lane_a -> /tmp/test.ini"
    )
