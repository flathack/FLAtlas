"""Reusable Qt widget setup helpers."""

from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QWidget,
)


def build_browse_path_row(button_text: str, on_browse) -> tuple[QWidget, QLineEdit, QPushButton]:
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    edit = QLineEdit()
    layout.addWidget(edit, 1)
    button = QPushButton(button_text)
    button.clicked.connect(on_browse)
    layout.addWidget(button)
    return widget, edit, button


def add_browse_path_form_row(
    form_layout: QFormLayout,
    label,
    *,
    button_text: str,
    on_browse,
) -> tuple[QWidget, QLineEdit, QPushButton]:
    row, edit, button = build_browse_path_row(button_text, on_browse)
    form_layout.addRow(label, row)
    return row, edit, button


def configure_trade_routes_table(table: QTableWidget) -> None:
    configure_readonly_table(table)
    table.setSortingEnabled(True)
    table.setContextMenuPolicy(Qt.CustomContextMenu)
    header = table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(1, QHeaderView.Stretch)
    header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(3, QHeaderView.Stretch)
    header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(8, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(9, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(10, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(11, QHeaderView.ResizeToContents)


def configure_readonly_table(table: QTableWidget) -> None:
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setAlternatingRowColors(True)


def apply_enabled_state(state: Mapping[str, object], bindings: Mapping[str, object | None]) -> None:
    for key, target in bindings.items():
        if target is None or not hasattr(target, "setEnabled"):
            continue
        target.setEnabled(bool(state.get(key)))


def show_status_message(status_bar: QStatusBar | None, message: str | None, timeout_ms: int = 0) -> None:
    if status_bar is None:
        return
    text = str(message or "")
    if timeout_ms > 0:
        status_bar.showMessage(text, int(timeout_ms))
    else:
        status_bar.showMessage(text)


def connect_trade_route_filter_controls(
    *,
    apply_button: QPushButton,
    search_edit,
    commodity_combo,
    min_profit_spin,
    same_system_checkbox,
    apply_filters,
    max_jumps_spin=None,
    source_system_combo=None,
    target_system_combo=None,
    cargo_capacity_spin=None,
) -> None:
    apply_button.clicked.connect(apply_filters)
    search_edit.returnPressed.connect(apply_filters)
    commodity_combo.currentTextChanged.connect(lambda _text: apply_filters())
    min_profit_spin.valueChanged.connect(lambda _value: apply_filters())
    same_system_checkbox.toggled.connect(lambda _on: apply_filters())
    if max_jumps_spin is not None:
        max_jumps_spin.valueChanged.connect(lambda _value: apply_filters())
    if source_system_combo is not None:
        source_system_combo.currentTextChanged.connect(lambda _text: apply_filters())
    if target_system_combo is not None:
        target_system_combo.currentTextChanged.connect(lambda _text: apply_filters())
    if cargo_capacity_spin is not None:
        cargo_capacity_spin.valueChanged.connect(lambda _value: apply_filters())
