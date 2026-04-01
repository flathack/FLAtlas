"""Reusable Qt widget setup helpers."""

from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QCompleter,
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
    header.setSectionResizeMode(12, QHeaderView.ResizeToContents)


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


def configure_contains_completer(combo: QComboBox | None) -> QCompleter | None:
    if combo is None:
        return None
    try:
        combo.setEditable(True)
    except Exception:
        return None
    completer = QCompleter(combo.model(), combo)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchContains)
    completer.setCompletionMode(QCompleter.PopupCompletion)
    combo.setCompleter(completer)
    return completer


def connect_debounced_line_edit(
    edit: QLineEdit,
    callback,
    *,
    delay_ms = None,
    trigger_return_pressed: bool = True,
    trigger_empty_immediately: bool = True,
) -> QTimer:
    timer = QTimer(edit)
    timer.setSingleShot(True)

    def _resolve_delay_ms() -> int:
        if callable(delay_ms):
            try:
                value = delay_ms()
            except Exception:
                value = 300
        elif delay_ms is None:
            app = QApplication.instance()
            value = app.property("flatlas_search_debounce_ms") if app is not None else 300
        else:
            value = delay_ms
        try:
            return max(0, int(value))
        except Exception:
            return 300

    def _run() -> None:
        timer.stop()
        callback()

    def _on_text_changed(text: str) -> None:
        if trigger_empty_immediately and not str(text or "").strip():
            _run()
            return
        delay_value = _resolve_delay_ms()
        if delay_value <= 0:
            _run()
            return
        timer.setInterval(delay_value)
        timer.start()

    timer.setInterval(max(1, _resolve_delay_ms()))
    timer.timeout.connect(callback)
    edit.textChanged.connect(_on_text_changed)
    if trigger_return_pressed:
        edit.returnPressed.connect(_run)
    return timer


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
    min_profit_per_jump_spin=None,
) -> None:
    apply_button.clicked.connect(apply_filters)
    connect_debounced_line_edit(search_edit, apply_filters)
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
    if min_profit_per_jump_spin is not None:
        min_profit_per_jump_spin.valueChanged.connect(lambda _value: apply_filters())
