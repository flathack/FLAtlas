from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QLineEdit, QPushButton, QTableWidget

from fl_editor.ui_helpers import (
    build_browse_path_row,
    configure_trade_routes_table,
    connect_trade_route_filter_controls,
)


def test_build_browse_path_row_creates_edit_and_button(qapp):
    calls: list[str] = []

    widget, edit, button = build_browse_path_row("Browse", lambda: calls.append("clicked"))
    button.click()

    assert widget is not None
    assert edit is not None
    assert button.text() == "Browse"
    assert calls == ["clicked"]


def test_configure_trade_routes_table_sets_expected_modes(qapp):
    table = QTableWidget(0, 10)

    configure_trade_routes_table(table)

    assert table.selectionBehavior() == QTableWidget.SelectRows
    assert table.selectionMode() == QTableWidget.SingleSelection
    assert table.editTriggers() == QTableWidget.NoEditTriggers
    assert table.contextMenuPolicy() == Qt.CustomContextMenu


def test_connect_trade_route_filter_controls_wires_apply_callbacks(qapp):
    apply_button = QPushButton("Apply")
    search_edit = QLineEdit()
    commodity_combo = QComboBox()
    commodity_combo.addItems(["A", "B"])
    min_profit_spin = QComboBox()
    same_system_checkbox = QCheckBox("Same")
    calls: list[str] = []

    class _SpinBox:
        def __init__(self):
            from PySide6.QtCore import QObject, Signal

            class _Emitter(QObject):
                valueChanged = Signal(float)

            self._emitter = _Emitter()
            self.valueChanged = self._emitter.valueChanged

        def emit(self, value: float):
            self._emitter.valueChanged.emit(value)

    spin = _SpinBox()

    connect_trade_route_filter_controls(
        apply_button=apply_button,
        search_edit=search_edit,
        commodity_combo=commodity_combo,
        min_profit_spin=spin,
        same_system_checkbox=same_system_checkbox,
        apply_filters=lambda: calls.append("apply"),
    )

    apply_button.click()
    search_edit.returnPressed.emit()
    commodity_combo.setCurrentText("B")
    spin.emit(250.0)
    same_system_checkbox.setChecked(True)

    assert len(calls) >= 5
