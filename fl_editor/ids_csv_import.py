from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable

NAME_CSV_FIELDS = ["System", "Sektion", "Nickname", "Archetype", "ids_name", "givenname"]
INFO_CSV_FIELDS = ["System", "Sektion", "Nickname", "Archetype", "ids_info", "xmlinfo"]


def load_ids_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with open(path, "r", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        return [dict(row) for row in reader]


def process_ids_csv_rows(
    rows: list[dict[str, str]],
    *,
    value_key: str,
    sys_map: dict[str, str],
    update_entry: Callable[[str, str, str, str], bool],
) -> tuple[int, list[dict[str, str]]]:
    updated = 0
    remaining: list[dict[str, str]] = []
    for row in rows:
        ids_val = str(row.get(value_key, "") or "").strip()
        if not ids_val:
            remaining.append(row)
            continue

        sys_nick = str(row.get("System", "") or "").strip()
        obj_nick = str(row.get("Nickname", "") or "").strip()
        sec_type = str(row.get("Sektion", "Object") or "Object").strip().lower()
        sys_path = sys_map.get(sys_nick.lower())
        if not sys_path:
            remaining.append(row)
            continue

        if update_entry(sys_path, sec_type, obj_nick, ids_val):
            updated += 1
        else:
            remaining.append(row)
    return updated, remaining


def persist_remaining_ids_csv(path: str | Path, rows: list[dict[str, str]], *, fieldnames: list[str]) -> None:
    csv_path = Path(path)
    if rows:
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)
        return
    csv_path.unlink(missing_ok=True)
