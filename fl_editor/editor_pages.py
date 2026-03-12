"""Helpers for creating and replacing editor pages in the center stack."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


def prepare_editor_page(
    *,
    center_stack,
    center_tab_specs: list,
    center_tab_index_for_widget,
    center_sync_tab_bar,
    old_page,
    title: str,
) -> tuple[QWidget, QVBoxLayout]:
    if old_page is not None and center_stack is not None:
        old_tab_idx = center_tab_index_for_widget(old_page) if center_tab_specs is not None else -1
        if old_tab_idx >= 0:
            center_tab_specs.pop(old_tab_idx)
            center_sync_tab_bar()
        idx = center_stack.indexOf(old_page)
        if idx >= 0:
            center_stack.removeWidget(old_page)
        old_page.deleteLater()
    page = QWidget()
    root = QVBoxLayout(page)
    root.setContentsMargins(10, 10, 10, 10)
    root.setSpacing(8)
    title_lbl = QLabel(str(title or "").strip())
    title_lbl.setStyleSheet("font-size: 15pt; font-weight: bold;")
    root.addWidget(title_lbl)
    if center_stack is not None:
        center_stack.addWidget(page)
    return page, root
