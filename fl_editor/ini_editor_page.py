from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTabBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


def build_ini_editor_page(window, *, tr, code_editor_factory, highlighter_factory, minimap_factory):
    page = QWidget()
    root = QVBoxLayout(page)
    root.setContentsMargins(10, 10, 10, 10)
    root.setSpacing(4)

    # ── Top toolbar ──────────────────────────────────────────────────
    toolbar = QWidget()
    tl = QHBoxLayout(toolbar)
    tl.setContentsMargins(0, 0, 0, 0)
    tl.setSpacing(6)

    window.ini_root_lbl = QLabel(tr("ini.root"))
    tl.addWidget(window.ini_root_lbl)
    window.ini_root_path_lbl = QLabel("-")
    window.ini_root_path_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
    tl.addWidget(window.ini_root_path_lbl, 1)
    window.ini_status_summary_val = QLabel("-")
    window.ini_status_summary_val.setTextInteractionFlags(Qt.TextSelectableByMouse)
    window.ini_status_summary_val.setWordWrap(False)
    window.ini_status_summary_val.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
    tl.addWidget(window.ini_status_summary_val)

    def _compact_toolbar_btn(label_key, tooltip_key, slot, *, style=""):
        btn = QPushButton(tr(label_key))
        btn.setToolTip(tr(tooltip_key))
        btn.setMinimumHeight(28)
        btn.setStyleSheet(style or "QPushButton { padding: 2px 8px; font-size: 12px; }")
        btn.clicked.connect(slot)
        tl.addWidget(btn)
        return btn

    window.ini_reload_btn = _compact_toolbar_btn(
        "ini.btn_short.reload_tree",
        "ini.btn.reload_tree",
        window._ini_editor_reload_tree,
    )
    window.ini_compare_btn = _compact_toolbar_btn(
        "ini.btn_short.compare",
        "ini.btn.compare",
        window._ini_editor_open_compare_dialog,
    )
    window.ini_validate_btn = _compact_toolbar_btn(
        "ini.btn_short.validate",
        "ini.btn.validate",
        window._ini_editor_open_validation_dialog,
    )
    window.ini_section_inspector_btn = _compact_toolbar_btn(
        "ini.btn_short.section_inspector",
        "ini.btn.section_inspector",
        window._ini_editor_open_section_inspector,
    )

    window.ini_discard_btn = _compact_toolbar_btn(
        "ini.btn_short.discard",
        "ini.btn.discard",
        window._ini_editor_discard_changes,
        style=(
            "QPushButton { background-color: #c0392b; color: #ffffff; font-weight: bold; "
            "padding: 2px 10px; border-radius: 3px; font-size: 12px; }"
            "QPushButton:hover { background-color: #e74c3c; }"
            "QPushButton:disabled { background-color: #555555; color: #999999; }"
        ),
    )
    window.ini_discard_btn.setEnabled(False)

    window.ini_save_btn = _compact_toolbar_btn(
        "ini.btn_short.save",
        "ini.btn.save",
        window._ini_editor_save_current,
        style=(
            "QPushButton { background-color: #27ae60; color: #ffffff; font-weight: bold; "
            "padding: 2px 10px; border-radius: 3px; font-size: 12px; }"
            "QPushButton:hover { background-color: #2ecc71; }"
            "QPushButton:disabled { background-color: #555555; color: #999999; }"
        ),
    )
    window.ini_save_btn.setEnabled(False)

    root.addWidget(toolbar)

    # ── Status bar ───────────────────────────────────────────────────
    window.ini_status_panel = QWidget()
    status_layout = QHBoxLayout(window.ini_status_panel)
    status_layout.setContentsMargins(0, 0, 0, 0)
    status_layout.setSpacing(6)
    window.ini_status_panel.setVisible(False)

    # ── File tab bar (sub-tabs for open files) ───────────────────────
    window.ini_file_tab_bar = QTabBar()
    window.ini_file_tab_bar.setTabsClosable(True)
    window.ini_file_tab_bar.setMovable(True)
    window.ini_file_tab_bar.setExpanding(False)
    window.ini_file_tab_bar.setDrawBase(False)
    window.ini_file_tab_bar.setContextMenuPolicy(Qt.CustomContextMenu)
    window.ini_file_tab_bar.currentChanged.connect(window._on_ini_file_tab_changed)
    window.ini_file_tab_bar.tabCloseRequested.connect(window._on_ini_file_tab_close_requested)
    window.ini_file_tab_bar.customContextMenuRequested.connect(window._on_ini_file_tab_context_menu)
    window.ini_file_tab_bar.setVisible(False)
    root.addWidget(window.ini_file_tab_bar)

    # ── Icon toolbar (Notepad-style) ─────────────────────────────────
    icon_bar = QWidget()
    ib_layout = QHBoxLayout(icon_bar)
    ib_layout.setContentsMargins(0, 4, 0, 4)
    ib_layout.setSpacing(4)

    def _icon_btn(icon, label, tooltip, slot, *, width=52, height=34):
        btn = QPushButton(f"{icon}\n{label}")
        btn.setFixedSize(width, height)
        btn.setStyleSheet(
            "QPushButton { font-size: 10px; line-height: 1.05; padding: 1px 2px; }"
        )
        btn.setToolTip(tooltip)
        btn.clicked.connect(slot)
        ib_layout.addWidget(btn)
        return btn

    window._ib_undo = _icon_btn("\u21B6", tr("ini.icon.short.undo"), tr("ini.icon.undo"), lambda: window.ini_code_edit.undo())
    window._ib_redo = _icon_btn("\u21B7", tr("ini.icon.short.redo"), tr("ini.icon.redo"), lambda: window.ini_code_edit.redo())
    ib_layout.addSpacing(4)
    window._ib_cut = _icon_btn("\u2702", tr("ini.icon.short.cut"), tr("ini.icon.cut"), lambda: window.ini_code_edit.cut())
    window._ib_copy = _icon_btn("\u2398", tr("ini.icon.short.copy"), tr("ini.icon.copy"), lambda: window.ini_code_edit.copy())
    window._ib_paste = _icon_btn("\U0001F4CB", tr("ini.icon.short.paste"), tr("ini.icon.paste"), lambda: window.ini_code_edit.paste())
    ib_layout.addSpacing(4)
    window._ib_find = _icon_btn("\U0001F50D", tr("ini.icon.short.find"), tr("ini.icon.find"), window._ini_editor_toggle_search)
    window._ib_replace = _icon_btn("\U0001F504", tr("ini.icon.short.replace"), tr("ini.icon.replace"), window._ini_editor_toggle_replace)
    window._ib_global_find = _icon_btn("\U0001F50E", tr("ini.icon.short.global_find"), tr("ini.icon.global_find"), window._ini_editor_toggle_global_search)
    ib_layout.addSpacing(4)
    window._ib_zoom_in = _icon_btn("+", tr("ini.icon.short.zoom_in"), tr("ini.icon.zoom_in"), window._ini_editor_zoom_in, width=42)
    window._ib_zoom_out = _icon_btn("\u2212", tr("ini.icon.short.zoom_out"), tr("ini.icon.zoom_out"), window._ini_editor_zoom_out, width=42)
    window._ib_zoom_reset = _icon_btn("1:1", tr("ini.icon.short.zoom_reset"), tr("ini.icon.zoom_reset"), window._ini_editor_zoom_reset, width=46)
    ib_layout.addSpacing(4)
    window._ib_wordwrap = _icon_btn("\u21A9", tr("ini.icon.short.wordwrap"), tr("ini.icon.wordwrap"), window._ini_editor_toggle_wordwrap)
    ib_layout.addStretch(1)
    root.addWidget(icon_bar)

    # ── Search / Replace bar (hidden by default) ─────────────────────
    window._ini_search_bar = QWidget()
    window._ini_search_bar.setVisible(False)
    sb_layout = QVBoxLayout(window._ini_search_bar)
    sb_layout.setContentsMargins(0, 0, 0, 0)
    sb_layout.setSpacing(2)

    search_row = QHBoxLayout()
    search_row.setSpacing(4)
    window._ini_search_input = QLineEdit()
    window._ini_search_input.setPlaceholderText(tr("ini.search.placeholder"))
    window._ini_search_input.returnPressed.connect(window._ini_editor_find_next)
    search_row.addWidget(window._ini_search_input, 1)
    window._ini_search_prev_btn = QPushButton(tr("ini.search.prev"))
    window._ini_search_prev_btn.clicked.connect(window._ini_editor_find_prev)
    search_row.addWidget(window._ini_search_prev_btn)
    window._ini_search_next_btn = QPushButton(tr("ini.search.next"))
    window._ini_search_next_btn.clicked.connect(window._ini_editor_find_next)
    search_row.addWidget(window._ini_search_next_btn)
    window._ini_search_count_lbl = QLabel("")
    search_row.addWidget(window._ini_search_count_lbl)
    window._ini_search_close_btn = QPushButton("\u2715")
    window._ini_search_close_btn.setFixedWidth(28)
    window._ini_search_close_btn.clicked.connect(window._ini_editor_close_search)
    search_row.addWidget(window._ini_search_close_btn)
    sb_layout.addLayout(search_row)

    replace_row = QHBoxLayout()
    replace_row.setSpacing(4)
    window._ini_replace_input = QLineEdit()
    window._ini_replace_input.setPlaceholderText(tr("ini.search.replace_placeholder"))
    replace_row.addWidget(window._ini_replace_input, 1)
    window._ini_replace_btn = QPushButton(tr("ini.search.replace"))
    window._ini_replace_btn.clicked.connect(window._ini_editor_replace_current)
    replace_row.addWidget(window._ini_replace_btn)
    window._ini_replace_all_btn = QPushButton(tr("ini.search.replace_all"))
    window._ini_replace_all_btn.clicked.connect(window._ini_editor_replace_all)
    replace_row.addWidget(window._ini_replace_all_btn)
    window._ini_replace_row_widget = QWidget()
    window._ini_replace_row_widget.setLayout(replace_row)
    window._ini_replace_row_widget.setVisible(False)
    sb_layout.addWidget(window._ini_replace_row_widget)

    root.addWidget(window._ini_search_bar)

    # ── Cross-file search bar (hidden by default) ────────────────────
    window._ini_global_search_bar = QWidget()
    window._ini_global_search_bar.setVisible(False)
    gs_layout = QHBoxLayout(window._ini_global_search_bar)
    gs_layout.setContentsMargins(0, 0, 0, 0)
    gs_layout.setSpacing(4)
    window._ini_global_search_input = QLineEdit()
    window._ini_global_search_input.setPlaceholderText(tr("ini.search.global_placeholder"))
    window._ini_global_search_input.returnPressed.connect(window._ini_editor_global_search)
    gs_layout.addWidget(window._ini_global_search_input, 1)
    window._ini_global_search_btn = QPushButton(tr("ini.search.global_search"))
    window._ini_global_search_btn.clicked.connect(window._ini_editor_global_search)
    gs_layout.addWidget(window._ini_global_search_btn)
    window._ini_global_search_close_btn = QPushButton("\u2715")
    window._ini_global_search_close_btn.setFixedWidth(28)
    window._ini_global_search_close_btn.clicked.connect(window._ini_editor_close_global_search)
    gs_layout.addWidget(window._ini_global_search_close_btn)
    root.addWidget(window._ini_global_search_bar)

    # ── Main content splitter ────────────────────────────────────────
    split = QSplitter(Qt.Horizontal)
    root.addWidget(split, 1)

    window.ini_tree = QTreeWidget()
    window.ini_tree.setColumnCount(2)
    window.ini_tree.setHeaderLabels([
        tr("ini.explorer.col.name"),
        tr("ini.explorer.col.modified"),
    ])
    tree_header = window.ini_tree.header()
    tree_header.setStretchLastSection(False)
    tree_header.setSectionResizeMode(0, QHeaderView.Stretch)
    tree_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
    window.ini_tree.itemActivated.connect(window._ini_editor_open_tree_item)
    window.ini_tree.itemClicked.connect(window._ini_editor_open_tree_item)
    window.ini_tree.itemExpanded.connect(window._ini_editor_on_tree_item_expanded)
    window.ini_tree.setContextMenuPolicy(Qt.CustomContextMenu)
    window.ini_tree.customContextMenuRequested.connect(window._on_ini_editor_tree_context_menu)
    split.addWidget(window.ini_tree)

    # Editor + search results stacked in a vertical splitter
    editor_col = QWidget()
    editor_col_layout = QVBoxLayout(editor_col)
    editor_col_layout.setContentsMargins(0, 0, 0, 0)
    editor_col_layout.setSpacing(0)

    window._ini_editor_vertical_splitter = QSplitter(Qt.Vertical)
    editor_col_layout.addWidget(window._ini_editor_vertical_splitter, 1)

    window._ini_editor_main_panel = QWidget()
    main_panel_layout = QVBoxLayout(window._ini_editor_main_panel)
    main_panel_layout.setContentsMargins(0, 0, 0, 0)
    main_panel_layout.setSpacing(0)

    window._ini_editor_text_panel = QWidget()
    editor_row_layout = QHBoxLayout(window._ini_editor_text_panel)
    editor_row_layout.setContentsMargins(0, 0, 0, 0)
    editor_row_layout.setSpacing(6)

    window.ini_code_edit = code_editor_factory()
    window.ini_code_edit.textChanged.connect(window._ini_editor_on_text_changed)
    window.ini_code_edit.setContextMenuPolicy(Qt.CustomContextMenu)
    window.ini_code_edit.customContextMenuRequested.connect(window._ini_editor_show_line_history_menu)
    window._ini_highlighter = highlighter_factory(window.ini_code_edit.document())
    editor_row_layout.addWidget(window.ini_code_edit, 1)

    window._ini_minimap = minimap_factory(window.ini_code_edit)
    editor_row_layout.addWidget(window._ini_minimap)
    main_panel_layout.addWidget(window._ini_editor_text_panel, 1)

    window._ini_model_preview_panel = QWidget()
    window._ini_model_preview_panel.setVisible(False)
    model_layout = QVBoxLayout(window._ini_model_preview_panel)
    model_layout.setContentsMargins(0, 0, 0, 0)
    model_layout.setSpacing(6)
    model_toolbar = QHBoxLayout()
    model_toolbar.setContentsMargins(0, 0, 0, 0)
    model_toolbar.setSpacing(4)
    window._ini_model_preview_label = QLabel("")
    window._ini_model_preview_label.setWordWrap(True)
    model_toolbar.addWidget(window._ini_model_preview_label, 1)
    window._ini_model_preview_open_btn = QPushButton(tr("ini.model.open_preview"))
    window._ini_model_preview_open_btn.clicked.connect(window._ini_editor_open_current_model_preview)
    model_toolbar.addWidget(window._ini_model_preview_open_btn)
    window._ini_model_preview_manager_btn = QPushButton(tr("ini.model.open_manager"))
    window._ini_model_preview_manager_btn.clicked.connect(window._ini_editor_open_current_model_in_manager)
    model_toolbar.addWidget(window._ini_model_preview_manager_btn)
    model_layout.addLayout(model_toolbar)
    window._ini_model_preview_host = QWidget()
    window._ini_model_preview_host_layout = QVBoxLayout(window._ini_model_preview_host)
    window._ini_model_preview_host_layout.setContentsMargins(0, 0, 0, 0)
    window._ini_model_preview_host_layout.setSpacing(0)
    model_layout.addWidget(window._ini_model_preview_host, 1)
    main_panel_layout.addWidget(window._ini_model_preview_panel, 1)

    # ── Folder explorer (hidden by default, shown when a dir is clicked) ──
    window._ini_folder_explorer = QWidget()
    window._ini_folder_explorer.setVisible(False)
    fe_layout = QVBoxLayout(window._ini_folder_explorer)
    fe_layout.setContentsMargins(0, 0, 0, 0)
    fe_layout.setSpacing(4)

    fe_toolbar = QHBoxLayout()
    fe_toolbar.setSpacing(4)
    window._ini_fe_path_lbl = QLabel("")
    window._ini_fe_path_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
    fe_toolbar.addWidget(window._ini_fe_path_lbl, 1)
    window._ini_fe_new_btn = QPushButton(tr("ini.explorer.new_file"))
    window._ini_fe_new_btn.clicked.connect(lambda: window._ini_editor_create_new_file(getattr(window, "_ini_explorer_current_dir", "")))
    fe_toolbar.addWidget(window._ini_fe_new_btn)
    window._ini_fe_copy_btn = QPushButton(tr("ini.explorer.copy"))
    window._ini_fe_copy_btn.clicked.connect(window._ini_explorer_copy_files)
    fe_toolbar.addWidget(window._ini_fe_copy_btn)
    window._ini_fe_move_btn = QPushButton(tr("ini.explorer.move"))
    window._ini_fe_move_btn.clicked.connect(window._ini_explorer_move_files)
    fe_toolbar.addWidget(window._ini_fe_move_btn)
    window._ini_fe_delete_btn = QPushButton(tr("ini.explorer.delete"))
    window._ini_fe_delete_btn.clicked.connect(window._ini_explorer_delete_files)
    fe_toolbar.addWidget(window._ini_fe_delete_btn)
    window._ini_fe_rename_btn = QPushButton(tr("ini.explorer.rename"))
    window._ini_fe_rename_btn.clicked.connect(window._ini_explorer_rename_file)
    fe_toolbar.addWidget(window._ini_fe_rename_btn)
    window._ini_fe_open_btn = QPushButton(tr("ini.explorer.open_folder"))
    window._ini_fe_open_btn.clicked.connect(window._ini_explorer_open_in_system)
    fe_toolbar.addWidget(window._ini_fe_open_btn)
    fe_layout.addLayout(fe_toolbar)

    window._ini_fe_file_tree = QTreeWidget()
    window._ini_fe_file_tree.setHeaderLabels([
        tr("ini.explorer.col.name"),
        tr("ini.explorer.col.size"),
        tr("ini.explorer.col.modified"),
    ])
    window._ini_fe_file_tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
    window._ini_fe_file_tree.setRootIsDecorated(False)
    window._ini_fe_file_tree.setSortingEnabled(True)
    window._ini_fe_file_tree.setContextMenuPolicy(Qt.CustomContextMenu)
    header = window._ini_fe_file_tree.header()
    header.setStretchLastSection(False)
    header.setSectionResizeMode(0, QHeaderView.Stretch)
    header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
    window._ini_fe_file_tree.itemClicked.connect(window._ini_explorer_open_item)
    window._ini_fe_file_tree.itemDoubleClicked.connect(window._ini_explorer_open_item)
    window._ini_fe_file_tree.customContextMenuRequested.connect(window._on_ini_explorer_file_context_menu)
    fe_layout.addWidget(window._ini_fe_file_tree, 1)

    main_panel_layout.addWidget(window._ini_folder_explorer, 1)
    window._ini_editor_vertical_splitter.addWidget(window._ini_editor_main_panel)

    window._ini_global_results_panel = QWidget()
    window._ini_global_results_panel.setVisible(False)
    results_panel_layout = QVBoxLayout(window._ini_global_results_panel)
    results_panel_layout.setContentsMargins(0, 0, 0, 0)
    results_panel_layout.setSpacing(4)

    results_toolbar = QHBoxLayout()
    results_toolbar.setContentsMargins(0, 0, 0, 0)
    results_toolbar.setSpacing(4)
    window._ini_global_results_label = QLabel(tr("ini.search.global_search"))
    results_toolbar.addWidget(window._ini_global_results_label, 1)
    window._ini_global_results_close_btn = QPushButton("\u2715")
    window._ini_global_results_close_btn.setFixedWidth(28)
    window._ini_global_results_close_btn.clicked.connect(window._ini_editor_close_global_search)
    results_toolbar.addWidget(window._ini_global_results_close_btn)
    results_panel_layout.addLayout(results_toolbar)

    window._ini_global_results_list = QListWidget()
    window._ini_global_results_list.itemActivated.connect(window._ini_editor_open_global_search_result)
    window._ini_global_results_list.itemDoubleClicked.connect(window._ini_editor_open_global_search_result)
    results_panel_layout.addWidget(window._ini_global_results_list, 1)
    window._ini_editor_vertical_splitter.addWidget(window._ini_global_results_panel)
    window._ini_editor_vertical_splitter.setSizes([700, 0])

    split.addWidget(editor_col)

    window.ini_sections_list = QListWidget()
    window.ini_sections_list.itemActivated.connect(window._ini_editor_jump_to_section)
    window.ini_sections_list.itemClicked.connect(window._ini_editor_jump_to_section)
    split.addWidget(window.ini_sections_list)
    split.setSizes([280, 900, 260])

    # ── Keyboard shortcuts ───────────────────────────────────────────
    find_sc = QShortcut(QKeySequence("Ctrl+F"), page)
    find_sc.activated.connect(window._ini_editor_toggle_search)
    replace_sc = QShortcut(QKeySequence("Ctrl+H"), page)
    replace_sc.activated.connect(window._ini_editor_toggle_replace)
    global_search_sc = QShortcut(QKeySequence("Ctrl+Shift+F"), page)
    global_search_sc.activated.connect(window._ini_editor_toggle_global_search)
    save_sc = QShortcut(QKeySequence("Ctrl+S"), page)
    save_sc.activated.connect(window._ini_editor_save_current)

    # ── State initialisation ─────────────────────────────────────────
    window._ini_editor_root = ""
    window._ini_editor_current_file = ""
    window._ini_editor_current_tree_item = None
    window._ini_editor_dirty = False
    window._ini_editor_opening_tab = False
    window._ini_editor_original_text = ""
    window._ini_explorer_current_dir = ""
    window._ini_editor_current_model_entry = None
    window._ini_file_tab_specs = []
    window._ini_file_tab_syncing = False
    window._ini_file_current_spec = None
    return page
