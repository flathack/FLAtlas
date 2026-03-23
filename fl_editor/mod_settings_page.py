from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from .mod_settings_runtime import KNOWN_EXE_OFFSETS
from .ui_helpers import configure_readonly_table


def build_mod_settings_page(window, *, tr):
    page = QWidget()
    root = QVBoxLayout(page)
    root.setContentsMargins(10, 10, 10, 10)
    root.setSpacing(8)

    window.mod_settings_title_lbl = QLabel(tr("mod_settings.title"))
    window.mod_settings_title_lbl.setStyleSheet("font-size: 15pt; font-weight: bold;")
    root.addWidget(window.mod_settings_title_lbl)

    window.mod_settings_info_lbl = QLabel(tr("mod_settings.info"))
    window.mod_settings_info_lbl.setWordWrap(True)
    root.addWidget(window.mod_settings_info_lbl)

    window.mod_settings_profile_lbl = QLabel("")
    window.mod_settings_profile_lbl.setWordWrap(True)
    window.mod_settings_profile_lbl.setStyleSheet("font-weight: 700;")
    root.addWidget(window.mod_settings_profile_lbl)

    window.mod_settings_top_view_icons_box = QGroupBox("2D Top-View Icons")
    top_view_form = QFormLayout(window.mod_settings_top_view_icons_box)
    top_view_form.setContentsMargins(8, 8, 8, 8)
    top_view_form.setHorizontalSpacing(10)
    top_view_form.setVerticalSpacing(8)
    window.mod_settings_top_view_icons_mod_content_lbl = QLabel("Mod content:")
    window.mod_settings_top_view_icons_mod_content_cb = QCheckBox(
        "Generate persistent 2D top-view icons for this mod's 3D objects"
    )
    window.mod_settings_top_view_icons_mod_content_cb.toggled.connect(window._mod_settings_apply_top_view_icon_toggle)
    window.mod_settings_top_view_icons_info_lbl = QLabel(
        "Vanilla Freelancer icons are generated and cached automatically. This switch only affects additional icons for the currently active mod profile."
    )
    window.mod_settings_top_view_icons_info_lbl.setWordWrap(True)
    window.mod_settings_top_view_icons_prewarm_btn = QPushButton("Prebuild Mod Icon Cache")
    window.mod_settings_top_view_icons_prewarm_btn.clicked.connect(window._mod_settings_prewarm_top_view_icon_cache)
    top_view_form.addRow(
        window.mod_settings_top_view_icons_mod_content_lbl,
        window.mod_settings_top_view_icons_mod_content_cb,
    )
    top_view_form.addRow(QLabel(""), window.mod_settings_top_view_icons_info_lbl)
    top_view_form.addRow(QLabel(""), window.mod_settings_top_view_icons_prewarm_btn)
    root.addWidget(window.mod_settings_top_view_icons_box)

    window.mod_settings_exe_path_box = QGroupBox(tr("mod_settings.exe_path_group"))
    exe_path_layout = QVBoxLayout(window.mod_settings_exe_path_box)
    exe_path_layout.setContentsMargins(8, 8, 8, 8)
    exe_path_layout.setSpacing(6)
    window.mod_settings_exe_path_info_lbl = QLabel(tr("mod_settings.exe_path_info"))
    window.mod_settings_exe_path_info_lbl.setWordWrap(True)
    exe_path_layout.addWidget(window.mod_settings_exe_path_info_lbl)
    window.mod_settings_edit_config_link = QLabel(tr("mod_settings.link.edit_config"))
    window.mod_settings_edit_config_link.setOpenExternalLinks(False)
    window.mod_settings_edit_config_link.linkActivated.connect(window._mod_settings_open_config_in_editor)
    exe_path_layout.addWidget(window.mod_settings_edit_config_link)
    window.mod_settings_exe_path_resolved_lbl = QLabel("")
    window.mod_settings_exe_path_resolved_lbl.setWordWrap(True)
    exe_path_layout.addWidget(window.mod_settings_exe_path_resolved_lbl)
    exe_path_row = QHBoxLayout()
    window.mod_settings_exe_path_edit = QLineEdit()
    exe_path_row.addWidget(window.mod_settings_exe_path_edit, 1)
    window.mod_settings_exe_path_browse_btn = QPushButton(tr("welcome.browse"))
    window.mod_settings_exe_path_browse_btn.clicked.connect(window._mod_settings_browse_exe_path)
    exe_path_row.addWidget(window.mod_settings_exe_path_browse_btn)
    window.mod_settings_exe_path_save_btn = QPushButton(tr("mod_settings.btn.save_exe_path"))
    window.mod_settings_exe_path_save_btn.clicked.connect(window._mod_settings_apply_exe_path)
    exe_path_row.addWidget(window.mod_settings_exe_path_save_btn)
    exe_path_layout.addLayout(exe_path_row)
    root.addWidget(window.mod_settings_exe_path_box)

    window.mod_settings_versions_box = QGroupBox(tr("mod_settings.versions_group"))
    versions_form = QFormLayout(window.mod_settings_versions_box)
    versions_form.setContentsMargins(8, 8, 8, 8)
    versions_form.setHorizontalSpacing(10)
    versions_form.setVerticalSpacing(8)

    window.mod_settings_version_current_labels = {}
    window.mod_settings_version_editors = {}
    window.mod_settings_version_buttons = {}
    window.mod_settings_launch_buttons = {}

    for exe_name in ("Freelancer.exe", "FLServer.exe"):
        row_wrap = QWidget()
        row_layout = QHBoxLayout(row_wrap)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        current_lbl = QLabel("")
        current_lbl.setMinimumWidth(220)
        row_layout.addWidget(current_lbl)

        edit = QLineEdit()
        row_layout.addWidget(edit, 1)

        btn = QPushButton(tr("mod_settings.btn.apply_version"))
        btn.clicked.connect(lambda checked=False, name=exe_name: window._mod_settings_apply_version(name))
        row_layout.addWidget(btn)
        launch_btn = QPushButton(tr("mod_settings.btn.launch_exe"))
        launch_btn.clicked.connect(lambda checked=False, name=exe_name: window._mod_settings_launch_exe(name))
        row_layout.addWidget(launch_btn)

        versions_form.addRow(exe_name, row_wrap)
        window.mod_settings_version_current_labels[exe_name] = current_lbl
        window.mod_settings_version_editors[exe_name] = edit
        window.mod_settings_version_buttons[exe_name] = btn
        window.mod_settings_launch_buttons[exe_name] = launch_btn

    root.addWidget(window.mod_settings_versions_box)

    window.mod_settings_offsets_box = QGroupBox(tr("mod_settings.offsets_group"))
    offsets_layout = QVBoxLayout(window.mod_settings_offsets_box)
    offsets_layout.setContentsMargins(8, 8, 8, 8)
    offsets_layout.setSpacing(8)

    window.mod_settings_offset_table = QTableWidget(len(KNOWN_EXE_OFFSETS), 7)
    configure_readonly_table(window.mod_settings_offset_table)
    window.mod_settings_offset_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    window.mod_settings_offset_table.setHorizontalHeaderLabels(
        [
            tr("mod_settings.col.setting"),
            tr("mod_settings.col.exe"),
            tr("mod_settings.col.offset"),
            tr("mod_settings.col.type"),
            tr("mod_settings.col.current"),
            tr("mod_settings.col.new"),
            tr("mod_settings.col.notes"),
        ]
    )
    window.mod_settings_offset_value_edits = {}
    for row, spec in enumerate(KNOWN_EXE_OFFSETS):
        edit = QLineEdit()
        window.mod_settings_offset_table.setCellWidget(row, 5, edit)
        window.mod_settings_offset_value_edits[spec.key] = edit
    header = window.mod_settings_offset_table.horizontalHeader()
    header.setStretchLastSection(True)
    offsets_layout.addWidget(window.mod_settings_offset_table)

    btn_row = QHBoxLayout()
    window.mod_settings_reload_btn = QPushButton(tr("mod_settings.btn.reload"))
    window.mod_settings_reload_btn.clicked.connect(window._mod_settings_refresh)
    btn_row.addWidget(window.mod_settings_reload_btn)
    btn_row.addStretch(1)
    window.mod_settings_apply_btn = QPushButton(tr("mod_settings.btn.apply_offsets"))
    window.mod_settings_apply_btn.clicked.connect(window._mod_settings_apply_offsets)
    btn_row.addWidget(window.mod_settings_apply_btn)
    offsets_layout.addLayout(btn_row)

    root.addWidget(window.mod_settings_offsets_box, 1)
    return page
