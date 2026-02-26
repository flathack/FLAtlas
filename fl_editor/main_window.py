"""Hauptfenster des Freelancer System Editors.

Orchestriert alle Untermodule (Browser, 2D/3D-Ansicht, Dialoge) und
verwaltet den Editor-Zustand (Laden, Speichern, Auswahl, Bearbeitung).
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QKeySequence,
    QPen,
    QShortcut,
    QTransform,
)

from .config import Config
from .parser import FLParser, find_universe_ini, find_all_systems
from .path_utils import ci_find, ci_resolve, parse_position, format_position
from .models import ZoneItem, SolarObject, UniverseSystem
from .browser import SystemBrowser
from .view_2d import SystemView
from .view_3d import System3DView
from .qt3d_compat import QT3D_AVAILABLE
from .dialogs import (
    ConnectionDialog,
    GateInfoDialog,
    MeshPreviewDialog,
    ObjectCreationDialog,
    SolarCreationDialog,
    SystemCreationDialog,
    ZoneCreationDialog,
)


# ══════════════════════════════════════════════════════════════════════
#  Stylesheet  (ausgelagert, damit __init__ übersichtlich bleibt)
# ══════════════════════════════════════════════════════════════════════
_APP_STYLESHEET = """
    * { background:#12122a; color:#dde; }
    QGroupBox { border:1px solid #334; margin-top:10px;
                padding:5px; border-radius:4px; }
    QGroupBox::title { color:#99aaff; }
    QPushButton { background:#1e1e50; border:1px solid #446;
                  padding:4px 8px; border-radius:3px; }
    QPushButton:hover    { background:#2a2a70; }
    QPushButton:disabled { color:#445; }
    QTextEdit  { background:#08080f; border:1px solid #334; }
    QLineEdit  { background:#0d0d22; border:1px solid #446;
                 padding:3px; border-radius:2px; }
    QListWidget { background:#0a0a1e; border:1px solid #334;
                  alternate-background-color:#0d0d25; }
    QListWidget::item:hover    { background:#1e2050; }
    QListWidget::item:selected { background:#2a3070; color:#fff; }
    QToolBar   { background:#0e0e28; border-bottom:1px solid #334;
                 spacing:4px; padding:2px; }
    QStatusBar { background:#0e0e28; color:#99aaff; }
    QSplitter::handle { background:#224; width:3px; }
    QCheckBox  { color:#dde; spacing:5px; }
    QCheckBox::indicator { width:14px; height:14px;
                           border:1px solid #556; border-radius:2px;
                           background:#1e1e50; }
    QCheckBox::indicator:checked { background:#5060c0; }
    QScrollBar:vertical   { background:#0a0a1e; width:10px; }
    QScrollBar::handle:vertical { background:#334; border-radius:4px; }
    QMenu { background:#16163a; color:#dde; border:1px solid #446; }
    QMenu::item { padding:6px 24px; }
    QMenu::item:selected { background:#2a2a70; }
"""

_LEGEND_ENTRIES = [
    ("#ffd728", "☀  Stern / Sonne"),
    ("#3c82dc", "🪐  Planet"),
    ("#50d264", "🏠  Basis / Station"),
    ("#d25ad2", "⭕  Jumpgate / -hole"),
    ("#966e46", "☄  Asteroidenfeld"),
    ("#bebebe", "◉  Sonstiges"),
    ("#0000ff", "─  Jumpgate-Verbindung"),
    ("#ffff00", "─  Jumphole-Verbindung"),
    ("", ""),
    ("#dc3232", "─  Zone Death"),
    ("#9650dc", "─  Zone Nebula"),
    ("#b4823c", "─  Zone Debris"),
    ("#3cb4dc", "--  Zone Tradelane"),
    ("#50a0c8", "─  Zone Sonstiges"),
]


class MainWindow(QMainWindow):
    """Hauptfenster – verbindet Browser, Karten, Editor und Dialoge."""

    # ==================================================================
    #  Initialisierung
    # ==================================================================
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Freelancer System Editor")
        self.resize(1600, 900)

        self._cfg = Config()
        self._parser = FLParser()

        # Editor-Zustand
        self._filepath: str | None = None
        self._sections: list = []
        self._objects: list[SolarObject] = []
        self._zones: list[ZoneItem] = []
        self._selected: SolarObject | ZoneItem | None = None
        self._scale = 1.0
        self._dirty = False
        self._ed_busy = False
        self._sys_fields_busy = False

        # Pending-Aktionen
        self._pending_zone: dict | None = None
        self._pending_create: dict | None = None
        self._pending_new_object = False
        self._pending_conn: dict | None = None
        self._pending_snapshots: list = []
        self._pending_new_system: dict | None = None

        # Universum-Ansicht: Verbindungslinien & Undo
        self._uni_edges: dict = {}           # frozenset→typ
        self._uni_lines: list = []           # (frozenset, QGraphicsLineItem)
        self._uni_original_pos: dict = {}    # nickname→(scene_x, scene_y)
        self._uni_sections: list = []        # geparste universe.ini Sektionen
        self._uni_ini_path: Path | None = None  # Pfad zur universe.ini
        self._uni_selected_nick: str | None = None  # aktuell gewähltes System

        # Archetype → Modell (Cache)
        self._arch_model_map: dict[str, str] = {}
        self._arch_index_game_path = ""
        self._stars: list[str] = []

        # Zone-Link-Editor-State
        self._zone_link_section_index: int | None = None
        self._zone_link_section_name: str | None = None
        self._zone_link_file_path: Path | None = None

        self._build_ui()
        self.setStyleSheet(_APP_STYLESHEET)

        # Gespeicherten Spielpfad laden
        saved = self._cfg.get("game_path", "")
        if saved:
            self._load_universe(saved)

    # ==================================================================
    #  UI-Aufbau
    # ==================================================================
    def _build_ui(self):
        # ── Toolbar ──────────────────────────────────────────────────
        tb = self.addToolBar("Haupt")
        tb.setMovable(False)

        universe_act = QAction("🌐 Universum", self)
        universe_act.triggered.connect(self._load_universe_action)
        tb.addAction(universe_act)

        from PySide6.QtWidgets import QToolButton, QMenu
        about_btn = QToolButton()
        about_btn.setText("ℹ️ Über")
        about_btn.setPopupMode(QToolButton.InstantPopup)
        about_menu = QMenu(about_btn)
        help_act = QAction("❓ Hilfe", self)
        help_act.triggered.connect(self._show_help)
        about_menu.addAction(help_act)
        about_btn.setMenu(about_menu)
        tb.addWidget(about_btn)

        model_act = QAction("🧊 Modell öffnen", self)
        model_act.triggered.connect(self._open_model_file)
        tb.addAction(model_act)

        tb.addSeparator()

        self.move_cb = QCheckBox("Move")
        self.move_cb.setToolTip("Objekte frei verschieben (Linke Maustaste)")
        self.move_cb.toggled.connect(self._toggle_move)
        tb.addWidget(self.move_cb)

        self.zone_cb = QCheckBox("Zonen")
        self.zone_cb.setChecked(True)
        self.zone_cb.setToolTip("Zonen ein-/ausblenden")
        self.zone_cb.toggled.connect(self._toggle_zones)
        tb.addWidget(self.zone_cb)

        self.view3d_switch = QCheckBox("3D")
        self.view3d_switch.setToolTip("Zwischen 2D- und 3D-Ansicht wechseln")
        self.view3d_switch.toggled.connect(self._toggle_3d_view)
        tb.addWidget(self.view3d_switch)

        self.new_system_btn = QPushButton("🌟 Neues System")
        self.new_system_btn.setToolTip("Neues Sternensystem auf der Universumskarte platzieren")
        self.new_system_btn.setStyleSheet(
            "QPushButton { background:#1a4020; border:1px solid #3a8040;"
            " color:#80ff80; padding:4px 10px; font-weight:bold; }"
            " QPushButton:hover { background:#2a6030; }"
        )
        self.new_system_btn.clicked.connect(self._start_new_system)
        self._new_system_action = tb.addWidget(self.new_system_btn)
        self._new_system_action.setVisible(False)

        self.uni_save_btn = QPushButton("💾 Speichern")
        self.uni_save_btn.setToolTip("Universe-Positionen in universe.ini speichern")
        self.uni_save_btn.setStyleSheet(
            "QPushButton { background:#1a3a1a; border:1px solid #2a5a2a;"
            " color:#80ff80; padding:4px 10px; font-weight:bold; }"
            " QPushButton:hover { background:#245a24; }"
        )
        self.uni_save_btn.clicked.connect(lambda: self._write_to_file(False))
        self._uni_save_action = tb.addWidget(self.uni_save_btn)
        self._uni_save_action.setVisible(False)

        self.uni_undo_btn = QPushButton("↩ Undo")
        self.uni_undo_btn.setToolTip("Alle Verschiebungen rückgängig machen")
        self.uni_undo_btn.setStyleSheet(
            "QPushButton { background:#3a1a1a; border:1px solid #5a2a2a;"
            " color:#ff8080; padding:4px 10px; font-weight:bold; }"
            " QPushButton:hover { background:#5a2424; }"
        )
        self.uni_undo_btn.clicked.connect(self._undo_universe_moves)
        self._uni_undo_action = tb.addWidget(self.uni_undo_btn)
        self._uni_undo_action.setVisible(False)

        tb.addSeparator()
        self.mode_lbl = QLabel("")
        self.mode_lbl.setStyleSheet("color:#f0c040; font-weight:bold; padding:0 8px;")
        tb.addWidget(self.mode_lbl)

        QShortcut(QKeySequence("Escape"), self).activated.connect(self._cancel_pending_actions)

        # ── Splitter: Links | Mitte | Rechts ────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        self._build_left_panel(splitter)
        self._build_center_panel(splitter)
        self._build_right_panel(splitter)
        splitter.setSizes([220, 1060, 320])

        # ── Zentralwidget mit Legende ────────────────────────────────
        central = QWidget()
        cl = QVBoxLayout(central)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addWidget(splitter)
        self._build_legend(cl)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Bereit — Pfad eingeben oder INI öffnen")

    # ------------------------------------------------------------------
    #  Linkes Panel
    # ------------------------------------------------------------------
    def _build_left_panel(self, splitter: QSplitter):
        self.left_stack = QStackedWidget()

        # Browser
        self.browser = SystemBrowser(self._cfg, self._parser)
        self.browser.system_load_requested.connect(self._load_from_browser)
        self.browser.path_updated.connect(lambda p: self._populate_quick_editor_options(p))
        self.left_stack.addWidget(self.browser)

        # INI-Editor-Panel
        self.left_ini_panel = QWidget()
        lipl = QVBoxLayout(self.left_ini_panel)
        lipl.setContentsMargins(4, 4, 4, 4)
        lipl.setSpacing(4)

        back_btn = QPushButton("↩  Zurück zur Systemliste")
        back_btn.clicked.connect(lambda: self.left_stack.setCurrentWidget(self.browser))
        lipl.addWidget(back_btn)

        g = QGroupBox("Objekt-Editor")
        gl = QVBoxLayout(g)
        self.editor = QTextEdit()
        self.editor.setVisible(False)
        gl.addWidget(self.editor)

        # Zone-Link-Editor
        self.zone_link_lbl = QLabel("Verknüpfte Sektion (Nebula/Asteroids):")
        self.zone_link_lbl.setVisible(False)
        gl.addWidget(self.zone_link_lbl)
        self.zone_link_editor = QTextEdit()
        self.zone_link_editor.setVisible(False)
        gl.addWidget(self.zone_link_editor)
        self.zone_file_lbl = QLabel("Zonen-Datei (verlinkte INI):")
        self.zone_file_lbl.setVisible(False)
        gl.addWidget(self.zone_file_lbl)
        self.zone_file_editor = QTextEdit()
        self.zone_file_editor.setVisible(False)
        gl.addWidget(self.zone_file_editor)

        lipl.addWidget(g)
        lipl.addStretch()

        # Buttons
        btn_row = QWidget()
        btn_layout = QVBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(4)

        self.edit_obj_btn = QPushButton("✏️ Objekt bearbeiten")
        self.edit_obj_btn.setEnabled(False)
        self.edit_obj_btn.clicked.connect(self._start_object_edit)
        btn_layout.addWidget(self.edit_obj_btn)

        self.apply_btn = QPushButton("✔  Objekt-Änderungen übernehmen")
        self.apply_btn.setToolTip("Texteditor → Objektdaten (nur im Speicher).")
        self.apply_btn.clicked.connect(self._apply)
        self.apply_btn.setEnabled(False)
        self.apply_btn.setVisible(False)
        btn_layout.addWidget(self.apply_btn)

        self.delete_btn = QPushButton("🗑  Objekt löschen")
        self.delete_btn.setToolTip("Das aktuell ausgewählte Objekt entfernen.")
        self.delete_btn.clicked.connect(self._delete_object)
        self.delete_btn.setEnabled(False)
        btn_layout.addWidget(self.delete_btn)

        self.preview3d_btn = QPushButton("🧊  3D Preview")
        self.preview3d_btn.setToolTip("Zeigt das Modell des gewählten Objekts als 3D-Vorschau an")
        self.preview3d_btn.clicked.connect(self._show_selected_3d_preview)
        self.preview3d_btn.setEnabled(False)
        btn_layout.addWidget(self.preview3d_btn)

        lipl.addWidget(btn_row)
        self.left_stack.addWidget(self.left_ini_panel)

        # Universe-System-Editor-Panel
        self.left_uni_panel = QWidget()
        upl = QVBoxLayout(self.left_uni_panel)
        upl.setContentsMargins(4, 4, 4, 4)
        upl.setSpacing(4)

        uni_back_btn = QPushButton("↩  Zurück zur Systemliste")
        uni_back_btn.clicked.connect(lambda: self.left_stack.setCurrentWidget(self.browser))
        upl.addWidget(uni_back_btn)

        self.uni_sys_lbl = QLabel("🌐 System")
        self.uni_sys_lbl.setStyleSheet("color:#99aaff; font-weight:bold; font-size:13px;")
        upl.addWidget(self.uni_sys_lbl)

        ug = QGroupBox("universe.ini Eintrag")
        ugl = QVBoxLayout(ug)
        self.uni_editor = QTextEdit()
        self.uni_editor.setMinimumHeight(180)
        ugl.addWidget(self.uni_editor)
        upl.addWidget(ug)

        self.uni_apply_btn = QPushButton("✔  Änderungen speichern")
        self.uni_apply_btn.setStyleSheet(
            "QPushButton { background:#1a3a1a; border:1px solid #2a5a2a;"
            " color:#80ff80; padding:6px 10px; font-weight:bold; }"
            " QPushButton:hover { background:#245a24; }"
        )
        self.uni_apply_btn.clicked.connect(self._apply_uni_system_edit)
        upl.addWidget(self.uni_apply_btn)

        upl.addStretch()
        self.left_stack.addWidget(self.left_uni_panel)

        splitter.addWidget(self.left_stack)

    # ------------------------------------------------------------------
    #  Mittel-Panel  (2D/3D)
    # ------------------------------------------------------------------
    def _build_center_panel(self, splitter: QSplitter):
        self.view = SystemView()
        self.view.object_selected.connect(self._select)
        self.view.zone_clicked.connect(self._select_zone)
        self.view.background_clicked.connect(self._on_background_click)
        self.view.system_double_clicked.connect(self._load_from_browser)

        self.view3d = System3DView()
        self.view3d.object_selected.connect(self._on_3d_object_selected)
        self.view3d.object_height_delta.connect(self._on_3d_height_delta)
        self.view3d.object_axis_delta.connect(self._on_3d_axis_delta)

        self.center_stack = QStackedWidget()
        self.center_stack.addWidget(self.view)
        self.center_stack.addWidget(self.view3d)
        self.center_stack.setCurrentWidget(self.view)
        splitter.addWidget(self.center_stack)

    # ------------------------------------------------------------------
    #  Rechtes Panel  (Schnell-Editor, Erstellung, System-Info)
    # ------------------------------------------------------------------
    def _build_right_panel(self, splitter: QSplitter):
        right = QWidget()
        self.right_panel = right
        rl = QVBoxLayout(right)
        rl.setContentsMargins(6, 6, 6, 6)

        self.name_lbl = QLabel("Kein Objekt ausgewählt")
        self.name_lbl.setStyleSheet("font-weight:bold; font-size:12pt;")
        rl.addWidget(self.name_lbl)

        # Objekt/Zonen-Dropdown
        self._build_obj_combo(rl)
        # Quick-Editor (versteckt)
        self._build_quick_editor(rl)
        # Erstellen-Buttons
        self._build_creation_group(rl)
        # System-Metadaten
        self._build_system_info_group(rl)

        self.info_lbl = QLabel("Keine Datei geladen.")
        self.info_lbl.setWordWrap(True)
        rl.addWidget(self.info_lbl)

        self.write_btn = QPushButton("💾  Änderungen in Datei schreiben")
        self.write_btn.setToolTip(
            "Alle Änderungen via .tmp-Datei in die Original-INI schreiben\n"
            "und Ansicht anschließend neu laden."
        )
        self.write_btn.setStyleSheet(
            "QPushButton{background:#1a3a1a;border:1px solid #2a5a2a;}"
            "QPushButton:hover{background:#245a24;}"
            "QPushButton:disabled{color:#445;background:#111;border-color:#333;}"
        )
        self.write_btn.clicked.connect(lambda checked=None: self._write_to_file(True))
        self.write_btn.setEnabled(False)
        rl.addWidget(self.write_btn)
        rl.addStretch()
        splitter.addWidget(right)

    def _build_obj_combo(self, layout: QVBoxLayout):
        obj_row = QWidget()
        obj_row_l = QHBoxLayout(obj_row)
        obj_row_l.setContentsMargins(0, 0, 0, 0)
        obj_row_l.setSpacing(4)
        self.obj_combo = QComboBox()
        self.obj_combo.setToolTip("Alle Objekte und Zonen – wählen Sie aus, um zu bearbeiten")
        self.obj_combo.currentIndexChanged.connect(self._on_obj_combo_changed)
        obj_row_l.addWidget(self.obj_combo, 1)
        self.obj_jump_btn = QPushButton("Springen")
        self.obj_jump_btn.setToolTip("Ansicht auf ausgewähltes Objekt/Zone zentrieren")
        self.obj_jump_btn.clicked.connect(self._jump_to_selected_from_combo)
        obj_row_l.addWidget(self.obj_jump_btn)
        layout.addWidget(obj_row)

    def _build_quick_editor(self, layout: QVBoxLayout):
        quick = QGroupBox("Schnell-Editor")
        ql = QVBoxLayout(quick)
        ql.setSpacing(4)

        def _combo_row(label: str, cb_attr: str, slot=None):
            row = QWidget()
            rowl = QHBoxLayout(row)
            rowl.setContentsMargins(0, 0, 0, 0)
            rowl.addWidget(QLabel(label))
            cb = QComboBox()
            cb.setEditable(True)
            if slot:
                cb.currentTextChanged.connect(slot)
            setattr(self, cb_attr, cb)
            rowl.addWidget(cb)
            ql.addWidget(row)

        _combo_row("Archetype:", "arch_cb",
                   lambda t: self._update_editor_field("archetype", t))
        _combo_row("Loadout:", "loadout_cb",
                   lambda t: self._update_editor_field("loadout", t))
        _combo_row("Faction:", "faction_cb", self._on_faction_changed)

        self.rep_edit = QLineEdit()
        self.rep_edit.setVisible(False)
        self.rep_edit.editingFinished.connect(self._on_rep_changed)

        # Suchfeld (intern, nicht sichtbar)
        self.search_edit = QLineEdit()
        self.search_edit.setVisible(False)

        quick.setVisible(False)
        layout.addWidget(quick)

    def _build_creation_group(self, layout: QVBoxLayout):
        create_grp = QGroupBox("Erstellung")
        cgl = QVBoxLayout(create_grp)
        cgl.setSpacing(4)

        self.new_obj_btn = QPushButton("Objekt")
        self.new_obj_btn.clicked.connect(self._create_new_object)
        cgl.addWidget(self.new_obj_btn)

        self.create_zone_btn = QPushButton("Zone")
        self.create_zone_btn.clicked.connect(self._start_zone_creation)
        cgl.addWidget(self.create_zone_btn)

        self.create_conn_btn = QPushButton("Jump")
        self.create_conn_btn.clicked.connect(self._start_connection_dialog)
        cgl.addWidget(self.create_conn_btn)

        self.save_conn_btn = QPushButton("💾 Verbindungen speichern")
        self.save_conn_btn.setVisible(False)
        self.save_conn_btn.clicked.connect(self._save_pending_connections)
        cgl.addWidget(self.save_conn_btn)

        self.sun_btn = QPushButton("Sonne")
        self.sun_btn.clicked.connect(self._create_sun)
        cgl.addWidget(self.sun_btn)

        self.planet_btn = QPushButton("Planet")
        self.planet_btn.clicked.connect(self._create_planet)
        cgl.addWidget(self.planet_btn)

        layout.addWidget(create_grp)

    def _build_system_info_group(self, layout: QVBoxLayout):
        sys_grp = QGroupBox("Aktuelles System")
        sgl = QVBoxLayout(sys_grp)
        sgl.setSpacing(4)

        def _row_widget(label: str, widget: QWidget) -> QWidget:
            w = QWidget()
            wl = QHBoxLayout(w)
            wl.setContentsMargins(0, 0, 0, 0)
            wl.addWidget(QLabel(label))
            wl.addWidget(widget)
            return w

        def _music_cb(attr: str, key: str) -> QComboBox:
            cb = QComboBox()
            cb.setEditable(True)
            cb.currentTextChanged.connect(lambda t: self._on_music_field_changed(key, t))
            setattr(self, attr, cb)
            return cb

        sgl.addWidget(_row_widget("Music Space:", _music_cb("music_space_cb", "space")))
        sgl.addWidget(_row_widget("Music Danger:", _music_cb("music_danger_cb", "danger")))
        sgl.addWidget(_row_widget("Music Battle:", _music_cb("music_battle_cb", "battle")))

        # Space Color
        self.space_color_btn = QPushButton("Farbe wählen")
        self.space_color_btn.clicked.connect(self._pick_space_color)
        self.space_color_lbl = QLabel("0, 0, 0")
        space_color_row = QWidget()
        space_color_l = QHBoxLayout(space_color_row)
        space_color_l.setContentsMargins(0, 0, 0, 0)
        space_color_l.addWidget(self.space_color_btn)
        space_color_l.addWidget(self.space_color_lbl)
        sgl.addWidget(_row_widget("Space Color:", space_color_row))

        self.local_faction_cb = QComboBox()
        self.local_faction_cb.setEditable(True)
        self.local_faction_cb.currentTextChanged.connect(
            lambda t: self._on_systeminfo_field_changed("local_faction", t)
        )
        sgl.addWidget(_row_widget("Local Faction:", self.local_faction_cb))

        # Ambient Color
        self.ambient_color_btn = QPushButton("Farbe wählen")
        self.ambient_color_btn.clicked.connect(self._pick_ambient_color)
        self.ambient_color_lbl = QLabel("0, 0, 0")
        ambient_color_row = QWidget()
        ambient_color_l = QHBoxLayout(ambient_color_row)
        ambient_color_l.setContentsMargins(0, 0, 0, 0)
        ambient_color_l.addWidget(self.ambient_color_btn)
        ambient_color_l.addWidget(self.ambient_color_lbl)
        sgl.addWidget(_row_widget("Ambient Color:", ambient_color_row))

        self.dust_cb = QComboBox()
        self.dust_cb.setEditable(True)
        self.dust_cb.currentTextChanged.connect(lambda t: self._on_system_field_changed("dust"))
        sgl.addWidget(_row_widget("Dust:", self.dust_cb))

        def _bg_cb(attr: str, key: str) -> QComboBox:
            cb = QComboBox()
            cb.setEditable(True)
            cb.currentTextChanged.connect(lambda t: self._on_background_field_changed(key, t))
            setattr(self, attr, cb)
            return cb

        sgl.addWidget(_row_widget("Background Basic:", _bg_cb("bg_basic_cb", "basic_stars")))
        sgl.addWidget(_row_widget("Background Complex:", _bg_cb("bg_complex_cb", "complex_stars")))
        sgl.addWidget(_row_widget("Background Nebulae:", _bg_cb("bg_nebulae_cb", "nebulae")))

        layout.addWidget(sys_grp)

    def _build_legend(self, layout: QVBoxLayout):
        self.legend_box = QGroupBox("Legende")
        ll = QHBoxLayout(self.legend_box)
        ll.setSpacing(8)
        for col, txt in _LEGEND_ENTRIES:
            if not col:
                ll.addSpacing(12)
                continue
            lbl = QLabel(f'<span style="color:{col}">■</span> {txt}')
            lbl.setTextFormat(Qt.RichText)
            lbl.setStyleSheet("font-size:8pt;")
            ll.addWidget(lbl)
        layout.addWidget(self.legend_box)
        self.legend_box.setMaximumHeight(self.legend_box.sizeHint().height())

    # ==================================================================
    #  Placement-Modus
    # ==================================================================
    def _set_placement_mode(self, active: bool, text: str = ""):
        if active:
            self.view.setCursor(Qt.CrossCursor)
            self.view.setStyleSheet("QGraphicsView { border: 2px solid #f0c040; }")
            self.mode_lbl.setText(f"⚑ {text}  (ESC zum Abbrechen)")
        else:
            self.view.unsetCursor()
            self.view.setStyleSheet("")
            self.mode_lbl.setText("")

    def _cancel_pending_actions(self):
        had_any = bool(
            self._pending_zone
            or self._pending_create
            or self._pending_new_object
            or self._pending_conn
            or self._pending_new_system
        )
        if not had_any:
            return
        self._pending_zone = None
        self._pending_create = None
        self._pending_new_object = False
        self._pending_conn = None
        self._pending_new_system = None
        if self._pending_snapshots:
            self._pending_snapshots.clear()
            self.save_conn_btn.setVisible(False)
            self.create_conn_btn.setEnabled(True)
        self._set_placement_mode(False)
        self.statusBar().showMessage("Platzierung abgebrochen")

    # ==================================================================
    #  3D/2D Umschaltung
    # ==================================================================
    def _toggle_3d_view(self, enabled: bool):
        if enabled and not self._filepath:
            self.view3d_switch.blockSignals(True)
            self.view3d_switch.setChecked(False)
            self.view3d_switch.blockSignals(False)
            self.center_stack.setCurrentWidget(self.view)
            self.statusBar().showMessage("3D ist in der Universumsansicht deaktiviert")
            return
        if enabled:
            self.center_stack.setCurrentWidget(self.view3d)
            self._refresh_3d_scene()
            self.view3d.set_selected(self._selected)
            if self._selected is not None:
                self.view3d.center_on_item(self._selected)
            self.statusBar().showMessage(
                "3D-Ansicht aktiv — Links ziehen: Orbit, Rechts ziehen: Pan, "
                "Mausrad: Zoom, Ctrl+Mausrad: Höhe"
            )
        else:
            self.center_stack.setCurrentWidget(self.view)
            self.statusBar().showMessage("2D-Ansicht aktiv")

    def _on_3d_object_selected(self, obj):
        if isinstance(obj, ZoneItem):
            self._select_zone(obj)
        else:
            self._select(obj)

    def _on_3d_height_delta(self, obj, delta_world: float):
        if obj is None or isinstance(obj, ZoneItem):
            return
        fx, fy, fz = parse_position(obj.data.get("pos", "0,0,0"))
        fy += delta_world
        new_pos = format_position(fx, fy, fz)
        obj.data["_entries"] = [
            (k, new_pos if k.lower() == "pos" else v) for k, v in obj.data.get("_entries", [])
        ]
        obj.data["pos"] = new_pos
        self.view3d.update_object_position(obj, self._scale)
        if self._selected is obj:
            self.editor.setPlainText(obj.raw_text())
        self._set_dirty(True)

    def _on_3d_axis_delta(self, obj, dx_world: float, dy_world: float, dz_world: float):
        if obj is None or isinstance(obj, ZoneItem):
            return
        fx, fy, fz = parse_position(obj.data.get("pos", "0,0,0"))
        fx += dx_world
        fy += dy_world
        fz += dz_world
        new_pos = format_position(fx, fy, fz)
        obj.data["_entries"] = [
            (k, new_pos if k.lower() == "pos" else v) for k, v in obj.data.get("_entries", [])
        ]
        obj.data["pos"] = new_pos
        try:
            obj.setPos(fx * self._scale, fz * self._scale)
        except Exception:
            pass
        self.view3d.update_object_position(obj, self._scale)
        if self._selected is obj:
            self.editor.setPlainText(obj.raw_text())
        self._set_dirty(True)

    def _refresh_3d_scene(self):
        if not hasattr(self, "view3d"):
            return
        zones = self._zones if self.zone_cb.isChecked() else []
        self.view3d.set_data(self._objects, zones, self._scale)
        self.view3d.set_selected(self._selected)

    # ==================================================================
    #  Laden  (Browser-Klick / Manuell / Universum)
    # ==================================================================
    def _load_from_browser(self, path: str):
        if self._filepath and path != self._filepath:
            if not self._confirm_save_if_dirty("System wechseln"):
                return
        self._filepath = path
        self._populate_quick_editor_options()
        self._load(path)
        self.browser.highlight_current(path)

    def _load_universe_action(self):
        if self._filepath and not self._confirm_save_if_dirty("zur Universumsansicht wechseln"):
            return
        path = self.browser.path_edit.text().strip()
        if path:
            self._load_universe(path)
        else:
            QMessageBox.warning(self, "Kein Pfad",
                                "Bitte zuerst Pfad eingeben und Systeme einlesen.")

    def _show_help(self):
        """HTML-Hilfeseite in einem eigenen Fenster anzeigen."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout
        from PySide6.QtWebEngineWidgets import QWebEngineView
        from PySide6.QtCore import QUrl
        help_path = Path(__file__).parent / "help.html"
        dlg = QDialog(self)
        dlg.setWindowTitle("FLEditor – Hilfe")
        dlg.resize(900, 700)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(0, 0, 0, 0)
        web = QWebEngineView()
        web.setUrl(QUrl.fromLocalFile(str(help_path)))
        lay.addWidget(web)
        dlg.exec()

    def _open_manual(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Freelancer INI öffnen", "", "INI (*.ini);;Alle (*)"
        )
        if path:
            if self._filepath and path != self._filepath:
                if not self._confirm_save_if_dirty("Datei wechseln"):
                    return
            self._filepath = path
            self._load(path)
            self.browser.highlight_current(path)

    def closeEvent(self, event):
        if self._confirm_save_if_dirty("Programm schließen"):
            event.accept()
        else:
            event.ignore()

    def _confirm_save_if_dirty(self, action_desc: str) -> bool:
        if not self._dirty or not self._filepath:
            return True
        ans = QMessageBox.question(
            self,
            "Ungespeicherte Änderungen",
            f"Es gibt ungespeicherte Änderungen.\nVor '{action_desc}' speichern?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if ans == QMessageBox.Cancel:
            return False
        if ans == QMessageBox.Save:
            self._write_to_file(reload=False)
            return not self._dirty
        return True

    # ------------------------------------------------------------------
    #  Universum laden
    # ------------------------------------------------------------------
    def _load_universe(self, game_path: str):
        self._populate_quick_editor_options(game_path)
        uni_ini = find_universe_ini(game_path)
        if not uni_ini:
            QMessageBox.warning(self, "Fehler", "universe.ini nicht gefunden.")
            return

        self._uni_ini_path = uni_ini
        self._uni_sections = self._parser.parse(str(uni_ini))

        systems = find_all_systems(game_path, self._parser)
        if not systems:
            QMessageBox.warning(self, "Fehler", "Keine Systeme in universe.ini gefunden.")
            return

        coords = []
        for s in systems:
            x, y = s.get("pos", (0.0, 0.0))
            coords.extend([abs(x), abs(y)])
        self._scale = 500.0 / (max(coords, default=1) or 1)

        # Szene zurücksetzen
        self.view._scene.clear()
        self._objects, self._zones = [], []
        self._selected = None
        self._clear_selection_ui()
        self._filepath = None
        self._hide_zone_extra_editors()
        self._set_placement_mode(False)
        if hasattr(self, "left_stack"):
            self.left_stack.setCurrentWidget(self.browser)

        # 3D deaktivieren
        self.view3d_switch.blockSignals(True)
        self.view3d_switch.setChecked(False)
        self.view3d_switch.setEnabled(False)
        self.view3d_switch.setVisible(False)
        self.view3d_switch.blockSignals(False)
        self.center_stack.setCurrentWidget(self.view)

        coord_map = {}
        for s in systems:
            x, y = s.get("pos", (0.0, 0.0))
            coord_map[s["nickname"].upper()] = (x * self._scale, y * self._scale)

        for s in systems:
            sys_item = UniverseSystem(
                s["nickname"], s["path"], s.get("pos", (0.0, 0.0)), self._scale
            )
            self.view._scene.addItem(sys_item)
            self._objects.append(sys_item)

        # Verbindungen zeichnen
        edges = self._compute_universe_edges(systems)
        self._uni_edges = edges
        self._uni_lines = []
        for key, typ in edges.items():
            a, b = list(key)
            if a not in coord_map or b not in coord_map:
                continue
            ax, ay = coord_map[a]
            bx, by = coord_map[b]
            if typ == "gate":
                col = QColor(70, 130, 255, 140)
                width = 1.8
            else:
                col = QColor(255, 220, 60, 100)
                width = 1.2
            pen = QPen(col, width)
            pen.setCosmetic(True)
            line = self.view._scene.addLine(ax, ay, bx, by, pen)
            line.setZValue(-2)
            self._uni_lines.append((key, line))

        # Original-Positionen für Undo merken
        self._uni_original_pos = {}
        for obj in self._objects:
            if hasattr(obj, "sys_path"):
                self._uni_original_pos[obj.nickname.upper()] = (obj.pos().x(), obj.pos().y())

        # Dunkler Weltraum-Hintergrund
        self.view._scene.setBackgroundBrush(QBrush(QColor(6, 6, 18)))

        self.info_lbl.setText(f"🌐 Universum: {len(systems)} Systeme")
        self.setWindowTitle("Freelancer System Editor — Universum")
        self.statusBar().showMessage(f"✔  Universum geladen: {len(systems)} Systeme")
        if hasattr(self, "right_panel"):
            self.right_panel.setVisible(False)
        if hasattr(self, "legend_box"):
            self.legend_box.setVisible(False)
        self._new_system_action.setVisible(True)
        self._uni_save_action.setVisible(True)
        self._uni_undo_action.setVisible(True)
        self._fit()
        self._refresh_3d_scene()

    def _compute_universe_edges(self, systems: list[dict]) -> dict:
        """Analysiert Verbindungen zwischen Systemen (Jump-Gates/-Holes)."""
        edges: dict = {}
        for s in systems:
            src = s["nickname"]
            try:
                secs = self._parser.parse(s["path"])
            except Exception:
                continue
            for o in self._parser.get_objects(secs):
                arch = o.get("archetype", "").lower()
                if "jumpgate" in arch or "nomad_gate" in arch:
                    typ = "gate"
                elif arch.startswith("jumphole"):
                    typ = "hole"
                else:
                    continue
                dest = None
                goto = o.get("goto", "")
                if goto:
                    dest = goto.split(",")[0].strip()
                if not dest:
                    m = re.search(r"to_([A-Za-z0-9]+)", o.get("nickname", ""), re.IGNORECASE)
                    if m:
                        dest = m.group(1)
                if not dest or dest.upper() == src.upper():
                    continue
                key = frozenset({src.upper(), dest.upper()})
                existing = edges.get(key)
                if existing is None or (existing == "hole" and typ == "gate"):
                    edges[key] = typ
        return edges

    # ------------------------------------------------------------------
    #  System laden
    # ------------------------------------------------------------------
    def _load(self, path: str, restore: QTransform | None = None):
        self._pending_conn = None
        self._pending_create = None
        self._pending_new_object = False
        self._set_placement_mode(False)
        self._filepath = path
        self._sections = self._parser.parse(path)
        raw_objs = self._parser.get_objects(self._sections)
        raw_zones = self._parser.get_zones(self._sections)

        # LightSource-Range als Fallback für leere Systeme
        light_range = 0.0
        for sec_name, entries in self._sections:
            if sec_name.lower() == "lightsource":
                for k, v in entries:
                    if k.lower() == "range":
                        try:
                            light_range = max(light_range, float(v.strip()))
                        except ValueError:
                            pass

        coords = []
        rmax = 0.0
        for d in raw_objs + raw_zones:
            pp = [float(c.strip()) for c in d.get("pos", "0,0,0").split(",")]
            if len(pp) > 0:
                coords.append(abs(pp[0]))
            if len(pp) > 2:
                coords.append(abs(pp[2]))
            fx = pp[0] if len(pp) > 0 else 0.0
            fz = pp[2] if len(pp) > 2 else (pp[1] if len(pp) > 1 else 0.0)
            dist = (fx * fx + fz * fz) ** 0.5
            sz = 0.0
            if "size" in d:
                try:
                    sz = float(d["size"].split(",")[0])
                except Exception:
                    pass
            rmax = max(rmax, dist + sz)

        # Bei leerem System: LightSource-Range als Skalierungsbasis nutzen
        if not coords and light_range > 0:
            coords.append(light_range)
            rmax = max(rmax, light_range)
        self._scale = 500.0 / (max(coords, default=1) or 1)
        boundary_radius = rmax

        self.view._scene.clear()
        self.view._scene.setBackgroundBrush(QBrush(QColor(8, 8, 15)))
        self._objects, self._zones = [], []
        self._selected = None
        self._clear_selection_ui()
        self._hide_zone_extra_editors()

        for zd in raw_zones:
            try:
                zi = ZoneItem(zd, self._scale)
                self.view._scene.addItem(zi)
                self._zones.append(zi)
            except Exception:
                pass

        move_on = self.move_cb.isChecked()
        for od in raw_objs:
            try:
                obj = SolarObject(od, self._scale)
                obj.setFlag(QGraphicsItem.ItemIsMovable, move_on)
                self.view._scene.addItem(obj)
                self._objects.append(obj)
            except Exception:
                pass

        if boundary_radius > 0:
            pen = QPen(QColor(200, 200, 200, 120))
            pen.setWidthF(0.5)
            r = boundary_radius * self._scale
            circ = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r)
            circ.setPen(pen)
            circ.setBrush(Qt.NoBrush)
            circ.setZValue(-1)
            self.view._scene.addItem(circ)

        if not self.zone_cb.isChecked():
            for z in self._zones:
                z.setVisible(False)

        name = Path(path).stem.upper()
        self.info_lbl.setText(
            f"📄 {Path(path).name}\nObjekte: {len(self._objects)}\nZonen:   {len(self._zones)}"
        )
        self._rebuild_object_combo()
        self.setWindowTitle(f"Freelancer System Editor — {name}")
        self.statusBar().showMessage(
            f"✔  {name}: {len(self._objects)} Objekte · {len(self._zones)} Zonen"
        )
        if hasattr(self, "right_panel"):
            self.right_panel.setVisible(True)
        if hasattr(self, "legend_box"):
            self.legend_box.setVisible(True)
        if hasattr(self, "left_stack"):
            self.left_stack.setCurrentWidget(self.left_ini_panel)
        self._new_system_action.setVisible(False)
        self._uni_save_action.setVisible(False)
        self._uni_undo_action.setVisible(False)
        self.view3d_switch.setEnabled(True)
        self.view3d_switch.setVisible(True)
        self._set_dirty(False)
        if restore:
            self.view.setTransform(restore)
        else:
            self._fit()
        self._refresh_3d_scene()
        self._populate_quick_editor_options()
        self._populate_system_options()
        self._refresh_system_fields()

    # ==================================================================
    #  Auswahl
    # ==================================================================
    def _select(self, obj: SolarObject):
        if hasattr(obj, "sys_path"):
            # Universum-System: Auswahl erlauben für Verschieben + Editor
            if self._selected and self._selected is not obj:
                self._selected._pos_change_cb = None
                if hasattr(self._selected, "set_highlighted"):
                    self._selected.set_highlighted(False)
            self._selected = obj
            obj._pos_change_cb = self._on_universe_system_moved
            obj.set_highlighted(True)
            self.statusBar().showMessage(f"System: {obj.nickname}")
            self._show_uni_system_editor(obj.nickname)
            return

        if self._selected:
            self._selected._pos_change_cb = None
            if hasattr(self._selected, "setPen") and hasattr(self._selected, "pen"):
                p = self._selected.pen()
                p.setColor(QColor(255, 255, 255, 70))
                p.setWidth(1)
                self._selected.setPen(p)

        self._selected = obj
        if hasattr(obj, "setPen") and hasattr(obj, "pen"):
            p = obj.pen()
            p.setColor(QColor(255, 200, 0))
            p.setWidth(2)
            obj.setPen(p)
            obj._pos_change_cb = self._on_obj_moved

        self.name_lbl.setText(f"📍 {obj.nickname}")
        self.editor.setPlainText(obj.raw_text())
        self.editor.setVisible(False)
        self.apply_btn.setVisible(False)
        self._hide_zone_extra_editors()
        self.edit_obj_btn.setEnabled(True)
        self.apply_btn.setEnabled(False)
        self.delete_btn.setEnabled(True)
        self.preview3d_btn.setEnabled(True)
        self.statusBar().showMessage(f"Ausgewählt: {obj.nickname}")
        self.view3d.set_selected(obj)
        self._sync_obj_combo_to_selection()

        # Quick-Editor füllen
        self.arch_cb.setCurrentText(obj.data.get("archetype", ""))
        self.loadout_cb.setCurrentText(obj.data.get("loadout", ""))
        rep_val = obj.data.get("reputation", "")
        if rep_val:
            parts = [p.strip() for p in rep_val.split(",")]
            self.faction_cb.setCurrentText(parts[0] if parts else "")
            self.rep_edit.setText(parts[1] if len(parts) > 1 else "")
        else:
            self.faction_cb.setCurrentText("")
            self.rep_edit.clear()

    def _select_zone(self, zone):
        if not self.zone_cb.isChecked():
            return
        self.name_lbl.setText(f"📍 {zone.nickname}")
        self.editor.setPlainText(zone.raw_text())
        self.editor.setVisible(False)
        self.apply_btn.setVisible(False)
        self._hide_zone_extra_editors()
        self.edit_obj_btn.setEnabled(True)
        self.apply_btn.setEnabled(False)
        self.delete_btn.setEnabled(True)
        self.preview3d_btn.setEnabled(False)
        self.statusBar().showMessage(f"Zone ausgewählt: {zone.nickname}")
        self._selected = zone
        self.view3d.set_selected(None)
        self._sync_obj_combo_to_selection()

    def _clear_selection_ui(self):
        """Setzt die UI-Elemente zurück wenn nichts ausgewählt ist."""
        self.apply_btn.setEnabled(False)
        self.edit_obj_btn.setEnabled(False)
        self.name_lbl.setText("Kein Objekt ausgewählt")
        self.editor.clear()
        self.editor.setVisible(False)
        self.apply_btn.setVisible(False)
        self.delete_btn.setEnabled(False)
        self.preview3d_btn.setEnabled(False)
        self.write_btn.setEnabled(False)

    # ==================================================================
    #  Echtzeit-Position (Drag)
    # ==================================================================
    def _on_obj_moved(self, obj: SolarObject):
        if self._ed_busy or obj is not self._selected:
            return
        new_pos = obj.fl_pos_str()
        updated = []
        for line in self.editor.toPlainText().splitlines():
            if line.partition("=")[0].strip().lower() == "pos":
                updated.append(f"pos = {new_pos}")
            else:
                updated.append(line)
        self._ed_busy = True
        cur = self.editor.textCursor().position()
        self.editor.setPlainText("\n".join(updated))
        tc = self.editor.textCursor()
        tc.setPosition(min(cur, len(self.editor.toPlainText())))
        self.editor.setTextCursor(tc)
        self._ed_busy = False
        self._set_dirty(True)
        self.view3d.update_object_position(obj, self._scale)

        # Zugehörige Death-Zonen mitverschieben
        self._move_linked_zones(obj)

    def _move_linked_zones(self, obj: SolarObject):
        """Verschiebt Death-Zonen, die zum Objekt gehören (z.B. Zone_SUN01_death)."""
        nick = obj.nickname.lower()
        # Suche nach Zonen mit Muster: Zone_{NICK}_death, {NICK}_death, zone_{NICK}
        for z in self._zones:
            zn = z.nickname.lower()
            if nick in zn and ("death" in zn or "exclusion" in zn):
                z.setPos(obj.pos())
                # Zone-Daten aktualisieren
                new_pos = obj.fl_pos_str()
                if "_entries" in z.data:
                    z.data["_entries"] = [
                        (k, new_pos) if k.lower() == "pos" else (k, v)
                        for k, v in z.data["_entries"]
                    ]
                z.data["pos"] = new_pos
                self._set_dirty(True)

    # ==================================================================
    #  Editor-Feld-Update (Quick-Editor)
    # ==================================================================
    def _update_editor_field(self, key: str, value: str):
        if not self._selected:
            return
        updated = []
        found = False
        lc_key = key.lower()
        for line in self.editor.toPlainText().splitlines():
            if line.partition("=")[0].strip().lower() == lc_key:
                if value.strip():
                    updated.append(f"{key} = {value}")
                found = True
            else:
                updated.append(line)
        if not found and value.strip():
            updated.append(f"{key} = {value}")
        self._ed_busy = True
        cur = self.editor.textCursor().position()
        self.editor.setPlainText("\n".join(updated))
        tc = self.editor.textCursor()
        tc.setPosition(min(cur, len(self.editor.toPlainText())))
        self.editor.setTextCursor(tc)
        self._ed_busy = False
        self._set_dirty(True)

    def _on_faction_changed(self, text: str):
        if not text:
            return
        rep_val = self.rep_edit.text().strip()
        if rep_val:
            self._update_editor_field("reputation", f"{text},{rep_val}")
        else:
            self._update_editor_field("reputation", text)

    def _on_rep_changed(self):
        if not self.faction_cb.currentText():
            return
        val = self.rep_edit.text().strip()
        if val:
            self._update_editor_field("reputation", f"{self.faction_cb.currentText()},{val}")
        else:
            self._update_editor_field("reputation", self.faction_cb.currentText())

    # ==================================================================
    #  Objekt-Editor / Zone-Link-Editor
    # ==================================================================
    def _start_object_edit(self):
        if not self._selected:
            return
        self.editor.setVisible(True)
        self.apply_btn.setVisible(True)
        self.apply_btn.setEnabled(True)
        self.editor.setPlainText(self._selected.raw_text())
        if isinstance(self._selected, ZoneItem):
            self._show_zone_extra_editors(self._selected)
        else:
            self._hide_zone_extra_editors()
        self.statusBar().showMessage("Objekt-Editor geöffnet")

    def _hide_zone_extra_editors(self):
        self.zone_link_lbl.setVisible(False)
        self.zone_link_editor.setVisible(False)
        self.zone_file_lbl.setVisible(False)
        self.zone_file_editor.setVisible(False)
        self.zone_link_editor.clear()
        self.zone_file_editor.clear()
        self._zone_link_section_index = None
        self._zone_link_section_name = None
        self._zone_link_file_path = None

    def _show_zone_extra_editors(self, zone: ZoneItem):
        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        if not game_path:
            self._hide_zone_extra_editors()
            return
        zone_nick = zone.nickname.strip().lower()
        match_idx = match_sec_name = match_entries = None
        for idx, (sec_name, entries) in enumerate(self._sections):
            if sec_name.lower() not in ("nebula", "asteroids"):
                continue
            zone_val = ""
            for k, v in entries:
                if k.lower() == "zone":
                    zone_val = v.strip().lower()
                    break
            if zone_val == zone_nick:
                match_idx, match_sec_name, match_entries = idx, sec_name, entries
                break
        if match_idx is None or match_entries is None or match_sec_name is None:
            self._hide_zone_extra_editors()
            return
        file_rel = ""
        for k, v in match_entries:
            if k.lower() == "file":
                file_rel = v.strip()
                break
        if not file_rel:
            self._hide_zone_extra_editors()
            return
        linked_file = self._resolve_game_path_case_insensitive(game_path, file_rel)
        if not linked_file:
            self._hide_zone_extra_editors()
            return
        self._zone_link_section_index = match_idx
        self._zone_link_section_name = match_sec_name
        self._zone_link_file_path = linked_file
        self.zone_link_lbl.setVisible(True)
        self.zone_link_editor.setVisible(True)
        self.zone_file_lbl.setVisible(True)
        self.zone_file_editor.setVisible(True)
        self.zone_link_editor.setPlainText(
            self._entries_to_text(match_sec_name, match_entries)
        )
        self.zone_file_lbl.setText(f"Zonen-Datei (verlinkte INI): {file_rel}")
        try:
            self.zone_file_editor.setPlainText(
                linked_file.read_text(encoding="utf-8", errors="ignore")
            )
        except Exception as ex:
            self.zone_file_editor.setPlainText(f"; Fehler beim Laden: {ex}")

    @staticmethod
    def _entries_to_text(section_name: str, entries: list[tuple[str, str]]) -> str:
        lines = [f"[{section_name}]"]
        for k, v in entries:
            lines.append(f"{k} = {v}")
        return "\n".join(lines)

    @staticmethod
    def _text_to_section_entries(text: str, default_section: str) -> tuple[str, list[tuple[str, str]]]:
        sec_name = default_section
        entries: list[tuple[str, str]] = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith(";") or line.startswith("//"):
                continue
            if line.startswith("[") and line.endswith("]"):
                sec_name = line[1:-1].strip() or default_section
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                entries.append((k.strip(), v.strip()))
        return sec_name, entries

    # ==================================================================
    #  Objekt/Zonen Combo
    # ==================================================================
    def _rebuild_object_combo(self):
        self.obj_combo.blockSignals(True)
        self.obj_combo.clear()
        for obj in self._objects:
            self.obj_combo.addItem(f"[OBJ] {obj.nickname}", obj)
        for zone in self._zones:
            self.obj_combo.addItem(f"[ZONE] {zone.nickname}", zone)
        if not self._objects and not self._zones:
            self.obj_combo.addItem("(keine Objekte/Zonen)")
        self.obj_combo.blockSignals(False)

    def _sync_obj_combo_to_selection(self):
        if not self._selected:
            self.obj_combo.setCurrentIndex(-1)
            return
        for i in range(self.obj_combo.count()):
            if self.obj_combo.itemData(i) is self._selected:
                self.obj_combo.blockSignals(True)
                self.obj_combo.setCurrentIndex(i)
                self.obj_combo.blockSignals(False)
                return
        self.obj_combo.setCurrentIndex(-1)

    def _on_obj_combo_changed(self, index):
        if index < 0:
            return
        item = self.obj_combo.itemData(index)
        if item is None:
            return
        if isinstance(item, ZoneItem):
            self._select_zone(item)
        elif isinstance(item, SolarObject):
            self._select(item)

    def _jump_to_selected_from_combo(self):
        idx = self.obj_combo.currentIndex()
        if idx < 0:
            return
        item = self.obj_combo.itemData(idx)
        if item is None:
            return
        if isinstance(item, ZoneItem):
            self._select_zone(item)
        else:
            self._select(item)
        try:
            self.view.centerOn(item)
        except Exception:
            pass
        try:
            self.view3d.center_on_item(item)
        except Exception:
            pass
        name = getattr(item, "nickname", "Auswahl")
        self.statusBar().showMessage(f"Zentriert auf: {name}")

    # ==================================================================
    #  Erstellen  (Objekt, Zone, Sonne, Planet, Jump)
    # ==================================================================
    def _create_new_object(self):
        if not self._filepath:
            QMessageBox.warning(self, "Kein System", "Bitte zuerst ein System laden.")
            return
        self._pending_new_object = True
        self.statusBar().showMessage("Klicke auf die Karte, um ein neues Objekt zu platzieren")
        self._set_placement_mode(True, "Objekt platzieren")

    def _create_object_at_pos(self, pos: QPointF):
        archetypes = [self.arch_cb.itemText(i) for i in range(self.arch_cb.count()) if self.arch_cb.itemText(i)]
        loadouts = [self.loadout_cb.itemText(i) for i in range(self.loadout_cb.count()) if self.loadout_cb.itemText(i)]
        factions = [self.faction_cb.itemText(i) for i in range(self.faction_cb.count()) if self.faction_cb.itemText(i)]
        dlg = ObjectCreationDialog(self, archetypes, loadouts, factions)
        dlg.nick_edit.setText(f"new_obj_{len(self._objects) + 1}")
        if dlg.exec() != QDialog.Accepted:
            self._pending_new_object = False
            return
        data_in = dlg.payload()
        nickname = data_in.get("nickname", "").strip() or f"new_obj_{len(self._objects) + 1}"
        pos_str = f"{pos.x() / self._scale:.2f}, 0, {pos.y() / self._scale:.2f}"
        entries = [
            ("nickname", nickname),
            ("pos", pos_str),
            ("ids_name", "0"),
            ("ids_info", "0"),
            ("rotate", "0,0,0"),
        ]
        arch = data_in.get("archetype", "").strip()
        if arch:
            entries.append(("archetype", arch))
        loadout = data_in.get("loadout", "").strip()
        if loadout:
            entries.append(("loadout", loadout))
        faction = data_in.get("faction", "").strip()
        if faction:
            rep_val = data_in.get("rep", "").strip()
            entries.append(("reputation", f"{faction},{rep_val}" if rep_val else faction))
        self._add_object_from_entries(entries, "Object")
        self._pending_new_object = False

    def _add_object_from_entries(self, entries: list[tuple[str, str]], section_name: str):
        """Erzeugt ein SolarObject aus Eintrags-Tupeln und fügt es zur Szene hinzu."""
        data = {"_entries": entries}
        for k, v in entries:
            if k.lower() not in data:
                data[k.lower()] = v
        obj = SolarObject(data, self._scale)
        obj.setFlag(QGraphicsItem.ItemIsMovable, self.move_cb.isChecked())
        self.view._scene.addItem(obj)
        self._objects.append(obj)
        self._sections.append((section_name, list(entries)))
        self._rebuild_object_combo()
        self._select(obj)
        self._set_dirty(True)
        self._refresh_3d_scene()

    def _create_sun(self):
        if not self._filepath:
            QMessageBox.warning(self, "Kein System", "Bitte zuerst ein System laden.")
            return
        sun_arches = [
            self.arch_cb.itemText(i) for i in range(self.arch_cb.count())
            if "sun" in self.arch_cb.itemText(i).lower()
        ]
        if not sun_arches:
            sun_arches = ["sun"]
        stars = self._stars if self._stars else ["med_white_sun"]
        dlg = SolarCreationDialog(
            self, "Sonne erstellen", sun_arches,
            default_radius=2000, default_damage=200000,
            stars=stars, default_star="med_white_sun",
        )
        if dlg.exec() != QDialog.Accepted:
            return
        payload = dlg.payload()
        if not payload["nickname"]:
            QMessageBox.warning(self, "Unvollständig", "Bitte einen Nickname angeben.")
            return
        self._pending_create = {
            "kind": "sun",
            "nickname": payload["nickname"],
            "archetype": payload["archetype"] or "sun",
            "burn_color": payload["burn_color"],
            "radius": payload["radius"],
            "damage": payload["damage"],
            "star": payload.get("star", "med_white_sun") or "med_white_sun",
            "atmosphere_range": payload.get("atmosphere_range", 5000) or 5000,
        }
        self.statusBar().showMessage("Klicke ins System, um die Sonne zu platzieren")
        self._set_placement_mode(True, "Sonne platzieren")

    def _create_planet(self):
        if not self._filepath:
            QMessageBox.warning(self, "Kein System", "Bitte zuerst ein System laden.")
            return
        planet_arches = [
            self.arch_cb.itemText(i) for i in range(self.arch_cb.count())
            if "planet" in self.arch_cb.itemText(i).lower()
        ]
        if not planet_arches:
            planet_arches = ["planet"]
        dlg = SolarCreationDialog(
            self, "Planet erstellen", planet_arches,
            default_radius=1500, default_damage=200000,
        )
        if dlg.exec() != QDialog.Accepted:
            return
        payload = dlg.payload()
        if not payload["nickname"]:
            QMessageBox.warning(self, "Unvollständig", "Bitte einen Nickname angeben.")
            return
        self._pending_create = {
            "kind": "planet",
            "nickname": payload["nickname"],
            "archetype": payload["archetype"] or "planet",
            "burn_color": payload["burn_color"],
            "radius": payload["radius"],
            "damage": payload["damage"],
            "atmosphere_range": payload.get("atmosphere_range", 2000),
        }
        self.statusBar().showMessage("Klicke ins System, um den Planeten zu platzieren")
        self._set_placement_mode(True, "Planet platzieren")

    def _create_solar_at_pos(self, pos: QPointF):
        spec = self._pending_create
        if not spec:
            return
        fx = pos.x() / self._scale
        fz = pos.y() / self._scale
        pos_str = f"{fx:.2f}, 0, {fz:.2f}"

        ids_name = "261008" if spec.get("kind") == "sun" else "0"
        ids_info = "66162" if spec.get("kind") == "sun" else "0"

        entries = [
            ("nickname", spec["nickname"]),
            ("ids_name", ids_name),
            ("ids_info", ids_info),
            ("pos", pos_str),
            ("rotate", "0,0,0"),
            ("archetype", spec["archetype"]),
        ]
        if spec.get("kind") == "planet":
            entries.append(("spin", "0,0,0"))
            entries.append(("atmosphere_range", str(spec.get("atmosphere_range", 2000) or 2000)))
        if spec.get("kind") == "sun":
            entries.append(("atmosphere_range", str(spec.get("atmosphere_range", 5000))))
            entries.append(("star", spec.get("star", "med_white_sun") or "med_white_sun"))
        if spec.get("burn_color"):
            entries.append(("burn_color", spec["burn_color"]))

        data = {"_entries": list(entries)}
        for k, v in entries:
            if k.lower() not in data:
                data[k.lower()] = v
        obj = SolarObject(data, self._scale)
        obj.setFlag(QGraphicsItem.ItemIsMovable, self.move_cb.isChecked())
        self.view._scene.addItem(obj)
        self._objects.append(obj)
        self._sections.append(("Object", list(entries)))

        # Death-Zone
        z_nick = f"Zone_{spec['nickname']}_death"
        zone_entries = [
            ("nickname", z_nick),
            ("pos", pos_str),
            ("rotate", "0,0,0"),
            ("shape", "SPHERE"),
            ("size", str(spec["radius"])),
            ("damage", str(spec["damage"])),
            ("ids_info", "0"),
        ]
        z_data = {"_entries": list(zone_entries)}
        for k, v in zone_entries:
            if k.lower() not in z_data:
                z_data[k.lower()] = v
        z_item = ZoneItem(z_data, self._scale)
        self.view._scene.addItem(z_item)
        self._zones.append(z_item)
        self._sections.append(("Zone", list(zone_entries)))

        self._rebuild_object_combo()
        self._select(obj)
        self._set_dirty(True)
        created_typ = "Sonne" if spec.get("kind") == "sun" else "Planet"
        self.statusBar().showMessage(f"{created_typ} + Death-Zone erstellt: {spec['nickname']}")
        self._pending_create = None
        self._refresh_3d_scene()

    def _create_zone_at_pos(self, pos: QPointF):
        if not self._pending_zone:
            return
        pz = self._pending_zone
        zone_type = pz["type"]
        ref_file = pz["ref_file"]
        zone_name = pz["name"]
        game_path = pz["game_path"]

        if zone_type == "Asteroid Field":
            src_dir_name = "solar\\asteroids"
            section_name = "Asteroids"
        else:
            src_dir_name = "solar\\nebula"
            section_name = "Nebula"

        base = Path(game_path)
        if not (base / "solar").exists() and not (base / "SOLAR").exists():
            data_dir = ci_find(base, "DATA")
            if data_dir and data_dir.is_dir():
                base = data_dir
        solar_dir = ci_find(base, "solar")
        if not solar_dir or not solar_dir.is_dir():
            QMessageBox.warning(self, "Fehler", f"solar-Verzeichnis nicht gefunden in {base}")
            return
        if zone_type == "Asteroid Field":
            src_dir = ci_find(solar_dir, "asteroids")
        else:
            src_dir = ci_find(solar_dir, "nebula")
        if not src_dir or not src_dir.is_dir():
            QMessageBox.warning(self, "Fehler", f"Verzeichnis nicht gefunden.")
            return
        src_file = src_dir / ref_file
        if not src_file.exists():
            QMessageBox.warning(self, "Fehler", f"Referenzdatei nicht gefunden: {src_file}")
            return

        sys_name = Path(self._filepath).stem.upper()
        tmp_name = zone_name.replace(" ", "_")
        safe_zone_name = "".join(ch for ch in tmp_name if ch.isalnum() or ch in ("_", "-"))
        existing = list(src_dir.glob(f"{sys_name}_{safe_zone_name}_*.ini"))
        next_num = len(existing) + 1
        new_zone_file = f"{sys_name}_{safe_zone_name}_{next_num}.ini"
        new_zone_path = src_dir / new_zone_file

        try:
            content = src_file.read_text(encoding="utf-8")
            lines = content.split("\n")
            new_lines = []
            skip_section = False
            for line in lines:
                l_lower = line.strip().lower()
                if l_lower == "[exclusion zones]":
                    skip_section = True
                elif l_lower.startswith("[") and skip_section:
                    skip_section = False
                if not skip_section:
                    new_lines.append(line)
            new_lines.append(f"\n; Copied by FLeditor from file: {src_dir_name}\\{ref_file}")
            new_zone_path.write_text("\n".join(new_lines), encoding="utf-8")
        except Exception as ex:
            QMessageBox.critical(self, "Fehler beim Kopieren", str(ex))
            return

        zone_nick = f"Zone_{sys_name}_{safe_zone_name}_{next_num}"
        zone_entries = [
            ("nickname", zone_nick),
            ("ids_name", "0"),
            ("pos", f"{pos.x() / self._scale:.2f}, 0, {pos.y() / self._scale:.2f}"),
            ("rotate", "0, 0, 0"),
            ("shape", "ELLIPSOID"),
            ("size", "1000, 1000, 1000"),
            ("property_flags", "0"),
            ("ids_info", "66146"),
            ("visit", "0"),
            ("damage", "0"),
        ]
        zone_data = {"_entries": zone_entries}
        for k, v in zone_entries:
            zone_data[k.lower()] = v
        zone = ZoneItem(zone_data, self._scale)
        self.view._scene.addItem(zone)
        self._zones.append(zone)
        self._rebuild_object_combo()
        self._select_zone(zone)

        self._sections.append(("Zone", list(zone_entries)))
        rel_path = f"{src_dir_name}\\{new_zone_file}"
        entry = (section_name, [("file", rel_path), ("zone", zone_nick)])
        insert_idx = None
        for i, (sec_name, _) in enumerate(self._sections):
            if sec_name.lower() == "music":
                insert_idx = i + 1
                break
        if insert_idx is not None:
            self._sections.insert(insert_idx, entry)
        else:
            self._sections.append(entry)
        self._set_dirty(True)
        self._pending_zone = None
        self.statusBar().showMessage(f"✓  Zone '{zone_name}' erstellt")
        self._refresh_3d_scene()

    # ------------------------------------------------------------------
    #  Jump-Verbindung
    # ------------------------------------------------------------------
    def _start_zone_creation(self):
        if not self._filepath:
            QMessageBox.warning(self, "Kein System", "Bitte zuerst ein System laden.")
            return
        game_path = self.browser.path_edit.text().strip()
        if not game_path:
            QMessageBox.warning(self, "Kein Spielpfad", "Bitte zuerst Spielpfad konfigurieren.")
            return
        base = Path(game_path)
        if not (base / "solar").exists() and not (base / "SOLAR").exists():
            data_dir = ci_find(base, "DATA")
            if data_dir and data_dir.is_dir():
                base = data_dir
        solar_dir = ci_find(base, "solar")
        if not solar_dir or not solar_dir.is_dir():
            QMessageBox.warning(self, "Fehler", f"solar-Verzeichnis nicht gefunden in {base}")
            return
        ast_dir = ci_find(solar_dir, "asteroids")
        neb_dir = ci_find(solar_dir, "nebula")
        asteroids = sorted([f.name for f in ast_dir.glob("*.ini")]) if ast_dir and ast_dir.is_dir() else []
        nebulas = sorted([f.name for f in neb_dir.glob("*.ini")]) if neb_dir and neb_dir.is_dir() else []
        dlg = ZoneCreationDialog(self, asteroids, nebulas)
        if dlg.exec() != QDialog.Accepted:
            return
        zone_type = dlg.type_cb.currentText()
        ref_file = dlg.ref_cb.currentText()
        zone_name = dlg.name_edit.text().strip()
        if not zone_name or not ref_file:
            QMessageBox.warning(self, "Unvollständig", "Bitte Name und Referenzdatei angeben.")
            return
        self._pending_zone = {
            "type": zone_type, "ref_file": ref_file,
            "name": zone_name, "game_path": game_path,
        }
        self._set_placement_mode(True, f"Zone platzieren: {zone_name}")

    def _start_connection_dialog(self):
        if not self._filepath:
            QMessageBox.warning(self, "Kein System", "Bitte zuerst ein System laden.")
            return
        if self._pending_snapshots:
            QMessageBox.warning(self, "Offene Änderungen", "Bitte vorhandene Verbindungen zuerst speichern.")
            return
        systems = []
        for i in range(self.browser.list_widget.count()):
            item = self.browser.list_widget.item(i)
            systems.append((item.text(), item.data(Qt.UserRole)))
        dlg = ConnectionDialog(self, systems)
        if dlg.exec() != QDialog.Accepted:
            return
        dest_path = dlg.dest_cb.currentData()
        typ = dlg.type_cb.currentText()
        origin = self._filepath
        if not origin:
            return
        origin_nick = Path(origin).stem.upper()
        gate_info: dict | None = None
        if typ == "Jump Gate":
            loads = [
                self.loadout_cb.itemText(i) for i in range(self.loadout_cb.count())
                if "jumpgate" in self.loadout_cb.itemText(i).lower()
            ]
            facts = [self.faction_cb.itemText(i) for i in range(self.faction_cb.count())]
            gdlg = GateInfoDialog(self, loads, facts)
            if gdlg.exec() != QDialog.Accepted:
                return
            gate_info = {
                "behavior": gdlg.behavior_edit.text().strip(),
                "difficulty": gdlg.difficulty_spin.value(),
                "loadout": gdlg.loadout_cb.currentText().strip(),
                "pilot": gdlg.pilot_edit.text().strip(),
                "reputation": gdlg.rep_cb.currentText().strip(),
            }
        self._pending_conn = {
            "origin": origin, "origin_nick": origin_nick,
            "type": typ, "dest": dest_path, "step": 1,
            "gate_info": gate_info,
        }
        self.statusBar().showMessage("Klicke im aktuellen System, um das erste Verbindungsobjekt zu platzieren")
        self._set_placement_mode(True, "Jump-Verbindung: Ursprung platzieren")

    # ------------------------------------------------------------------
    #  Neues System erstellen
    # ------------------------------------------------------------------
    def _start_new_system(self):
        """Öffnet Dialog und aktiviert Platzierungsmodus auf der Karte."""
        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        if not game_path:
            QMessageBox.warning(self, "Kein Pfad", "Bitte zuerst einen Spielpfad eingeben.")
            return

        # Sammle Optionen aus allen vorhandenen Systemen
        music_vals = {"space": set(), "danger": set(), "battle": set()}
        bg_vals = {"basic_stars": set(), "complex_stars": set(), "nebulae": set()}
        try:
            for s in find_all_systems(game_path, self._parser):
                try:
                    secs = self._parser.parse(s["path"])
                except Exception:
                    continue
                for sec_name, entries in secs:
                    low = sec_name.lower()
                    if low == "music":
                        for k, v in entries:
                            lk = k.lower()
                            if lk in music_vals and v:
                                music_vals[lk].add(v)
                    elif low == "background":
                        for k, v in entries:
                            lk = k.lower()
                            if lk in bg_vals and v:
                                bg_vals[lk].add(v)
        except Exception:
            pass

        factions: list[str] = []
        iw_file = ci_resolve(Path(game_path), "DATA/initialworld.ini")
        if iw_file and iw_file.exists():
            try:
                for sec_name, entries in self._parser.parse(str(iw_file)):
                    if sec_name.lower() == "group":
                        for k, v in entries:
                            if k.lower() == "nickname" and v not in factions:
                                factions.append(v)
            except Exception:
                pass
        factions.sort(key=str.lower)

        dlg = SystemCreationDialog(
            self,
            music_space=sorted(music_vals["space"], key=str.lower),
            music_danger=sorted(music_vals["danger"], key=str.lower),
            music_battle=sorted(music_vals["battle"], key=str.lower),
            bg_basic=sorted(bg_vals["basic_stars"], key=str.lower),
            bg_complex=sorted(bg_vals["complex_stars"], key=str.lower),
            bg_nebulae=sorted(bg_vals["nebulae"], key=str.lower),
            factions=factions,
        )
        if dlg.exec() != QDialog.Accepted:
            return

        payload = dlg.payload()
        if not payload["name"] or not payload["prefix"]:
            QMessageBox.warning(self, "Fehler", "Name und Prefix sind Pflichtfelder.")
            return

        self._pending_new_system = {**payload, "game_path": game_path}
        self._set_placement_mode(True, "Neues System: Klicke auf die Karte")
        self.statusBar().showMessage("Klicke auf die Universum-Karte, um das System zu platzieren.")

    def _create_system_at_pos(self, pos: QPointF):
        """Erstellt das neue System an der Klickposition auf der Karte."""
        info = self._pending_new_system
        if not info:
            return
        self._pending_new_system = None

        game_path = info["game_path"]
        prefix = info["prefix"]
        name = info["name"]
        size = info["size"]

        # Auto-Nummerierung: existierende Systeme mit gleichem Prefix zählen
        existing_nums: list[int] = []
        try:
            systems = find_all_systems(game_path, self._parser)
            for s in systems:
                nick = s["nickname"].upper()
                if nick.startswith(prefix):
                    suffix = nick[len(prefix):]
                    if suffix.isdigit():
                        existing_nums.append(int(suffix))
        except Exception:
            pass
        next_num = max(existing_nums, default=0) + 1
        num_str = f"{next_num:02d}"
        nickname = f"{prefix}{num_str}"

        # Verzeichnis erstellen
        uni_ini = find_universe_ini(game_path)
        if not uni_ini:
            QMessageBox.critical(self, "Fehler", "universe.ini nicht gefunden!")
            return

        # System-Datei Pfad (Großbuchstaben für Ordner/Datei)
        systems_dir = uni_ini.parent / "SYSTEMS"
        systems_dir.mkdir(parents=True, exist_ok=True)
        sys_dir = systems_dir / nickname
        sys_dir.mkdir(parents=True, exist_ok=True)
        sys_file = sys_dir / f"{nickname}.ini"

        # System-INI schreiben
        light_nick = f"{nickname}_system_light"
        ini_lines = [
            f"[SystemInfo]",
            f"space_color = {info['space_color']}",
            f"local_faction = {info['local_faction']}",
            f"",
            f"[TexturePanels]",
            f"file = universe\\heavens\\shapes.ini",
            f"",
            f"[Music]",
            f"space = {info['music_space']}",
            f"danger = {info['music_danger']}",
            f"battle = {info['music_battle']}",
            f"",
            f"[Dust]",
            f"spacedust = Dust",
            f"",
            f"[Ambient]",
            f"color = {info['ambient_color']}",
            f"",
            f"[Background]",
            f"basic_stars = {info['bg_basic']}",
            f"complex_stars = {info['bg_complex']}",
            f"nebulae = {info['bg_nebulae']}",
            f"",
            f"[LightSource]",
            f"nickname = {light_nick}",
            f"pos = 0, 0, 0",
            f"color = {info['light_color']}",
            f"range = {size}",
            f"type = DIRECTIONAL",
            f"atten_curve = DYNAMIC_DIRECTION",
            f"",
        ]
        sys_file.write_text("\n".join(ini_lines), encoding="utf-8")

        # universe.ini aktualisieren  —  neuen [system]-Block anhängen
        uni_x = pos.x() / self._scale
        uni_y = pos.y() / self._scale
        nickname_lower = nickname.lower()
        rel_path = f"systems\\{nickname}\\{nickname}.ini"
        uni_block = (
            f"\n[system]\n"
            f"nickname = {nickname_lower}\n"
            f"file = {rel_path}\n"
            f"pos = {uni_x:.0f}, {uni_y:.0f}\n"
            f"visit = 0\n"
            f"strid_name = 0\n"
            f"ids_info = 66106\n"
            f"NavMapScale = 1.360000\n"
            f"msg_id_prefix = gcs_refer_system_{nickname_lower}\n"
        )
        with open(str(uni_ini), "a", encoding="utf-8") as f:
            f.write(uni_block)

        self.statusBar().showMessage(
            f"✔  System '{name}' ({nickname}) erstellt → {sys_file}"
        )

        # Universum neu laden, dann das neue System öffnen
        self._load_universe(game_path)
        self._filepath = str(sys_file)
        self._load(str(sys_file))
        self.browser.highlight_current(str(sys_file))

    def _on_background_click(self, pos: QPointF):
        if self._pending_new_system:
            self._create_system_at_pos(pos)
            self._set_placement_mode(False)
            return
        if self._pending_new_object:
            self._create_object_at_pos(pos)
            self._set_placement_mode(False)
            return
        if self._pending_zone:
            self._create_zone_at_pos(pos)
            self._set_placement_mode(False)
            return
        if self._pending_create:
            self._create_solar_at_pos(pos)
            self._set_placement_mode(False)
            return
        if not self._pending_conn:
            return
        self._place_connection(pos)

    def _place_connection(self, pos: QPointF):
        """Platziert ein Jump-Verbindungsobjekt an der Klickposition."""
        step = self._pending_conn.get("step", 1)
        orig = self._pending_conn["origin_nick"]
        typ = self._pending_conn["type"]
        arch = "jumpgate" if "Gate" in typ else "jumphole"

        def _snapshot():
            fp = self._filepath
            secs = [(n, list(e)) for n, e in self._sections]
            objs = []
            for o in self._objects:
                d = {k: v for k, v in o.data.items() if k != "_entries"}
                ents = list(o.data.get("_entries", []))
                d["_entries"] = ents
                objs.append(d)
            return (fp, secs, objs)

        def _make_obj(nick, goto_val, extras=None):
            entries = [
                ("nickname", nick),
                ("pos", f"{pos.x() / self._scale:.2f}, 0, {pos.y() / self._scale:.2f}"),
                ("archetype", arch),
                ("goto", goto_val),
            ]
            if extras:
                entries.extend(extras)
            data = {"_entries": entries}
            for k, v in entries:
                if k.lower() not in data:
                    data[k.lower()] = v
            obj = SolarObject(data, self._scale)
            obj.setFlag(QGraphicsItem.ItemIsMovable, self.move_cb.isChecked())
            self.view._scene.addItem(obj)
            self._objects.append(obj)
            self._select(obj)
            self._set_dirty(True)
            return obj

        def _gate_extras():
            extras = [
                ("rotate", "0,0,0"),
                ("ids_name", "0"),
                ("ids_info", "66145" if arch == "jumpgate" else "66146"),
            ]
            if arch == "jumpgate":
                info = self._pending_conn.get("gate_info", {}) or {}
                extras += [
                    ("behavior", info.get("behavior", "NOTHING")),
                    ("difficulty_level", str(info.get("difficulty", 1))),
                    ("loadout", info.get("loadout", "")),
                    ("pilot", info.get("pilot", "pilot_solar_hardest")),
                    ("reputation", info.get("reputation", "")),
                ]
            return extras

        if step == 1:
            destnick = Path(self._pending_conn["dest"]).stem.upper()
            nick = f"{orig}_to_{destnick}_{arch}"
            goto_str = f"{destnick}, {destnick}_to_{orig}_{arch}, gate_tunnel_bretonia"
            extras = _gate_extras()
            extras.append(("msg_id_prefix", f"gcs_refer_system_{destnick}"))
            _make_obj(nick, goto_str, extras)
            self._pending_snapshots.append(_snapshot())
            dest_path = self._pending_conn["dest"]
            self._pending_conn["step"] = 2
            pending = self._pending_conn
            self._load(dest_path)
            self._pending_conn = pending
            self.browser.highlight_current(dest_path)
            self.statusBar().showMessage("Origin platziert – klicke im Zielsystem, um Gegenstück zu setzen")
            self._set_placement_mode(True, "Jump-Verbindung: Gegenstück platzieren")
        else:
            destnick = Path(self._filepath).stem.upper()
            nick = f"{destnick}_to_{orig}_{arch}"
            goto_str = f"{orig}, {orig}_to_{destnick}_{arch}, gate_tunnel_bretonia"
            extras = _gate_extras()
            extras.append(("msg_id_prefix", f"gcs_refer_system_{orig}"))
            _make_obj(nick, goto_str, extras)
            self._pending_snapshots.append(_snapshot())
            self.save_conn_btn.setVisible(True)
            self.create_conn_btn.setEnabled(False)
            self._pending_conn = None
            self.statusBar().showMessage("Ziel erstellt – bitte Verbindungen speichern")
            self._set_placement_mode(False)

    # ==================================================================
    #  Löschen
    # ==================================================================
    def _delete_object(self):
        if not self._selected:
            return
        obj = self._selected
        if isinstance(obj, ZoneItem):
            self._delete_zone(obj)
            return
        self._delete_solar_object(obj)

    def _delete_zone(self, zone: ZoneItem):
        z_idx = None
        try:
            z_idx = self._zones.index(zone)
        except ValueError:
            pass
        if z_idx is not None:
            count = 0
            for i, (sec_name, entries) in enumerate(list(self._sections)):
                if sec_name.lower() == "zone":
                    if count == z_idx:
                        self._sections.pop(i)
                        break
                    count += 1
        self.view._scene.removeItem(zone)
        if zone in self._zones:
            self._zones.remove(zone)
        self._rebuild_object_combo()
        self._selected = None
        self._clear_selection_ui()
        self._hide_zone_extra_editors()
        self._set_dirty(True)
        self._write_to_file(reload=False)
        self.statusBar().showMessage(f"✓  Zone '{zone.nickname}' gelöscht")
        self._refresh_3d_scene()

    def _delete_solar_object(self, obj: SolarObject):
        nick = obj.nickname.lower()
        arch = obj.data.get("archetype", "").lower()
        is_gate = "jumpgate" in arch
        is_hole = "jumphole" in arch
        counterpart_nick = counterpart_file = counterpart_sys = None

        if is_gate or is_hole:
            goto_val = obj.data.get("goto", "").strip()
            if goto_val:
                tokens = [t.strip() for t in goto_val.split(",") if t.strip()]
                if len(tokens) >= 2:
                    counterpart_sys = tokens[0]
                    counterpart_nick = tokens[1]
                    try:
                        systems = find_all_systems(
                            self.browser.path_edit.text().strip(), self._parser
                        )
                        for sys_ in systems:
                            if sys_.get("nickname", "").upper() == counterpart_sys.upper():
                                counterpart_file = sys_.get("path")
                                break
                    except Exception:
                        pass

        msg = f"Objekt '{obj.nickname}' wirklich löschen?"
        if counterpart_nick and counterpart_file:
            msg += (
                f"\n\nDas Gegenstück '{counterpart_nick}'\n"
                "im anderen System wird automatisch gelöscht."
            )
            if QMessageBox.warning(self, "Löschen bestätigen", msg,
                                   QMessageBox.Ok | QMessageBox.Cancel) != QMessageBox.Ok:
                return
        elif counterpart_nick and not counterpart_file:
            err = (
                f"Gegenstück '{counterpart_nick}' wurde anhand des 'goto'-Feldes erkannt,\n"
                f"die zugehörige Systemdatei ('{counterpart_sys}') wurde jedoch nicht gefunden.\n\n"
                "Soll trotzdem gelöscht werden?"
            )
            if QMessageBox.question(self, "Gegenstück nicht gefunden", err,
                                    QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                return

        # Sektion entfernen
        obj_idx = None
        try:
            obj_idx = self._objects.index(obj)
        except ValueError:
            pass
        if obj_idx is not None:
            count = 0
            for i, (sec_name, entries) in enumerate(list(self._sections)):
                if sec_name.lower() == "object":
                    if count == obj_idx:
                        self._sections.pop(i)
                        break
                    count += 1
        self.view._scene.removeItem(obj)
        if obj in self._objects:
            self._objects.remove(obj)

        # Sonne/Planet → verknüpfte Death-Zone löschen
        if "sun" in arch or "planet" in arch:
            target_zone_nick = f"zone_{nick}_death"
            linked_zone = next(
                (z for z in self._zones if z.nickname.lower() == target_zone_nick), None
            )
            if linked_zone:
                z_idx = None
                try:
                    z_idx = self._zones.index(linked_zone)
                except ValueError:
                    pass
                if z_idx is not None:
                    count = 0
                    for i, (sec_name, entries) in enumerate(list(self._sections)):
                        if sec_name.lower() == "zone":
                            if count == z_idx:
                                self._sections.pop(i)
                                break
                            count += 1
                self.view._scene.removeItem(linked_zone)
                if linked_zone in self._zones:
                    self._zones.remove(linked_zone)

        self._rebuild_object_combo()
        self._selected = None
        self._clear_selection_ui()
        self._hide_zone_extra_editors()
        self._set_dirty(True)
        self._write_to_file(reload=False)

        if counterpart_nick and counterpart_file:
            try:
                self._delete_counterpart(counterpart_file, counterpart_nick)
            except Exception as ex:
                QMessageBox.warning(self, "Gegenpart-Löschung",
                                    f"Konnte Gegenstück nicht löschen:\n{ex}")
        self.statusBar().showMessage(f"✓  Objekt '{nick}' gelöscht")
        self._refresh_3d_scene()

    def _delete_counterpart(self, filepath: str, nick_to_delete: str):
        secs = self._parser.parse(filepath)
        objs = self._parser.get_objects(secs)
        obj_idx = -1
        for i, o in enumerate(objs):
            if o.get("nickname", "").lower() == nick_to_delete.lower():
                obj_idx = i
                break
        if obj_idx < 0:
            return
        obj_count = 0
        new_secs = []
        for sec_name, entries in secs:
            if sec_name.lower() == "object":
                if obj_count == obj_idx:
                    obj_count += 1
                    continue
                obj_count += 1
            new_secs.append((sec_name, entries))
        lines = []
        for sec_name, entries in new_secs:
            lines.append(f"[{sec_name}]")
            for k, v in entries:
                lines.append(f"{k} = {v}")
            lines.append("")
        try:
            Path(filepath).write_text("\n".join(lines), encoding="utf-8")
        except Exception:
            tmp = str(filepath) + ".tmp"
            Path(tmp).write_text("\n".join(lines), encoding="utf-8")
            try:
                shutil.move(tmp, filepath)
            except Exception:
                pass

    # ==================================================================
    #  Änderungen übernehmen / Speichern
    # ==================================================================
    def _apply(self):
        if not self._selected:
            return
        self._selected.apply_text(self.editor.toPlainText())
        self._refresh_3d_scene()

        if isinstance(self._selected, ZoneItem) and self._zone_link_section_index is not None:
            sec_name, sec_entries = self._text_to_section_entries(
                self.zone_link_editor.toPlainText(),
                self._zone_link_section_name or "Nebula",
            )
            if sec_entries:
                self._sections[self._zone_link_section_index] = (sec_name, sec_entries)
            if self._zone_link_file_path and self.zone_file_editor.isVisible():
                try:
                    self._zone_link_file_path.write_text(
                        self.zone_file_editor.toPlainText(), encoding="utf-8"
                    )
                except Exception as ex:
                    QMessageBox.warning(self, "Zonen-Datei",
                                        f"Konnte Zonen-Datei nicht speichern:\n{ex}")

        self.name_lbl.setText(f"📍 {self._selected.nickname}")
        self._set_dirty(True)
        self.statusBar().showMessage(
            f"✔  '{self._selected.nickname}' übernommen (noch nicht gespeichert)"
        )

    def _write_to_file(self, reload: bool = True):
        if not self._filepath:
            # Universum-Ansicht: Positionen in universe.ini speichern
            self._save_universe_positions()
            return
        if self._selected:
            self._selected.apply_text(self.editor.toPlainText())

        for obj in self._objects:
            new_pos = obj.fl_pos_str()
            obj.data["_entries"] = [
                (k, new_pos if k.lower() == "pos" else v) for k, v in obj.data["_entries"]
            ]

        obj_idx = 0
        zone_idx = 0
        lines: list[str] = []
        for sec_name, entries in self._sections:
            lines.append(f"[{sec_name}]")
            if sec_name.lower() == "object":
                if obj_idx < len(self._objects):
                    for k, v in self._objects[obj_idx].data["_entries"]:
                        lines.append(f"{k} = {v}")
                    obj_idx += 1
                else:
                    for k, v in entries:
                        lines.append(f"{k} = {v}")
            elif sec_name.lower() == "zone":
                found = False
                for i, z in enumerate(self._zones[zone_idx:], start=zone_idx):
                    if z.nickname == self._extract_nickname_from_entries(entries):
                        for k, v in z.data["_entries"]:
                            lines.append(f"{k} = {v}")
                        zone_idx = i + 1
                        found = True
                        break
                if not found:
                    for k, v in entries:
                        lines.append(f"{k} = {v}")
            else:
                for k, v in entries:
                    lines.append(f"{k} = {v}")
            lines.append("")

        for o in self._objects[obj_idx:]:
            lines.append("[Object]")
            for k, v in o.data["_entries"]:
                lines.append(f"{k} = {v}")
            lines.append("")
        for z in self._zones[zone_idx:]:
            lines.append("[Zone]")
            for k, v in z.data["_entries"]:
                lines.append(f"{k} = {v}")
            lines.append("")

        tmp = self._filepath + ".tmp"
        try:
            Path(tmp).write_text("\n".join(lines), encoding="utf-8")
            shutil.move(tmp, self._filepath)
        except Exception as ex:
            QMessageBox.critical(self, "Fehler beim Speichern", str(ex))
            return

        if reload:
            self.statusBar().showMessage("✔  Gespeichert · Lade neu …")
            self._load(self._filepath, restore=self.view.transform())
            self.browser.highlight_current(self._filepath)
        else:
            self._set_dirty(False)
            self.statusBar().showMessage("✔  Gespeichert")

    def _on_universe_system_moved(self, obj: SolarObject):
        """Callback wenn ein System auf der Universumskarte verschoben wird."""
        self._set_dirty(True)
        x = obj.pos().x() / self._scale
        y = obj.pos().y() / self._scale
        self.statusBar().showMessage(f"System {obj.nickname} → ({x:.0f}, {y:.0f})")
        self._update_universe_lines()
        # Position im Editor aktualisieren
        if self._uni_selected_nick and self._uni_selected_nick.lower() == obj.nickname.lower():
            self._show_uni_system_editor(obj.nickname)

    def _show_uni_system_editor(self, nickname: str):
        """Zeigt den universe.ini-Eintrag für das gewählte System im Editor."""
        self._uni_selected_nick = nickname
        nick_lower = nickname.lower()

        # Eintrag aus den geparsed sections finden
        text_lines = []
        for sec_name, entries in self._uni_sections:
            if sec_name.lower() == "system":
                sec_nick = None
                for k, v in entries:
                    if k.lower() == "nickname":
                        sec_nick = v.lower()
                        break
                if sec_nick == nick_lower:
                    for k, v in entries:
                        # Pos aus aktueller Szene nehmen
                        if k.lower() == "pos" and self._selected and hasattr(self._selected, "sys_path"):
                            sx = self._selected.pos().x() / self._scale
                            sy = self._selected.pos().y() / self._scale
                            text_lines.append(f"pos = {sx:.0f}, {sy:.0f}")
                        else:
                            text_lines.append(f"{k} = {v}")
                    break

        self.uni_sys_lbl.setText(f"🌐 {nickname}")
        self.uni_editor.setPlainText("\n".join(text_lines))
        if hasattr(self, "left_stack"):
            self.left_stack.setCurrentWidget(self.left_uni_panel)

    def _apply_uni_system_edit(self):
        """Speichert den bearbeiteten universe.ini-Eintrag."""
        if not self._uni_selected_nick or not self._uni_ini_path:
            return

        nick_lower = self._uni_selected_nick.lower()
        new_text = self.uni_editor.toPlainText()

        # Neue Einträge parsen
        new_entries: list[tuple[str, str]] = []
        for line in new_text.splitlines():
            line = line.strip()
            if "=" in line:
                k, _, v = line.partition("=")
                new_entries.append((k.strip(), v.strip()))

        if not new_entries:
            QMessageBox.warning(self, "Fehler", "Keine gültigen Einträge gefunden.")
            return

        # Sektionen aktualisieren
        updated = False
        for i, (sec_name, entries) in enumerate(self._uni_sections):
            if sec_name.lower() == "system":
                sec_nick = None
                for k, v in entries:
                    if k.lower() == "nickname":
                        sec_nick = v.lower()
                        break
                if sec_nick == nick_lower:
                    self._uni_sections[i] = (sec_name, new_entries)
                    updated = True
                    break

        if not updated:
            QMessageBox.warning(self, "Fehler", f"System '{self._uni_selected_nick}' nicht gefunden.")
            return

        # universe.ini neu schreiben
        lines: list[str] = []
        for sec_name, entries in self._uni_sections:
            lines.append(f"[{sec_name}]")
            for k, v in entries:
                lines.append(f"{k} = {v}")
            lines.append("")

        tmp = str(self._uni_ini_path) + ".tmp"
        try:
            Path(tmp).write_text("\n".join(lines), encoding="utf-8")
            shutil.move(tmp, str(self._uni_ini_path))
            self.statusBar().showMessage(f"✔  System '{self._uni_selected_nick}' in universe.ini gespeichert")
        except Exception as ex:
            QMessageBox.critical(self, "Fehler beim Speichern", str(ex))

    def _update_universe_lines(self):
        """Aktualisiert alle Verbindungslinien nach Systemverschiebung."""
        # Aktuelle Positionen der Systeme sammeln
        pos_map: dict[str, tuple[float, float]] = {}
        for obj in self._objects:
            if hasattr(obj, "sys_path"):
                pos_map[obj.nickname.upper()] = (obj.pos().x(), obj.pos().y())
        # Linien aktualisieren
        for key, line_item in self._uni_lines:
            nodes = list(key)
            if len(nodes) != 2:
                continue
            a, b = nodes
            if a in pos_map and b in pos_map:
                ax, ay = pos_map[a]
                bx, by = pos_map[b]
                line_item.setLine(ax, ay, bx, by)

    def _undo_universe_moves(self):
        """Setzt alle Systeme auf ihre Originalpositionen zurück."""
        if not self._uni_original_pos:
            return
        for obj in self._objects:
            if hasattr(obj, "sys_path"):
                key = obj.nickname.upper()
                if key in self._uni_original_pos:
                    ox, oy = self._uni_original_pos[key]
                    obj.setPos(ox, oy)
        self._update_universe_lines()
        self._set_dirty(False)
        self.statusBar().showMessage("↩  Alle Verschiebungen rückgängig gemacht")

    def _save_universe_positions(self):
        """Speichert verschobene System-Positionen zurück in universe.ini."""
        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        if not game_path:
            return
        uni_ini = find_universe_ini(game_path)
        if not uni_ini:
            return

        # Aktuelle Positionen aus der Szene sammeln
        pos_map: dict[str, tuple[float, float]] = {}
        for obj in self._objects:
            if hasattr(obj, "sys_path"):
                x = obj.pos().x() / self._scale
                y = obj.pos().y() / self._scale
                pos_map[obj.nickname.lower()] = (x, y)

        if not pos_map:
            return

        # universe.ini parsen und Positionen aktualisieren
        sections = self._parser.parse(str(uni_ini))
        lines: list[str] = []
        for sec_name, entries in sections:
            lines.append(f"[{sec_name}]")
            if sec_name.lower() == "system":
                nick = None
                for k, v in entries:
                    if k.lower() == "nickname":
                        nick = v.lower()
                        break
                for k, v in entries:
                    if k.lower() == "pos" and nick and nick in pos_map:
                        px, py = pos_map[nick]
                        lines.append(f"pos = {px:.0f}, {py:.0f}")
                    else:
                        lines.append(f"{k} = {v}")
            else:
                for k, v in entries:
                    lines.append(f"{k} = {v}")
            lines.append("")

        tmp = str(uni_ini) + ".tmp"
        try:
            Path(tmp).write_text("\n".join(lines), encoding="utf-8")
            shutil.move(tmp, str(uni_ini))
            self._set_dirty(False)
            self.statusBar().showMessage("✔  Universe-Positionen gespeichert")
        except Exception as ex:
            QMessageBox.critical(self, "Fehler beim Speichern", str(ex))

    @staticmethod
    def _extract_nickname_from_entries(entries) -> str | None:
        for k, v in entries:
            if k.lower() == "nickname":
                return v
        return None

    def _write_snapshot(self, snapshot):
        filepath, sections, objs = snapshot
        lines: list[str] = []
        obj_iter = iter(objs)
        for sec_name, entries in sections:
            lines.append(f"[{sec_name}]")
            if sec_name.lower() == "object":
                try:
                    o = next(obj_iter)
                    for k, v in o.get("_entries", []):
                        lines.append(f"{k} = {v}")
                except StopIteration:
                    for k, v in entries:
                        lines.append(f"{k} = {v}")
            else:
                for k, v in entries:
                    lines.append(f"{k} = {v}")
            lines.append("")
        for o in obj_iter:
            lines.append("[Object]")
            for k, v in o.get("_entries", []):
                lines.append(f"{k} = {v}")
            lines.append("")
        tmp = filepath + ".tmp"
        try:
            Path(tmp).write_text("\n".join(lines), encoding="utf-8")
            shutil.move(tmp, filepath)
        except Exception as ex:
            QMessageBox.critical(self, "Fehler beim Speichern", str(ex))

    def _save_pending_connections(self):
        origin_path = self._pending_snapshots[0][0] if self._pending_snapshots else None
        for snap in list(self._pending_snapshots):
            self._write_snapshot(snap)
        self._pending_snapshots.clear()
        self.save_conn_btn.setVisible(False)
        self.create_conn_btn.setEnabled(True)
        if origin_path and Path(origin_path).exists():
            self._load(origin_path, restore=self.view.transform())
            self.browser.highlight_current(origin_path)
        self._set_dirty(False)
        self._set_placement_mode(False)
        self.statusBar().showMessage("✔  Verbindungen gespeichert und Ansicht aktualisiert")

    # ==================================================================
    #  Dirty-Flag  &  Diverse Toggler
    # ==================================================================
    def _set_dirty(self, d: bool):
        self._dirty = d
        # Im Universe-Modus den Universe-Save-Button aktivieren
        is_universe = self._filepath is None and hasattr(self, '_uni_save_action')
        self.write_btn.setEnabled(bool(self._filepath) and d)
        if is_universe and hasattr(self, 'uni_save_btn'):
            self.uni_save_btn.setEnabled(d)
        t = self.windowTitle()
        if d and not t.startswith("*"):
            self.setWindowTitle("* " + t)
        elif not d and t.startswith("* "):
            self.setWindowTitle(t[2:])

    def _toggle_move(self, checked: bool):
        for obj in self._objects:
            obj.setFlag(QGraphicsItem.ItemIsMovable, checked)
        self.view3d.set_move_mode(checked)
        self.statusBar().showMessage(
            "Move-Modus AN — Linke Maustaste zum Verschieben"
            if checked else "Move-Modus AUS"
        )

    def _toggle_zones(self, checked: bool):
        for z in self._zones:
            z.setVisible(checked)
        self._refresh_3d_scene()

    def _fit(self):
        r = self.view._scene.itemsBoundingRect()
        pad = 20 if self._filepath is None else 80
        self.view.fitInView(r.adjusted(-pad, -pad, pad, pad), Qt.KeepAspectRatio)

    # ==================================================================
    #  Quick-Editor-Optionen & System-Metadaten
    # ==================================================================
    def _populate_quick_editor_options(self, game_path: str | None = None):
        if game_path is None:
            game_path = self.browser.path_edit.text().strip()
        if not game_path:
            return
        base = Path(game_path)

        # Fraktionen
        self.faction_cb.clear()
        iw_file = ci_resolve(base, "DATA/initialworld.ini")
        factions: list[str] = []
        if iw_file and iw_file.exists():
            try:
                secs = self._parser.parse(str(iw_file))
                for name, entries in secs:
                    if name.lower() == "group":
                        for k, v in entries:
                            if k.lower() == "nickname" and v not in factions:
                                factions.append(v)
            except Exception:
                pass
        factions.sort(key=str.lower)
        self.faction_cb.addItems(factions)

        # Loadouts
        self.loadout_cb.clear()
        ld_file = ci_resolve(base, "DATA/SOLAR/loadouts.ini")
        loadouts: list[str] = []
        if ld_file and ld_file.exists():
            try:
                secs = self._parser.parse(str(ld_file))
                for name, entries in secs:
                    if name.lower() == "loadout":
                        for k, v in entries:
                            if k.lower() == "nickname" and v not in loadouts:
                                loadouts.append(v)
            except Exception:
                pass
        loadouts.sort(key=str.lower)
        self.loadout_cb.addItems(loadouts)

        # Archetypen
        self.arch_cb.clear()
        archs: set[str] = set()
        try:
            systems = find_all_systems(game_path, self._parser)
            for s in systems:
                try:
                    secs = self._parser.parse(s["path"])
                except Exception:
                    continue
                for o in self._parser.get_objects(secs):
                    a = o.get("archetype", "")
                    if a:
                        archs.add(a)
        except Exception:
            pass
        for item in sorted(archs, key=str.lower):
            self.arch_cb.addItem(item)

        # Stars
        self._stars = []
        star_file = ci_resolve(base, "DATA/SOLAR/stararch.ini")
        if star_file and star_file.exists():
            try:
                secs = self._parser.parse(str(star_file))
                for name, entries in secs:
                    if name.lower() == "star":
                        for k, v in entries:
                            if k.lower() == "nickname" and v not in self._stars:
                                self._stars.append(v)
            except Exception:
                pass
        self._stars.sort(key=str.lower)
        self._build_archetype_model_index(game_path)

    def _build_archetype_model_index(self, game_path: str):
        if not game_path:
            return
        if self._arch_index_game_path == game_path and self._arch_model_map:
            return
        base = Path(game_path)
        arch_map: dict[str, str] = {}
        arch_files = [
            "DATA/SOLAR/solararch.ini",
            "DATA/SHIPS/shiparch.ini",
            "DATA/EQUIPMENT/stationarch.ini",
            "DATA/EQUIPMENT/asteroidarch.ini",
        ]
        for rel in arch_files:
            ini = ci_resolve(base, rel)
            if not ini or not ini.exists():
                continue
            try:
                secs = self._parser.parse(str(ini))
            except Exception:
                continue
            for _sec_name, entries in secs:
                nickname = da_arch = ""
                for k, v in entries:
                    lk = k.lower()
                    if lk == "nickname":
                        nickname = v.strip()
                    elif lk == "da_archetype":
                        da_arch = v.strip()
                if nickname and da_arch:
                    key = nickname.lower()
                    if key not in arch_map:
                        arch_map[key] = da_arch
        self._arch_model_map = arch_map
        self._arch_index_game_path = game_path

    def _resolve_game_path_case_insensitive(self, game_path: str, rel_path: str) -> Path | None:
        if not game_path or not rel_path:
            return None
        base = Path(game_path)
        hit = ci_resolve(base, rel_path)
        if hit:
            return hit
        data_dir = ci_find(base, "DATA")
        if data_dir and data_dir.is_dir():
            hit = ci_resolve(data_dir, rel_path)
            if hit:
                return hit
        return None

    def _resolve_model_for_archetype(self, archetype: str, game_path: str) -> tuple[Path | None, str | None]:
        if not archetype:
            return None, None
        self._build_archetype_model_index(game_path)
        da_arch = self._arch_model_map.get(archetype.lower())
        if not da_arch:
            return None, None
        model_path = self._resolve_game_path_case_insensitive(game_path, da_arch)
        return model_path, da_arch

    def _find_preview_mesh_candidate(self, model_path: Path) -> Path | None:
        supported_exts = [".obj", ".stl", ".ply", ".gltf", ".glb", ".dae", ".fbx", ".3ds"]
        if model_path.suffix.lower() in supported_exts and model_path.exists():
            return model_path
        for ext in supported_exts:
            cand = model_path.with_suffix(ext)
            if cand.exists():
                return cand
        return None

    @staticmethod
    def _primitive_for_model(obj, model_path: Path) -> str:
        ext = model_path.suffix.lower()
        archetype = obj.data.get("archetype", "").lower()
        if ext == ".sph" or "sun" in archetype or "planet" in archetype:
            return "sphere"
        return "cube"

    # ==================================================================
    #  3D-Preview / Modell öffnen
    # ==================================================================
    def _show_selected_3d_preview(self):
        obj = self._selected
        if not obj or isinstance(obj, ZoneItem):
            QMessageBox.information(self, "3D Preview", "Bitte zuerst ein Objekt auswählen.")
            return
        archetype = obj.data.get("archetype", "").strip()
        if not archetype:
            QMessageBox.warning(self, "3D Preview", "Dieses Objekt hat keinen Archetype-Eintrag.")
            return
        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        if not game_path:
            QMessageBox.warning(self, "3D Preview", "Kein Spielpfad konfiguriert.")
            return
        model_path, da_arch = self._resolve_model_for_archetype(archetype, game_path)
        if not da_arch:
            QMessageBox.warning(self, "3D Preview",
                                f"Für Archetype '{archetype}' wurde kein DA_archetype gefunden.")
            return
        if not model_path:
            QMessageBox.warning(self, "3D Preview",
                                f"DA_archetype gefunden, Datei aber nicht aufgelöst:\n{da_arch}")
            return
        preview_mesh = self._find_preview_mesh_candidate(model_path)
        if not QT3D_AVAILABLE:
            QMessageBox.information(
                self, "3D Preview",
                f"Qt3D ist nicht verfügbar.\n\nArchetype: {archetype}\n"
                f"DA_archetype: {da_arch}\nDatei: {model_path}",
            )
            return
        if not preview_mesh:
            prim = self._primitive_for_model(obj, model_path)
            dlg = MeshPreviewDialog(
                self, None, f"3D Preview — {obj.nickname} (Fallback)",
                primitive=prim,
                info_text=f"Original-Datei ist kein renderbares Qt3D-Mesh.\n"
                          f"Archetype: {archetype}\nDA_archetype: {da_arch}\n"
                          f"Datei: {model_path}\nFallback: {prim}",
            )
            dlg.exec()
            return
        MeshPreviewDialog(self, preview_mesh, f"3D Preview — {obj.nickname}").exec()

    def _open_model_file(self):
        start_dir = self.browser.path_edit.text().strip() or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self, "Modell öffnen", start_dir,
            "Freelancer/3D Dateien (*.cmp *.3db *.sph *.obj *.stl *.ply "
            "*.gltf *.glb *.dae *.fbx *.3ds);;Alle Dateien (*)",
        )
        if not path:
            return
        model_path = Path(path)
        preview_mesh = self._find_preview_mesh_candidate(model_path)
        if not QT3D_AVAILABLE:
            QMessageBox.information(self, "3D Preview", f"Qt3D ist nicht verfügbar.\n\nDatei: {model_path}")
            return
        if preview_mesh:
            MeshPreviewDialog(self, preview_mesh, f"3D Preview — {model_path.name}").exec()
            return
        prim = "sphere" if model_path.suffix.lower() == ".sph" else "cube"
        MeshPreviewDialog(
            self, None, f"3D Preview — {model_path.name} (Fallback)",
            primitive=prim,
            info_text=f"Datei geöffnet, kein renderbares Qt3D-Mesh.\nDatei: {model_path}\n"
                      f"Format: {model_path.suffix.lower()}\nFallback: {prim}",
        ).exec()

    # ==================================================================
    #  System-Metadaten  (Musik, Farben, Background)
    # ==================================================================
    def _get_section_value(self, section: str, key: str) -> str:
        for sec_name, entries in self._sections:
            if sec_name.lower() == section.lower():
                for k, v in entries:
                    if k.lower() == key.lower():
                        return v
        return ""

    def _set_section_value(self, section: str, key: str, value: str):
        for idx, (sec_name, entries) in enumerate(self._sections):
            if sec_name.lower() == section.lower():
                for j, (k, v) in enumerate(entries):
                    if k.lower() == key.lower():
                        entries[j] = (k, value)
                        self._sections[idx] = (sec_name, entries)
                        return
                entries.append((key, value))
                self._sections[idx] = (sec_name, entries)
                return
        self._sections.append((section, [(key, value)]))

    def _on_system_field_changed(self, key: str):
        if self._sys_fields_busy:
            return
        val = getattr(self, f"{key}_cb").currentText()
        self._set_section_value("System", key, val)
        self._set_dirty(True)

    def _on_music_field_changed(self, key: str, value: str):
        if self._sys_fields_busy:
            return
        self._set_section_value("Music", key, value)
        self._set_dirty(True)

    def _on_systeminfo_field_changed(self, key: str, value: str):
        if self._sys_fields_busy:
            return
        self._set_section_value("SystemInfo", key, value)
        self._set_dirty(True)

    def _on_background_field_changed(self, key: str, value: str):
        if self._sys_fields_busy:
            return
        self._set_section_value("Background", key, value)
        self._set_dirty(True)

    def _pick_space_color(self):
        col = QColorDialog.getColor(parent=self)
        if not col.isValid():
            return
        rgb = f"{col.red()}, {col.green()}, {col.blue()}"
        self.space_color_lbl.setText(rgb)
        self._set_section_value("SystemInfo", "space_color", rgb)
        self._set_dirty(True)

    def _pick_ambient_color(self):
        col = QColorDialog.getColor(parent=self)
        if not col.isValid():
            return
        rgb = f"{col.red()}, {col.green()}, {col.blue()}"
        self.ambient_color_lbl.setText(rgb)
        self._set_section_value("Ambient", "color", rgb)
        self._set_dirty(True)

    def _populate_system_options(self):
        game_path = self._cfg.get("game_path", "")
        self._sys_fields_busy = True
        try:
            music_vals = {"space": set(), "danger": set(), "battle": set()}
            bg_vals = {"basic_stars": set(), "complex_stars": set(), "nebulae": set()}
            if game_path:
                try:
                    for s in find_all_systems(game_path, self._parser):
                        try:
                            secs = self._parser.parse(s["path"])
                        except Exception:
                            continue
                        for sec_name, entries in secs:
                            low = sec_name.lower()
                            if low == "music":
                                for k, v in entries:
                                    lk = k.lower()
                                    if lk in music_vals and v:
                                        music_vals[lk].add(v)
                            elif low == "background":
                                for k, v in entries:
                                    lk = k.lower()
                                    if lk in bg_vals and v:
                                        bg_vals[lk].add(v)
                except Exception:
                    pass
            self.music_space_cb.clear()
            self.music_space_cb.addItems(sorted(music_vals["space"], key=str.lower))
            self.music_danger_cb.clear()
            self.music_danger_cb.addItems(sorted(music_vals["danger"], key=str.lower))
            self.music_battle_cb.clear()
            self.music_battle_cb.addItems(sorted(music_vals["battle"], key=str.lower))
            self.bg_basic_cb.clear()
            self.bg_basic_cb.addItems(sorted(bg_vals["basic_stars"], key=str.lower))
            self.bg_complex_cb.clear()
            self.bg_complex_cb.addItems(sorted(bg_vals["complex_stars"], key=str.lower))
            self.bg_nebulae_cb.clear()
            self.bg_nebulae_cb.addItems(sorted(bg_vals["nebulae"], key=str.lower))

            # Local Faction
            self.local_faction_cb.clear()
            factions: list[str] = []
            if game_path:
                iw_file = ci_resolve(Path(game_path), "DATA/initialworld.ini")
                if iw_file and iw_file.exists():
                    try:
                        for sec_name, entries in self._parser.parse(str(iw_file)):
                            if sec_name.lower() == "group":
                                for k, v in entries:
                                    if k.lower() == "nickname" and v not in factions:
                                        factions.append(v)
                    except Exception:
                        pass
            factions.sort(key=str.lower)
            self.local_faction_cb.addItems(factions)
        finally:
            self._sys_fields_busy = False

    def _refresh_system_fields(self):
        self._sys_fields_busy = True
        try:
            self.music_space_cb.setCurrentText(self._get_section_value("Music", "space"))
            self.music_danger_cb.setCurrentText(self._get_section_value("Music", "danger"))
            self.music_battle_cb.setCurrentText(self._get_section_value("Music", "battle"))
            self.space_color_lbl.setText(self._get_section_value("SystemInfo", "space_color"))
            self.local_faction_cb.setCurrentText(self._get_section_value("SystemInfo", "local_faction"))
            self.ambient_color_lbl.setText(self._get_section_value("Ambient", "color"))
            self.dust_cb.setCurrentText(self._get_section_value("System", "dust"))
            self.bg_basic_cb.setCurrentText(self._get_section_value("Background", "basic_stars"))
            self.bg_complex_cb.setCurrentText(self._get_section_value("Background", "complex_stars"))
            self.bg_nebulae_cb.setCurrentText(self._get_section_value("Background", "nebulae"))
        finally:
            self._sys_fields_busy = False

    def _search_nickname(self):
        term = self.search_edit.text().strip().lower()
        if not term:
            return
        for o in self._objects:
            if o.nickname.lower() == term:
                self.view.centerOn(o)
                self._select(o)
                return
        QMessageBox.information(self, "Nicht gefunden", f"Kein Objekt mit Nickname '{term}'")
