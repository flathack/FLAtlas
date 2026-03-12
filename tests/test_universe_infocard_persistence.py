from __future__ import annotations

from fl_editor.universe_infocard_persistence import should_refresh_universe_system_editor


def test_should_refresh_universe_system_editor_matches_case_insensitively():
    assert should_refresh_universe_system_editor("LI01", "li01") is True
    assert should_refresh_universe_system_editor(" br01 ", "BR01") is True
    assert should_refresh_universe_system_editor("li01", "br01") is False
    assert should_refresh_universe_system_editor(None, "li01") is False
