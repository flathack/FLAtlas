"""Linkes Panel: Spielpfad-Eingabe + Systemliste."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from .config import Config
from .parser import FLParser, find_universe_ini, find_all_systems
from .i18n import tr


class SystemBrowser(QWidget):
    """Panel zum Auswählen und Laden von System-INI-Dateien."""

    system_load_requested = Signal(str)
    path_updated = Signal(str)
    trade_routes_requested = Signal()

    def __init__(self, config: Config, parser: FLParser):
        super().__init__()
        self._config = config
        self._parser = parser
        self._build_ui()
        saved = config.get("game_path", "")
        if saved:
            self.path_edit.setText(saved)
        self._scan()

    # ------------------------------------------------------------------
    #  UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        title = QLabel("⭐  System-Browser")
        title.setStyleSheet(
            "font-weight:bold; font-size:11pt; color:#99aaff; padding:4px 0;"
        )
        layout.addWidget(title)

        # --- Pfad-Gruppe --------------------------------------------------
        grp = QGroupBox("Freelancer-Verzeichnis")
        gl = QVBoxLayout(grp)
        gl.setSpacing(4)

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(3)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("/pfad/zu/Freelancer HD Edition/")
        self.path_edit.setToolTip(
            "Basis-Verzeichnis des Spiels.\n"
            "Erwartet: <pfad>/DATA/UNIVERSE/universe.ini"
        )
        self.path_edit.returnPressed.connect(self._save_and_scan)
        rl.addWidget(self.path_edit)

        browse_btn = QPushButton("📁")
        browse_btn.setFixedWidth(32)
        browse_btn.setToolTip("Verzeichnis auswählen")
        browse_btn.clicked.connect(self._browse)
        rl.addWidget(browse_btn)
        gl.addWidget(row)

        scan_btn = QPushButton("🔍  Systeme einlesen")
        scan_btn.clicked.connect(self._save_and_scan)
        gl.addWidget(scan_btn)

        self.trade_btn = QPushButton(tr("action.trade_routes"))
        self.trade_btn.setToolTip(tr("tip.trade_routes_open"))
        self.trade_btn.clicked.connect(self.trade_routes_requested.emit)
        gl.addWidget(self.trade_btn)
        layout.addWidget(grp)

        # --- Systemliste --------------------------------------------------
        list_lbl = QLabel("Systeme  (Klick zum Laden):")
        list_lbl.setStyleSheet("color:#aab; font-size:9pt;")
        layout.addWidget(list_lbl)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setToolTip("System anklicken um es zu laden")
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget, stretch=1)

        self.status_lbl = QLabel("")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet("color:#888; font-size:9pt; padding:2px;")
        layout.addWidget(self.status_lbl)

    # ------------------------------------------------------------------
    #  Aktionen
    # ------------------------------------------------------------------
    def _browse(self):
        start = self.path_edit.text() or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, "Freelancer-Verzeichnis wählen", start)
        if path:
            self.path_edit.setText(path)
            self._save_and_scan()

    def _save_and_scan(self):
        path = self.path_edit.text().strip()
        if path:
            self._config.set("game_path", path)
        else:
            self._config.set("game_path", "")
        self.path_updated.emit(path)
        self._scan()

    def _scan(self):
        path = self.path_edit.text().strip()
        mode = str(self._config.get("storage.mode", "single") or "single").strip().lower()
        fallback = str(self._config.get("storage.vanilla_path", "") or "").strip() if mode == "overlay" else ""
        if not path:
            self.status_lbl.setText("⚠  Kein Pfad angegeben.")
            self.list_widget.clear()
            if hasattr(self, "trade_btn"):
                self.trade_btn.setEnabled(False)
            return

        self.status_lbl.setText("Suche …")
        QApplication.processEvents()

        uni_ini = find_universe_ini(path) or (find_universe_ini(fallback) if fallback else None)
        if not uni_ini:
            self.status_lbl.setText(
                "⚠  universe.ini nicht gefunden.\n"
                "Erwartet: <pfad>/DATA/UNIVERSE/universe.ini"
            )
            self.list_widget.clear()
            if hasattr(self, "trade_btn"):
                self.trade_btn.setEnabled(False)
            return

        systems = find_all_systems(path, self._parser, fallback_root=fallback or None)
        self.list_widget.clear()

        for s in systems:
            item = QListWidgetItem(s["nickname"])
            item.setData(Qt.UserRole, s["path"])
            item.setToolTip(s["path"])
            self.list_widget.addItem(item)

        if systems:
            self.status_lbl.setText(f"✔  {len(systems)} Systeme\n{uni_ini}")
            if hasattr(self, "trade_btn"):
                self.trade_btn.setEnabled(True)
        else:
            self.status_lbl.setText(
                "⚠  universe.ini gefunden,\naber keine gültigen [system]-Pfade."
            )
            if hasattr(self, "trade_btn"):
                self.trade_btn.setEnabled(False)

    def _on_item_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.UserRole)
        if path:
            self.system_load_requested.emit(path)

    # ------------------------------------------------------------------
    #  Öffentliche API
    # ------------------------------------------------------------------
    def highlight_current(self, filepath: str):
        """Hebt das aktuell geladene System in der Liste hervor."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            is_cur = item.data(Qt.UserRole) == filepath
            item.setBackground(QColor(40, 60, 100) if is_cur else QColor(0, 0, 0, 0))
            f = item.font()
            f.setBold(is_cur)
            item.setFont(f)

    def retranslate_ui(self):
        if hasattr(self, "trade_btn"):
            self.trade_btn.setText(tr("action.trade_routes"))
            self.trade_btn.setToolTip(tr("tip.trade_routes_open"))

    def set_game_path(self, path: str, scan: bool = True):
        self.path_edit.setText(path.strip())
        if scan:
            self._save_and_scan()
