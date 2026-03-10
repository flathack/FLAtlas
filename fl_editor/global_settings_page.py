from __future__ import annotations

import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QHeaderView,
)

from .ui_helpers import build_browse_path_row, configure_readonly_table


def build_global_settings_page(
    window,
    *,
    tr,
    available_languages,
    theme_names,
    savegame_editor_github_url: str,
):
    page = QWidget()
    root = QVBoxLayout(page)
    root.setContentsMargins(20, 18, 20, 18)
    root.setSpacing(10)
    window.gs_title_lbl = QLabel(window._global_settings_caption())
    window.gs_title_lbl.setStyleSheet("font-size: 16pt; font-weight: bold;")
    root.addWidget(window.gs_title_lbl)
    window.gs_info_lbl = QLabel(tr("settings.global_info"))
    window.gs_info_lbl.setWordWrap(True)
    window.gs_info_lbl.setStyleSheet("")
    root.addWidget(window.gs_info_lbl)

    window.gs_tabs = QTabWidget()
    root.addWidget(window.gs_tabs, 1)

    window.gs_system_editor_tab = QWidget()
    sys_l = QVBoxLayout(window.gs_system_editor_tab)
    sys_l.setContentsMargins(10, 10, 10, 10)
    sys_l.setSpacing(8)
    window.gs_system_editor_info_lbl = QLabel(tr("settings.system_editor_info"))
    window.gs_system_editor_info_lbl.setWordWrap(True)
    sys_l.addWidget(window.gs_system_editor_info_lbl)
    window.gs_xml_editor_box = QGroupBox(tr("settings.system_editor_xml_group"))
    gs_xml_form = QFormLayout(window.gs_xml_editor_box)
    gs_xml_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    window.gs_xml_editor_path_lbl = QLabel(tr("settings.system_editor_xml_editor"))
    window.gs_xml_editor_row, window.gs_xml_editor_edit, window.gs_xml_editor_browse_btn = build_browse_path_row(
        tr("welcome.browse"),
        lambda: window._global_settings_browse("xml_editor"),
    )
    window.gs_xml_editor_hint_lbl = QLabel(tr("settings.system_editor_xml_hint"))
    window.gs_xml_editor_hint_lbl.setWordWrap(True)
    gs_xml_form.addRow(window.gs_xml_editor_path_lbl, window.gs_xml_editor_row)
    gs_xml_form.addRow(QLabel(""), window.gs_xml_editor_hint_lbl)
    sys_l.addWidget(window.gs_xml_editor_box)
    sys_l.addStretch(1)
    window.gs_tabs.addTab(window.gs_system_editor_tab, tr("settings.tab.system_editor"))

    window.gs_mod_manager_tab = QWidget()
    mm_l = QVBoxLayout(window.gs_mod_manager_tab)
    mm_l.setContentsMargins(10, 10, 10, 10)
    mm_l.setSpacing(8)

    window.gs_mod_paths_box = QGroupBox(tr("mod_manager.paths_group"))
    gs_mod_form = QFormLayout(window.gs_mod_paths_box)
    gs_mod_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    window.gs_repo_lbl = QLabel(tr("mod_manager.repo_label"))
    window.gs_repo_row, window.gs_repo_edit, window.gs_repo_browse_btn = build_browse_path_row(
        tr("welcome.browse"),
        lambda: window._global_settings_browse("mod_repo"),
    )
    gs_mod_form.addRow(window.gs_repo_lbl, window.gs_repo_row)
    window.gs_repo_multi_lbl = QLabel(tr("mod_manager.repo_multi_label"))
    window.gs_repo_multi_edit = QTextEdit()
    window.gs_repo_multi_edit.setAcceptRichText(False)
    window.gs_repo_multi_edit.setMinimumHeight(88)
    window.gs_repo_multi_hint_lbl = QLabel(tr("mod_manager.repo_multi_hint"))
    window.gs_repo_multi_hint_lbl.setWordWrap(True)
    gs_mod_form.addRow(window.gs_repo_multi_lbl, window.gs_repo_multi_edit)
    gs_mod_form.addRow(QLabel(""), window.gs_repo_multi_hint_lbl)
    window.gs_flmm_lbl = QLabel(tr("mod_manager.flmm_install_label"))
    window.gs_flmm_row, window.gs_flmm_edit, window.gs_flmm_browse_btn = build_browse_path_row(
        tr("welcome.browse"),
        lambda: window._global_settings_browse("flmm_install"),
    )
    window.gs_flmm_detect_btn = QPushButton(tr("mod_manager.flmm_detect"))
    window.gs_flmm_detect_btn.clicked.connect(window._mod_manager_detect_flmm_installation)
    gs_mod_form.addRow(window.gs_flmm_lbl, window.gs_flmm_row)
    gs_mod_form.addRow(QLabel(""), window.gs_flmm_detect_btn)
    mm_l.addWidget(window.gs_mod_paths_box)

    window.gs_mm_placeholder_lbl = QLabel(tr("settings.mod_manager_placeholder"))
    window.gs_mm_placeholder_lbl.setWordWrap(True)
    mm_l.addWidget(window.gs_mm_placeholder_lbl)

    mm_btn_row = QHBoxLayout()
    mm_btn_row.addStretch(1)
    window.gs_mm_apply_btn = QPushButton(tr("settings.apply"))
    window.gs_mm_apply_btn.clicked.connect(window._apply_mod_manager_settings_from_global)
    mm_btn_row.addWidget(window.gs_mm_apply_btn)
    mm_l.addLayout(mm_btn_row)
    mm_l.addStretch(1)
    window.gs_tabs.addTab(window.gs_mod_manager_tab, tr("settings.tab.mod_manager"))

    window.gs_editors_tab = QWidget()
    editors_l = QVBoxLayout(window.gs_editors_tab)
    editors_l.setContentsMargins(10, 10, 10, 10)
    editors_l.setSpacing(8)

    window.gs_editors_info_lbl = QLabel(tr("settings.editors_info"))
    window.gs_editors_info_lbl.setWordWrap(True)
    editors_l.addWidget(window.gs_editors_info_lbl)

    window.gs_savegame_box = QGroupBox(tr("settings.savegame_group"))
    gs_savegame_form = QFormLayout(window.gs_savegame_box)
    gs_savegame_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    window.gs_savegame_editor_path_lbl = QLabel(tr("settings.savegame_editor_path"))
    window.gs_savegame_editor_row, window.gs_savegame_editor_edit, window.gs_savegame_editor_browse = build_browse_path_row(
        tr("welcome.browse"),
        lambda: window._global_settings_browse("savegame_editor"),
    )
    window.gs_savegame_info_lbl = QLabel(tr("settings.savegame_info"))
    window.gs_savegame_info_lbl.setWordWrap(True)
    window.gs_savegame_repo_lbl = QLabel(tr("settings.savegame_repo_label"))
    window.gs_savegame_repo_link = QLabel(
        f'<a href="{html.escape(savegame_editor_github_url)}">{html.escape(savegame_editor_github_url)}</a>'
    )
    window.gs_savegame_repo_link.setTextFormat(Qt.RichText)
    window.gs_savegame_repo_link.setOpenExternalLinks(True)
    window.gs_savegame_repo_btn = QPushButton(tr("settings.savegame_repo_open"))
    window.gs_savegame_repo_btn.clicked.connect(window._open_savegame_editor_repo)
    window.gs_savegame_status_lbl = QLabel("")
    window.gs_savegame_status_lbl.setWordWrap(True)
    window.gs_savegame_check_btn = QPushButton(tr("settings.savegame_check_updates"))
    window.gs_savegame_check_btn.clicked.connect(window._check_savegame_editor_updates_manual)
    window.gs_savegame_install_btn = QPushButton(tr("settings.savegame_install_update"))
    window.gs_savegame_install_btn.clicked.connect(window._install_or_update_savegame_editor)
    repo_wrap = QWidget()
    repo_row = QHBoxLayout(repo_wrap)
    repo_row.setContentsMargins(0, 0, 0, 0)
    repo_row.setSpacing(8)
    repo_row.addWidget(window.gs_savegame_repo_link, 1)
    repo_row.addWidget(window.gs_savegame_repo_btn, 0)
    btn_wrap = QWidget()
    btn_row = QHBoxLayout(btn_wrap)
    btn_row.setContentsMargins(0, 0, 0, 0)
    btn_row.setSpacing(8)
    btn_row.addWidget(window.gs_savegame_check_btn, 0)
    btn_row.addWidget(window.gs_savegame_install_btn, 0)
    btn_row.addStretch(1)
    gs_savegame_form.addRow(window.gs_savegame_editor_path_lbl, window.gs_savegame_editor_row)
    gs_savegame_form.addRow(window.gs_savegame_repo_lbl, repo_wrap)
    gs_savegame_form.addRow(QLabel(""), window.gs_savegame_status_lbl)
    gs_savegame_form.addRow(QLabel(""), btn_wrap)
    gs_savegame_form.addRow(QLabel(""), window.gs_savegame_info_lbl)
    editors_l.addWidget(window.gs_savegame_box)
    editors_l.addStretch(1)
    window.gs_tabs.addTab(window.gs_editors_tab, tr("settings.tab.editors"))

    window.gs_general_tab = QWidget()
    general_l = QVBoxLayout(window.gs_general_tab)
    general_l.setContentsMargins(10, 10, 10, 10)
    general_l.setSpacing(8)

    box = QGroupBox(tr("welcome.settings_group"))
    form = QFormLayout(box)
    form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    window.gs_lang_lbl = QLabel(tr("welcome.lang_label"))
    window.gs_theme_lbl = QLabel(tr("welcome.theme_label"))
    window.gs_auto_name_lang_lbl = QLabel(tr("settings.auto_name_lang_label"))
    window.gs_update_check_lbl = QLabel(tr("settings.update_check_label"))
    window.gs_show_splash_lbl = QLabel(tr("settings.show_splash_label"))
    window.gs_update_prerelease_lbl = QLabel(tr("settings.update_prerelease_label"))

    window.gs_lang_cb = QComboBox()
    window.gs_lang_cb.addItems(available_languages() or ["de", "en"])
    window.gs_theme_cb = QComboBox()
    window.gs_theme_cb.addItems(theme_names)
    window.gs_auto_name_lang_cb = QComboBox()
    window.gs_auto_name_lang_cb.addItem(tr("settings.auto_name_lang.de"), "de")
    window.gs_auto_name_lang_cb.addItem(tr("settings.auto_name_lang.en"), "en")
    window.gs_update_check_cb = QCheckBox(tr("settings.update_check_enabled"))
    window.gs_show_splash_cb = QCheckBox(tr("settings.show_splash_enabled"))
    window.gs_update_prerelease_cb = QCheckBox(tr("settings.update_prerelease_enabled"))

    form.addRow(window.gs_lang_lbl, window.gs_lang_cb)
    form.addRow(window.gs_theme_lbl, window.gs_theme_cb)
    form.addRow(window.gs_auto_name_lang_lbl, window.gs_auto_name_lang_cb)
    form.addRow(window.gs_update_check_lbl, window.gs_update_check_cb)
    form.addRow(window.gs_update_prerelease_lbl, window.gs_update_prerelease_cb)
    form.addRow(window.gs_show_splash_lbl, window.gs_show_splash_cb)
    general_l.addWidget(box)

    window.gs_bini_box = QGroupBox(tr("settings.bini_group"))
    bini_form = QFormLayout(window.gs_bini_box)
    bini_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    window.gs_bini_path_lbl = QLabel(tr("settings.bini_path"))
    window.gs_bini_target_row, window.gs_bini_target_edit, window.gs_bini_target_browse = build_browse_path_row(
        tr("welcome.browse"),
        lambda: window._global_settings_browse("bini_target"),
    )
    window.gs_bini_info_lbl = QLabel(tr("settings.bini_info"))
    window.gs_bini_info_lbl.setWordWrap(True)
    window.gs_bini_convert_btn = QPushButton(tr("settings.bini_convert"))
    window.gs_bini_convert_btn.clicked.connect(window._convert_bini_folder_from_settings)
    bini_form.addRow(window.gs_bini_path_lbl, window.gs_bini_target_row)
    bini_form.addRow(QLabel(""), window.gs_bini_info_lbl)
    bini_form.addRow(QLabel(""), window.gs_bini_convert_btn)
    general_l.addWidget(window.gs_bini_box)

    window.gs_dll_debug_box = QGroupBox(tr("settings.dll_debug_group"))
    gs_dbg_l = QVBoxLayout(window.gs_dll_debug_box)
    gs_dbg_l.setContentsMargins(8, 8, 8, 8)
    gs_dbg_l.setSpacing(6)
    window.gs_dll_debug_info_lbl = QLabel(tr("settings.dll_debug_info"))
    window.gs_dll_debug_info_lbl.setWordWrap(True)
    gs_dbg_l.addWidget(window.gs_dll_debug_info_lbl)
    window.gs_dll_debug_text = QTextEdit()
    window.gs_dll_debug_text.setReadOnly(True)
    window.gs_dll_debug_text.setMinimumHeight(170)
    window.gs_dll_debug_text.setAcceptRichText(False)
    window.gs_dll_debug_text.setLineWrapMode(QTextEdit.NoWrap)
    gs_dbg_l.addWidget(window.gs_dll_debug_text, 1)
    dbg_btn_row = QHBoxLayout()
    dbg_btn_row.addStretch(1)
    window.gs_dll_debug_refresh_btn = QPushButton(tr("settings.dll_debug_refresh"))
    window.gs_dll_debug_refresh_btn.clicked.connect(window._refresh_dll_debug_view)
    dbg_btn_row.addWidget(window.gs_dll_debug_refresh_btn)
    gs_dbg_l.addLayout(dbg_btn_row)
    general_l.addWidget(window.gs_dll_debug_box)

    window.gs_freelancer_ini_btn = QPushButton(tr("settings.freelancer_ini_editor"))
    window.gs_freelancer_ini_btn.clicked.connect(window._open_freelancer_ini_editor)
    window.gs_apply_btn = QPushButton(tr("settings.apply"))
    window.gs_apply_btn.clicked.connect(window._apply_global_settings)
    general_l.addStretch(1)
    window.gs_tabs.insertTab(0, window.gs_general_tab, tr("settings.tab.general"))

    window.gs_dev_status_tab = QWidget()
    dev_l = QVBoxLayout(window.gs_dev_status_tab)
    dev_l.setContentsMargins(10, 10, 10, 10)
    dev_l.setSpacing(8)

    window.gs_dev_status_info_lbl = QLabel(tr("dev_status.info"))
    window.gs_dev_status_info_lbl.setWordWrap(True)
    dev_l.addWidget(window.gs_dev_status_info_lbl)

    window.gs_dev_states_box = QGroupBox(tr("dev_status.states_title"))
    dev_states_l = QVBoxLayout(window.gs_dev_states_box)
    dev_states_l.setContentsMargins(8, 8, 8, 8)
    dev_states_l.setSpacing(4)
    window.gs_dev_states_lbl = QLabel("")
    window.gs_dev_states_lbl.setWordWrap(True)
    dev_states_l.addWidget(window.gs_dev_states_lbl)
    dev_l.addWidget(window.gs_dev_states_box)

    window.gs_dev_table = QTableWidget(0, 3)
    configure_readonly_table(window.gs_dev_table)
    window.gs_dev_table.setHorizontalHeaderLabels(
        [tr("dev_status.col.nav"), tr("dev_status.col.status"), tr("dev_status.col.details")]
    )
    dev_h = window.gs_dev_table.horizontalHeader()
    dev_h.setSectionResizeMode(0, QHeaderView.Interactive)
    dev_h.setSectionResizeMode(1, QHeaderView.Interactive)
    dev_h.setSectionResizeMode(2, QHeaderView.Stretch)
    window.gs_dev_table.setColumnWidth(0, 220)
    window.gs_dev_table.setColumnWidth(1, 170)
    dev_l.addWidget(window.gs_dev_table, 1)

    window.gs_tabs.addTab(window.gs_dev_status_tab, tr("settings.tab.dev_status"))
    gs_bottom_btn_row = QHBoxLayout()
    gs_bottom_btn_row.addStretch(1)
    gs_bottom_btn_row.addWidget(window.gs_freelancer_ini_btn)
    gs_bottom_btn_row.addWidget(window.gs_apply_btn)
    root.addLayout(gs_bottom_btn_row)

    return page
