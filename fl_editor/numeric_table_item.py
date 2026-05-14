"""Table item helpers with numeric sort semantics."""

from __future__ import annotations

from PySide6.QtWidgets import QTableWidgetItem


class _NumericTableWidgetItem(QTableWidgetItem):
    """QTableWidgetItem mit numerischem Sortierverhalten."""

    def __init__(self, value: float | int, display: str | None = None, decimals: int | None = None):
        self._num = float(value)
        if display is None:
            if decimals is None:
                decimals = 0 if abs(self._num - round(self._num)) < 1e-9 else 2
            if decimals <= 0:
                display = f"{self._num:,.0f}"
            else:
                display = f"{self._num:,.{decimals}f}"
        super().__init__(display)

    def __lt__(self, other):
        if isinstance(other, _NumericTableWidgetItem):
            return self._num < other._num
        return super().__lt__(other)
