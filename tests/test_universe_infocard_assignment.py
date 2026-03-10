from __future__ import annotations

from fl_editor.universe_infocard_assignment import assign_universe_system_ids_info


def test_assign_universe_system_ids_info_updates_target_section():
    sections = [
        ("System", [("nickname", "li01"), ("ids_info", "100")]),
        ("System", [("nickname", "br01")]),
    ]

    def _entry_set(entries, key, value):
        updated = list(entries)
        for index, (entry_key, _entry_value) in enumerate(updated):
            if entry_key == key:
                updated[index] = (entry_key, value)
                return updated
        updated.append((key, value))
        return updated

    updated_sections, updated_entries = assign_universe_system_ids_info(
        sections,
        1,
        "200",
        entry_set=_entry_set,
    )

    assert updated_entries == [("nickname", "br01"), ("ids_info", "200")]
    assert updated_sections == [
        ("System", [("nickname", "li01"), ("ids_info", "100")]),
        ("System", [("nickname", "br01"), ("ids_info", "200")]),
    ]
