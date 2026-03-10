from __future__ import annotations

from typing import Callable


def optional_text_value(*, present: bool, text: str | None) -> str:
    if not present:
        return ""
    return str(text or "").strip()


def collect_first_column_raw_rows(
    *,
    row_count: int,
    cell_text: Callable[[int, int], str],
) -> list[list[str]]:
    return [[cell_text(row, 0)] for row in range(max(0, int(row_count)))]


def collect_table_raw_rows(
    *,
    row_count: int,
    column_count: int,
    cell_text: Callable[[int, int], str],
) -> list[list[str]]:
    return [
        [cell_text(row, col) for col in range(max(0, int(column_count)))]
        for row in range(max(0, int(row_count)))
    ]


def collect_combo_texts(*, combos: list[object]) -> list[str]:
    return [str(combo.currentText()).strip() for combo in list(combos or [])]
