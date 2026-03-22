from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)


def build_ini_editor_page(window, *, tr, code_editor_factory, highlighter_factory):
    page = QWidget()
    root = QVBoxLayout(page)
    root.setContentsMargins(10, 10, 10, 10)
    root.setSpacing(8)

    window.ini_title_lbl = QLabel(tr("ini.title"))
    window.ini_title_lbl.setStyleSheet("font-size: 15pt; font-weight: bold;")
    root.addWidget(window.ini_title_lbl)
    window.ini_subtitle_lbl = QLabel(tr("ini.subtitle"))
    window.ini_subtitle_lbl.setWordWrap(True)
    root.addWidget(window.ini_subtitle_lbl)

    toolbar = QWidget()
    tl = QHBoxLayout(toolbar)
    tl.setContentsMargins(0, 0, 0, 0)
    tl.setSpacing(6)
    window.ini_root_lbl = QLabel(tr("ini.root"))
    tl.addWidget(window.ini_root_lbl)
    window.ini_root_path_lbl = QLabel("-")
    window.ini_root_path_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
    tl.addWidget(window.ini_root_path_lbl, 1)
    window.ini_reload_btn = QPushButton(tr("ini.btn.reload_tree"))
    window.ini_reload_btn.clicked.connect(window._ini_editor_reload_tree)
    tl.addWidget(window.ini_reload_btn)
    window.ini_compare_btn = QPushButton(tr("ini.btn.compare"))
    window.ini_compare_btn.clicked.connect(window._ini_editor_open_compare_dialog)
    tl.addWidget(window.ini_compare_btn)
    window.ini_find_usages_btn = QPushButton(tr("ini.btn.find_usages"))
    window.ini_find_usages_btn.clicked.connect(window._ini_editor_open_find_usages_dialog)
    tl.addWidget(window.ini_find_usages_btn)
    window.ini_save_btn = QPushButton(tr("ini.btn.save"))
    window.ini_save_btn.clicked.connect(window._ini_editor_save_current)
    tl.addWidget(window.ini_save_btn)
    root.addWidget(toolbar)

    window.ini_status_panel = QWidget()
    status_layout = QFormLayout(window.ini_status_panel)
    status_layout.setContentsMargins(0, 0, 0, 0)
    status_layout.setSpacing(6)
    window.ini_status_file_lbl = QLabel(tr("ini.status.file"))
    window.ini_status_file_val = QLabel("-")
    window.ini_status_file_val.setTextInteractionFlags(Qt.TextSelectableByMouse)
    status_layout.addRow(window.ini_status_file_lbl, window.ini_status_file_val)
    window.ini_status_source_lbl = QLabel(tr("ini.status.source"))
    window.ini_status_source_val = QLabel("-")
    window.ini_status_source_val.setTextInteractionFlags(Qt.TextSelectableByMouse)
    status_layout.addRow(window.ini_status_source_lbl, window.ini_status_source_val)
    window.ini_status_write_target_lbl = QLabel(tr("ini.status.write_target"))
    window.ini_status_write_target_val = QLabel("-")
    window.ini_status_write_target_val.setTextInteractionFlags(Qt.TextSelectableByMouse)
    status_layout.addRow(window.ini_status_write_target_lbl, window.ini_status_write_target_val)
    window.ini_status_counterpart_lbl = QLabel(tr("ini.status.counterpart"))
    window.ini_status_counterpart_val = QLabel("-")
    window.ini_status_counterpart_val.setTextInteractionFlags(Qt.TextSelectableByMouse)
    status_layout.addRow(window.ini_status_counterpart_lbl, window.ini_status_counterpart_val)
    window.ini_status_state_lbl = QLabel(tr("ini.status.state"))
    window.ini_status_state_val = QLabel("-")
    window.ini_status_state_val.setTextInteractionFlags(Qt.TextSelectableByMouse)
    status_layout.addRow(window.ini_status_state_lbl, window.ini_status_state_val)
    root.addWidget(window.ini_status_panel)

    split = QSplitter(Qt.Horizontal)
    root.addWidget(split, 1)

    window.ini_tree = QTreeWidget()
    window.ini_tree.setHeaderHidden(True)
    window.ini_tree.itemActivated.connect(window._ini_editor_open_tree_item)
    window.ini_tree.itemClicked.connect(window._ini_editor_open_tree_item)
    window.ini_tree.itemExpanded.connect(window._ini_editor_on_tree_item_expanded)
    window.ini_tree.setContextMenuPolicy(Qt.CustomContextMenu)
    window.ini_tree.customContextMenuRequested.connect(window._on_ini_editor_tree_context_menu)
    split.addWidget(window.ini_tree)

    window.ini_code_edit = code_editor_factory()
    window.ini_code_edit.textChanged.connect(window._ini_editor_on_text_changed)
    window._ini_highlighter = highlighter_factory(window.ini_code_edit.document())
    split.addWidget(window.ini_code_edit)

    window.ini_sections_list = QListWidget()
    window.ini_sections_list.itemActivated.connect(window._ini_editor_jump_to_section)
    window.ini_sections_list.itemClicked.connect(window._ini_editor_jump_to_section)
    split.addWidget(window.ini_sections_list)
    split.setSizes([280, 900, 260])

    window._ini_editor_root = ""
    window._ini_editor_current_file = ""
    window._ini_editor_current_tree_item = None
    window._ini_editor_dirty = False
    window._ini_editor_opening_tab = False
    return page
