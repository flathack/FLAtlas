from __future__ import annotations

from fl_editor.base_edit_readers import collect_first_column_raw_rows, collect_table_raw_rows, optional_text_value
from fl_editor.base_edit_readers import collect_combo_texts


def test_optional_text_value_respects_presence_and_strips_text():
    assert optional_text_value(present=False, text=" value ") == ""
    assert optional_text_value(present=True, text=" value ") == "value"


def test_collect_first_column_raw_rows_reads_requested_row_count():
    values = {
        (0, 0): "gun_a",
        (1, 0): "",
        (2, 0): "gun_b",
    }
    rows = collect_first_column_raw_rows(
        row_count=3,
        cell_text=lambda row, col: values.get((row, col), ""),
    )
    assert rows == [["gun_a"], [""], ["gun_b"]]


def test_collect_table_raw_rows_reads_rectangular_cell_matrix():
    values = {
        (0, 0): "food",
        (0, 1): "1",
        (1, 0): "water",
        (1, 1): "2",
    }
    rows = collect_table_raw_rows(
        row_count=2,
        column_count=2,
        cell_text=lambda row, col: values.get((row, col), ""),
    )
    assert rows == [["food", "1"], ["water", "2"]]


class _Combo:
    def __init__(self, text: str):
        self._text = text

    def currentText(self):
        return self._text


def test_collect_combo_texts_reads_current_texts():
    assert collect_combo_texts(combos=[_Combo("ship_a"), _Combo(" ship_b "), _Combo("")]) == [
        "ship_a",
        "ship_b",
        "",
    ]
