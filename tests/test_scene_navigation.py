from __future__ import annotations

from fl_editor.scene_navigation import goto_destination_nickname, linked_system_path


def test_goto_destination_nickname_reads_first_token():
    assert goto_destination_nickname("li01, jumpgate, dock") == "LI01"
    assert goto_destination_nickname("  ") == ""
    assert goto_destination_nickname("") == ""


def test_linked_system_path_matches_nickname_case_insensitively():
    systems = [
        {"nickname": "li01", "path": "/game/universe/li01.ini"},
        {"nickname": "br01", "path": "/game/universe/br01.ini"},
    ]

    assert linked_system_path(systems, "LI01") == "/game/universe/li01.ini"
    assert linked_system_path(systems, "br01") == "/game/universe/br01.ini"
    assert linked_system_path(systems, "ku01") is None
