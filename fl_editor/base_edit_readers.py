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


def collect_first_column_values_from_cells(
    *,
    row_count: int,
    cell_text: Callable[[int, int], str],
) -> list[str]:
    return [
        str(cell_text(row, 0) or "").strip()
        for row in range(max(0, int(row_count)))
        if str(cell_text(row, 0) or "").strip()
    ]


def collect_table_values_from_cells(
    *,
    row_count: int,
    column_count: int,
    cell_text: Callable[[int, int], str],
    max_cols: int | None = None,
) -> list[list[str]]:
    cols = max(0, int(column_count))
    if max_cols is not None:
        cols = min(cols, max(0, int(max_cols)))
    rows: list[list[str]] = []
    for row in range(max(0, int(row_count))):
        values = [str(cell_text(row, col) or "").strip() for col in range(cols)]
        if values and values[0]:
            rows.append(values)
    return rows
