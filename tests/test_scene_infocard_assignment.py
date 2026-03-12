from __future__ import annotations

from fl_editor.scene_infocard_assignment import assign_ids_info_entry


def test_assign_ids_info_entry_replaces_or_appends_ids_info():
    def _entry_set(entries, key, value):
        updated = list(entries)
        for index, (entry_key, _entry_value) in enumerate(updated):
            if entry_key == key:
                updated[index] = (entry_key, value)
                return updated
        updated.append((key, value))
        return updated

    updated, ids_value = assign_ids_info_entry(
        [("nickname", "obj"), ("ids_info", "10")],
        "20",
        entry_set=_entry_set,
    )
    assert ids_value == "20"
    assert updated == [("nickname", "obj"), ("ids_info", "20")]

    appended, ids_value = assign_ids_info_entry(
        [("nickname", "obj")],
        "30",
        entry_set=_entry_set,
    )
    assert ids_value == "30"
    assert appended == [("nickname", "obj"), ("ids_info", "30")]
