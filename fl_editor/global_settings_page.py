from __future__ import annotations

import html
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QHeaderView,
)

from .ui_helpers import add_browse_path_form_row, configure_readonly_table


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
    window.gs_xml_editor_row, window.gs_xml_editor_edit, window.gs_xml_editor_browse_btn = add_browse_path_form_row(
        gs_xml_form,
        window.gs_xml_editor_path_lbl,
        button_text=tr("welcome.browse"),
        on_browse=lambda: window._global_settings_browse("xml_editor"),
    )
    window.gs_xml_editor_hint_lbl = QLabel(tr("settings.system_editor_xml_hint"))
    window.gs_xml_editor_hint_lbl.setWordWrap(True)
    gs_xml_form.addRow(QLabel(""), window.gs_xml_editor_hint_lbl)
    sys_l.addWidget(window.gs_xml_editor_box)
    sys_l.addStretch(1)
    window.gs_tabs.addTab(window.gs_system_editor_tab, tr("settings.tab.system_editor"))

    window.gs_mod_manager_tab = QWidget()
    mm_l = QVBoxLayout(window.gs_mod_manager_tab)
    mm_l.setContentsMargins(10, 10, 10, 10)
    mm_l.setSpacing(8)

    window.gs_mod_support_cb = QCheckBox(tr("settings.mod_support_enabled"))
    mm_l.addWidget(window.gs_mod_support_cb)

    window.gs_mod_paths_box = QGroupBox(tr("mod_manager.paths_group"))
    gs_mod_form = QFormLayout(window.gs_mod_paths_box)
    gs_mod_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    window.gs_repo_lbl = QLabel(tr("mod_manager.repo_label"))
    window.gs_repo_row, window.gs_repo_edit, window.gs_repo_browse_btn = add_browse_path_form_row(
        gs_mod_form,
        window.gs_repo_lbl,
        button_text=tr("welcome.browse"),
        on_browse=lambda: window._global_settings_browse("mod_repo"),
    )
    window.gs_repo_multi_lbl = QLabel(tr("mod_manager.repo_multi_label"))
    window.gs_repo_multi_edit = QTextEdit()
    window.gs_repo_multi_edit.setAcceptRichText(False)
    window.gs_repo_multi_edit.setMinimumHeight(88)
    window.gs_repo_multi_hint_lbl = QLabel(tr("mod_manager.repo_multi_hint"))
    window.gs_repo_multi_hint_lbl.setWordWrap(True)
    gs_mod_form.addRow(window.gs_repo_multi_lbl, window.gs_repo_multi_edit)
    gs_mod_form.addRow(QLabel(""), window.gs_repo_multi_hint_lbl)
    window.gs_flmm_lbl = QLabel(tr("mod_manager.flmm_install_label"))
    window.gs_flmm_row, window.gs_flmm_edit, window.gs_flmm_browse_btn = add_browse_path_form_row(
        gs_mod_form,
        window.gs_flmm_lbl,
        button_text=tr("welcome.browse"),
        on_browse=lambda: window._global_settings_browse("flmm_install"),
    )
    window.gs_flmm_detect_btn = QPushButton(tr("mod_manager.flmm_detect"))
    window.gs_flmm_detect_btn.clicked.connect(window._mod_manager_detect_flmm_installation)
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

    window.gs_pinned_tools_tab = QWidget()
    pinned_l = QVBoxLayout(window.gs_pinned_tools_tab)
    pinned_l.setContentsMargins(10, 10, 10, 10)
    pinned_l.setSpacing(8)

    window.gs_pinned_tools_info_lbl = QLabel(tr("settings.pinned_tools_info"))
    window.gs_pinned_tools_info_lbl.setWordWrap(True)
    pinned_l.addWidget(window.gs_pinned_tools_info_lbl)

    window.gs_pinned_tools_box = QGroupBox(tr("settings.pinned_tools_group"))
    gs_pinned_form = QFormLayout(window.gs_pinned_tools_box)
    gs_pinned_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    window._gs_pinned_tool_checks = {}
    for row in window._pinned_tool_definitions():
        key = str(row.get("key", "") or "").strip().lower()
        cb = QCheckBox(str(row.get("label", "") or key))
        window._gs_pinned_tool_checks[key] = cb
        gs_pinned_form.addRow(QLabel(""), cb)
    pinned_l.addWidget(window.gs_pinned_tools_box)
    pinned_l.addStretch(1)
    window.gs_tabs.addTab(window.gs_pinned_tools_tab, tr("settings.tab.pinned_tools"))

    window.gs_config_tab = QWidget()
    config_l = QVBoxLayout(window.gs_config_tab)
    config_l.setContentsMargins(10, 10, 10, 10)
    config_l.setSpacing(8)

    window.gs_config_info_lbl = QLabel(tr("settings.config_info"))
    window.gs_config_info_lbl.setWordWrap(True)
    config_l.addWidget(window.gs_config_info_lbl)

    window.gs_config_storage_box = QGroupBox(tr("settings.config_storage_group"))
    config_form = QFormLayout(window.gs_config_storage_box)
    config_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    window.gs_config_path_lbl = QLabel(tr("settings.config_path"))
    window.gs_config_path_row, window.gs_config_path_edit, window.gs_config_path_browse_btn = add_browse_path_form_row(
        config_form,
        window.gs_config_path_lbl,
        button_text=tr("welcome.browse"),
        on_browse=lambda: window._global_settings_browse("config_path"),
    )
    window.gs_config_path_edit.setReadOnly(True)
    config_btn_host = QWidget()
    config_btn_row = QHBoxLayout(config_btn_host)
    config_btn_row.setContentsMargins(0, 0, 0, 0)
    config_btn_row.setSpacing(8)
    window.gs_config_open_folder_btn = QPushButton(tr("settings.config_open_folder"))
    window.gs_config_open_folder_btn.clicked.connect(window._open_config_folder)
    window.gs_config_backup_btn = QPushButton(tr("settings.config_backup_now"))
    window.gs_config_backup_btn.clicked.connect(window._backup_app_config_from_settings)
    config_btn_row.addWidget(window.gs_config_open_folder_btn)
    config_btn_row.addWidget(window.gs_config_backup_btn)
    config_btn_row.addStretch(1)
    config_form.addRow(QLabel(""), config_btn_host)
    config_l.addWidget(window.gs_config_storage_box)

    window.gs_config_editor_box = QGroupBox(tr("settings.config_editor_group"))
    config_editor_l = QVBoxLayout(window.gs_config_editor_box)
    config_editor_l.setContentsMargins(8, 8, 8, 8)
    config_editor_l.setSpacing(6)
    window.gs_config_text = QTextEdit()
    window.gs_config_text.setAcceptRichText(False)
    window.gs_config_text.setLineWrapMode(QTextEdit.NoWrap)
    window.gs_config_text.setMinimumHeight(260)
    config_editor_l.addWidget(window.gs_config_text, 1)
    editor_btn_row = QHBoxLayout()
    window.gs_config_reload_btn = QPushButton(tr("settings.config_reload"))
    window.gs_config_reload_btn.clicked.connect(window._reload_config_editor_from_disk)
    window.gs_config_save_btn = QPushButton(tr("settings.config_save"))
    window.gs_config_save_btn.clicked.connect(window._save_config_editor_to_disk)
    window.gs_config_export_btn = QPushButton(tr("config.export_title"))
    window.gs_config_export_btn.clicked.connect(window._export_app_config)
    window.gs_config_import_btn = QPushButton(tr("config.import_title"))
    window.gs_config_import_btn.clicked.connect(window._import_app_config)
    editor_btn_row.addStretch(1)
    editor_btn_row.addWidget(window.gs_config_reload_btn)
    editor_btn_row.addWidget(window.gs_config_save_btn)
    editor_btn_row.addWidget(window.gs_config_export_btn)
    editor_btn_row.addWidget(window.gs_config_import_btn)
    config_editor_l.addLayout(editor_btn_row)
    config_l.addWidget(window.gs_config_editor_box, 1)

    window.gs_tabs.addTab(window.gs_config_tab, tr("settings.tab.config"))

    window.gs_suite_apps_tab = QWidget()
    window.gs_editors_tab = window.gs_suite_apps_tab
    editors_l = QVBoxLayout(window.gs_suite_apps_tab)
    editors_l.setContentsMargins(10, 10, 10, 10)
    editors_l.setSpacing(8)

    window.gs_editors_info_lbl = QLabel(tr("settings.suite_apps_info"))
    window.gs_editors_info_lbl.setWordWrap(True)
    editors_l.addWidget(window.gs_editors_info_lbl)

    window.gs_savegame_box = QGroupBox(tr("settings.savegame_group"))
    gs_savegame_form = QFormLayout(window.gs_savegame_box)
    gs_savegame_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    window.gs_savegame_editor_path_lbl = QLabel(tr("settings.savegame_editor_path"))
    window.gs_savegame_editor_row, window.gs_savegame_editor_edit, window.gs_savegame_editor_browse = add_browse_path_form_row(
        gs_savegame_form,
        window.gs_savegame_editor_path_lbl,
        button_text=tr("welcome.browse"),
        on_browse=lambda: window._global_settings_browse("savegame_editor"),
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
    gs_savegame_form.addRow(window.gs_savegame_repo_lbl, repo_wrap)
    gs_savegame_form.addRow(QLabel(""), window.gs_savegame_status_lbl)
    gs_savegame_form.addRow(QLabel(""), btn_wrap)
    gs_savegame_form.addRow(QLabel(""), window.gs_savegame_info_lbl)
    editors_l.addWidget(window.gs_savegame_box)

    window.gs_suite_desktop_box = QGroupBox(tr("suite.desktop.group"))
    gs_suite_desktop_form = QFormLayout(window.gs_suite_desktop_box)
    gs_suite_desktop_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    window._gs_suite_desktop_status_labels = {}
    window._gs_suite_desktop_path_labels = {}
    for row in window._suite_desktop_app_definitions():
        key = str(row.get("key", "") or "").strip().lower()
        if key == "savegame_editor":
            continue
        label = QLabel(tr(str(row.get("label_key", "") or "").strip()))
        window._gs_suite_desktop_path_labels[key] = label
        row_wrap, edit, browse_btn = add_browse_path_form_row(
            gs_suite_desktop_form,
            label,
            button_text=tr("welcome.browse"),
            on_browse=lambda app_key=key: window._global_settings_browse(f"suite_app:{app_key}"),
        )
        setattr(window, f"gs_suite_{key}_row", row_wrap)
        setattr(window, f"gs_suite_{key}_edit", edit)
        setattr(window, f"gs_suite_{key}_browse_btn", browse_btn)
        repo_btn = QPushButton(tr("suite.desktop.repo_open"))
        repo_btn.clicked.connect(lambda checked=False, app_key=key: window._open_suite_desktop_repo(app_key))
        setattr(window, f"gs_suite_{key}_repo_btn", repo_btn)
        open_btn = QPushButton(tr("suite.desktop.open"))
        open_btn.clicked.connect(lambda checked=False, app_key=key: window._launch_suite_desktop_app(app_key))
        setattr(window, f"gs_suite_{key}_open_btn", open_btn)
        install_btn = QPushButton(tr("settings.savegame_install_update"))
        install_btn.clicked.connect(lambda checked=False, app_key=key: window._install_or_update_suite_desktop_app(app_key))
        setattr(window, f"gs_suite_{key}_install_btn", install_btn)
        status_lbl = QLabel("")
        status_lbl.setWordWrap(True)
        setattr(window, f"gs_suite_{key}_status_lbl", status_lbl)
        window._gs_suite_desktop_status_labels[key] = status_lbl
        btn_host = QWidget()
        btn_row = QHBoxLayout(btn_host)
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(8)
        btn_row.addWidget(open_btn, 0)
        btn_row.addWidget(install_btn, 0)
        btn_row.addWidget(repo_btn, 0)
        btn_row.addStretch(1)
        gs_suite_desktop_form.addRow(QLabel(""), status_lbl)
        gs_suite_desktop_form.addRow(QLabel(""), btn_host)
    editors_l.addWidget(window.gs_suite_desktop_box)

    window.gs_suite_web_box = QGroupBox(tr("suite.web.group"))
    gs_suite_web_l = QVBoxLayout(window.gs_suite_web_box)
    gs_suite_web_l.setContentsMargins(8, 8, 8, 8)
    gs_suite_web_l.setSpacing(6)
    window.gs_suite_web_info_lbl = QLabel(tr("suite.web.info"))
    window.gs_suite_web_info_lbl.setWordWrap(True)
    gs_suite_web_l.addWidget(window.gs_suite_web_info_lbl)
    web_btn_wrap = QWidget()
    web_btn_row = QHBoxLayout(web_btn_wrap)
    web_btn_row.setContentsMargins(0, 0, 0, 0)
    web_btn_row.setSpacing(8)
    window._gs_suite_web_buttons = {}
    for row in window._suite_web_tool_definitions():
        key = str(row.get("key", "") or "").strip().lower()
        btn = QPushButton(window._suite_web_tool_label(key))
        btn.clicked.connect(lambda checked=False, web_key=key: window._open_suite_web_tool(web_key))
        window._gs_suite_web_buttons[key] = btn
        web_btn_row.addWidget(btn, 0)
    web_btn_row.addStretch(1)
    gs_suite_web_l.addWidget(web_btn_wrap)
    editors_l.addWidget(window.gs_suite_web_box)
    editors_l.addStretch(1)
    window.gs_tabs.addTab(window.gs_suite_apps_tab, tr("settings.tab.suite_apps"))

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
    window.gs_restore_tabs_lbl = QLabel(tr("settings.restore_tabs_label"))
    window.gs_update_prerelease_lbl = QLabel(tr("settings.update_prerelease_label"))
    window.gs_search_debounce_lbl = QLabel("Search Delay (ms)")

    window.gs_lang_cb = QComboBox()
    window.gs_lang_cb.addItems(available_languages() or ["de", "en"])
    window.gs_theme_cb = QComboBox()
    window.gs_theme_cb.addItems(theme_names)
    window.gs_auto_name_lang_cb = QComboBox()
    window.gs_auto_name_lang_cb.addItem(tr("settings.auto_name_lang.de"), "de")
    window.gs_auto_name_lang_cb.addItem(tr("settings.auto_name_lang.en"), "en")
    window.gs_update_check_cb = QCheckBox(tr("settings.update_check_enabled"))
    window.gs_show_splash_cb = QCheckBox(tr("settings.show_splash_enabled"))
    window.gs_restore_tabs_cb = QCheckBox(tr("settings.restore_tabs_enabled"))
    window.gs_update_prerelease_cb = QCheckBox(tr("settings.update_prerelease_enabled"))
    window.gs_search_debounce_spin = QSpinBox()
    window.gs_search_debounce_spin.setRange(0, 2000)
    window.gs_search_debounce_spin.setSingleStep(25)
    window.gs_search_debounce_spin.setSuffix(" ms")
    window.gs_search_debounce_spin.setToolTip("0 = immediate search, higher values wait longer after typing")

    form.addRow(window.gs_lang_lbl, window.gs_lang_cb)
    form.addRow(window.gs_theme_lbl, window.gs_theme_cb)
    form.addRow(window.gs_auto_name_lang_lbl, window.gs_auto_name_lang_cb)
    form.addRow(window.gs_search_debounce_lbl, window.gs_search_debounce_spin)
    form.addRow(window.gs_update_check_lbl, window.gs_update_check_cb)
    form.addRow(window.gs_update_prerelease_lbl, window.gs_update_prerelease_cb)
    form.addRow(window.gs_show_splash_lbl, window.gs_show_splash_cb)
    form.addRow(window.gs_restore_tabs_lbl, window.gs_restore_tabs_cb)
    general_l.addWidget(box)

    window.gs_ids_resource_box = QGroupBox(tr("settings.ids_resource_group"))
    ids_resource_form = QFormLayout(window.gs_ids_resource_box)
    ids_resource_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    window.gs_ids_resource_target_lbl = QLabel(tr("settings.ids_resource_target"))
    window.gs_ids_resource_target_cb = QComboBox()
    window.gs_ids_resource_target_cb.setEditable(True)
    ids_resource_form.addRow(window.gs_ids_resource_target_lbl, window.gs_ids_resource_target_cb)
    window.gs_ids_resource_info_lbl = QLabel(tr("settings.ids_resource_info"))
    window.gs_ids_resource_info_lbl.setWordWrap(True)
    ids_resource_form.addRow(QLabel(""), window.gs_ids_resource_info_lbl)
    general_l.addWidget(window.gs_ids_resource_box)

    window.gs_bini_box = QGroupBox(tr("settings.bini_group"))
    bini_form = QFormLayout(window.gs_bini_box)
    bini_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    window.gs_bini_path_lbl = QLabel(tr("settings.bini_path"))
    window.gs_bini_target_row, window.gs_bini_target_edit, window.gs_bini_target_browse = add_browse_path_form_row(
        bini_form,
        window.gs_bini_path_lbl,
        button_text=tr("welcome.browse"),
        on_browse=lambda: window._global_settings_browse("bini_target"),
    )
    window.gs_bini_info_lbl = QLabel(tr("settings.bini_info"))
    window.gs_bini_info_lbl.setWordWrap(True)
    window.gs_bini_convert_btn = QPushButton(tr("settings.bini_convert"))
    window.gs_bini_convert_btn.clicked.connect(window._convert_bini_folder_from_settings)
    bini_form.addRow(QLabel(""), window.gs_bini_info_lbl)
    bini_form.addRow(QLabel(""), window.gs_bini_convert_btn)
    general_l.addWidget(window.gs_bini_box)

    window.gs_ids_toolchain_box = QGroupBox(tr("settings.ids_toolchain_group"))
    ids_toolchain_form = QFormLayout(window.gs_ids_toolchain_box)
    ids_toolchain_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    window.gs_ids_toolchain_path_lbl = QLabel(tr("settings.ids_toolchain_path"))
    (
        window.gs_ids_toolchain_row,
        window.gs_ids_toolchain_edit,
        window.gs_ids_toolchain_browse_btn,
    ) = add_browse_path_form_row(
        ids_toolchain_form,
        window.gs_ids_toolchain_path_lbl,
        button_text=tr("welcome.browse"),
        on_browse=lambda: window._global_settings_browse("ids_toolchain_dir"),
    )
    window.gs_ids_toolchain_info_lbl = QLabel(tr("settings.ids_toolchain_info"))
    window.gs_ids_toolchain_info_lbl.setWordWrap(True)
    ids_toolchain_form.addRow(QLabel(""), window.gs_ids_toolchain_info_lbl)
    window.gs_ids_toolchain_help_btn = QPushButton("?")
    window.gs_ids_toolchain_help_btn.setFixedWidth(28)
    window.gs_ids_toolchain_help_btn.setToolTip(tr("settings.ids_toolchain_help_tip"))
    window.gs_ids_toolchain_help_btn.clicked.connect(window._show_ids_toolchain_help_dialog)
    row_layout = window.gs_ids_toolchain_row.layout()
    if row_layout is not None:
        row_layout.addWidget(window.gs_ids_toolchain_help_btn)
    window.gs_ids_toolchain_box.setVisible(sys.platform.startswith("linux"))
    general_l.addWidget(window.gs_ids_toolchain_box)

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

    window.gs_reset_tab = QWidget()
    reset_l = QVBoxLayout(window.gs_reset_tab)
    reset_l.setContentsMargins(10, 10, 10, 10)
    reset_l.setSpacing(10)

    window.gs_reset_info_lbl = QLabel(tr("settings.reset_info"))
    window.gs_reset_info_lbl.setWordWrap(True)
    reset_l.addWidget(window.gs_reset_info_lbl)

    window.gs_reset_box = QGroupBox(tr("settings.reset_group"))
    reset_box_layout = QVBoxLayout(window.gs_reset_box)
    reset_box_layout.setContentsMargins(10, 10, 10, 10)
    reset_box_layout.setSpacing(8)
    window.gs_reset_warn_lbl = QLabel(tr("settings.reset_warning"))
    window.gs_reset_warn_lbl.setWordWrap(True)
    reset_box_layout.addWidget(window.gs_reset_warn_lbl)
    reset_btn_row = QHBoxLayout()
    reset_btn_row.addStretch(1)
    window.gs_factory_reset_btn = QPushButton(tr("help.reset_factory"))
    window.gs_factory_reset_btn.clicked.connect(window._factory_reset_from_help)
    reset_btn_row.addWidget(window.gs_factory_reset_btn)
    reset_box_layout.addLayout(reset_btn_row)
    reset_l.addWidget(window.gs_reset_box)
    reset_l.addStretch(1)
    window.gs_tabs.addTab(window.gs_reset_tab, tr("settings.tab.reset"))

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
    window.gs_dev_table.itemActivated.connect(window._on_dev_status_item_activated)
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
