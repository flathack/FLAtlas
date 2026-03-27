from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QLineEdit, QPushButton, QTableWidget, QWidget

from fl_editor.ui_helpers import (
    add_browse_path_form_row,
    apply_enabled_state,
    build_browse_path_row,
    configure_readonly_table,
    configure_trade_routes_table,
    connect_trade_route_filter_controls,
    show_status_message,
)


def test_build_browse_path_row_creates_edit_and_button(qapp):
    calls: list[str] = []

    widget, edit, button = build_browse_path_row("Browse", lambda: calls.append("clicked"))
    button.click()

    assert widget is not None
    assert edit is not None
    assert button.text() == "Browse"
    assert calls == ["clicked"]


def test_add_browse_path_form_row_adds_row_and_wires_button(qapp):
    parent = QWidget()
    form = QFormLayout(parent)
    calls: list[str] = []

    row, edit, button = add_browse_path_form_row(
        form,
        "Path:",
        button_text="Browse",
        on_browse=lambda: calls.append("clicked"),
    )
    button.click()

    assert form.rowCount() == 1
    assert row is not None
    assert edit is not None
    assert button.text() == "Browse"
    assert calls == ["clicked"]


def test_configure_trade_routes_table_sets_expected_modes(qapp):
    table = QTableWidget(0, 13)

    configure_trade_routes_table(table)

    assert table.selectionBehavior() == QTableWidget.SelectRows
    assert table.selectionMode() == QTableWidget.SingleSelection
    assert table.editTriggers() == QTableWidget.NoEditTriggers
    assert table.contextMenuPolicy() == Qt.CustomContextMenu


def test_configure_readonly_table_sets_common_table_flags(qapp):
    table = QTableWidget(0, 2)

    configure_readonly_table(table)

    assert table.selectionBehavior() == QTableWidget.SelectRows
    assert table.selectionMode() == QTableWidget.SingleSelection
    assert table.editTriggers() == QTableWidget.NoEditTriggers


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
        cargo_capacity_spin=spin,
        min_profit_per_jump_spin=spin,
    )

    apply_button.click()
    search_edit.returnPressed.emit()
    commodity_combo.setCurrentText("B")
    spin.emit(250.0)
    same_system_checkbox.setChecked(True)

    assert len(calls) >= 5


def test_apply_enabled_state_updates_known_targets(qapp):
    one = QPushButton("One")
    two = QPushButton("Two")
    three = QPushButton("Three")

    apply_enabled_state(
        {"first": True, "second": False},
        {"first": one, "second": two, "missing": None, "unknown": three},
    )

    assert one.isEnabled()
    assert not two.isEnabled()
    assert not three.isEnabled()


def test_show_status_message_sets_text_on_statusbar(qapp):
    from PySide6.QtWidgets import QMainWindow

    window = QMainWindow()
    status = window.statusBar()

    show_status_message(status, "ready")

    assert status.currentMessage() == "ready"
