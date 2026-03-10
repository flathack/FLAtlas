from pathlib import Path

from fl_editor.ids_csv_import import (
    INFO_CSV_FIELDS,
    NAME_CSV_FIELDS,
    load_ids_csv_rows,
    persist_remaining_ids_csv,
    process_ids_csv_rows,
)


def test_process_ids_csv_rows_updates_and_keeps_remaining():
    calls = []

    def updater(sys_path: str, sec_type: str, obj_nick: str, value: str) -> bool:
        calls.append((sys_path, sec_type, obj_nick, value))
        return obj_nick == "obj_ok"

    rows = [
        {"System": "sys_a", "Sektion": "Object", "Nickname": "obj_ok", "ids_name": "123"},
        {"System": "sys_a", "Sektion": "Zone", "Nickname": "obj_fail", "ids_name": "456"},
        {"System": "missing", "Sektion": "Object", "Nickname": "obj_x", "ids_name": "789"},
        {"System": "sys_a", "Sektion": "Object", "Nickname": "obj_empty", "ids_name": ""},
    ]

    updated, remaining = process_ids_csv_rows(
        rows,
        value_key="ids_name",
        sys_map={"sys_a": "/tmp/sys_a.ini"},
        update_entry=updater,
    )

    assert updated == 1
    assert [row["Nickname"] for row in remaining] == ["obj_fail", "obj_x", "obj_empty"]
    assert calls == [
        ("/tmp/sys_a.ini", "object", "obj_ok", "123"),
        ("/tmp/sys_a.ini", "zone", "obj_fail", "456"),
    ]


def test_persist_remaining_ids_csv_writes_bom_csv(tmp_path: Path):
    csv_path = tmp_path / "missing_ids_name.csv"
    rows = [
        {
            "System": "sys_a",
            "Sektion": "Object",
            "Nickname": "obj_a",
            "Archetype": "arch_a",
            "ids_name": "123",
            "givenname": "Foo",
        }
    ]

    persist_remaining_ids_csv(csv_path, rows, fieldnames=NAME_CSV_FIELDS)

    assert csv_path.exists()
    loaded = load_ids_csv_rows(csv_path)
    assert loaded[0]["Nickname"] == "obj_a"
    assert loaded[0]["givenname"] == "Foo"


def test_persist_remaining_ids_csv_deletes_empty_file(tmp_path: Path):
    csv_path = tmp_path / "missing_ids_info.csv"
    csv_path.write_text("dummy", encoding="utf-8")

    persist_remaining_ids_csv(csv_path, [], fieldnames=INFO_CSV_FIELDS)

    assert not csv_path.exists()
