from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStyle,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .ui_helpers import configure_readonly_table


def build_mod_manager_page(window, *, tr, sys_platform: str):
    page = QWidget()
    root = QVBoxLayout(page)
    root.setContentsMargins(10, 10, 10, 10)
    root.setSpacing(8)

    window.mm_title_lbl = QLabel(tr("mod_manager.title"))
    window.mm_title_lbl.setStyleSheet("font-size: 15pt; font-weight: bold;")
    root.addWidget(window.mm_title_lbl)
    window.mm_info_lbl = QLabel(tr("mod_manager.info"))
    window.mm_info_lbl.setWordWrap(True)
    window.mm_info_lbl.setStyleSheet("")
    root.addWidget(window.mm_info_lbl)
    window.mm_setup_notice_lbl = QLabel("")
    window.mm_setup_notice_lbl.setWordWrap(True)
    window.mm_setup_notice_lbl.setTextFormat(Qt.RichText)
    window.mm_setup_notice_lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
    window.mm_setup_notice_lbl.setOpenExternalLinks(False)
    window.mm_setup_notice_lbl.linkActivated.connect(window._mod_manager_on_setup_notice_link)
    window.mm_setup_notice_lbl.setStyleSheet(
        "QLabel { color: #b00020; font-weight: 700; } "
        "QLabel a { color: #b00020; text-decoration: underline; }"
    )
    window.mm_setup_notice_lbl.setVisible(False)
    root.addWidget(window.mm_setup_notice_lbl)
    body = QSplitter(Qt.Horizontal)
    root.addWidget(body, 1)

    side_scroll = QScrollArea()
    side_scroll.setWidgetResizable(True)
    side_scroll.setFrameShape(QScrollArea.NoFrame)
    side_wrap = QWidget()
    sv = QVBoxLayout(side_wrap)
    sv.setContentsMargins(0, 0, 0, 0)
    sv.setSpacing(8)

    window.mm_paths_hint = QLabel(tr("mod_manager.paths_moved_info"))
    window.mm_paths_hint.setWordWrap(True)
    sv.addWidget(window.mm_paths_hint)

    window.mm_linux_cmd_edit = QLineEdit()
    window.mm_linux_cmd_edit.setPlaceholderText(tr("mod_manager.linux_cmd_placeholder"))
    window.mm_linux_cmd_edit.setToolTip(tr("mod_manager.linux_cmd_hint"))
    is_linux = sys_platform.startswith("linux")
    window.mm_linux_cmd_edit.setVisible(is_linux)
    window.mm_linux_cmd_box = None
    if is_linux:
        window.mm_linux_cmd_box = QGroupBox(tr("mod_manager.linux_cmd_label"))
        lnx_l = QVBoxLayout(window.mm_linux_cmd_box)
        lnx_l.setContentsMargins(8, 8, 8, 8)
        lnx_l.addWidget(window.mm_linux_cmd_edit)
        sv.addWidget(window.mm_linux_cmd_box)

    ops_box = QGroupBox(tr("mod_manager.title"))
    ops_l = QVBoxLayout(ops_box)
    ops_l.setContentsMargins(8, 8, 8, 8)
    ops_l.setSpacing(6)
    window.mm_new_repo_btn = QPushButton(tr("mod_manager.btn.new_mod"))
    window.mm_new_repo_btn.clicked.connect(window._mod_manager_create_repo_mod)
    ops_l.addWidget(window.mm_new_repo_btn)
    window.mm_add_direct_btn = QPushButton(tr("mod_manager.btn.add_direct"))
    window.mm_add_direct_btn.clicked.connect(window._mod_manager_add_direct_mod)
    ops_l.addWidget(window.mm_add_direct_btn)
    window.mm_create_install_from_mod_btn = QPushButton(tr("mod_manager.btn.create_install_from_mod"))
    window.mm_create_install_from_mod_btn.clicked.connect(window._mod_manager_create_installation_from_selected_mod)
    ops_l.addWidget(window.mm_create_install_from_mod_btn)
    window.mm_delete_btn = QPushButton(tr("mod_manager.btn.delete"))
    window.mm_delete_btn.clicked.connect(window._mod_manager_delete_selected)
    ops_l.addWidget(window.mm_delete_btn)
    window.mm_open_folder_btn = QPushButton(tr("mod_manager.btn.open_folder"))
    window.mm_open_folder_btn.clicked.connect(window._mod_manager_open_selected_folder)
    ops_l.addWidget(window.mm_open_folder_btn)
    window.mm_open_saves_btn = QPushButton(tr("mod_manager.btn.open_savegames"))
    window.mm_open_saves_btn.clicked.connect(window._mod_manager_open_savegames_folder)
    ops_l.addWidget(window.mm_open_saves_btn)
    window.mm_refresh_btn = QPushButton(tr("mod_manager.ctx.refresh"))
    window.mm_refresh_btn.clicked.connect(window._mod_manager_refresh_table)
    ops_l.addWidget(window.mm_refresh_btn)
    sv.addWidget(ops_box)

    window.mm_profile_header_lbl = QLabel(tr("mod_manager.selected_profile_none"))
    window.mm_profile_header_lbl.setWordWrap(True)
    window.mm_profile_header_lbl.setStyleSheet("font-size: 11pt; font-weight: 700; padding: 4px 2px;")
    sv.addWidget(window.mm_profile_header_lbl)
    window.mm_set_target_btn = QPushButton(tr("mod_manager.btn.set_target_installation"))
    window.mm_set_target_btn.clicked.connect(window._mod_manager_set_selected_as_target_installation)
    sv.addWidget(window.mm_set_target_btn)
    window.mm_force_saves_cb = QCheckBox(tr("mod_manager.save_risk.force_backup"))
    window.mm_force_saves_cb.toggled.connect(window._mod_manager_set_selected_force_save_backup)
    sv.addWidget(window.mm_force_saves_cb)

    edit_box = QGroupBox(tr("grp.editing"))
    el = QVBoxLayout(edit_box)
    el.setContentsMargins(8, 8, 8, 8)
    el.setSpacing(6)
    window.mm_edit_ctx_btn = QPushButton(tr("mod_manager.btn.open_for_editing"))
    window.mm_edit_ctx_btn.clicked.connect(window._mod_manager_use_for_editing)
    el.addWidget(window.mm_edit_ctx_btn)
    window.mm_clear_edit_ctx_btn = QPushButton(tr("mod_manager.btn.clear_editing"))
    window.mm_clear_edit_ctx_btn.setIcon(window.style().standardIcon(QStyle.SP_DialogCancelButton))
    window.mm_clear_edit_ctx_btn.clicked.connect(window._mod_manager_clear_edit_context)
    el.addWidget(window.mm_clear_edit_ctx_btn)
    window.mm_opensp_cb = QCheckBox(tr("mod_manager.opensp.enable_for_mod"))
    window.mm_opensp_cb.toggled.connect(window._mod_manager_set_selected_opensp)
    el.addWidget(window.mm_opensp_cb)
    window.mm_edit_sp_ship_btn = QPushButton(tr("mod_manager.btn.edit_sp_ship"))
    window.mm_edit_sp_ship_btn.clicked.connect(window._mod_manager_edit_sp_starter_ship)
    el.addWidget(window.mm_edit_sp_ship_btn)
    sv.addWidget(edit_box)

    run_box = QGroupBox(tr("mod_manager.run_group"))
    rl = QVBoxLayout(run_box)
    rl.setContentsMargins(8, 8, 8, 8)
    rl.setSpacing(6)
    window.mm_activate_btn = QPushButton(tr("mod_manager.btn.activate"))
    window.mm_activate_btn.clicked.connect(window._mod_manager_activate_selected)
    rl.addWidget(window.mm_activate_btn)
    window.mm_deactivate_btn = QPushButton(tr("mod_manager.btn.deactivate"))
    window.mm_deactivate_btn.clicked.connect(window._mod_manager_deactivate_clicked)
    rl.addWidget(window.mm_deactivate_btn)
    window.mm_repair_btn = QPushButton(window._mod_manager_repair_caption())
    window.mm_repair_btn.clicked.connect(window._mod_manager_repair_selected)
    rl.addWidget(window.mm_repair_btn)
    window.mm_launch_btn = QPushButton(tr("mod_manager.btn.launch_fl"))
    window.mm_launch_btn.clicked.connect(window._mod_manager_launch_fl_clicked)
    rl.addWidget(window.mm_launch_btn)
    window.mm_launch_apply_res_cb = QCheckBox(tr("mod_manager.launch.apply_resolution"))
    window.mm_launch_apply_res_cb.toggled.connect(window._mod_manager_set_launch_apply_resolution)
    rl.addWidget(window.mm_launch_apply_res_cb)
    window.mm_launch_ratio_lbl = QLabel(tr("mod_manager.launch.ratio_label"))
    rl.addWidget(window.mm_launch_ratio_lbl)
    window.mm_launch_ratio_combo = QComboBox()
    window.mm_launch_ratio_combo.setEditable(False)
    window.mm_launch_ratio_combo.addItems(window._mod_manager_ratio_options())
    cur_ratio = window._mm_launch_ratio or window._mod_manager_ratio_for_resolution_text(window._mm_launch_resolution) or "16:9"
    i_ratio = window.mm_launch_ratio_combo.findText(cur_ratio)
    if i_ratio < 0:
        window.mm_launch_ratio_combo.addItem(cur_ratio)
        i_ratio = window.mm_launch_ratio_combo.findText(cur_ratio)
    if i_ratio >= 0:
        window.mm_launch_ratio_combo.setCurrentIndex(i_ratio)
    window.mm_launch_ratio_combo.currentTextChanged.connect(window._mod_manager_set_launch_ratio)
    rl.addWidget(window.mm_launch_ratio_combo)
    window.mm_launch_res_lbl = QLabel(tr("mod_manager.launch.resolution_label"))
    rl.addWidget(window.mm_launch_res_lbl)
    window.mm_launch_res_combo = QComboBox()
    window.mm_launch_res_combo.setEditable(False)
    window.mm_launch_res_combo.addItems(window._mod_manager_resolution_options(cur_ratio))
    cur_res = window._mm_launch_resolution or window._mod_manager_default_resolution_text()
    i_res = window.mm_launch_res_combo.findText(cur_res)
    if i_res < 0:
        window.mm_launch_res_combo.addItem(cur_res)
        i_res = window.mm_launch_res_combo.findText(cur_res)
    if i_res >= 0:
        window.mm_launch_res_combo.setCurrentIndex(i_res)
    window.mm_launch_res_combo.currentTextChanged.connect(window._mod_manager_set_launch_resolution)
    rl.addWidget(window.mm_launch_res_combo)
    window.mm_launch_depth_cb = QCheckBox(tr("mod_manager.launch.set_color_depth_32"))
    window.mm_launch_depth_cb.toggled.connect(window._mod_manager_set_launch_color_depth_32)
    rl.addWidget(window.mm_launch_depth_cb)
    sv.addWidget(run_box)

    for widget in (
        window.mm_new_repo_btn,
        window.mm_add_direct_btn,
        window.mm_create_install_from_mod_btn,
        window.mm_delete_btn,
        window.mm_open_folder_btn,
        window.mm_open_saves_btn,
        window.mm_refresh_btn,
        window.mm_set_target_btn,
        window.mm_edit_ctx_btn,
        window.mm_opensp_cb,
        window.mm_edit_sp_ship_btn,
        window.mm_activate_btn,
        window.mm_deactivate_btn,
        window.mm_repair_btn,
        window.mm_launch_btn,
        window.mm_launch_apply_res_cb,
        window.mm_launch_ratio_lbl,
        window.mm_launch_ratio_combo,
        window.mm_launch_res_lbl,
        window.mm_launch_res_combo,
        window.mm_launch_depth_cb,
    ):
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    sv.addStretch(1)
    side_scroll.setWidget(side_wrap)
    side_scroll.setMinimumWidth(250)
    side_scroll.setMaximumWidth(360)
    body.addWidget(side_scroll)

    right_wrap = QWidget()
    rv = QVBoxLayout(right_wrap)
    rv.setContentsMargins(0, 0, 0, 0)
    rv.setSpacing(8)

    window.mm_direct_lbl = QLabel(tr("mod_manager.section.direct_mods"))
    window.mm_direct_lbl.setStyleSheet("font-weight: 700; font-size: 11pt;")
    rv.addWidget(window.mm_direct_lbl)
    window.mm_table = QTableWidget(0, 5)
    configure_readonly_table(window.mm_table)
    window.mm_table.setContextMenuPolicy(Qt.CustomContextMenu)
    window.mm_table.customContextMenuRequested.connect(window._on_mod_manager_table_context_menu)
    window.mm_table.itemSelectionChanged.connect(window._mod_manager_on_direct_selection_changed)
    window.mm_table.setHorizontalHeaderLabels(
        [tr("mod_manager.col.name"), tr("mod_manager.col.type"), tr("mod_manager.col.source"), tr("mod_manager.col.version"), tr("mod_manager.col.status")]
    )
    hm = window.mm_table.horizontalHeader()
    hm.setSectionResizeMode(0, QHeaderView.Interactive)
    hm.setSectionResizeMode(1, QHeaderView.Interactive)
    hm.setSectionResizeMode(2, QHeaderView.Stretch)
    hm.setSectionResizeMode(3, QHeaderView.Interactive)
    hm.setSectionResizeMode(4, QHeaderView.Interactive)
    window.mm_table.setColumnWidth(0, 240)
    window.mm_table.setColumnWidth(1, 120)
    window.mm_table.setColumnWidth(3, 110)
    window.mm_table.setColumnWidth(4, 180)
    window.mm_table.setIconSize(QSize(20, 20))
    window._mod_manager_apply_table_style()
    window.mm_table.setMinimumHeight(180)
    rv.addWidget(window.mm_table, 0)

    window.mm_target_line_lbl = QLabel("")
    window.mm_target_line_lbl.setWordWrap(True)
    window.mm_target_line_lbl.setTextFormat(Qt.RichText)
    window.mm_target_line_lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
    window.mm_target_line_lbl.setOpenExternalLinks(False)
    window.mm_target_line_lbl.linkActivated.connect(window._mod_manager_on_target_inline_link)
    rv.addWidget(window.mm_target_line_lbl)

    window.mm_repo_lbl = QLabel(tr("mod_manager.section.mods"))
    window.mm_repo_lbl.setStyleSheet("font-weight: 700; font-size: 11pt;")
    rv.addWidget(window.mm_repo_lbl)
    window.mm_repo_grid = QTableWidget(0, 5)
    window.mm_repo_grid.setSelectionMode(QAbstractItemView.SingleSelection)
    window.mm_repo_grid.setSelectionBehavior(QAbstractItemView.SelectItems)
    window.mm_repo_grid.setEditTriggers(QAbstractItemView.NoEditTriggers)
    window.mm_repo_grid.setShowGrid(False)
    window.mm_repo_grid.setAlternatingRowColors(False)
    window.mm_repo_grid.setWordWrap(True)
    window.mm_repo_grid.setContextMenuPolicy(Qt.CustomContextMenu)
    window.mm_repo_grid.customContextMenuRequested.connect(window._on_mod_manager_table_context_menu)
    window.mm_repo_grid.itemSelectionChanged.connect(window._mod_manager_on_repo_selection_changed)
    window.mm_repo_grid.setHorizontalHeaderLabels(["", "", "", "", ""])
    repo_h = window.mm_repo_grid.horizontalHeader()
    for col in range(5):
        repo_h.setSectionResizeMode(col, QHeaderView.Interactive)
    window.mm_repo_grid.verticalHeader().setVisible(False)
    window.mm_repo_grid.horizontalHeader().setVisible(False)
    window.mm_repo_grid.setIconSize(QSize(48, 48))
    rv.addWidget(window.mm_repo_grid, 1)

    window.mm_log = QTextEdit()
    window.mm_log.setReadOnly(True)
    window.mm_log.setMinimumHeight(88)
    window.mm_log.setMaximumHeight(140)
    rv.addWidget(window.mm_log)
    body.addWidget(right_wrap)
    body.setStretchFactor(0, 0)
    body.setStretchFactor(1, 1)
    window._mod_manager_apply_button_styles(False)
    window._mod_manager_apply_tooltips()
    return page
