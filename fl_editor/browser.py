"""Left panel: system list and quick navigation actions."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from .config import Config
from .parser import FLParser, find_universe_ini, find_all_systems
from .i18n import tr, get_language


class SystemBrowser(QWidget):
    """Panel to load system INI files from the active Mod-Manager context."""

    system_load_requested = Signal(str)
    trade_routes_requested = Signal()
    name_editor_requested = Signal()

    def __init__(self, config: Config, parser: FLParser):
        super().__init__()
        self._config = config
        self._parser = parser
        self._game_path = str(config.get("game_path", "") or "").strip()
        self._system_name_mode = str(config.get("view.system_name_mode", "ingame") or "ingame").strip().lower()
        if self._system_name_mode not in ("ingame", "nickname"):
            self._system_name_mode = "ingame"
        self._system_name_map: dict[str, str] = {}
        self._build_ui()
        self._scan()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self.title_lbl = QLabel("⭐  " + ("System Browser" if get_language() == "en" else "System-Browser"))
        self.title_lbl.setStyleSheet("font-weight:bold; font-size:11pt; color:#99aaff; padding:4px 0;")
        layout.addWidget(self.title_lbl)

        grp = QGroupBox(tr("browser.quick_group"))
        gl = QVBoxLayout(grp)
        gl.setSpacing(4)

        self.scan_btn = QPushButton(tr("browser.refresh_systems"))
        self.scan_btn.clicked.connect(self._scan)
        gl.addWidget(self.scan_btn)

        self.trade_btn = QPushButton(tr("action.trade_routes"))
        self.trade_btn.setToolTip(tr("tip.trade_routes_open"))
        self.trade_btn.clicked.connect(self.trade_routes_requested.emit)
        gl.addWidget(self.trade_btn)

        self.name_editor_btn = QPushButton(tr("action.name_editor"))
        self.name_editor_btn.setToolTip(tr("tip.name_editor_open"))
        self.name_editor_btn.clicked.connect(self.name_editor_requested.emit)
        gl.addWidget(self.name_editor_btn)
        layout.addWidget(grp)

        self.list_lbl = QLabel(tr("browser.system_list"))
        self.list_lbl.setStyleSheet("color:#aab; font-size:9pt;")
        layout.addWidget(self.list_lbl)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setToolTip(tr("browser.system_list_tip"))
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget, stretch=1)

        self.status_lbl = QLabel("")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet("color:#888; font-size:9pt; padding:2px;")
        layout.addWidget(self.status_lbl)

    def _scan(self):
        path = str(self._game_path or "").strip()
        mode = str(self._config.get("storage.mode", "single") or "single").strip().lower()
        fallback = str(self._config.get("storage.vanilla_path", "") or "").strip() if mode == "overlay" else ""
        if not path:
            self.status_lbl.setText(tr("browser.status.no_context"))
            self.list_widget.clear()
            if hasattr(self, "trade_btn"):
                self.trade_btn.setEnabled(False)
            if hasattr(self, "name_editor_btn"):
                self.name_editor_btn.setEnabled(False)
            return

        self.status_lbl.setText(tr("browser.status.searching"))
        QApplication.processEvents()

        uni_ini = find_universe_ini(path) or (find_universe_ini(fallback) if fallback else None)
        if not uni_ini:
            self.status_lbl.setText(tr("browser.status.no_universe"))
            self.list_widget.clear()
            if hasattr(self, "trade_btn"):
                self.trade_btn.setEnabled(False)
            if hasattr(self, "name_editor_btn"):
                self.name_editor_btn.setEnabled(False)
            return

        systems = find_all_systems(path, self._parser, fallback_root=fallback or None)
        self.list_widget.clear()

        for s in systems:
            nick = str(s.get("nickname", "")).strip()
            label = nick
            if self._system_name_mode == "ingame":
                label = self._system_name_map.get(nick.upper(), "") or nick
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, {"path": s["path"], "nickname": nick})
            item.setToolTip(s["path"])
            self.list_widget.addItem(item)

        if systems:
            self.status_lbl.setText(tr("browser.status.systems_found").format(count=len(systems), uni=uni_ini))
            if hasattr(self, "trade_btn"):
                self.trade_btn.setEnabled(True)
            if hasattr(self, "name_editor_btn"):
                self.name_editor_btn.setEnabled(True)
        else:
            self.status_lbl.setText(tr("browser.status.no_systems"))
            if hasattr(self, "trade_btn"):
                self.trade_btn.setEnabled(False)
            if hasattr(self, "name_editor_btn"):
                self.name_editor_btn.setEnabled(False)

    def _on_item_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole)
        path = data.get("path") if isinstance(data, dict) else data
        if path:
            self.system_load_requested.emit(path)

    def highlight_current(self, filepath: str):
        """Highlight currently loaded system in list."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            data = item.data(Qt.UserRole)
            path = data.get("path") if isinstance(data, dict) else data
            is_cur = path == filepath
            item.setBackground(QColor(40, 60, 100) if is_cur else QColor(0, 0, 0, 0))
            f = item.font()
            f.setBold(is_cur)
            item.setFont(f)

    def retranslate_ui(self):
        if hasattr(self, "title_lbl"):
            self.title_lbl.setText("⭐  " + ("System Browser" if get_language() == "en" else "System-Browser"))
        if hasattr(self, "scan_btn"):
            self.scan_btn.setText(tr("browser.refresh_systems"))
        if hasattr(self, "trade_btn"):
            self.trade_btn.setText(tr("action.trade_routes"))
            self.trade_btn.setToolTip(tr("tip.trade_routes_open"))
        if hasattr(self, "name_editor_btn"):
            self.name_editor_btn.setText(tr("action.name_editor"))
            self.name_editor_btn.setToolTip(tr("tip.name_editor_open"))
        if hasattr(self, "list_lbl"):
            self.list_lbl.setText(tr("browser.system_list"))
        if hasattr(self, "list_widget"):
            self.list_widget.setToolTip(tr("browser.system_list_tip"))

    def set_game_path(self, path: str, scan: bool = True):
        self._game_path = str(path or "").strip()
        self._config.set("game_path", self._game_path)
        if scan:
            self._scan()

    def set_system_name_mode(self, mode: str, scan: bool = True):
        m = str(mode or "").strip().lower()
        if m not in ("ingame", "nickname"):
            m = "ingame"
        self._system_name_mode = m
        if scan:
            self._scan()

    def set_system_name_map(self, name_map: dict[str, str], scan: bool = True):
        self._system_name_map = {str(k).upper(): str(v) for k, v in dict(name_map or {}).items()}
        if scan:
            self._scan()
