from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


def build_welcome_page(window, *, tr, available_languages, get_language, current_theme, theme_names):
    page = QWidget()
    root = QVBoxLayout(page)
    root.setContentsMargins(28, 20, 28, 20)
    root.setSpacing(10)

    window.welcome_title_lbl = QLabel(tr("welcome.title"))
    window.welcome_title_lbl.setStyleSheet("font-size: 18pt; font-weight: bold;")
    root.addWidget(window.welcome_title_lbl)

    window.welcome_reason_lbl = QLabel(tr("welcome.reason.no_path"))
    window.welcome_reason_lbl.setWordWrap(True)
    window.welcome_reason_lbl.setStyleSheet("")
    root.addWidget(window.welcome_reason_lbl)

    window.welcome_intro_grp = QGroupBox(tr("welcome.intro_group"))
    intro_l = QVBoxLayout(window.welcome_intro_grp)
    intro_l.setContentsMargins(10, 8, 10, 8)
    intro_l.setSpacing(6)
    window.welcome_intro_lbl = QLabel(tr("welcome.intro_text"))
    window.welcome_intro_lbl.setWordWrap(True)
    window.welcome_intro_lbl.setTextFormat(Qt.RichText)
    intro_l.addWidget(window.welcome_intro_lbl)
    window.welcome_next_title_lbl = QLabel(tr("welcome.next_title"))
    window.welcome_next_title_lbl.setStyleSheet("font-weight: bold;")
    intro_l.addWidget(window.welcome_next_title_lbl)
    window.welcome_next_steps_lbl = QLabel(tr("welcome.next_steps"))
    window.welcome_next_steps_lbl.setWordWrap(True)
    window.welcome_next_steps_lbl.setTextFormat(Qt.RichText)
    intro_l.addWidget(window.welcome_next_steps_lbl)
    root.addWidget(window.welcome_intro_grp)

    window.welcome_settings_grp = QGroupBox(tr("welcome.settings_group"))
    form = QFormLayout(window.welcome_settings_grp)
    form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

    window.welcome_lang_cb = QComboBox()
    window.welcome_lang_cb.addItems(available_languages() or ["de", "en"])
    lang_index = window.welcome_lang_cb.findText(get_language())
    if lang_index >= 0:
        window.welcome_lang_cb.setCurrentIndex(lang_index)

    window.welcome_theme_cb = QComboBox()
    window.welcome_theme_cb.addItems(theme_names)
    theme_index = window.welcome_theme_cb.findText(current_theme())
    if theme_index >= 0:
        window.welcome_theme_cb.setCurrentIndex(theme_index)

    window.welcome_lang_lbl = QLabel(tr("welcome.lang_label"))
    window.welcome_theme_lbl = QLabel(tr("welcome.theme_label"))
    window.welcome_update_check_lbl = QLabel(tr("settings.update_check_label"))
    window.welcome_update_check_cb = QCheckBox(tr("settings.update_check_enabled"))
    window.welcome_update_check_cb.setChecked(bool(window._cfg.get("settings.update_check_enabled", True)))
    form.addRow(window.welcome_lang_lbl, window.welcome_lang_cb)
    form.addRow(window.welcome_theme_lbl, window.welcome_theme_cb)
    form.addRow(window.welcome_update_check_lbl, window.welcome_update_check_cb)
    root.addWidget(window.welcome_settings_grp)

    window.welcome_tools_lbl = QLabel("")
    window.welcome_tools_lbl.setWordWrap(True)
    window.welcome_tools_lbl.setTextFormat(Qt.RichText)
    root.addWidget(window.welcome_tools_lbl)

    btn_row = QHBoxLayout()
    window.welcome_help_btn = QPushButton(tr("welcome.help"))
    window.welcome_help_btn.clicked.connect(window._open_github_wiki)
    btn_row.addWidget(window.welcome_help_btn)
    window.welcome_install_tools_btn = QPushButton(tr("welcome.install_ids_tools"))
    window.welcome_install_tools_btn.clicked.connect(window._open_ids_toolchain_installer)
    btn_row.addWidget(window.welcome_install_tools_btn)
    btn_row.addStretch(1)
    window.welcome_continue_btn = QPushButton(tr("welcome.continue_mod_manager"))
    window.welcome_continue_btn.clicked.connect(window._welcome_continue)
    btn_row.addWidget(window.welcome_continue_btn)
    root.addLayout(btn_row)
    root.addStretch(1)
    return page
