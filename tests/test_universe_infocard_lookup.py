from __future__ import annotations

from fl_editor.universe_infocard_lookup import universe_system_ids_info


def test_universe_system_ids_info_returns_matching_ids_info():
    sections = [
        ("System", [("nickname", "li01"), ("ids_info", "1234")]),
        ("System", [("nickname", "br01"), ("ids_info", "9999")]),
    ]

    result = universe_system_ids_info(
        sections,
        "LI01",
        entry_get_value=lambda entries, key: next((value for entry_key, value in entries if entry_key == key), ""),
        safe_int=lambda raw: int(str(raw or "0")),
    )

    assert result == 1234


def test_universe_system_ids_info_returns_zero_when_missing():
    sections = [("System", [("nickname", "li01")])]

    result = universe_system_ids_info(
        sections,
        "ku01",
        entry_get_value=lambda entries, key: next((value for entry_key, value in entries if entry_key == key), ""),
        safe_int=lambda raw: int(str(raw or "0")),
    )

    assert result == 0
