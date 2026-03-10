"""Reusable Qt widget setup helpers."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
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


def configure_trade_routes_table(table: QTableWidget) -> None:
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setAlternatingRowColors(True)
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


def connect_trade_route_filter_controls(
    *,
    apply_button: QPushButton,
    search_edit,
    commodity_combo,
    min_profit_spin,
    same_system_checkbox,
    apply_filters,
) -> None:
    apply_button.clicked.connect(apply_filters)
    search_edit.returnPressed.connect(apply_filters)
    commodity_combo.currentTextChanged.connect(lambda _text: apply_filters())
    min_profit_spin.valueChanged.connect(lambda _value: apply_filters())
    same_system_checkbox.toggled.connect(lambda _on: apply_filters())
