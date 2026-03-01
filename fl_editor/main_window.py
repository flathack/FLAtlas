"""Hauptfenster des Freelancer System Editors.

Orchestriert alle Untermodule (Browser, 2D/3D-Ansicht, Dialoge) und
verwaltet den Editor-Zustand (Laden, Speichern, Auswahl, Bearbeitung).
"""

from __future__ import annotations

import math
import re
import shutil
import hashlib
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QDoubleSpinBox,
    QGraphicsEllipseItem,
    QGraphicsRectItem,
    QGraphicsItem,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
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
    QIcon,
    QKeySequence,
    QPen,
    QPixmap,
    QShortcut,
    QTransform,
)

from .config import Config
from .i18n import tr, set_language, get_language
from .themes import apply_theme, THEME_NAMES, get_palette, get_stylesheet, current_theme, set_theme, palette_from_accent, PALETTES
from .parser import FLParser, find_universe_ini, find_all_systems
from .path_utils import ci_find, ci_resolve, parse_position, format_position
from .models import ZoneItem, SolarObject, UniverseSystem
from .browser import SystemBrowser
from .view_2d import SystemView
from .view_3d import System3DView
from .qt3d_compat import QT3D_AVAILABLE
from .dialogs import (
    BaseCreationDialog,
    BaseEditDialog,
    BuoyDialog,
    CategoryObjectDialog,
    ConnectionDialog,
    DockingRingDialog,
    ExclusionZoneDialog,
    GateInfoDialog,
    LightSourceDialog,
    MeshPreviewDialog,
    ObjectCreationDialog,
    SimpleZoneDialog,
    SolarCreationDialog,
    SystemCreationDialog,
    SystemSettingsDialog,
    TradeLaneDialog,
    TradeLaneEditDialog,
    ZoneCreationDialog,
    ZonePopulationDialog,
)
from .exclusion_zones import (
    build_exclusion_zone_entries,
    generate_exclusion_nickname,
    is_field_zone_nickname,
    patch_field_ini_remove_exclusion,
    patch_field_ini_exclusion_section,
    patch_system_ini_for_exclusion,
)


# ══════════════════════════════════════════════════════════════════════
#  Legend-Farben (keys verweisen auf translations.json)
# ══════════════════════════════════════════════════════════════════════
_LEGEND_KEYS = [
    ("#ffd728", "legend.star"),
    ("#3c82dc", "legend.planet"),
    ("#50d264", "legend.station"),
    ("#d25ad2", "legend.jumpgate"),
    ("#966e46", "legend.asteroid"),
    ("#bebebe", "legend.other"),
    ("#0000ff", "legend.gate_conn"),
    ("#ffff00", "legend.hole_conn"),
    ("", ""),
    ("#dc3232", "legend.zone_death"),
    ("#9650dc", "legend.zone_nebula"),
    ("#b4823c", "legend.zone_debris"),
    ("#3cb4dc", "legend.zone_tradelane"),
    ("#50a0c8", "legend.zone_other"),
]


class MainWindow(QMainWindow):
    """Hauptfenster – verbindet Browser, Karten, Editor und Dialoge."""

    # ==================================================================
    #  Initialisierung
    # ==================================================================
    # Pfad zum images-Verzeichnis
    _ICON_DIR = Path(__file__).resolve().parent / "images"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FL Atlas")
        self.resize(1600, 900)

        # Fenster-Icon setzen
        icon = QIcon()
        for size in (16, 24, 32, 48, 64, 128, 256):
            icon.addFile(str(self._ICON_DIR / f"FLAtlas-Logo-{size}.png"))
        self.setWindowIcon(icon)

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
        self._cached_music_opts: dict[str, list[str]] = {"space": [], "danger": [], "battle": []}
        self._cached_bg_opts: dict[str, list[str]] = {"basic_stars": [], "complex_stars": [], "nebulae": []}
        self._cached_factions: list[str] = []
        self._cached_dust_opts: list[str] = []

        # Pending-Aktionen
        self._pending_zone: dict | None = None
        self._pending_simple_zone: dict | None = None
        self._pending_exclusion_zone: dict | None = None
        self._pending_light_source: dict | None = None
        self._pending_template_object: dict | None = None
        self._pending_buoy: dict | None = None
        self._pending_create: dict | None = None
        self._pending_new_object = False
        self._pending_tradelane: dict | None = None
        self._pending_tl_reposition: dict | None = None
        self._tl_rubber_line = None  # QGraphicsLineItem für Vorschau
        self._zone_rubber_ellipse = None  # QGraphicsEllipseItem für Zonen-Vorschau
        self._zone_rubber_origin: QPointF | None = None  # Startpunkt für Zonen-Sizing
        self._pending_conn: dict | None = None
        self._pending_snapshots: list = []
        self._pending_new_system: dict | None = None
        self._pending_base: dict | None = None
        self._pending_dock_ring: dict | None = None
        self._dock_ring_orbit_circle = None
        self._dock_ring_preview_dot = None
        self._measure_start: QPointF | None = None
        self._measure_line = None
        self._measure_label = None
        self._multi_selected: list[SolarObject | ZoneItem] = []
        self._change_log_entries: list[str] = []
        self._status_log_entries: list[str] = []
        self._change_snapshots: list[dict] = []
        self._last_snapshot_fp: str = ""
        self._history_restore_in_progress = False
        self._undo_actions: list[dict] = list(self._cfg.get("undo_actions", []))
        self._zoom_slider_busy = False

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
        self._viewer_text_visible = True
        self._flight_lock_active = False
        self._flight_prev_left_visible = True
        self._flight_prev_right_visible = True
        self._star_bg_pixmap = QPixmap(str(self._ICON_DIR / "star-background.png"))
        if self._star_bg_pixmap.isNull():
            self._star_bg_pixmap = None

        # Sprache aus Config laden
        saved_lang = self._cfg.get("language", "de")
        set_language(saved_lang)

        self._build_ui()
        apply_theme(self)     # Theme aus Config laden und anwenden

        # Gespeicherten Spielpfad laden
        saved = self._cfg.get("game_path", "")
        if saved:
            self._load_universe(saved)

    def _apply_scene_wallpaper(self, fallback: QColor):
        self.view.set_background_pixmap(self._star_bg_pixmap, fallback)
        if self._star_bg_pixmap is not None:
            self.view._scene.setBackgroundBrush(QBrush(self._star_bg_pixmap))
        else:
            self.view._scene.setBackgroundBrush(QBrush(fallback))

    # ==================================================================
    #  UI-Aufbau
    # ==================================================================
    def _build_ui(self):
        # ── Toolbar ──────────────────────────────────────────────────
        tb = self.addToolBar("Main")
        tb.setMovable(False)

        # ── Einheitliches Button-Stylesheet (theme-aware) ────────────
        self._tb_btn_style = self._make_tb_btn_style()

        self._universe_act = QAction(tr("action.universe"), self)
        self._universe_act.triggered.connect(self._load_universe_action)
        tb.addAction(self._universe_act)

        self._model_act = QAction(tr("action.open_3d"), self)
        self._model_act.triggered.connect(self._open_model_file)
        tb.addAction(self._model_act)

        tb.addSeparator()

        self.move_cb = QCheckBox(tr("cb.move_objects"))
        self.move_cb.setToolTip(tr("tip.move_objects"))
        self.move_cb.toggled.connect(self._toggle_move)
        tb.addWidget(self.move_cb)

        self.zone_cb = QCheckBox(tr("cb.toggle_zones"))
        self.zone_cb.setChecked(True)
        self.zone_cb.setToolTip(tr("tip.toggle_zones"))
        self.zone_cb.toggled.connect(self._toggle_zones)
        tb.addWidget(self.zone_cb)

        self.viewer_text_cb = QCheckBox(tr("cb.toggle_viewer_text"))
        self.viewer_text_cb.setChecked(True)
        self.viewer_text_cb.setToolTip(tr("tip.toggle_viewer_text"))
        self.viewer_text_cb.toggled.connect(self._toggle_viewer_text)
        tb.addWidget(self.viewer_text_cb)

        self.view3d_switch = QCheckBox("3D")
        self.view3d_switch.setToolTip(tr("tip.3d_switch"))
        self.view3d_switch.toggled.connect(self._toggle_3d_view)
        tb.addWidget(self.view3d_switch)

        self._zoom_lbl = QLabel("Zoom")
        tb.addWidget(self._zoom_lbl)
        self._zoom_slider = QSlider(Qt.Horizontal)
        self._zoom_slider.setRange(10, 450)
        self._zoom_slider.setValue(100)
        self._zoom_slider.setFixedWidth(130)
        self._zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        tb.addWidget(self._zoom_slider)
        self._zoom_lbl.setVisible(False)
        self._zoom_slider.setVisible(False)

        self.flight_mode_btn = QPushButton("Flight Mode")
        self.flight_mode_btn.setCheckable(True)
        self.flight_mode_btn.setToolTip("Toggle freelancer-style flight controls in 3D view")
        self.flight_mode_btn.setStyleSheet(self._tb_btn_style)
        self.flight_mode_btn.clicked.connect(self._on_flight_mode_toggled)
        self.flight_mode_btn.setVisible(True)
        tb.addWidget(self.flight_mode_btn)

        self.new_system_btn = QPushButton(tr("btn.new_system"))
        self.new_system_btn.setToolTip(tr("tip.new_system"))
        self.new_system_btn.setStyleSheet(self._tb_btn_style)
        self.new_system_btn.clicked.connect(self._start_new_system)
        self._new_system_action = tb.addWidget(self.new_system_btn)
        self._new_system_action.setVisible(False)

        self.uni_save_btn = QPushButton(tr("btn.save"))
        self.uni_save_btn.setToolTip(tr("tip.save_universe"))
        self.uni_save_btn.setStyleSheet(self._tb_btn_style)
        self.uni_save_btn.clicked.connect(lambda: self._write_to_file(False))
        self._uni_save_action = tb.addWidget(self.uni_save_btn)
        self._uni_save_action.setVisible(False)

        self.uni_undo_btn = QPushButton(tr("btn.undo"))
        self.uni_undo_btn.setToolTip(tr("tip.undo"))
        self.uni_undo_btn.setStyleSheet(self._tb_btn_style)
        self.uni_undo_btn.clicked.connect(self._undo_universe_moves)
        self._uni_undo_action = tb.addWidget(self.uni_undo_btn)
        self._uni_undo_action.setVisible(False)

        self.uni_delete_btn = QPushButton(tr("btn.delete_system"))
        self.uni_delete_btn.setStyleSheet(self._tb_btn_style)
        self.uni_delete_btn.clicked.connect(self._delete_selected_universe_system)
        self._uni_delete_action = tb.addWidget(self.uni_delete_btn)
        self._uni_delete_action.setVisible(False)
        self.uni_delete_btn.setEnabled(False)

        self.ids_scan_btn = QPushButton(tr("btn.missing_ids"))
        self.ids_scan_btn.setToolTip(tr("tip.missing_ids"))
        self.ids_scan_btn.setStyleSheet(self._tb_btn_style)
        self.ids_scan_btn.clicked.connect(self._scan_missing_ids)
        self._ids_scan_action = tb.addWidget(self.ids_scan_btn)
        self._ids_scan_action.setVisible(False)

        self.ids_import_btn = QPushButton(tr("btn.import_ids"))
        self.ids_import_btn.setToolTip(tr("tip.import_ids"))
        self.ids_import_btn.setStyleSheet(self._tb_btn_style)
        self.ids_import_btn.clicked.connect(self._import_ids_from_csv)
        self._ids_import_action = tb.addWidget(self.ids_import_btn)
        self._ids_import_action.setVisible(False)

        tb.addSeparator()
        self.mode_lbl = QLabel("")
        self.mode_lbl.setStyleSheet("color:#f0c040; font-weight:bold; padding:0 8px;")
        tb.addWidget(self.mode_lbl)

        # ── Spacer → Theme / Sprache / Über ganz rechts ─────────────
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy())
        from PySide6.QtWidgets import QSizePolicy, QToolButton, QMenu
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

        # ── Theme-Dropdown ───────────────────────────────────────────
        self._theme_btn = QToolButton()
        self._theme_btn.setText(tr("theme.label"))
        self._theme_btn.setPopupMode(QToolButton.InstantPopup)
        self._theme_btn.setStyleSheet(self._tb_btn_style)
        self._theme_menu = QMenu(self._theme_btn)
        self._theme_actions: dict[str, QAction] = {}
        for tname in THEME_NAMES:
            label = tr(f"theme.{tname}")
            act = QAction(label, self)
            act.setCheckable(True)
            act.triggered.connect(lambda checked, n=tname: self._on_theme_changed(n))
            self._theme_menu.addAction(act)
            self._theme_actions[tname] = act
        self._theme_actions[current_theme()].setChecked(True)
        self._theme_btn.setMenu(self._theme_menu)
        tb.addWidget(self._theme_btn)

        # ── Language-Toggle ──────────────────────────────────────────
        self._lang_btn = QPushButton(tr("lang.switch"))
        self._lang_btn.setToolTip("Deutsch ↔ English")
        self._lang_btn.setStyleSheet(self._tb_btn_style)
        self._lang_btn.setFixedWidth(42)
        self._lang_btn.clicked.connect(self._on_language_toggled)
        tb.addWidget(self._lang_btn)

        # ── About-Dropdown ───────────────────────────────────────────
        self._about_btn = QToolButton()
        self._about_btn.setText(tr("action.about"))
        self._about_btn.setPopupMode(QToolButton.InstantPopup)
        self._about_btn.setStyleSheet(self._tb_btn_style)
        about_menu = QMenu(self._about_btn)
        self._help_act = QAction(tr("action.help"), self)
        self._help_act.triggered.connect(self._show_help)
        about_menu.addAction(self._help_act)
        self._about_act = QAction(tr("action.about_app"), self)
        self._about_act.triggered.connect(self._show_about)
        about_menu.addAction(self._about_act)
        self._about_btn.setMenu(about_menu)
        tb.addWidget(self._about_btn)

        QShortcut(QKeySequence("Escape"), self).activated.connect(self._cancel_pending_actions)
        QShortcut(QKeySequence(Qt.Key_Delete), self).activated.connect(self._delete_object)

        # ── Splitter: Links | Mitte | Rechts ────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        self._build_left_panel(splitter)
        self._build_center_panel(splitter)
        self._build_right_panel(splitter)
        splitter.setSizes([220, 1060, 320])

        # ── Zentralwidget mit hervorgehobener Statusanzeige ──────────
        central = QWidget()
        cl = QVBoxLayout(central)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addWidget(splitter)
        self._build_legend(cl)
        self.setCentralWidget(central)
        self._build_flight_sidebar()
        self.statusBar().messageChanged.connect(self._on_status_message_changed)
        self.statusBar().showMessage(tr("status.ready"))

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

        self._back_btn = QPushButton(tr("btn.back_to_list"))
        self._back_btn.clicked.connect(lambda: self.left_stack.setCurrentWidget(self.browser))
        self._back_btn.setVisible(False)

        self._obj_editor_grp = QGroupBox(tr("grp.object_editor"))
        g = self._obj_editor_grp
        gl = QVBoxLayout(g)
        self.editor = QTextEdit()
        self.editor.setVisible(True)
        gl.addWidget(self.editor)

        # Zone-Link-Editor
        self.zone_link_lbl = QLabel(tr("lbl.linked_section"))
        self.zone_link_lbl.setVisible(False)
        gl.addWidget(self.zone_link_lbl)
        self.zone_link_editor = QTextEdit()
        self.zone_link_editor.setVisible(False)
        gl.addWidget(self.zone_link_editor)
        self.zone_file_lbl = QLabel(tr("lbl.zone_file"))
        self.zone_file_lbl.setVisible(False)
        gl.addWidget(self.zone_file_lbl)
        self.zone_file_editor = QTextEdit()
        self.zone_file_editor.setVisible(False)
        gl.addWidget(self.zone_file_editor)

        rot_grp = QGroupBox(tr("grp.rotation_xyz"))
        self._rot_grp = rot_grp
        rgl = QVBoxLayout(rot_grp)
        rgl.setContentsMargins(6, 6, 6, 6)
        rgl.setSpacing(4)

        def _rot_row(axis_name: str, axis_idx: int):
            row = QWidget()
            row_l = QHBoxLayout(row)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.setSpacing(4)
            row_l.addWidget(QLabel(axis_name), 1)
            btn_l = QPushButton("↺ -15°")
            btn_l.clicked.connect(lambda: self._rotate_selected_object(-15.0, axis=axis_idx))
            row_l.addWidget(btn_l)
            btn_r = QPushButton("↻ +15°")
            btn_r.clicked.connect(lambda: self._rotate_selected_object(15.0, axis=axis_idx))
            row_l.addWidget(btn_r)
            return row

        rgl.addWidget(_rot_row("X", 0))
        rgl.addWidget(_rot_row("Y", 1))
        rgl.addWidget(_rot_row("Z", 2))
        gl.addWidget(rot_grp)

        self._change_log_grp = QGroupBox(tr("grp.change_log"))
        clg = QVBoxLayout(self._change_log_grp)
        clg.setContentsMargins(6, 6, 6, 6)
        clg.setSpacing(4)
        crow = QHBoxLayout()
        crow.setContentsMargins(0, 0, 0, 0)
        crow.addStretch()
        self._action_history_btn = QPushButton("⋯")
        self._action_history_btn.setFixedWidth(28)
        self._action_history_btn.setToolTip(tr("tip.action_history"))
        self._action_history_btn.clicked.connect(self._open_action_history_dialog)
        crow.addWidget(self._action_history_btn)
        self._change_undo_btn = QPushButton("↶")
        self._change_undo_btn.setFixedWidth(28)
        self._change_undo_btn.setToolTip("Undo letzte Änderung (inkl. persistenter Aktionen)")
        self._change_undo_btn.clicked.connect(self._undo_last_change_snapshot)
        self._change_undo_btn.setEnabled(bool(self._undo_actions))
        crow.addWidget(self._change_undo_btn)
        clg.addLayout(crow)
        self.change_log_view = QTextEdit()
        self.change_log_view.setReadOnly(True)
        self.change_log_view.setMinimumHeight(110)
        self.change_log_view.setMaximumHeight(130)
        clg.addWidget(self.change_log_view)
        gl.addWidget(self._change_log_grp)

        lipl.addWidget(g)
        lipl.addStretch()

        # Buttons
        btn_row = QWidget()
        btn_layout = QVBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(4)

        self.edit_obj_btn = QPushButton(tr("btn.edit_object"))
        self.edit_obj_btn.setEnabled(False)
        self.edit_obj_btn.clicked.connect(self._start_object_edit)
        btn_layout.addWidget(self.edit_obj_btn)

        self.apply_btn = QPushButton(tr("btn.apply_changes"))
        self.apply_btn.setToolTip(tr("tip.editor_apply"))
        self.apply_btn.clicked.connect(self._apply)
        self.apply_btn.setEnabled(False)
        self.apply_btn.setVisible(True)
        btn_layout.addWidget(self.apply_btn)

        self.delete_btn = QPushButton(tr("btn.delete_object"))
        self.delete_btn.setToolTip(tr("tip.delete_object"))
        self.delete_btn.clicked.connect(self._delete_object)
        self.delete_btn.setEnabled(False)
        btn_layout.addWidget(self.delete_btn)

        self.preview3d_btn = QPushButton(tr("btn.3d_preview"))
        self.preview3d_btn.setToolTip(tr("tip.3d_preview"))
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

        self._uni_back_btn = QPushButton(tr("btn.back_to_list"))
        self._uni_back_btn.clicked.connect(lambda: self.left_stack.setCurrentWidget(self.browser))
        self._uni_back_btn.setVisible(False)

        self.uni_sys_lbl = QLabel(tr("lbl.system"))
        self.uni_sys_lbl.setStyleSheet("color:#99aaff; font-weight:bold; font-size:13px;")
        upl.addWidget(self.uni_sys_lbl)

        self._uni_entry_grp = QGroupBox(tr("grp.universe_entry"))
        ug = self._uni_entry_grp
        ugl = QVBoxLayout(ug)
        self.uni_editor = QTextEdit()
        self.uni_editor.setMinimumHeight(180)
        ugl.addWidget(self.uni_editor)
        upl.addWidget(ug)

        self.uni_apply_btn = QPushButton(tr("btn.save_uni_changes"))
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
        self._apply_scene_wallpaper(QColor(6, 6, 18))
        self.view.zoom_factor_changed.connect(self._sync_zoom_slider_from_view)
        self.view.object_selected.connect(self._select)
        self.view.zone_clicked.connect(self._select_zone)
        self.view.item_clicked.connect(self._on_2d_item_clicked)
        self.view.background_clicked.connect(self._on_background_click)
        self.view.system_double_clicked.connect(self._load_from_browser)
        self.view.context_menu_requested.connect(self._on_view_context_menu)

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

        self.name_lbl = QLabel(tr("lbl.no_object"))
        self.name_lbl.setStyleSheet("font-weight:bold; font-size:12pt;")
        rl.addWidget(self.name_lbl)

        # Quick-Editor (versteckt)
        self._build_quick_editor(rl)
        # Erstellen-Buttons
        self._build_creation_group(rl)
        # Bearbeiten (Objekt-Dropdown + Tradelane)
        self._build_editing_group(rl)
        # System-Metadaten
        self._build_system_info_group(rl)

        self.info_lbl = QLabel(tr("lbl.no_file"))
        self.info_lbl.setWordWrap(True)
        rl.addWidget(self.info_lbl)

        self.write_btn = QPushButton(tr("btn.write_to_file"))
        self.write_btn.setToolTip(tr("tip.write_to_file"))
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

    def _on_zoom_slider_changed(self, value: int):
        if self._zoom_slider_busy:
            return
        if not hasattr(self, "view") or self._filepath is None:
            return
        self.view.set_zoom_factor(float(value) / 100.0)

    def _sync_zoom_slider_from_view(self, zoom_factor: float):
        if not hasattr(self, "_zoom_slider"):
            return
        self._zoom_slider_busy = True
        self._zoom_slider.setValue(max(self._zoom_slider.minimum(), min(self._zoom_slider.maximum(), int(round(float(zoom_factor) * 100.0)))))
        self._zoom_slider_busy = False

    def _set_system_zoom_controls_visible(self, visible: bool):
        if hasattr(self, "_zoom_lbl"):
            self._zoom_lbl.setVisible(bool(visible))
        if hasattr(self, "_zoom_slider"):
            self._zoom_slider.setVisible(bool(visible))

    def _build_editing_group(self, layout: QVBoxLayout):
        self._edit_grp = QGroupBox(tr("grp.editing"))
        egl = QVBoxLayout(self._edit_grp)
        egl.setSpacing(4)

        # Objekt-/Zonen-Dropdown
        obj_row = QWidget()
        obj_row_l = QHBoxLayout(obj_row)
        obj_row_l.setContentsMargins(0, 0, 0, 0)
        obj_row_l.setSpacing(4)
        self.obj_combo = QComboBox()
        self.obj_combo.setToolTip(tr("tip.obj_combo"))
        self.obj_combo.currentIndexChanged.connect(self._on_obj_combo_changed)
        obj_row_l.addWidget(self.obj_combo, 1)
        self.obj_jump_btn = QPushButton(tr("btn.jump"))
        self.obj_jump_btn.setToolTip(tr("tip.jump_to"))
        self.obj_jump_btn.clicked.connect(self._jump_to_selected_from_combo)
        obj_row_l.addWidget(self.obj_jump_btn)
        egl.addWidget(obj_row)

        # Tradelane bearbeiten
        self.edit_tradelane_btn = QPushButton(tr("edit.tradelane"))
        self.edit_tradelane_btn.setToolTip(tr("tip.edit_tradelane"))
        self.edit_tradelane_btn.clicked.connect(self._edit_tradelane)
        egl.addWidget(self.edit_tradelane_btn)

        # Zone Population bearbeiten
        self.edit_zone_pop_btn = QPushButton(tr("edit.zone_pop"))
        self.edit_zone_pop_btn.setToolTip(tr("tip.edit_zone_pop"))
        self.edit_zone_pop_btn.clicked.connect(self._edit_zone_population)
        egl.addWidget(self.edit_zone_pop_btn)
        self.add_exclusion_btn = QPushButton(tr("edit.add_exclusion"))
        self.add_exclusion_btn.setToolTip(tr("tip.add_exclusion"))
        self.add_exclusion_btn.clicked.connect(self._start_exclusion_zone_creation)
        self.add_exclusion_btn.setEnabled(False)
        egl.addWidget(self.add_exclusion_btn)

        # Base bearbeiten
        self.edit_base_btn = QPushButton(tr("edit.base"))
        self.edit_base_btn.setToolTip(tr("tip.edit_base"))
        self.edit_base_btn.clicked.connect(self._edit_base)
        egl.addWidget(self.edit_base_btn)

        layout.addWidget(self._edit_grp)

    def _build_obj_combo(self, layout: QVBoxLayout):
        """Legacy-Stub – Combo wird jetzt in _build_editing_group erstellt."""
        pass

    def _build_quick_editor(self, layout: QVBoxLayout):
        self._quick_grp = QGroupBox(tr("grp.quick_editor"))
        ql = QVBoxLayout(self._quick_grp)
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

        _combo_row(tr("lbl.archetype"), "arch_cb",
                   lambda t: self._update_editor_field("archetype", t))
        _combo_row(tr("lbl.loadout"), "loadout_cb",
                   lambda t: self._update_editor_field("loadout", t))
        _combo_row(tr("lbl.faction"), "faction_cb", self._on_faction_changed)

        self.rep_edit = QLineEdit()
        self.rep_edit.setVisible(False)
        self.rep_edit.editingFinished.connect(self._on_rep_changed)

        # Suchfeld (intern, nicht sichtbar)
        self.search_edit = QLineEdit()
        self.search_edit.setVisible(False)

        self._quick_grp.setVisible(False)
        layout.addWidget(self._quick_grp)

    def _build_creation_group(self, layout: QVBoxLayout):
        self._create_grp = QGroupBox(tr("grp.creation"))
        cgl = QVBoxLayout(self._create_grp)
        cgl.setSpacing(4)

        self.new_obj_btn = QPushButton(tr("create.object"))
        self.new_obj_btn.clicked.connect(self._create_new_object)
        cgl.addWidget(self.new_obj_btn)

        self.create_zone_btn = QPushButton(tr("create.asteroid_nebula"))
        self.create_zone_btn.clicked.connect(self._start_zone_creation)
        cgl.addWidget(self.create_zone_btn)

        self.create_simple_zone_btn = QPushButton(tr("create.zone"))
        self.create_simple_zone_btn.clicked.connect(self._start_simple_zone_creation)
        cgl.addWidget(self.create_simple_zone_btn)

        self.create_conn_btn = QPushButton(tr("create.jump"))
        self.create_conn_btn.clicked.connect(self._start_connection_dialog)
        cgl.addWidget(self.create_conn_btn)

        self.save_conn_btn = QPushButton(tr("btn.save_connections"))
        self.save_conn_btn.setVisible(False)
        self.save_conn_btn.clicked.connect(self._save_pending_connections)
        cgl.addWidget(self.save_conn_btn)

        self.sun_btn = QPushButton(tr("create.sun"))
        self.sun_btn.clicked.connect(self._create_sun)
        cgl.addWidget(self.sun_btn)

        self.planet_btn = QPushButton(tr("create.planet"))
        self.planet_btn.clicked.connect(self._create_planet)
        cgl.addWidget(self.planet_btn)

        self.light_btn = QPushButton(tr("create.light_source"))
        self.light_btn.clicked.connect(self._start_light_source_creation)
        cgl.addWidget(self.light_btn)

        self.wreck_btn = QPushButton(tr("create.wreck"))
        self.wreck_btn.clicked.connect(self._start_wreck_creation)
        cgl.addWidget(self.wreck_btn)

        self.buoy_btn = QPushButton(tr("create.buoy"))
        self.buoy_btn.clicked.connect(self._start_buoy_creation)
        cgl.addWidget(self.buoy_btn)

        self.weapon_platform_btn = QPushButton(tr("create.weapon_platform"))
        self.weapon_platform_btn.clicked.connect(self._start_weapon_platform_creation)
        cgl.addWidget(self.weapon_platform_btn)

        self.depot_btn = QPushButton(tr("create.depot"))
        self.depot_btn.clicked.connect(self._start_depot_creation)
        cgl.addWidget(self.depot_btn)

        self.tradelane_btn = QPushButton(tr("create.tradelane"))
        self.tradelane_btn.clicked.connect(self._start_tradelane_creation)
        cgl.addWidget(self.tradelane_btn)

        self.base_btn = QPushButton(tr("create.base"))
        self.base_btn.clicked.connect(self._start_base_creation)
        cgl.addWidget(self.base_btn)

        self.dock_ring_btn = QPushButton(tr("create.docking_ring"))
        self.dock_ring_btn.setToolTip(tr("tip.docking_ring"))
        self.dock_ring_btn.clicked.connect(self._attach_docking_ring)
        cgl.addWidget(self.dock_ring_btn)

        layout.addWidget(self._create_grp)

    def _build_system_info_group(self, layout: QVBoxLayout):
        self.sys_settings_btn = QPushButton(tr("btn.system_settings"))
        self.sys_settings_btn.setToolTip(tr("tip.system_settings"))
        self.sys_settings_btn.setStyleSheet(self._tb_btn_style)
        self.sys_settings_btn.clicked.connect(self._open_system_settings)
        layout.addWidget(self.sys_settings_btn)

    def _build_legend(self, layout: QVBoxLayout):
        from PySide6.QtWidgets import QSizePolicy
        self._status_grp = QGroupBox("")
        sgl = QHBoxLayout(self._status_grp)
        sgl.setContentsMargins(6, 1, 6, 1)
        self._status_history_btn = QPushButton("⋯")
        self._status_history_btn.setFixedWidth(28)
        self._status_history_btn.setToolTip(tr("tip.status_history"))
        self._status_history_btn.clicked.connect(self._open_status_history_dialog)
        self._status_info_lbl = QLabel("")
        self._status_info_lbl.setWordWrap(False)
        self._status_info_lbl.setStyleSheet("font-size:10pt; font-weight:600;")
        self._status_info_lbl.setMinimumHeight(16)
        self._status_info_lbl.setMaximumHeight(16)
        sgl.addWidget(self._status_info_lbl, 1)
        sgl.addWidget(self._status_history_btn)
        self._status_grp.setMinimumHeight(26)
        self._status_grp.setMaximumHeight(26)
        layout.addWidget(self._status_grp)
        # Nur einen sichtbaren Status-Standort nutzen (StatusBar unten).
        self._status_grp.setVisible(False)

        self.legend_box = QGroupBox(tr("grp.legend"))
        ll = QHBoxLayout(self.legend_box)
        ll.setContentsMargins(4, 2, 4, 2)
        ll.setSpacing(4)
        for col, key in _LEGEND_KEYS:
            if not col:
                ll.addSpacing(6)
                continue
            lbl = QLabel(f'<span style="color:{col}">■</span> {tr(key)}')
            lbl.setTextFormat(Qt.RichText)
            lbl.setStyleSheet("font-size:7pt;")
            ll.addWidget(lbl)
        # Legende kompakt halten, damit Statusmeldungen nicht verdeckt werden.
        self.legend_box.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.legend_box.setMaximumHeight(self.legend_box.sizeHint().height())
        self.statusBar().addPermanentWidget(self.legend_box, 0)

    def _build_flight_sidebar(self):
        self._flight_info_dock = QDockWidget("Flight HUD", self)
        self._flight_info_dock.setAllowedAreas(Qt.LeftDockWidgetArea)
        self._flight_info_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        host = QWidget(self._flight_info_dock)
        l = QVBoxLayout(host)
        l.setContentsMargins(6, 6, 6, 6)
        self.flight_free_btn = QPushButton("Freiflug", host)
        self.flight_free_btn.clicked.connect(self._on_flight_free_clicked)
        l.addWidget(self.flight_free_btn)
        self.flight_approach_btn = QPushButton("Anfliegen", host)
        self.flight_approach_btn.clicked.connect(self._on_flight_approach_clicked)
        l.addWidget(self.flight_approach_btn)
        self.flight_dock_btn = QPushButton("Andocken", host)
        self.flight_dock_btn.clicked.connect(self._on_flight_dock_clicked)
        l.addWidget(self.flight_dock_btn)
        self.flight_cam_dist_lbl = QLabel("Kameraabstand: 1.8x", host)
        l.addWidget(self.flight_cam_dist_lbl)
        self.flight_cam_dist_slider = QSlider(Qt.Horizontal, host)
        self.flight_cam_dist_slider.setRange(5, 80)  # 0.5x .. 8.0x Schifflänge
        self.flight_cam_dist_slider.setSingleStep(1)
        self.flight_cam_dist_slider.setPageStep(5)
        self.flight_cam_dist_slider.setValue(18)
        self.flight_cam_dist_slider.valueChanged.connect(self._on_flight_cam_distance_changed)
        l.addWidget(self.flight_cam_dist_slider)
        self.flight_info_view = QTextEdit(host)
        self.flight_info_view.setReadOnly(True)
        self.flight_info_view.setMinimumWidth(250)
        self.flight_info_view.setPlainText("Flight HUD")
        l.addWidget(self.flight_info_view)
        self._flight_info_dock.setWidget(host)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._flight_info_dock)
        self._flight_info_dock.hide()

    def _on_flight_free_clicked(self):
        if hasattr(self, "view3d") and hasattr(self.view3d, "flight_set_freeflight"):
            self.view3d.flight_set_freeflight()

    def _on_flight_approach_clicked(self):
        if hasattr(self, "view3d") and hasattr(self.view3d, "flight_start_autopilot_selected"):
            self.view3d.flight_start_autopilot_selected()

    def _on_flight_dock_clicked(self):
        if hasattr(self, "view3d") and hasattr(self.view3d, "flight_dock_selected_tradelane"):
            self.view3d.flight_dock_selected_tradelane()

    def _on_flight_cam_distance_changed(self, value: int):
        dist = float(value) / 10.0
        if hasattr(self, "flight_cam_dist_lbl"):
            self.flight_cam_dist_lbl.setText(f"Kameraabstand: {dist:.1f}x")
        if hasattr(self, "view3d") and hasattr(self.view3d, "flight_set_chase_distance_ship_lengths"):
            self.view3d.flight_set_chase_distance_ship_lengths(dist)

    # ==================================================================
    #  Toolbar-Button-Style (aus aktuellem Theme generiert)
    # ==================================================================
    def _make_tb_btn_style(self) -> str:
        p = get_palette(current_theme())
        return (
            f"QToolButton, QPushButton {{ background:{p['btn_bg']}; border:1px solid {p['border_light']};"
            f" color:{p['fg']}; padding:4px 10px; border-radius:3px; font-weight:bold; }}"
            f" QToolButton:hover, QPushButton:hover {{ background:{p['btn_hover']}; }}"
            " QToolButton::menu-indicator { image:none; }"
        )

    # ==================================================================
    #  Theme wechseln
    # ==================================================================
    def _on_theme_changed(self, theme_name: str):
        from PySide6.QtWidgets import QColorDialog
        if theme_name == "custom":
            cur = self._cfg.get("custom_accent", "#5060c0")
            color = QColorDialog.getColor(QColor(cur), self, tr("theme.pick_color"))
            if not color.isValid():
                return
            self._cfg.set("custom_accent", color.name())
        # Alle Häkchen aktualisieren
        for n, act in self._theme_actions.items():
            act.setChecked(n == theme_name)
        apply_theme(self, theme_name)
        # Toolbar-Button-Style aktualisieren
        self._tb_btn_style = self._make_tb_btn_style()
        for w in (self.new_system_btn, self.uni_save_btn, self.uni_undo_btn,
                  self.uni_delete_btn,
                  self.ids_scan_btn, self.ids_import_btn,
                  self.flight_mode_btn,
                  self._theme_btn, self._lang_btn, self._about_btn,
                  self.sys_settings_btn):
            w.setStyleSheet(self._tb_btn_style)

    # ==================================================================
    #  Sprache wechseln
    # ==================================================================
    def _on_language_toggled(self):
        new_lang = "en" if get_language() == "de" else "de"
        set_language(new_lang)
        self._cfg.set("language", new_lang)
        self._retranslate_ui()

    # ==================================================================
    #  Retranslate – aktualisiert alle sichtbaren Strings
    # ==================================================================
    def _retranslate_ui(self):
        """Aktualisiert alle übersetzbaren Texte nach Sprachenwechsel."""
        # ── Toolbar ──────────────────────────────────────────────────
        self._universe_act.setText(tr("action.universe"))
        self._model_act.setText(tr("action.open_3d"))
        self.move_cb.setText(tr("cb.move_objects"))
        self.move_cb.setToolTip(tr("tip.move_objects"))
        self.zone_cb.setText(tr("cb.toggle_zones"))
        self.zone_cb.setToolTip(tr("tip.toggle_zones"))
        self.viewer_text_cb.setText(tr("cb.toggle_viewer_text"))
        self.viewer_text_cb.setToolTip(tr("tip.toggle_viewer_text"))
        self.view3d_switch.setToolTip(tr("tip.3d_switch"))
        self.flight_mode_btn.setText("Flight Mode")
        self.new_system_btn.setText(tr("btn.new_system"))
        self.new_system_btn.setToolTip(tr("tip.new_system"))
        self.uni_save_btn.setText(tr("btn.save"))
        self.uni_save_btn.setToolTip(tr("tip.save_universe"))
        self.uni_undo_btn.setText(tr("btn.undo"))
        self.uni_undo_btn.setToolTip(tr("tip.undo"))
        self.uni_delete_btn.setText(tr("btn.delete_system"))
        self.ids_scan_btn.setText(tr("btn.missing_ids"))
        self.ids_scan_btn.setToolTip(tr("tip.missing_ids"))
        self.ids_import_btn.setText(tr("btn.import_ids"))
        self.ids_import_btn.setToolTip(tr("tip.import_ids"))

        # ── Theme / Lang / About ─────────────────────────────────────
        self._theme_btn.setText(tr("theme.label"))
        for tname, act in self._theme_actions.items():
            act.setText(tr(f"theme.{tname}"))
        self._lang_btn.setText(tr("lang.switch"))
        self._about_btn.setText(tr("action.about"))
        self._help_act.setText(tr("action.help"))
        self._about_act.setText(tr("action.about_app"))

        # ── Left panel ───────────────────────────────────────────────
        self._back_btn.setText(tr("btn.back_to_list"))
        self._obj_editor_grp.setTitle(tr("grp.object_editor"))
        if hasattr(self, "_rot_grp"):
            self._rot_grp.setTitle(tr("grp.rotation_xyz"))
        self.zone_link_lbl.setText(tr("lbl.linked_section"))
        self.zone_file_lbl.setText(tr("lbl.zone_file"))
        self.edit_obj_btn.setText(tr("btn.edit_object"))
        self.apply_btn.setText(tr("btn.apply_changes"))
        self.apply_btn.setToolTip(tr("tip.editor_apply"))
        self.delete_btn.setText(tr("btn.delete_object"))
        self.delete_btn.setToolTip(tr("tip.delete_object"))
        self.preview3d_btn.setText(tr("btn.3d_preview"))
        self.preview3d_btn.setToolTip(tr("tip.3d_preview"))

        # ── Left panel – Universe editor ─────────────────────────────
        self._uni_back_btn.setText(tr("btn.back_to_list"))
        self.uni_sys_lbl.setText(tr("lbl.system"))
        self._uni_entry_grp.setTitle(tr("grp.universe_entry"))
        self.uni_apply_btn.setText(tr("btn.save_uni_changes"))

        # ── Right panel ──────────────────────────────────────────────
        if not self._selected:
            self.name_lbl.setText(tr("lbl.no_object"))
        if not self._filepath:
            self.info_lbl.setText(tr("lbl.no_file"))
        self.write_btn.setText(tr("btn.write_to_file"))
        self.write_btn.setToolTip(tr("tip.write_to_file"))

        # ── Groups ───────────────────────────────────────────────────
        self._edit_grp.setTitle(tr("grp.editing"))
        self.obj_combo.setToolTip(tr("tip.obj_combo"))
        self.obj_jump_btn.setText(tr("btn.jump"))
        self.obj_jump_btn.setToolTip(tr("tip.jump_to"))
        self.edit_tradelane_btn.setText(tr("edit.tradelane"))
        self.edit_tradelane_btn.setToolTip(tr("tip.edit_tradelane"))
        self.edit_zone_pop_btn.setText(tr("edit.zone_pop"))
        self.edit_zone_pop_btn.setToolTip(tr("tip.edit_zone_pop"))
        self.add_exclusion_btn.setText(tr("edit.add_exclusion"))
        self.add_exclusion_btn.setToolTip(tr("tip.add_exclusion"))
        self.edit_base_btn.setText(tr("edit.base"))
        self.edit_base_btn.setToolTip(tr("tip.edit_base"))

        self._quick_grp.setTitle(tr("grp.quick_editor"))

        self._create_grp.setTitle(tr("grp.creation"))
        self.new_obj_btn.setText(tr("create.object"))
        self.create_zone_btn.setText(tr("create.asteroid_nebula"))
        self.create_simple_zone_btn.setText(tr("create.zone"))
        self.create_conn_btn.setText(tr("create.jump"))
        self.save_conn_btn.setText(tr("btn.save_connections"))
        self.sun_btn.setText(tr("create.sun"))
        self.planet_btn.setText(tr("create.planet"))
        self.light_btn.setText(tr("create.light_source"))
        self.wreck_btn.setText(tr("create.wreck"))
        self.buoy_btn.setText(tr("create.buoy"))
        self.weapon_platform_btn.setText(tr("create.weapon_platform"))
        self.depot_btn.setText(tr("create.depot"))
        self.tradelane_btn.setText(tr("create.tradelane"))
        self.base_btn.setText(tr("create.base"))
        self.dock_ring_btn.setText(tr("create.docking_ring"))
        self.dock_ring_btn.setToolTip(tr("tip.docking_ring"))

        self.sys_settings_btn.setText(tr("btn.system_settings"))
        self.sys_settings_btn.setToolTip(tr("tip.system_settings"))
        if hasattr(self, "_status_history_btn"):
            self._status_history_btn.setToolTip(tr("tip.status_history"))
        if hasattr(self, "_action_history_btn"):
            self._action_history_btn.setToolTip(tr("tip.action_history"))

        # ── Legend (rebuild) ─────────────────────────────────────────
        self._rebuild_legend()

        # ── Status Bar ───────────────────────────────────────────────
        self.statusBar().showMessage(tr("status.ready"))

    def _rebuild_legend(self):
        """Legende komplett neu aufbauen (nach Sprachwechsel)."""
        box = self.legend_box
        box.setTitle(tr("grp.legend"))
        if hasattr(self, "_change_log_grp"):
            self._change_log_grp.setTitle(tr("grp.change_log"))
        layout = box.layout()
        # Alle alten Widgets entfernen
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        # Neu aufbauen
        for col, key in _LEGEND_KEYS:
            if not col:
                layout.addSpacing(6)
                continue
            lbl = QLabel(f'<span style="color:{col}">■</span> {tr(key)}')
            lbl.setTextFormat(Qt.RichText)
            lbl.setStyleSheet("font-size:7pt;")
            layout.addWidget(lbl)

    def _append_change_log(self, message: str):
        stamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{stamp}] {message}"
        self._change_log_entries.append(line)
        self._render_change_log_entries()
        self._change_undo_btn.setEnabled(bool(self._change_snapshots) or bool(self._undo_actions))

    def _render_change_log_entries(self):
        self.change_log_view.setPlainText("\n".join(self._change_log_entries))
        self.change_log_view.verticalScrollBar().setValue(
            self.change_log_view.verticalScrollBar().maximum()
        )

    def _on_flight_hud_update(self, hud: dict | None):
        if not hud:
            if hasattr(self, "flight_info_view"):
                self.flight_info_view.setPlainText("")
            return
        x, y, z = hud.get("pos", (0.0, 0.0, 0.0))
        target_name = str(hud.get("target_name", "") or "")
        target_dist = hud.get("target_distance", None)
        lines = [
            "Steuerung (Flight Mode)",
            "Sidebar: Freiflug / Anfliegen / Andocken",
            "LMB halten + Maus: lenken",
            "W: beschleunigen / S: bremsen",
            "Shift+W: Cruise",
            "F2: Autopilot",
            "F3: Trade Lane",
            "H: Orbit-Kamera um Schiff",
            "ESC: Flight beenden",
            "",
            f"Mode: {hud.get('mode', '-')}",
            f"Speed: {float(hud.get('speed', 0.0)):.1f} m/s",
            f"MaxSpeed: {float(hud.get('max_speed', 0.0)):.0f} m/s",
            f"Pos: X {float(x):.1f}  Y {float(y):.1f}  Z {float(z):.1f}",
        ]
        if bool(hud.get("orbit_cam_active", False)):
            lines.append("Kamera: ORBIT (H zum Zurückschalten)")
        if target_name and target_dist is not None:
            lines.append(f"Ziel: {target_name}")
            lines.append(f"Distanz: {float(target_dist):.1f} m")
        charge = float(hud.get("charge_progress", 0.0))
        if bool(hud.get("charge_active", False)):
            lines.append(f"Cruise Charge: {charge * 100.0:.0f}%")
        err = str(hud.get("error", "") or "")
        if err:
            lines.append(f"Fehler: {err}")
        if hasattr(self, "flight_info_view"):
            self.flight_info_view.setPlainText("\n".join(lines))

    def _append_status_log(self, message: str):
        stamp = datetime.now().strftime("%H:%M:%S")
        self._status_log_entries.append(f"[{stamp}] {message}")

    def _open_history_dialog(self, title: str, lines: list[str]):
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.resize(860, 480)
        lay = QVBoxLayout(dlg)
        txt = QTextEdit(dlg)
        txt.setReadOnly(True)
        txt.setPlainText("\n".join(lines) if lines else "-")
        lay.addWidget(txt)
        dlg.exec()

    def _open_status_history_dialog(self):
        self._open_history_dialog(tr("dlg.status_history"), self._status_log_entries)

    def _open_action_history_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("dlg.action_history"))
        dlg.resize(900, 520)
        lay = QVBoxLayout(dlg)
        lst = QListWidget(dlg)
        lst.setSelectionMode(QAbstractItemView.SingleSelection)
        lay.addWidget(lst)

        hint = QLabel("Hinweis: Beim Rückgängigmachen einer älteren Änderung bleiben neuere Änderungen erhalten.")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        btn_row = QHBoxLayout()
        undo_btn = QPushButton("Ausgewählte Änderung rückgängig")
        close_btn = QPushButton(tr("dlg.close"))
        btn_row.addWidget(undo_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        lay.addLayout(btn_row)

        def _action_caption(action: dict) -> str:
            label = str(action.get("label", action.get("type", "Änderung"))).strip() or "Änderung"
            ts = str(action.get("ts", "")).strip()
            return f"[{ts}] {label}" if ts else label

        def _reload():
            lst.clear()
            for action in reversed(self._undo_actions):
                item = QListWidgetItem(_action_caption(action))
                lst.addItem(item)
            undo_btn.setEnabled(lst.count() > 0)
            if lst.count() > 0:
                lst.setCurrentRow(0)

        def _undo_selected():
            row = lst.currentRow()
            if row < 0:
                return
            stack_idx = len(self._undo_actions) - 1 - row
            if not self._undo_action_at_index(stack_idx):
                self.statusBar().showMessage("Ausgewählte Änderung konnte nicht rückgängig gemacht werden")
                return
            self.statusBar().showMessage("Ausgewählte Änderung rückgängig gemacht")
            _reload()

        undo_btn.clicked.connect(_undo_selected)
        close_btn.clicked.connect(dlg.accept)
        _reload()
        dlg.exec()

    def _persist_undo_actions(self):
        try:
            self._cfg.set("undo_actions", self._undo_actions)
        except Exception:
            pass

    def _push_undo_action(self, action: dict):
        if not isinstance(action, dict):
            return
        if not action.get("ts"):
            action["ts"] = datetime.now().strftime("%H:%M:%S")
        self._undo_actions.append(action)
        if len(self._undo_actions) > 300:
            self._undo_actions = self._undo_actions[-300:]
        self._persist_undo_actions()
        self._change_undo_btn.setEnabled(True)

    def _undo_action_at_index(self, stack_index: int) -> bool:
        if stack_index < 0 or stack_index >= len(self._undo_actions):
            return False
        action = self._undo_actions[stack_index]
        if not self._apply_undo_action(action):
            return False
        self._undo_actions.pop(stack_index)
        self._persist_undo_actions()
        self._append_change_log(f"Undo: {action.get('label', action.get('type', 'Änderung'))}")
        self._change_undo_btn.setEnabled(bool(self._change_snapshots) or bool(self._undo_actions))
        return True

    def _apply_undo_action(self, action: dict) -> bool:
        typ = str(action.get("type", ""))
        if typ == "edit_object":
            return self._undo_edit_object_action(action)
        if typ == "move_object":
            return self._undo_move_object_action(action)
        if typ == "move_universe_system":
            return self._undo_move_universe_action(action)
        if typ == "delete_zone":
            return self._undo_delete_zone_action(action)
        if typ == "delete_object":
            return self._undo_delete_object_action(action)
        if typ == "create_object":
            return self._undo_create_object_action(action)
        if typ == "create_zone":
            return self._undo_create_zone_action(action)
        if typ == "create_exclusion_zone":
            return self._undo_create_exclusion_zone_action(action)
        if typ == "create_lightsource":
            return self._undo_create_lightsource_action(action)
        return False

    @staticmethod
    def _entries_to_data(entries: list[list[str]] | list[tuple[str, str]]) -> dict:
        out: dict = {"_entries": []}
        for pair in entries or []:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                continue
            k = str(pair[0])
            v = str(pair[1])
            out["_entries"].append((k, v))
            lk = k.lower()
            if lk not in out:
                out[lk] = v
        return out

    def _section_index_for_object_index(self, obj_index: int) -> int | None:
        count = 0
        for i, (sec_name, _entries) in enumerate(self._sections):
            if sec_name.lower() != "object":
                continue
            if count == obj_index:
                return i
            count += 1
        return None

    def _section_index_for_zone_index(self, zone_index: int) -> int | None:
        count = 0
        for i, (sec_name, _entries) in enumerate(self._sections):
            if sec_name.lower() != "zone":
                continue
            if count == zone_index:
                return i
            count += 1
        return None

    def _scene_to_fl_pos_with_y(self, scene_pos: QPointF, y_value: float) -> str:
        return f"{scene_pos.x() / self._scale:.2f}, {float(y_value):.2f}, {scene_pos.y() / self._scale:.2f}"

    @staticmethod
    def _parse_exclusion_nicks_from_field_ini(ini_text: str) -> list[str]:
        out: list[str] = []
        in_block = False
        for raw in (ini_text or "").splitlines():
            s = raw.strip()
            if s.startswith("[") and s.endswith("]") and len(s) > 2:
                in_block = s[1:-1].strip().lower() == "exclusion zones"
                continue
            if not in_block or not s or s.startswith(";") or s.startswith("//") or "=" not in s:
                continue
            k, _, v = s.partition("=")
            if k.strip().lower() != "exclusion":
                continue
            nick = v.strip()
            if nick and nick.lower() not in {n.lower() for n in out}:
                out.append(nick)
        return out

    def _remove_zones_by_nickname(self, nickname: str) -> list[dict]:
        nick = str(nickname).strip().lower()
        if not nick:
            return []
        removed: list[dict] = []
        while True:
            target = next((z for z in self._zones if z.nickname.strip().lower() == nick), None)
            if target is None:
                break
            try:
                z_idx = self._zones.index(target)
            except ValueError:
                break
            z_sec_idx = self._section_index_for_zone_index(z_idx)
            if z_sec_idx is not None:
                self._sections.pop(z_sec_idx)
            self.view._scene.removeItem(target)
            self._zones.pop(z_idx)
            removed.append(
                {
                    "nickname": target.nickname,
                    "entries": [list(p) for p in target.data.get("_entries", [])],
                    "zone_index": int(z_idx),
                    "section_index": int(z_sec_idx) if z_sec_idx is not None else None,
                }
            )
        return removed

    def _undo_from_action_log(self) -> bool:
        if not self._undo_actions:
            self._change_undo_btn.setEnabled(bool(self._change_snapshots) or bool(self._undo_actions))
            return False
        action = self._undo_actions[-1]
        if not self._apply_undo_action(action):
            return False
        self._undo_actions.pop()
        self._persist_undo_actions()
        self._append_change_log(f"Undo: {action.get('label', action.get('type', 'Änderung'))}")
        self._change_undo_btn.setEnabled(bool(self._change_snapshots) or bool(self._undo_actions))
        return True

    def _undo_create_object_action(self, action: dict) -> bool:
        filepath = str(action.get("filepath", "")).strip()
        nick = str(action.get("nickname", "")).strip().lower()
        if not filepath or not nick:
            return False
        if not self._filepath or Path(self._filepath).resolve() != Path(filepath).resolve():
            self._load(filepath)
            self.browser.highlight_current(filepath)
        target = next((o for o in self._objects if o.nickname.lower() == nick), None)
        if target is None:
            return False
        try:
            obj_idx = self._objects.index(target)
        except ValueError:
            return False
        sec_idx = self._section_index_for_object_index(obj_idx)
        if sec_idx is not None:
            self._sections.pop(sec_idx)
        self.view._scene.removeItem(target)
        self._objects.pop(obj_idx)
        self._rebuild_object_combo()
        if self._selected is target:
            self._clear_selection_ui()
        self._refresh_3d_scene(preserve_camera=True)
        self._set_dirty(True)
        return True

    def _undo_create_zone_action(self, action: dict) -> bool:
        filepath = str(action.get("filepath", "")).strip()
        nick = str(action.get("nickname", "")).strip().lower()
        if not filepath or not nick:
            return False
        if not self._filepath or Path(self._filepath).resolve() != Path(filepath).resolve():
            self._load(filepath)
            self.browser.highlight_current(filepath)
        target = next((z for z in self._zones if z.nickname.lower() == nick), None)
        if target is None:
            return False
        try:
            z_idx = self._zones.index(target)
        except ValueError:
            return False
        z_sec_idx = self._section_index_for_zone_index(z_idx)
        if z_sec_idx is not None:
            self._sections.pop(z_sec_idx)
        sec_name = str(action.get("linked_section", "")).strip().lower()
        if sec_name:
            for i, (sn, entries) in enumerate(list(self._sections)):
                if sn.lower() != sec_name:
                    continue
                zone_val = ""
                for k, v in entries:
                    if k.lower() == "zone":
                        zone_val = v.strip().lower()
                        break
                if zone_val == nick:
                    self._sections.pop(i)
                    break
        self.view._scene.removeItem(target)
        self._zones.pop(z_idx)
        linked_abs = str(action.get("linked_file_abs", "")).strip()
        if linked_abs:
            try:
                linked_text = Path(linked_abs).read_text(encoding="utf-8", errors="ignore")
            except Exception:
                linked_text = ""
            exclusion_nicks = self._parse_exclusion_nicks_from_field_ini(linked_text)
            known_excl = {n.lower() for n in exclusion_nicks}
            prefix = f"{nick}_exclusion_"
            for z in self._zones:
                zn = z.nickname.strip()
                if zn.lower().startswith(prefix) and zn.lower() not in known_excl:
                    exclusion_nicks.append(zn)
                    known_excl.add(zn.lower())
            if exclusion_nicks:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Question)
                msg.setWindowTitle("Exclusion-Zonen")
                msg.setText("Für dieses Feld existieren verknüpfte Exclusion-Zonen.")
                msg.setInformativeText(
                    "Sollen diese Exclusion-Zonen ebenfalls aus der System-INI gelöscht werden?\n\n"
                    + "\n".join(f"- {n}" for n in exclusion_nicks)
                )
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.setDefaultButton(QMessageBox.No)
                if msg.exec() == QMessageBox.Yes:
                    removed_count = 0
                    for ex_nick in exclusion_nicks:
                        removed_count += len(self._remove_zones_by_nickname(ex_nick))
                    if removed_count:
                        self._append_change_log(f"{removed_count} verknüpfte Exclusion-Zonen gelöscht")
        if linked_abs:
            try:
                Path(linked_abs).unlink(missing_ok=True)
            except Exception:
                pass
        self._rebuild_object_combo()
        if self._selected is target:
            self._clear_selection_ui()
        self._refresh_3d_scene(preserve_camera=True)
        self._set_dirty(True)
        return True

    def _undo_create_exclusion_zone_action(self, action: dict) -> bool:
        filepath = str(action.get("filepath", "")).strip()
        nick = str(action.get("nickname", "")).strip().lower()
        if not filepath or not nick:
            return False
        if not self._filepath or Path(self._filepath).resolve() != Path(filepath).resolve():
            self._load(filepath)
            self.browser.highlight_current(filepath)
        removed_all = self._remove_zones_by_nickname(nick)
        if not removed_all:
            return False
        removed = removed_all[0]
        linked_files = action.get("linked_files")
        if isinstance(linked_files, list):
            game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
            for info in linked_files:
                if not isinstance(info, dict):
                    continue
                rel = str(info.get("rel", "")).strip()
                if not rel:
                    continue
                path = self._target_game_path_for_rel(game_path, rel)
                if path is None or not path.is_file():
                    continue
                try:
                    original = path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    original = ""
                if not original:
                    continue
                patched, changed = patch_field_ini_remove_exclusion(original, removed["nickname"])
                if not changed:
                    continue
                try:
                    tmp = str(path) + ".tmp"
                    Path(tmp).write_text(patched, encoding="utf-8")
                    shutil.move(tmp, path)
                except Exception:
                    pass
        self._rebuild_object_combo()
        if self._selected and isinstance(self._selected, ZoneItem) and self._selected.nickname.lower() == nick:
            self._clear_selection_ui()
        self._refresh_3d_scene(preserve_camera=True)
        self._set_dirty(True)
        return True

    def _undo_create_lightsource_action(self, action: dict) -> bool:
        filepath = str(action.get("filepath", "")).strip()
        nickname = str(action.get("nickname", "")).strip().lower()
        if not filepath or not nickname:
            return False
        if not self._filepath or Path(self._filepath).resolve() != Path(filepath).resolve():
            self._load(filepath)
            self.browser.highlight_current(filepath)
        for i, (sec_name, entries) in enumerate(list(self._sections)):
            if sec_name.lower() != "lightsource":
                continue
            nick = ""
            for k, v in entries:
                if k.lower() == "nickname":
                    nick = v.strip().lower()
                    break
            if nick == nickname:
                self._sections.pop(i)
                self._set_dirty(True)
                return True
        return False

    def _undo_edit_object_action(self, action: dict) -> bool:
        filepath = str(action.get("filepath", "")).strip()
        if not filepath:
            return False
        if not self._filepath or Path(self._filepath).resolve() != Path(filepath).resolve():
            self._load(filepath)
            self.browser.highlight_current(filepath)
        old_entries = action.get("old_entries", [])
        if not old_entries:
            return False
        obj_idx = action.get("object_index")
        target = None
        if isinstance(obj_idx, int) and 0 <= obj_idx < len(self._objects):
            cand = self._objects[obj_idx]
            if isinstance(cand, SolarObject) and not hasattr(cand, "sys_path"):
                target = cand
        if target is None:
            old_nick = str(action.get("old_nickname", "")).strip().lower()
            new_nick = str(action.get("new_nickname", "")).strip().lower()
            for o in self._objects:
                n = o.nickname.lower()
                if n == new_nick or n == old_nick:
                    target = o
                    break
        if target is None:
            return False
        restored = [(str(k), str(v)) for k, v in old_entries if isinstance(k, (str, int, float))]
        if not restored:
            return False
        target.data = self._entries_to_data(restored)
        target.nickname = target.data.get("nickname", target.nickname)
        if target.label:
            target.label.setPlainText(target.nickname)
        fx, _, fz = parse_position(target.data.get("pos", "0,0,0"))
        target.setPos(fx * self._scale, fz * self._scale)
        self._sync_object_section_from_obj(target)
        if self._selected is target:
            self.editor.setPlainText(target.raw_text())
            self.name_lbl.setText(f"📍 {target.nickname}")
        self._rebuild_object_combo()
        self._sync_obj_combo_to_selection()
        self.view3d.update_object_position(target, self._scale)
        self.view3d.update_object_rotation(target)
        self._set_dirty(True)
        self._refresh_3d_scene(preserve_camera=True)
        return True

    def _undo_move_object_action(self, action: dict) -> bool:
        filepath = str(action.get("filepath", "")).strip()
        nickname = str(action.get("nickname", "")).strip().lower()
        old_pos = str(action.get("old_pos", "")).strip()
        if not filepath or not nickname or not old_pos:
            return False
        if not self._filepath or Path(self._filepath).resolve() != Path(filepath).resolve():
            self._load(filepath)
            self.browser.highlight_current(filepath)
        target = next((o for o in self._objects if o.nickname.lower() == nickname), None)
        if target is None:
            return False
        target.data["_entries"] = [
            (k, old_pos if k.lower() == "pos" else v) for k, v in target.data.get("_entries", [])
        ]
        target.data["pos"] = old_pos
        fx, fy, fz = parse_position(old_pos)
        target.setPos(fx * self._scale, fz * self._scale)
        self._sync_object_section_from_obj(target)
        self.view3d.update_object_position(target, self._scale)
        if self._selected is target:
            self.editor.setPlainText(target.raw_text())
        self._set_dirty(True)
        return True

    def _undo_move_universe_action(self, action: dict) -> bool:
        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        nick = str(action.get("nickname", "")).strip().lower()
        old_x = action.get("old_x")
        old_y = action.get("old_y")
        if not game_path or not nick or old_x is None or old_y is None:
            return False
        if self._filepath is not None:
            self._load_universe(game_path)
        target = next((o for o in self._objects if hasattr(o, "sys_path") and o.nickname.lower() == nick), None)
        if target is None:
            return False
        target.setPos(float(old_x) * self._scale, float(old_y) * self._scale)
        self._update_universe_lines()
        self._set_dirty(True)
        return True

    def _undo_delete_zone_action(self, action: dict) -> bool:
        filepath = str(action.get("filepath", "")).strip()
        zone_data = action.get("zone", {})
        if not filepath or not isinstance(zone_data, dict):
            return False
        if not self._filepath or Path(self._filepath).resolve() != Path(filepath).resolve():
            self._load(filepath)
            self.browser.highlight_current(filepath)
        entries = zone_data.get("entries", [])
        if not entries:
            return False
        zone = ZoneItem(self._entries_to_data(entries), self._scale)
        zone.set_label_visibility(self._viewer_text_visible)
        insert_index = int(zone_data.get("zone_index", len(self._zones)))
        insert_index = max(0, min(insert_index, len(self._zones)))
        self._zones.insert(insert_index, zone)
        self.view._scene.addItem(zone)
        sec_index = zone_data.get("section_index")
        if sec_index is None:
            sec_index = self._section_index_for_zone_index(insert_index) or len(self._sections)
        self._sections.insert(int(sec_index), ("Zone", list(zone.data.get("_entries", []))))

        linked_section = action.get("linked_section")
        if isinstance(linked_section, dict):
            ls_name = str(linked_section.get("name", ""))
            ls_entries = linked_section.get("entries", [])
            ls_idx = int(linked_section.get("section_index", len(self._sections)))
            if ls_name and ls_entries:
                self._sections.insert(max(0, min(ls_idx, len(self._sections))), (ls_name, [(str(k), str(v)) for k, v in ls_entries]))
        linked_file = action.get("linked_file")
        if isinstance(linked_file, dict):
            rel = str(linked_file.get("rel", "")).strip()
            content = str(linked_file.get("content", ""))
            if rel and content:
                game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
                path = self._target_game_path_for_rel(game_path, rel)
                if path is not None:
                    try:
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(content, encoding="utf-8")
                    except Exception:
                        pass
        exclusion_linked_files = action.get("exclusion_linked_files")
        if isinstance(exclusion_linked_files, list):
            game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
            for info in exclusion_linked_files:
                if not isinstance(info, dict):
                    continue
                rel = str(info.get("rel", "")).strip()
                content = str(info.get("content", ""))
                if not rel or not content:
                    continue
                path = self._target_game_path_for_rel(game_path, rel)
                if path is None:
                    continue
                try:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
                except Exception:
                    pass
        deleted_exclusion_zones = action.get("deleted_exclusion_zones")
        if isinstance(deleted_exclusion_zones, list):
            for info in deleted_exclusion_zones:
                if not isinstance(info, dict):
                    continue
                z_entries = info.get("entries", [])
                if not z_entries:
                    continue
                ex_zone = ZoneItem(self._entries_to_data(z_entries), self._scale)
                ex_zone.set_label_visibility(self._viewer_text_visible)
                ex_idx = int(info.get("zone_index", len(self._zones)))
                ex_idx = max(0, min(ex_idx, len(self._zones)))
                self._zones.insert(ex_idx, ex_zone)
                self.view._scene.addItem(ex_zone)
                ex_sec_idx = info.get("section_index")
                if ex_sec_idx is None:
                    ex_sec_idx = self._section_index_for_zone_index(ex_idx) or len(self._sections)
                self._sections.insert(
                    max(0, min(int(ex_sec_idx), len(self._sections))),
                    ("Zone", list(ex_zone.data.get("_entries", []))),
                )
        self._rebuild_object_combo()
        self._refresh_3d_scene(preserve_camera=True)
        self._set_dirty(True)
        return True

    def _undo_delete_object_action(self, action: dict) -> bool:
        filepath = str(action.get("filepath", "")).strip()
        obj_data = action.get("object", {})
        if not filepath or not isinstance(obj_data, dict):
            return False
        if not self._filepath or Path(self._filepath).resolve() != Path(filepath).resolve():
            self._load(filepath)
            self.browser.highlight_current(filepath)
        entries = obj_data.get("entries", [])
        if not entries:
            return False
        obj = SolarObject(self._entries_to_data(entries), self._scale)
        obj.setFlag(QGraphicsItem.ItemIsMovable, self.move_cb.isChecked())
        insert_index = int(obj_data.get("object_index", len(self._objects)))
        insert_index = max(0, min(insert_index, len(self._objects)))
        self._objects.insert(insert_index, obj)
        self.view._scene.addItem(obj)
        sec_index = obj_data.get("section_index")
        if sec_index is None:
            sec_index = self._section_index_for_object_index(insert_index) or len(self._sections)
        self._sections.insert(int(sec_index), ("Object", list(obj.data.get("_entries", []))))

        linked_zone = action.get("linked_zone")
        if isinstance(linked_zone, dict):
            z_entries = linked_zone.get("entries", [])
            if z_entries:
                zone = ZoneItem(self._entries_to_data(z_entries), self._scale)
                zone.set_label_visibility(self._viewer_text_visible)
                z_idx = int(linked_zone.get("zone_index", len(self._zones)))
                z_idx = max(0, min(z_idx, len(self._zones)))
                self._zones.insert(z_idx, zone)
                self.view._scene.addItem(zone)
                z_sec_idx = int(linked_zone.get("section_index", len(self._sections)))
                self._sections.insert(max(0, min(z_sec_idx, len(self._sections))), ("Zone", list(zone.data.get("_entries", []))))

        self._rebuild_object_combo()
        self._refresh_3d_scene(preserve_camera=True)
        self._set_dirty(True)
        return True

    def _sections_fingerprint(self, sections=None) -> str:
        src = self._sections if sections is None else sections
        parts: list[str] = []
        for sec_name, entries in src:
            parts.append(f"[{sec_name}]")
            for k, v in entries:
                parts.append(f"{k}={v}")
        return hashlib.sha1("\n".join(parts).encode("utf-8", errors="ignore")).hexdigest()

    def _capture_change_snapshot(self, reason: str = "Änderung"):
        if self._history_restore_in_progress:
            return
        if not self._filepath or not self._sections:
            return
        fp = self._sections_fingerprint(self._sections)
        if fp == self._last_snapshot_fp:
            return
        self._last_snapshot_fp = fp
        self._change_snapshots.append(
            {
                "sections": deepcopy(self._sections),
                "selection": self._capture_selection_ref(),
                "label": reason,
            }
        )
        if len(self._change_snapshots) > 120:
            self._change_snapshots.pop(0)
        self._append_change_log(reason)

    def _apply_sections_snapshot(self, snapshot: dict):
        sections = snapshot.get("sections")
        if not sections:
            return
        self._history_restore_in_progress = True
        try:
            self._sections = deepcopy(sections)
            raw_objs = self._parser.get_objects(self._sections)
            raw_zones = self._parser.get_zones(self._sections)

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

            if not coords and light_range > 0:
                coords.append(light_range)
                rmax = max(rmax, light_range)

            self._scale = 500.0 / (max(coords, default=1) or 1)
            self.view.set_world_scale(self._scale)

            self.view._scene.clear()
            self.view._scene.setSceneRect(0, 0, 0, 0)
            self._apply_scene_wallpaper(QColor(8, 8, 15))
            self._objects, self._zones = [], []
            self._selected = None
            self._clear_selection_ui()
            self._hide_zone_extra_editors()

            for zd in raw_zones:
                try:
                    zi = ZoneItem(zd, self._scale)
                    if hasattr(zi, "set_label_visibility"):
                        zi.set_label_visibility(self._viewer_text_visible)
                    self.view._scene.addItem(zi)
                    self._zones.append(zi)
                except Exception:
                    pass

            move_on = self.move_cb.isChecked()
            for od in raw_objs:
                try:
                    obj = SolarObject(od, self._scale)
                    if hasattr(obj, "set_label_visibility"):
                        obj.set_label_visibility(self._viewer_text_visible)
                    obj.setFlag(QGraphicsItem.ItemIsMovable, move_on)
                    self.view._scene.addItem(obj)
                    self._objects.append(obj)
                except Exception:
                    pass

            if rmax > 0:
                pen = QPen(QColor(200, 200, 200, 120))
                pen.setWidthF(0.5)
                r = rmax * self._scale
                circ = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r)
                circ.setPen(pen)
                circ.setBrush(Qt.NoBrush)
                circ.setZValue(-1)
                self.view._scene.addItem(circ)

            if not self.zone_cb.isChecked():
                for z in self._zones:
                    z.setVisible(False)

            self._rebuild_object_combo()
            self._restore_selection_ref(snapshot.get("selection"))
            self._refresh_3d_scene(force=True, preserve_camera=True)
            self._set_dirty(True)
        finally:
            self._history_restore_in_progress = False

    def _undo_last_change_snapshot(self):
        if self._change_snapshots:
            snap = self._change_snapshots.pop()
            # After undo, this snapshot content is current state.
            self._last_snapshot_fp = self._sections_fingerprint(snap.get("sections", [])) if snap.get("sections") else ""
            self._apply_sections_snapshot(snap)
            self.statusBar().showMessage("Änderung rückgängig gemacht")
            self._change_undo_btn.setEnabled(bool(self._change_snapshots) or bool(self._undo_actions))
            return
        had_undo_actions = bool(self._undo_actions)
        if self._undo_from_action_log():
            self.statusBar().showMessage("Änderung rückgängig gemacht")
            return
        if had_undo_actions:
            self.statusBar().showMessage("Letzte Änderung kann nicht rückgängig gemacht werden")
            return
        self.statusBar().showMessage("Nichts zum Rückgängigmachen")

    def _on_status_message_changed(self, message: str):
        if hasattr(self, "_status_info_lbl"):
            self._status_info_lbl.setText(message)
        if not message:
            return
        self._append_status_log(message)
        # Nur User-Aktionen in den Änderungsverlauf schreiben.
        log_triggers = ("gelöscht", "erstellt", "updated", "deleted", "created", "import")
        log_exclude = (
            "geladen",
            "loaded",
            "gespeichert",
            "saved",
            "lade neu",
            "reloading",
            "universum geladen",
            "universe loaded",
            "objekte ·",
            "objects ·",
        )
        low = message.lower()
        if any(x in low for x in log_exclude):
            return
        if message.startswith(("✓", "✔")) or any(t in low for t in log_triggers):
            self._append_change_log(message)

    # ==================================================================
    #  Placement-Modus
    # ==================================================================
    def _on_flight_mode_toggled(self, checked: bool):
        self._set_flight_mode(checked, sync_button=True)

    def _sync_flight_button_visibility(self):
        self.flight_mode_btn.setVisible(True)

    def _set_flight_sidebars_visible(self, visible: bool):
        if visible:
            if hasattr(self, "left_stack"):
                self.left_stack.setVisible(self._flight_prev_left_visible)
            if hasattr(self, "right_panel"):
                self.right_panel.setVisible(self._flight_prev_right_visible)
            if hasattr(self, "_flight_info_dock"):
                self._flight_info_dock.hide()
            return
        if hasattr(self, "left_stack"):
            self._flight_prev_left_visible = self.left_stack.isVisible()
        if hasattr(self, "right_panel"):
            self._flight_prev_right_visible = self.right_panel.isVisible()
        if hasattr(self, "left_stack"):
            self.left_stack.setVisible(False)
        if hasattr(self, "right_panel"):
            self.right_panel.setVisible(False)
        if hasattr(self, "_flight_info_dock"):
            self._flight_info_dock.show()

    def _set_flight_mode(self, enabled: bool, sync_button: bool = True):
        if enabled:
            if not QT3D_AVAILABLE:
                if sync_button:
                    self.flight_mode_btn.blockSignals(True)
                    self.flight_mode_btn.setChecked(False)
                    self.flight_mode_btn.blockSignals(False)
                self.statusBar().showMessage("Flight Mode requires Qt3D support")
                return
            if not self._filepath:
                if sync_button:
                    self.flight_mode_btn.blockSignals(True)
                    self.flight_mode_btn.setChecked(False)
                    self.flight_mode_btn.blockSignals(False)
                self.statusBar().showMessage("Flight Mode requires a loaded system")
                return
            sel = self._selected
            if not isinstance(sel, SolarObject) or isinstance(sel, ZoneItem) or hasattr(sel, "sys_path"):
                if sync_button:
                    self.flight_mode_btn.blockSignals(True)
                    self.flight_mode_btn.setChecked(False)
                    self.flight_mode_btn.blockSignals(False)
                self.statusBar().showMessage("Select an object first (required for Flight Mode start)")
                return
            if not self.view3d_switch.isChecked():
                self.view3d_switch.setChecked(True)
            self._set_flight_sidebars_visible(False)
            if hasattr(self.view3d, "set_flight_hud_callback"):
                self.view3d.set_flight_hud_callback(self._on_flight_hud_update)
            if hasattr(self, "flight_cam_dist_slider") and hasattr(self.view3d, "flight_get_chase_distance_ship_lengths"):
                cur = self.view3d.flight_get_chase_distance_ship_lengths()
                self.flight_cam_dist_slider.blockSignals(True)
                self.flight_cam_dist_slider.setValue(max(5, min(80, int(round(cur * 10.0)))))
                self.flight_cam_dist_slider.blockSignals(False)
                self._on_flight_cam_distance_changed(self.flight_cam_dist_slider.value())
            self.view3d.set_flight_mode_active(True, self)
            self._set_flight_edit_lock(True)
            self.statusBar().showMessage("Flight Mode active (ESC to exit)")
        else:
            if hasattr(self.view3d, "set_flight_hud_callback"):
                self.view3d.set_flight_hud_callback(None)
            self.view3d.set_flight_mode_active(False, self)
            self._set_flight_edit_lock(False)
            self._on_flight_hud_update(None)
            self._set_flight_sidebars_visible(True)
            self.statusBar().showMessage("Flight Mode disabled")
        if sync_button:
            self.flight_mode_btn.blockSignals(True)
            self.flight_mode_btn.setChecked(enabled)
            self.flight_mode_btn.blockSignals(False)
        self._sync_flight_button_visibility()

    def _set_flight_edit_lock(self, locked: bool):
        self._flight_lock_active = bool(locked)
        if locked and self.move_cb.isChecked():
            self.move_cb.setChecked(False)
        if locked:
            for obj in self._objects:
                obj.setFlag(QGraphicsItem.ItemIsMovable, False)
            self.view3d.set_move_mode(False)

        for w in (
            self.move_cb,
            self.new_obj_btn,
            self.create_zone_btn,
            self.create_simple_zone_btn,
            self.create_conn_btn,
            self.save_conn_btn,
            self.sun_btn,
            self.planet_btn,
            self.light_btn,
            self.wreck_btn,
            self.buoy_btn,
            self.weapon_platform_btn,
            self.depot_btn,
            self.tradelane_btn,
            self.base_btn,
            self.dock_ring_btn,
            self.edit_tradelane_btn,
            self.edit_zone_pop_btn,
            self.add_exclusion_btn,
            self.edit_base_btn,
            self.edit_obj_btn,
            self.apply_btn,
            self.delete_btn,
            self.editor,
            self.zone_link_editor,
            self.zone_file_editor,
            self.uni_editor,
            self.uni_save_btn,
            self.uni_undo_btn,
            self.uni_apply_btn,
            self.uni_delete_btn,
        ):
            if w is not None:
                w.setEnabled(not locked)
        if locked:
            self.write_btn.setEnabled(False)
            self.preview3d_btn.setEnabled(False)
        else:
            if self._selected is not None:
                self.edit_obj_btn.setEnabled(True)
                self.apply_btn.setEnabled(True)
                self.delete_btn.setEnabled(True)
                self.preview3d_btn.setEnabled(not isinstance(self._selected, ZoneItem))
                self.add_exclusion_btn.setEnabled(isinstance(self._selected, ZoneItem) and self._is_field_zone(self._selected.nickname))
            self.write_btn.setEnabled(bool(self._filepath) and self._dirty)

    def _set_placement_mode(self, active: bool, text: str = ""):
        if active and self._flight_lock_active:
            return
        self.view.set_placement_passthrough(active)
        if active:
            self.view.setCursor(Qt.CrossCursor)
            self.view.setStyleSheet("QGraphicsView { border: 2px solid #f0c040; }")
            self.mode_lbl.setText(tr("placement.esc").format(text=text))
        else:
            self.view.unsetCursor()
            self.view.setStyleSheet("")
            self.mode_lbl.setText("")

    def _has_pending_placement(self) -> bool:
        return bool(
            self._pending_zone
            or self._pending_simple_zone
            or self._pending_exclusion_zone
            or self._pending_light_source
            or self._pending_template_object
            or self._pending_buoy
            or self._pending_create
            or self._pending_new_object
            or self._pending_conn
            or self._pending_new_system
            or self._pending_tradelane
            or self._pending_tl_reposition
            or self._pending_base
            or self._pending_dock_ring
        )

    def _cancel_pending_actions(self):
        if self._flight_lock_active:
            self._set_flight_mode(False)
            return
        had_placement = self._has_pending_placement() or self._measure_start is not None or self._measure_line is not None
        had_selection = self._selected is not None or bool(self._multi_selected)
        had_any = (
            had_placement
            or had_selection
        )
        if not had_any:
            return
        self._pending_zone = None
        self._pending_simple_zone = None
        self._pending_exclusion_zone = None
        self._pending_light_source = None
        self._pending_template_object = None
        self._pending_buoy = None
        self._pending_create = None
        self._pending_new_object = False
        self._pending_conn = None
        self._pending_new_system = None
        self._pending_tradelane = None
        self._pending_tl_reposition = None
        self._pending_base = None
        self._pending_dock_ring = None
        self._remove_tl_rubber_line()
        self._remove_zone_rubber_ellipse()
        self._remove_dock_ring_orbit()
        self._clear_measure_line()
        if self._pending_snapshots:
            self._pending_snapshots.clear()
            self.save_conn_btn.setVisible(False)
            self.create_conn_btn.setEnabled(True)
        self._set_placement_mode(False)
        if had_selection:
            self._cancel_selection()
        if had_placement:
            self.statusBar().showMessage(tr("status.placement_cancelled"))

    # ==================================================================
    #  3D/2D Umschaltung
    # ==================================================================
    def _toggle_3d_view(self, enabled: bool):
        if enabled and not self._filepath:
            self.view3d_switch.blockSignals(True)
            self.view3d_switch.setChecked(False)
            self.view3d_switch.blockSignals(False)
            self.center_stack.setCurrentWidget(self.view)
            self.statusBar().showMessage(tr("status.3d_disabled"))
            self._sync_flight_button_visibility()
            return
        if enabled:
            self.center_stack.setCurrentWidget(self.view3d)
            self._refresh_3d_scene()
            self.view3d.set_selected(self._selected)
            if self._selected is not None:
                self.view3d.center_on_item(self._selected)
            self.statusBar().showMessage(tr("status.3d_active"))
            self._sync_flight_button_visibility()
        else:
            if self._flight_lock_active:
                self._set_flight_mode(False)
            self.center_stack.setCurrentWidget(self.view)
            self.statusBar().showMessage(tr("status.2d_active"))
            self._sync_flight_button_visibility()

    def _on_3d_object_selected(self, obj):
        if isinstance(obj, ZoneItem):
            self._select_zone(obj)
        else:
            self._select(obj)

    def _on_3d_height_delta(self, obj, delta_world: float):
        if self._flight_lock_active:
            return
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
        if self._flight_lock_active:
            return
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

    def _refresh_3d_scene(self, force: bool = False, preserve_camera: bool = False):
        if not hasattr(self, "view3d"):
            return
        if not force and (not self.view3d_switch.isVisible() or not self.view3d_switch.isChecked()):
            return
        cam_state = None
        if preserve_camera and hasattr(self.view3d, "get_camera_state"):
            cam_state = self.view3d.get_camera_state()
        zones = self._zones if self.zone_cb.isChecked() else []
        self.view3d.set_data(self._objects, zones, self._scale)
        if cam_state and hasattr(self.view3d, "set_camera_state"):
            self.view3d.set_camera_state(cam_state)
        self.view3d.set_selected(self._selected)
        self._apply_viewer_text_visibility()

    def _toggle_viewer_text(self, enabled: bool):
        self._viewer_text_visible = bool(enabled)
        self._apply_viewer_text_visibility()

    def _apply_viewer_text_visibility(self):
        for obj in self._objects:
            if hasattr(obj, "set_label_visibility"):
                obj.set_label_visibility(self._viewer_text_visible)
        for zone in self._zones:
            if hasattr(zone, "set_label_visibility"):
                zone.set_label_visibility(self._viewer_text_visible)
        if hasattr(self, "view3d") and hasattr(self.view3d, "set_label_visibility"):
            self.view3d.set_label_visibility(self._viewer_text_visible)

    # ==================================================================
    #  Laden  (Browser-Klick / Manuell / Universum)
    # ==================================================================
    def _load_from_browser(self, path: str):
        if self._filepath and path != self._filepath:
            if not self._confirm_save_if_dirty(tr("msg.unsaved_text").split("\n")[0]):
                return
        self._filepath = path
        self._populate_quick_editor_options()
        self._load(path)
        self.browser.highlight_current(path)

    def _load_universe_action(self):
        if self._filepath and not self._confirm_save_if_dirty(tr("action.universe")):
            return
        path = self.browser.path_edit.text().strip()
        if path:
            self._load_universe(path)
        else:
            QMessageBox.warning(self, tr("msg.no_path"),
                                tr("msg.no_path_text"))

    def _show_help(self):
        """HTML-Hilfeseite in einem eigenen Fenster anzeigen."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout
        from PySide6.QtWebEngineWidgets import QWebEngineView
        from PySide6.QtCore import QUrl
        base_dir = Path(__file__).parent
        lang = "en" if get_language() == "en" else "de"
        help_candidates = [
            base_dir / "help" / f"index_{lang}.html",
            base_dir / "help" / "index_de.html",
            base_dir / "help_en.html",
            base_dir / "help.html",
        ]
        help_path = next((p for p in help_candidates if p.exists()), help_candidates[-1])
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("app.title_help"))
        dlg.resize(900, 700)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(0, 0, 0, 0)
        web = QWebEngineView()
        web.setUrl(QUrl.fromLocalFile(str(help_path)))
        lay.addWidget(web)
        dlg.exec()

    def _show_about(self):
        """About-Dialog für FL Atlas anzeigen."""
        from PySide6.QtWidgets import QMessageBox
        from PySide6.QtCore import Qt
        about_text = (
            "<h2>FL Atlas</h2>"
            f"<p><b>{tr('about.version_label')}</b> {tr('about.version')}</p>"
            f"<p><b>{tr('about.author_label')}</b> {tr('about.author')}</p>"
            f"<p><b>{tr('about.license_label')}</b> {tr('about.license')}</p>"
            "<hr>"
            f"<p>{tr('about.description')}</p>"
            f"<p>{tr('about.features')}</p>"
            "<hr>"
            f"<p><b>{tr('about.tech_label')}</b> {tr('about.tech')}</p>"
            f"<p><b>{tr('about.game_label')}</b> {tr('about.game')}</p>"
            f"<p style='color:gray; font-size:small;'>{tr('about.copyright')}</p>"
        )
        msg = QMessageBox(self)
        msg.setWindowTitle(tr("app.title_about"))
        msg.setTextFormat(Qt.RichText)
        msg.setText(about_text)
        # Logo als Icon im About-Dialog
        logo_path = self._ICON_DIR / "FLAtlas-Logo-128.png"
        if logo_path.exists():
            msg.setIconPixmap(QPixmap(str(logo_path)))
        else:
            msg.setIcon(QMessageBox.Information)
        msg.exec()

    def _open_manual(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("msg.open_ini"), "", "INI (*.ini);;" + tr("msg.all_files")
        )
        if path:
            if self._filepath and path != self._filepath:
                if not self._confirm_save_if_dirty(tr("action.open_3d")):
                    return
            self._filepath = path
            self._load(path)
            self.browser.highlight_current(path)

    def closeEvent(self, event):
        if self._confirm_save_if_dirty(tr("action.universe")):
            event.accept()
        else:
            event.ignore()

    def _confirm_save_if_dirty(self, action_desc: str) -> bool:
        if not self._dirty or not self._filepath:
            return True
        ans = QMessageBox.question(
            self,
            tr("msg.unsaved_title"),
            tr("msg.unsaved_text").format(action=action_desc),
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
        if self._flight_lock_active:
            self._set_flight_mode(False)
        self._populate_quick_editor_options(game_path)
        uni_ini = find_universe_ini(game_path)
        if not uni_ini:
            QMessageBox.warning(self, tr("msg.error"), tr("msg.universe_not_found"))
            return

        self._uni_ini_path = uni_ini
        self._uni_sections = self._parser.parse(str(uni_ini))

        systems = find_all_systems(game_path, self._parser)
        if not systems:
            QMessageBox.warning(self, tr("msg.error"), tr("msg.no_systems"))
            return

        coords = []
        for s in systems:
            x, y = s.get("pos", (0.0, 0.0))
            coords.extend([abs(x), abs(y)])
        self._scale = 500.0 / (max(coords, default=1) or 1)
        self.view.set_world_scale(self._scale)
        self.view.set_zoom_out_limit_to_scene(True)
        self._set_system_zoom_controls_visible(False)

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
        self.flight_mode_btn.blockSignals(True)
        self.flight_mode_btn.setChecked(False)
        self.flight_mode_btn.blockSignals(False)
        self._sync_flight_button_visibility()
        self.center_stack.setCurrentWidget(self.view)

        coord_map = {}
        for s in systems:
            x, y = s.get("pos", (0.0, 0.0))
            coord_map[s["nickname"].upper()] = (x * self._scale, y * self._scale)

        for s in systems:
            sys_item = UniverseSystem(
                s["nickname"], s["path"], s.get("pos", (0.0, 0.0)), self._scale
            )
            if hasattr(sys_item, "set_label_visibility"):
                sys_item.set_label_visibility(self._viewer_text_visible)
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

        # Weltraum-Wallpaper (Fallback: dunkle Farbe)
        self._apply_scene_wallpaper(QColor(6, 6, 18))

        # Szene-Rect begrenzen, damit man nicht ins Leere scrollen kann
        r = self.view._scene.itemsBoundingRect()
        margin = 60
        self.view._scene.setSceneRect(r.adjusted(-margin, -margin, margin, margin))

        self.info_lbl.setText(tr("info.universe").format(count=len(systems)))
        self.setWindowTitle(tr("app.title_universe"))
        self.statusBar().showMessage(tr("status.universe_loaded").format(count=len(systems)))
        if hasattr(self, "right_panel"):
            self.right_panel.setVisible(False)
        if hasattr(self, "legend_box"):
            self.legend_box.setVisible(False)
        if hasattr(self, "_status_grp"):
            self._status_grp.setVisible(False)
        self._new_system_action.setVisible(True)
        self._uni_save_action.setVisible(False)
        self._uni_undo_action.setVisible(False)
        self._uni_delete_action.setVisible(True)
        self.uni_delete_btn.setEnabled(False)
        self._ids_scan_action.setVisible(True)
        self._ids_import_action.setVisible(True)
        self._fit()
        self._sync_zoom_slider_from_view(self.view.current_zoom_factor())
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
        if self._flight_lock_active:
            self._set_flight_mode(False)
        self._pending_conn = None
        self._pending_create = None
        self._pending_light_source = None
        self._pending_new_object = False
        self._pending_tradelane = None
        self._pending_tl_reposition = None
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
        self.view.set_world_scale(self._scale)
        self.view.set_zoom_out_limit_to_scene(False)
        self._set_system_zoom_controls_visible(True)
        boundary_radius = rmax

        self.view._scene.clear()
        self.view._scene.setSceneRect(0, 0, 0, 0)  # Begrenzung aufheben
        self._apply_scene_wallpaper(QColor(8, 8, 15))
        self._objects, self._zones = [], []
        self._selected = None
        self._clear_selection_ui()
        self._hide_zone_extra_editors()

        for zd in raw_zones:
            try:
                zi = ZoneItem(zd, self._scale)
                if hasattr(zi, "set_label_visibility"):
                    zi.set_label_visibility(self._viewer_text_visible)
                self.view._scene.addItem(zi)
                self._zones.append(zi)
            except Exception:
                pass

        move_on = self.move_cb.isChecked()
        for od in raw_objs:
            try:
                obj = SolarObject(od, self._scale)
                if hasattr(obj, "set_label_visibility"):
                    obj.set_label_visibility(self._viewer_text_visible)
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
            tr("info.system").format(filename=Path(path).name, obj_count=len(self._objects), zone_count=len(self._zones))
        )
        self._rebuild_object_combo()
        self.setWindowTitle(tr("app.title_system").format(name=name))
        self.statusBar().showMessage(
            tr("status.system_loaded").format(name=name, obj_count=len(self._objects), zone_count=len(self._zones))
        )
        if hasattr(self, "right_panel"):
            self.right_panel.setVisible(True)
        if hasattr(self, "legend_box"):
            self.legend_box.setVisible(True)
        if hasattr(self, "_status_grp"):
            self._status_grp.setVisible(False)
        if hasattr(self, "left_stack"):
            self.left_stack.setCurrentWidget(self.left_ini_panel)
        self._new_system_action.setVisible(False)
        self._uni_save_action.setVisible(False)
        self._uni_undo_action.setVisible(False)
        self._uni_delete_action.setVisible(False)
        self.uni_delete_btn.setEnabled(False)
        self._ids_scan_action.setVisible(False)
        self._ids_import_action.setVisible(False)
        self.view3d_switch.setEnabled(True)
        self.view3d_switch.setVisible(True)
        self._set_dirty(False)
        if restore:
            self.view.setTransform(restore)
            self._sync_zoom_slider_from_view(self.view.current_zoom_factor())
        else:
            self._fit()
        self._refresh_3d_scene()
        self._populate_quick_editor_options()
        self._populate_system_options()
        self._refresh_system_fields()
        self._sync_flight_button_visibility()

    # ==================================================================
    #  Auswahl
    # ==================================================================
    def _clear_multi_selection(self):
        for it in list(self._multi_selected):
            if isinstance(it, SolarObject) and hasattr(it, "setPen") and hasattr(it, "pen"):
                try:
                    p = it.pen()
                    p.setColor(QColor(255, 255, 255, 70))
                    p.setWidth(1)
                    it.setPen(p)
                except Exception:
                    pass
        self._multi_selected.clear()

    def _toggle_multi_selection(self, it):
        if it in self._multi_selected:
            self._multi_selected.remove(it)
            if isinstance(it, SolarObject) and hasattr(it, "setPen") and hasattr(it, "pen"):
                p = it.pen()
                p.setColor(QColor(255, 255, 255, 70))
                p.setWidth(1)
                it.setPen(p)
        else:
            self._multi_selected.append(it)
            if isinstance(it, SolarObject) and hasattr(it, "setPen") and hasattr(it, "pen"):
                p = it.pen()
                p.setColor(QColor(120, 220, 255))
                p.setWidth(2)
                it.setPen(p)
        self.statusBar().showMessage(
            tr("status.multi_select_count").format(count=len(self._multi_selected))
        )

    def _on_2d_item_clicked(self, item, ctrl_held: bool):
        if self._filepath is None:
            return
        if not ctrl_held:
            return
        if isinstance(item, (SolarObject, ZoneItem)):
            self._toggle_multi_selection(item)

    def _select(self, obj: SolarObject):
        # Docking-Ring-Workflow: Planet-Auswahl abfangen
        if (self._pending_dock_ring
                and self._pending_dock_ring.get("step") == 1
                and isinstance(obj, SolarObject)
                and not hasattr(obj, "sys_path")):
            if not self._is_planet_object(obj):
                self.statusBar().showMessage("Bitte einen Planeten auswählen")
                return
            self._on_dock_ring_planet_selected(obj)
            return

        if hasattr(obj, "sys_path"):
            # Universum-System: Auswahl erlauben für Verschieben + Editor
            if self._selected and self._selected is not obj:
                self._selected._pos_change_cb = None
                self._selected._drag_finished_cb = None
                if hasattr(self._selected, "set_highlighted"):
                    self._selected.set_highlighted(False)
            self._selected = obj
            obj._pos_change_cb = self._on_universe_system_moved
            obj._drag_finished_cb = self._on_universe_drag_finished
            obj.set_highlighted(True)
            self.uni_delete_btn.setEnabled(True)
            self.statusBar().showMessage(tr("status.system_info").format(nickname=obj.nickname))
            self._show_uni_system_editor(obj.nickname)
            return

        if self._selected:
            self._selected._pos_change_cb = None
            self._selected._drag_finished_cb = None
            if (
                hasattr(self._selected, "setPen")
                and hasattr(self._selected, "pen")
                and self._selected not in self._multi_selected
            ):
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
            obj._drag_finished_cb = self._on_obj_drag_finished
            obj._last_scene_pos = (obj.pos().x(), obj.pos().y())
            obj._drag_snapshot_taken = False

        if obj not in self._multi_selected:
            self._clear_multi_selection()
        self.name_lbl.setText(f"📍 {obj.nickname}")
        self.editor.setPlainText(obj.raw_text())
        self.editor.setVisible(True)
        self.apply_btn.setVisible(True)
        self._hide_zone_extra_editors()
        self.edit_obj_btn.setEnabled(True)
        self.apply_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.preview3d_btn.setEnabled(True)
        self.add_exclusion_btn.setEnabled(False)
        self.statusBar().showMessage(tr("status.object_selected").format(nickname=obj.nickname))
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
        if self._flight_lock_active:
            self._set_flight_edit_lock(True)

    def _select_zone(self, zone):
        if self._pending_dock_ring and self._pending_dock_ring.get("step") == 1:
            # Klick auf Zone statt Planet: versuche passenden Planeten am Zonen-Zentrum zu finden.
            best_obj = None
            best_dist = None
            zx = zone.pos().x()
            zy = zone.pos().y()
            for obj in self._objects:
                if not isinstance(obj, SolarObject) or hasattr(obj, "sys_path"):
                    continue
                if not self._is_planet_object(obj):
                    continue
                dx = obj.pos().x() - zx
                dy = obj.pos().y() - zy
                d2 = dx * dx + dy * dy
                if best_dist is None or d2 < best_dist:
                    best_dist = d2
                    best_obj = obj
            if best_obj is not None and best_dist is not None and best_dist <= (25.0 * 25.0):
                self._on_dock_ring_planet_selected(best_obj)
                return
            self.statusBar().showMessage("Bitte einen Planeten auswählen")
            return

        if not self.zone_cb.isChecked():
            return
        if zone not in self._multi_selected:
            self._clear_multi_selection()
        self.name_lbl.setText(f"📍 {zone.nickname}")
        self.editor.setPlainText(zone.raw_text())
        self.editor.setVisible(True)
        self.apply_btn.setVisible(True)
        self._hide_zone_extra_editors()
        self.edit_obj_btn.setEnabled(True)
        self.apply_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.preview3d_btn.setEnabled(False)
        self.add_exclusion_btn.setEnabled(self._is_field_zone(zone.nickname))
        self.statusBar().showMessage(tr("status.zone_selected").format(nickname=zone.nickname))
        self._selected = zone
        self.view3d.set_selected(None)
        self._sync_obj_combo_to_selection()
        if self._flight_lock_active:
            self._set_flight_edit_lock(True)

    def _clear_selection_ui(self):
        """Setzt die UI-Elemente zurück wenn nichts ausgewählt ist."""
        if self._selected is not None:
            self._selected._pos_change_cb = None
            self._selected._drag_finished_cb = None
        self._clear_multi_selection()
        self._selected = None
        self.view3d.set_selected(None)
        self.apply_btn.setEnabled(False)
        self.edit_obj_btn.setEnabled(False)
        self.name_lbl.setText(tr("lbl.no_object"))
        self.editor.clear()
        self.editor.setVisible(True)
        self.apply_btn.setVisible(True)
        self.delete_btn.setEnabled(False)
        self.preview3d_btn.setEnabled(False)
        self.add_exclusion_btn.setEnabled(False)
        if hasattr(self, "uni_delete_btn"):
            self.uni_delete_btn.setEnabled(False)
        self.write_btn.setEnabled(False)
        if self._flight_lock_active:
            self._set_flight_edit_lock(True)

    def _cancel_selection(self):
        if self._selected is None and not self._multi_selected:
            return
        self._clear_selection_ui()
        self._hide_zone_extra_editors()
        self.obj_combo.blockSignals(True)
        self.obj_combo.setCurrentIndex(-1)
        self.obj_combo.blockSignals(False)
        self.statusBar().showMessage(tr("status.selection_cleared"))

    # ==================================================================
    #  Echtzeit-Position (Drag)
    # ==================================================================
    def _on_obj_moved(self, obj: SolarObject):
        if self._ed_busy or obj is not self._selected:
            return
        new_pos = obj.fl_pos_str()
        obj.data["_entries"] = [
            (k, new_pos if k.lower() == "pos" else v) for k, v in obj.data.get("_entries", [])
        ]
        obj.data["pos"] = new_pos
        self._sync_object_section_from_obj(obj)
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
        self._move_linked_docking_rings(obj)

    def _on_obj_drag_finished(self, obj: SolarObject, start_pos: QPointF, end_pos: QPointF):
        if obj is None:
            return
        obj._drag_snapshot_taken = False
        obj._last_scene_pos = (end_pos.x(), end_pos.y())
        _, cur_y, _ = parse_position(obj.data.get("pos", "0,0,0"))
        old_pos = self._scene_to_fl_pos_with_y(start_pos, cur_y)
        new_pos = self._scene_to_fl_pos_with_y(end_pos, cur_y)
        if old_pos != new_pos:
            self._push_undo_action(
                {
                    "type": "move_object",
                    "label": f"Objekt verschoben: {obj.nickname}",
                    "filepath": self._filepath or "",
                    "nickname": obj.nickname,
                    "old_pos": old_pos,
                    "new_pos": new_pos,
                }
            )
        sx = start_pos.x() / self._scale
        sz = start_pos.y() / self._scale
        ex = end_pos.x() / self._scale
        ez = end_pos.y() / self._scale
        self._append_change_log(
            f"Objekt verschoben: {obj.nickname} ({sx:.1f}, {sz:.1f}) → ({ex:.1f}, {ez:.1f})"
        )

    def _on_universe_drag_finished(self, obj: SolarObject, start_pos: QPointF, end_pos: QPointF):
        if obj is None:
            return
        sx = start_pos.x() / self._scale
        sy = start_pos.y() / self._scale
        ex = end_pos.x() / self._scale
        ey = end_pos.y() / self._scale
        if abs(sx - ex) > 1e-6 or abs(sy - ey) > 1e-6:
            self._push_undo_action(
                {
                    "type": "move_universe_system",
                    "label": f"System verschoben: {obj.nickname}",
                    "nickname": obj.nickname,
                    "old_x": sx,
                    "old_y": sy,
                    "new_x": ex,
                    "new_y": ey,
                }
            )
        self._append_change_log(
            f"System verschoben: {obj.nickname} ({sx:.0f}, {sy:.0f}) → ({ex:.0f}, {ey:.0f})"
        )

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
                self._sync_zone_section_from_zone(z)
                self._set_dirty(True)

    def _move_linked_docking_rings(self, obj: SolarObject):
        arch = obj.data.get("archetype", "").lower()
        if "planet" not in arch:
            return
        base_nick = obj.data.get("base", "").strip()
        if not base_nick:
            return

        prev_scene = getattr(obj, "_last_scene_pos", None)
        if prev_scene is None:
            prev_scene = (obj.pos().x(), obj.pos().y())
        dx = obj.pos().x() - prev_scene[0]
        dy = obj.pos().y() - prev_scene[1]
        if abs(dx) < 0.001 and abs(dy) < 0.001:
            obj._last_scene_pos = (obj.pos().x(), obj.pos().y())
            return

        bn_lower = base_nick.lower()
        for other in self._objects:
            if other is obj:
                continue
            if other.data.get("dock_with", "").strip().lower() != bn_lower:
                continue

            other.setPos(other.pos().x() + dx, other.pos().y() + dy)
            cur_pos_raw = other.data.get("pos", "0, 0, 0")
            cur_parts = [p.strip() for p in cur_pos_raw.split(",")]
            try:
                cur_y = float(cur_parts[1])
            except (ValueError, IndexError):
                cur_y = 0.0
            new_pos = (
                f"{other.pos().x() / self._scale:.2f}, "
                f"{cur_y:.2f}, "
                f"{other.pos().y() / self._scale:.2f}"
            )
            other.data["_entries"] = [
                (k, new_pos if k.lower() == "pos" else v)
                for k, v in other.data.get("_entries", [])
            ]
            other.data["pos"] = new_pos
            self._sync_object_section_from_obj(other)
            self.view3d.update_object_position(other, self._scale)
            self._set_dirty(True)
        obj._last_scene_pos = (obj.pos().x(), obj.pos().y())

    def _sync_object_section_from_obj(self, obj: SolarObject):
        try:
            obj_idx = self._objects.index(obj)
        except ValueError:
            return
        count = 0
        for i, (sec_name, _entries) in enumerate(self._sections):
            if sec_name.lower() != "object":
                continue
            if count == obj_idx:
                self._sections[i] = ("Object", list(obj.data.get("_entries", [])))
                return
            count += 1

    def _sync_zone_section_from_zone(self, zone: ZoneItem):
        try:
            zone_idx = self._zones.index(zone)
        except ValueError:
            return
        count = 0
        for i, (sec_name, _entries) in enumerate(self._sections):
            if sec_name.lower() != "zone":
                continue
            if count == zone_idx:
                self._sections[i] = ("Zone", list(zone.data.get("_entries", [])))
                return
            count += 1

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
        sel = self._selected
        self._sync_obj_combo_to_selection()
        if isinstance(sel, ZoneItem):
            self._edit_zone_population()
            return
        if not isinstance(sel, SolarObject):
            return

        entries = sel.data.get("_entries", [])
        arch = sel.data.get("archetype", "").lower()
        nick = sel.nickname.lower()
        has_base = any(k.lower() in ("base", "dock_with") and str(v).strip() for k, v in entries)
        is_tradelane = (
            "trade_lane_ring" in arch
            or "tradelane_ring" in arch
            or "trade_lane_ring" in nick
            or "tradelane_ring" in nick
        )

        if has_base:
            self._edit_base()
            return
        if is_tradelane:
            self._edit_tradelane()
            return
        self._open_generic_object_editor(sel)

    @staticmethod
    def _parse_vec3(raw: str, default: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> tuple[float, float, float]:
        vals = [s.strip() for s in str(raw or "").split(",")]
        out = [default[0], default[1], default[2]]
        for i in range(min(3, len(vals))):
            try:
                out[i] = float(vals[i])
            except ValueError:
                pass
        return out[0], out[1], out[2]

    def _open_generic_object_editor(self, obj: SolarObject):
        old_entries = [(str(k), str(v)) for k, v in obj.data.get("_entries", [])]
        old_nickname = str(obj.nickname)
        dlg = QDialog(self)
        dlg.setWindowTitle(f"{tr('btn.edit_object')}: {obj.nickname}")
        dlg.setModal(True)
        fl = QFormLayout(dlg)

        nick_edit = QLineEdit(obj.data.get("nickname", obj.nickname))
        arch_cb = QComboBox()
        arch_cb.setEditable(True)
        arch_vals = [self.arch_cb.itemText(i) for i in range(self.arch_cb.count()) if self.arch_cb.itemText(i)]
        arch_cb.addItems(arch_vals)
        arch_cb.setCurrentText(obj.data.get("archetype", ""))

        loadout_cb = QComboBox()
        loadout_cb.setEditable(True)
        loadout_vals = [self.loadout_cb.itemText(i) for i in range(self.loadout_cb.count()) if self.loadout_cb.itemText(i)]
        loadout_cb.addItems(loadout_vals)
        loadout_cb.setCurrentText(obj.data.get("loadout", ""))

        faction_cb = QComboBox()
        faction_cb.setEditable(True)
        faction_vals = [self.faction_cb.itemText(i) for i in range(self.faction_cb.count()) if self.faction_cb.itemText(i)]
        faction_cb.addItems(faction_vals)
        faction_cb.setCurrentText(obj.data.get("reputation", ""))

        px, py, pz = self._parse_vec3(obj.data.get("pos", "0,0,0"))
        rx, ry, rz = self._parse_vec3(obj.data.get("rotate", "0,0,0"))

        pos_x = QDoubleSpinBox()
        pos_y = QDoubleSpinBox()
        pos_z = QDoubleSpinBox()
        for spin, val in ((pos_x, px), (pos_y, py), (pos_z, pz)):
            spin.setRange(-10000000.0, 10000000.0)
            spin.setDecimals(2)
            spin.setValue(val)

        rot_x = QDoubleSpinBox()
        rot_y = QDoubleSpinBox()
        rot_z = QDoubleSpinBox()
        for spin, val in ((rot_x, rx), (rot_y, ry), (rot_z, rz)):
            spin.setRange(-360.0, 360.0)
            spin.setDecimals(2)
            spin.setValue(val)

        fl.addRow("Nickname", nick_edit)
        fl.addRow("Archetype", arch_cb)
        fl.addRow("Loadout", loadout_cb)
        fl.addRow("Reputation", faction_cb)
        fl.addRow("Pos X", pos_x)
        fl.addRow("Pos Y", pos_y)
        fl.addRow("Pos Z", pos_z)
        fl.addRow("Rot X", rot_x)
        fl.addRow("Rot Y", rot_y)
        fl.addRow("Rot Z", rot_z)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        fl.addRow(bb)

        if dlg.exec() != QDialog.Accepted:
            return

        new_map = {
            "nickname": nick_edit.text().strip(),
            "archetype": arch_cb.currentText().strip(),
            "loadout": loadout_cb.currentText().strip(),
            "reputation": faction_cb.currentText().strip(),
            "pos": f"{pos_x.value():.2f}, {pos_y.value():.2f}, {pos_z.value():.2f}",
            "rotate": f"{rot_x.value():.2f}, {rot_y.value():.2f}, {rot_z.value():.2f}",
        }

        entries = list(obj.data.get("_entries", []))
        changed_keys: set[str] = set()
        merged: list[tuple[str, str]] = []
        for k, v in entries:
            lk = k.lower()
            if lk in new_map and lk not in changed_keys:
                nv = new_map[lk]
                if nv:
                    merged.append((k, nv))
                changed_keys.add(lk)
            else:
                merged.append((k, v))
        for lk, nv in new_map.items():
            if lk not in changed_keys and nv:
                merged.append((lk, nv))

        obj.data["_entries"] = merged
        for k, v in merged:
            obj.data[k.lower()] = v
        obj.nickname = obj.data.get("nickname", obj.nickname)
        if obj.label:
            obj.label.setPlainText(obj.nickname)

        px2, _, pz2 = self._parse_vec3(obj.data.get("pos", "0,0,0"))
        obj.setPos(px2 * self._scale, pz2 * self._scale)

        obj_idx = None
        try:
            obj_idx = self._objects.index(obj)
        except ValueError:
            obj_idx = None
        if obj_idx is not None:
            count = 0
            for i, (sec_name, _) in enumerate(self._sections):
                if sec_name.lower() == "object":
                    if count == obj_idx:
                        self._sections[i] = ("Object", list(merged))
                        break
                    count += 1

        self.editor.setPlainText(obj.raw_text())
        self._rebuild_object_combo()
        self._selected = obj
        self._sync_obj_combo_to_selection()
        self.name_lbl.setText(f"📍 {obj.nickname}")
        new_entries = [(str(k), str(v)) for k, v in obj.data.get("_entries", [])]
        if new_entries != old_entries:
            try:
                obj_idx = self._objects.index(obj)
            except ValueError:
                obj_idx = None
            self._push_undo_action(
                {
                    "type": "edit_object",
                    "label": f"Objekt bearbeitet: {obj.nickname}",
                    "filepath": self._filepath or "",
                    "object_index": obj_idx,
                    "old_nickname": old_nickname,
                    "new_nickname": obj.nickname,
                    "old_entries": [list(p) for p in old_entries],
                    "new_entries": [list(p) for p in new_entries],
                }
            )
            self._append_change_log(f"Objekt bearbeitet: {old_nickname} -> {obj.nickname}")
        self._set_dirty(True)
        self._refresh_3d_scene()
        self.statusBar().showMessage(tr("status.changes_applied").format(nickname=obj.nickname))

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
        self.zone_file_lbl.setText(tr("lbl.zone_file_value").format(file=file_rel))
        try:
            self.zone_file_editor.setPlainText(
                linked_file.read_text(encoding="utf-8", errors="ignore")
            )
        except Exception as ex:
            self.zone_file_editor.setPlainText(tr("lbl.zone_file_error").format(error=ex))

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
            self.obj_combo.addItem(tr("lbl.no_items"))
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
        name = getattr(item, "nickname", tr("type.selection"))
        self.statusBar().showMessage(tr("status.centered").format(name=name))

    @staticmethod
    def _normalize_angle_180(val: float) -> float:
        # Freelancer arbeitet praktisch mit -180..180.
        x = (float(val) + 180.0) % 360.0 - 180.0
        if abs(x + 180.0) < 1e-9:
            return 180.0
        return x

    def _get_object_rotate(self, obj: SolarObject) -> tuple[float, float, float]:
        raw = str(obj.data.get("rotate", "0,0,0"))
        parts = [p.strip() for p in raw.split(",")]
        try:
            rx = float(parts[0]) if len(parts) > 0 else 0.0
        except ValueError:
            rx = 0.0
        try:
            ry = float(parts[1]) if len(parts) > 1 else 0.0
        except ValueError:
            ry = 0.0
        try:
            rz = float(parts[2]) if len(parts) > 2 else 0.0
        except ValueError:
            rz = 0.0
        return (rx, ry, rz)

    def _set_object_rotate(self, obj: SolarObject, rot_xyz: tuple[float, float, float]):
        rx = self._normalize_angle_180(rot_xyz[0])
        ry = self._normalize_angle_180(rot_xyz[1])
        rz = self._normalize_angle_180(rot_xyz[2])
        rotate_str = f"{rx:.0f}, {ry:.0f}, {rz:.0f}"
        entries = list(obj.data.get("_entries", []))
        replaced = False
        for i, (k, v) in enumerate(entries):
            if k.lower() == "rotate":
                entries[i] = (k, rotate_str)
                replaced = True
                break
        if not replaced:
            entries.append(("rotate", rotate_str))
        obj.data["_entries"] = entries
        obj.data["rotate"] = rotate_str
        try:
            obj.setRotation(ry)
        except Exception:
            pass
        if self._selected is obj:
            self.editor.setPlainText(obj.raw_text())

    def _rotate_selected_object(self, delta: float, axis: int = 1):
        obj = self._selected
        if not isinstance(obj, SolarObject) or hasattr(obj, "sys_path"):
            return
        rx, ry, rz = self._get_object_rotate(obj)
        rot = [rx, ry, rz]
        axis_idx = max(0, min(2, int(axis)))
        rot[axis_idx] = self._normalize_angle_180(rot[axis_idx] + float(delta))
        self._set_object_rotate(obj, (rot[0], rot[1], rot[2]))
        self._set_dirty(True)
        if hasattr(self, "view3d") and hasattr(self.view3d, "update_object_rotation"):
            self.view3d.update_object_rotation(obj)
        axis_name = ("X", "Y", "Z")[axis_idx]
        self.statusBar().showMessage(f"Rotation {axis_name}: {rot[axis_idx]:.0f}°")

    def _jump_to_linked_system(self, obj: SolarObject):
        goto_val = str(obj.data.get("goto", "")).strip()
        if not goto_val:
            self.statusBar().showMessage(tr("status.goto_missing"))
            return
        tokens = [t.strip() for t in goto_val.split(",") if t.strip()]
        if not tokens:
            self.statusBar().showMessage(tr("status.goto_missing"))
            return
        dest = tokens[0].upper()
        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        if not game_path:
            return
        dest_path = None
        try:
            for sys_ in find_all_systems(game_path, self._parser):
                if sys_.get("nickname", "").upper() == dest:
                    dest_path = sys_.get("path")
                    break
        except Exception:
            dest_path = None
        if not dest_path:
            self.statusBar().showMessage(tr("status.goto_not_found").format(dest=dest))
            return
        self._load_from_browser(dest_path)

    def _clear_measure_line(self):
        if self._measure_line is not None:
            try:
                self.view._scene.removeItem(self._measure_line)
            except Exception:
                pass
            self._measure_line = None
        if self._measure_label is not None:
            try:
                self.view._scene.removeItem(self._measure_label)
            except Exception:
                pass
            self._measure_label = None
        self._measure_start = None
        if not self._has_pending_placement():
            self._set_placement_mode(False)

    def _start_measure_from(self, pos: QPointF):
        if self._filepath is None:
            return
        self._clear_measure_line()
        self._measure_start = QPointF(pos.x(), pos.y())
        self._set_placement_mode(True, tr("placement.measure"))
        self.statusBar().showMessage(tr("status.measure_start"))

    def _finish_measure_to(self, pos: QPointF):
        if self._measure_start is None:
            return
        p0 = self._measure_start
        p1 = QPointF(pos.x(), pos.y())
        pen = QPen(QColor(245, 210, 85, 220), 2, Qt.DashLine)
        self._measure_line = self.view._scene.addLine(p0.x(), p0.y(), p1.x(), p1.y(), pen)
        self._measure_line.setZValue(9997)
        dist_km = (
            math.hypot(p1.x() - p0.x(), p1.y() - p0.y())
            / max(self._scale, 1e-9)
            / 1000.0
        )
        mid = QPointF((p0.x() + p1.x()) * 0.5, (p0.y() + p1.y()) * 0.5)
        self._measure_label = self.view._scene.addText(f"{dist_km:,.2f} km".replace(",", "."))
        self._measure_label.setDefaultTextColor(QColor(245, 210, 85))
        self._measure_label.setPos(mid.x() + 6, mid.y() + 6)
        self._measure_label.setZValue(9998)
        self._measure_start = None
        if not self._has_pending_placement():
            self._set_placement_mode(False)
        dist_text = f"{dist_km:,.2f}".replace(",", ".")
        self.statusBar().showMessage(tr("status.measure_distance").format(distance=dist_text))

    def _on_view_context_menu(self, scene_pos: QPointF, item):
        from PySide6.QtWidgets import QMenu

        if isinstance(item, ZoneItem):
            self._select_zone(item)
        elif isinstance(item, SolarObject):
            self._select(item)

        menu = QMenu(self)
        if isinstance(item, SolarObject) and hasattr(item, "sys_path"):
            act_open = menu.addAction(tr("ctx.open_system"))
            act_open.triggered.connect(lambda checked=False, p=item.sys_path: self._load_from_browser(p))
            if self._filepath is None:
                act_del_sys = menu.addAction(tr("ctx.delete_system"))
                act_del_sys.triggered.connect(lambda checked=False, o=item: self._delete_universe_system(o))
        elif isinstance(item, ZoneItem):
            act_edit = menu.addAction(tr("ctx.edit_zone"))
            act_edit.triggered.connect(self._start_object_edit)
            act_del = menu.addAction(tr("ctx.delete_zone"))
            act_del.triggered.connect(self._delete_object)
        elif isinstance(item, SolarObject):
            act_rot_l = menu.addAction(tr("ctx.rotate_y_neg"))
            act_rot_l.triggered.connect(lambda: self._rotate_selected_object(-15.0, axis=1))
            act_rot_r = menu.addAction(tr("ctx.rotate_y_pos"))
            act_rot_r.triggered.connect(lambda: self._rotate_selected_object(15.0, axis=1))
            arch = item.data.get("archetype", "").lower()
            if "jumpgate" in arch or "jumphole" in arch or "jump_gate" in arch or "jump_hole" in arch:
                act_jump = menu.addAction(tr("ctx.jump_target"))
                act_jump.triggered.connect(lambda checked=False, o=item: self._jump_to_linked_system(o))
            act_del = menu.addAction(tr("ctx.delete_object"))
            act_del.triggered.connect(self._delete_object)

        if self._filepath is not None:
            menu.addSeparator()
            if self._measure_start is None:
                act_m0 = menu.addAction(tr("ctx.measure_start"))
                act_m0.triggered.connect(lambda checked=False, p=QPointF(scene_pos.x(), scene_pos.y()): self._start_measure_from(p))
                if self._measure_line is not None:
                    act_md = menu.addAction(tr("ctx.measure_clear"))
                    act_md.triggered.connect(self._clear_measure_line)
            else:
                act_m1 = menu.addAction(tr("ctx.measure_end"))
                act_m1.triggered.connect(lambda checked=False, p=QPointF(scene_pos.x(), scene_pos.y()): self._finish_measure_to(p))
                act_mc = menu.addAction(tr("ctx.measure_cancel"))
                act_mc.triggered.connect(self._clear_measure_line)
            if self._selected is not None or self._multi_selected:
                menu.addSeparator()
                act_sc = menu.addAction(tr("ctx.clear_selection"))
                act_sc.triggered.connect(self._cancel_selection)

        if not menu.actions():
            return
        global_pos = self.view.mapToGlobal(self.view.mapFromScene(scene_pos))
        menu.exec(global_pos)

    def _delete_selected_universe_system(self):
        if self._filepath is not None:
            return
        if isinstance(self._selected, SolarObject) and hasattr(self._selected, "sys_path"):
            self._delete_universe_system(self._selected)

    def _delete_universe_system(self, sys_item: SolarObject):
        if self._filepath is not None:
            return
        if not hasattr(sys_item, "sys_path"):
            return
        sys_nick = getattr(sys_item, "nickname", "").strip()
        sys_path = getattr(sys_item, "sys_path", "")
        if not sys_nick or not sys_path or not self._uni_ini_path:
            return
        ans = QMessageBox.warning(
            self,
            tr("msg.delete_system_title"),
            tr("msg.delete_system_text").format(nickname=sys_nick),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return

        kept_sections: list[tuple[str, list[tuple[str, str]]]] = []
        removed = False
        for sec_name, entries in self._uni_sections:
            if sec_name.lower() != "system":
                kept_sections.append((sec_name, entries))
                continue
            nick_val = ""
            for k, v in entries:
                if k.lower() == "nickname":
                    nick_val = v.strip()
                    break
            if nick_val.upper() == sys_nick.upper():
                removed = True
                continue
            kept_sections.append((sec_name, entries))
        if not removed:
            return

        lines: list[str] = []
        for sec_name, entries in kept_sections:
            lines.append(f"[{sec_name}]")
            for k, v in entries:
                lines.append(f"{k} = {v}")
            lines.append("")
        self._uni_ini_path.write_text("\n".join(lines), encoding="utf-8")

        removed_links = self._remove_jump_objects_targeting_system(sys_nick, sys_path)

        try:
            p = Path(sys_path)
            if p.exists():
                p.unlink()
            parent = p.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
        except Exception:
            pass

        self._uni_sections = kept_sections
        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        if game_path:
            self._load_universe(game_path)
        self.statusBar().showMessage(
            tr("status.system_deleted_with_links").format(
                nickname=sys_nick,
                count=removed_links,
            )
        )

    def _remove_jump_objects_targeting_system(self, deleted_system_nick: str, deleted_sys_path: str) -> int:
        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        if not game_path:
            return 0
        deleted_upper = deleted_system_nick.upper()
        deleted_path = str(Path(deleted_sys_path).resolve())
        removed_total = 0
        try:
            systems = find_all_systems(game_path, self._parser)
        except Exception:
            return 0

        for sys_ in systems:
            path = sys_.get("path", "")
            if not path:
                continue
            try:
                if str(Path(path).resolve()) == deleted_path:
                    continue
                sections = self._parser.parse(path)
            except Exception:
                continue
            new_sections: list[tuple[str, list[tuple[str, str]]]] = []
            changed = False
            for sec_name, entries in sections:
                if sec_name.lower() != "object":
                    new_sections.append((sec_name, entries))
                    continue
                data = {}
                for k, v in entries:
                    lk = k.lower()
                    if lk not in data:
                        data[lk] = v
                arch = str(data.get("archetype", "")).lower()
                if "jumpgate" not in arch and "jumphole" not in arch and "jump_gate" not in arch and "jump_hole" not in arch:
                    new_sections.append((sec_name, entries))
                    continue
                goto_val = str(data.get("goto", "")).strip()
                target = ""
                if goto_val:
                    toks = [t.strip() for t in goto_val.split(",") if t.strip()]
                    if toks:
                        target = toks[0].upper()
                if target == deleted_upper:
                    changed = True
                    removed_total += 1
                    continue
                new_sections.append((sec_name, entries))
            if not changed:
                continue
            lines: list[str] = []
            for sec_name, entries in new_sections:
                lines.append(f"[{sec_name}]")
                for k, v in entries:
                    lines.append(f"{k} = {v}")
                lines.append("")
            try:
                Path(path).write_text("\n".join(lines), encoding="utf-8")
            except Exception:
                pass
        return removed_total

    # ==================================================================
    #  Erstellen  (Objekt, Zone, Sonne, Planet, Jump)
    # ==================================================================
    def _create_new_object(self):
        if not self._filepath:
            QMessageBox.warning(self, tr("msg.no_system"), tr("msg.no_system_text"))
            return
        self._pending_new_object = True
        self.statusBar().showMessage(tr("status.click_place_object"))
        self._set_placement_mode(True, tr("placement.object"))

    def _create_object_at_pos(self, pos: QPointF):
        archetypes = [self.arch_cb.itemText(i) for i in range(self.arch_cb.count()) if self.arch_cb.itemText(i)]
        loadouts = [self.loadout_cb.itemText(i) for i in range(self.loadout_cb.count()) if self.loadout_cb.itemText(i)]
        factions = [self.faction_cb.itemText(i) for i in range(self.faction_cb.count()) if self.faction_cb.itemText(i)]
        dlg = ObjectCreationDialog(self, archetypes, loadouts, factions)
        dlg.nick_edit.setText(
            self._suggest_system_scoped_name("object", [o.nickname for o in self._objects])
        )
        if dlg.exec() != QDialog.Accepted:
            self._pending_new_object = False
            return
        data_in = dlg.payload()
        nickname = data_in.get("nickname", "").strip() or self._suggest_system_scoped_name(
            "object", [o.nickname for o in self._objects]
        )
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
        if hasattr(obj, "set_label_visibility"):
            obj.set_label_visibility(self._viewer_text_visible)
        obj.setFlag(QGraphicsItem.ItemIsMovable, self.move_cb.isChecked())
        self.view._scene.addItem(obj)
        self._objects.append(obj)
        self._sections.append((section_name, list(entries)))
        self._rebuild_object_combo()
        self._select(obj)
        self._push_undo_action(
            {
                "type": "create_object",
                "label": f"Objekt erstellt: {obj.nickname}",
                "filepath": self._filepath or "",
                "nickname": obj.nickname,
            }
        )
        self._append_change_log(f"Objekt erstellt: {obj.nickname}")
        self._set_dirty(True)
        self._refresh_3d_scene()

    def _create_sun(self):
        if not self._filepath:
            QMessageBox.warning(self, tr("msg.no_system"), tr("msg.no_system_text"))
            return
        sun_arches = [
            self.arch_cb.itemText(i) for i in range(self.arch_cb.count())
            if "sun" in self.arch_cb.itemText(i).lower()
        ]
        if not sun_arches:
            sun_arches = ["sun"]
        stars = self._stars if self._stars else ["med_white_sun"]
        dlg = SolarCreationDialog(
            self, tr("dlg.sun_create"), sun_arches,
            default_radius=2000, default_damage=200000,
            stars=stars, default_star="med_white_sun",
        )
        dlg.nick_edit.setText(
            self._suggest_system_scoped_name("sun", [o.nickname for o in self._objects])
        )
        if dlg.exec() != QDialog.Accepted:
            return
        payload = dlg.payload()
        if not payload["nickname"]:
            QMessageBox.warning(self, tr("msg.incomplete"), tr("msg.enter_nickname"))
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
        self.statusBar().showMessage(tr("status.click_place_sun"))
        self._set_placement_mode(True, tr("placement.sun"))

    def _create_planet(self):
        if not self._filepath:
            QMessageBox.warning(self, tr("msg.no_system"), tr("msg.no_system_text"))
            return
        planet_arches = [
            self.arch_cb.itemText(i) for i in range(self.arch_cb.count())
            if "planet" in self.arch_cb.itemText(i).lower()
        ]
        if not planet_arches:
            planet_arches = ["planet"]
        dlg = SolarCreationDialog(
            self, tr("dlg.planet_create"), planet_arches,
            default_radius=1500, default_damage=200000,
        )
        dlg.nick_edit.setText(
            self._suggest_system_scoped_name("planet", [o.nickname for o in self._objects])
        )
        if dlg.exec() != QDialog.Accepted:
            return
        payload = dlg.payload()
        if not payload["nickname"]:
            QMessageBox.warning(self, tr("msg.incomplete"), tr("msg.enter_nickname"))
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
        self.statusBar().showMessage(tr("status.click_place_planet"))
        self._set_placement_mode(True, tr("placement.planet"))

    def _scan_light_source_options(self) -> tuple[list[str], list[str]]:
        """Sammelt bekannte LightSource-Typen und atten_curve-Werte aus Systemen."""
        type_vals: set[str] = {"DIRECTIONAL", "POINT"}
        atten_vals: set[str] = {"DYNAMIC_DIRECTION"}

        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        if game_path:
            try:
                for s in find_all_systems(game_path, self._parser):
                    try:
                        sections = self._parser.parse(s["path"])
                    except Exception:
                        continue
                    for sec_name, entries in sections:
                        if sec_name.lower() != "lightsource":
                            continue
                        for k, v in entries:
                            kl = k.lower()
                            vv = v.strip()
                            if kl == "type" and vv:
                                type_vals.add(vv.upper())
                            elif kl == "atten_curve" and vv:
                                atten_vals.add(vv)
            except Exception:
                pass

        for sec_name, entries in self._sections:
            if sec_name.lower() != "lightsource":
                continue
            for k, v in entries:
                kl = k.lower()
                vv = v.strip()
                if kl == "type" and vv:
                    type_vals.add(vv.upper())
                elif kl == "atten_curve" and vv:
                    atten_vals.add(vv)

        return sorted(type_vals), sorted(atten_vals, key=str.lower)

    def _start_light_source_creation(self):
        if not self._filepath:
            QMessageBox.warning(self, tr("msg.no_system"), tr("msg.no_system_text"))
            return

        sys_nick = Path(self._filepath).stem.upper()
        existing = set()
        for sec_name, entries in self._sections:
            if sec_name.lower() != "lightsource":
                continue
            for k, v in entries:
                if k.lower() == "nickname":
                    existing.add(v.strip().lower())
                    break
        n = 1
        while True:
            suggested = f"{sys_nick}_light_{n}"
            if suggested.lower() not in existing:
                break
            n += 1

        types, atten_curves = self._scan_light_source_options()
        dlg = LightSourceDialog(
            self,
            nickname=suggested,
            types=types,
            atten_curves=atten_curves,
        )
        if dlg.exec() != QDialog.Accepted:
            return

        payload = dlg.payload()
        nick = payload.get("nickname", "").strip()
        if not nick:
            QMessageBox.warning(self, tr("msg.incomplete"), tr("msg.enter_nickname"))
            return

        self._pending_light_source = payload
        self.statusBar().showMessage(tr("status.click_place_light"))
        self._set_placement_mode(True, tr("placement.light_source").format(name=nick))

    def _create_light_source_at_pos(self, pos: QPointF):
        pl = self._pending_light_source
        if not pl:
            return

        nickname = pl.get("nickname", "").strip()
        if not nickname:
            return

        pos_str = f"{pos.x() / self._scale:.2f}, 0, {pos.y() / self._scale:.2f}"
        entries: list[tuple[str, str]] = [
            ("nickname", nickname),
            ("pos", pos_str),
            ("color", pl.get("color", "255, 255, 255")),
            ("range", str(int(pl.get("range", 100000)))),
            ("type", pl.get("type", "DIRECTIONAL")),
            ("atten_curve", pl.get("atten_curve", "DYNAMIC_DIRECTION")),
        ]

        insert_idx = None
        for i, (sec_name, _entries) in enumerate(self._sections):
            if sec_name.lower() == "lightsource":
                insert_idx = i + 1
        if insert_idx is None:
            for i, (sec_name, _entries) in enumerate(self._sections):
                if sec_name.lower() == "object":
                    insert_idx = i
                    break

        if insert_idx is None:
            self._sections.append(("LightSource", entries))
        else:
            self._sections.insert(insert_idx, ("LightSource", entries))

        self._pending_light_source = None
        self._push_undo_action(
            {
                "type": "create_lightsource",
                "label": f"Lichtquelle erstellt: {nickname}",
                "filepath": self._filepath or "",
                "nickname": nickname,
            }
        )
        self._append_change_log(f"Lichtquelle erstellt: {nickname}")
        self._set_dirty(True)
        self.statusBar().showMessage(tr("status.light_source_created").format(nickname=nickname))

    @staticmethod
    def _filter_items_by_keywords(items: list[str], keywords: list[str]) -> list[str]:
        kws = [k.lower() for k in keywords]
        out = [
            item for item in items
            if any(k in item.lower() for k in kws)
        ]
        return sorted(set(out), key=str.lower)

    @staticmethod
    def _norm_name_token(value: str) -> str:
        token = re.sub(r"[^A-Za-z0-9_]+", "_", (value or "").strip())
        token = re.sub(r"_+", "_", token).strip("_")
        return token or "item"

    def _system_name_token(self) -> str:
        if not self._filepath:
            return "SYS"
        return self._norm_name_token(Path(self._filepath).stem.upper())

    def _suggest_system_scoped_name(self, kind: str, existing: list[str], width: int = 3) -> str:
        sys_tok = self._system_name_token()
        kind_tok = self._norm_name_token(kind).lower()
        prefix = f"{sys_tok}_{kind_tok}_"
        nums: list[int] = []
        pat = re.compile(rf"^{re.escape(prefix)}(\d+)$", re.IGNORECASE)
        for name in existing:
            m = pat.match(str(name).strip())
            if m:
                try:
                    nums.append(int(m.group(1)))
                except ValueError:
                    pass
        nxt = (max(nums) + 1) if nums else 1
        return f"{prefix}{nxt:0{width}d}"

    def _zone_art_from_input(self, raw_name: str, fallback_kind: str = "zone") -> str:
        sys_tok = self._system_name_token().lower()
        token = self._norm_name_token(raw_name).lower()
        if not token:
            return self._norm_name_token(fallback_kind).lower()
        if token.startswith("zone_"):
            token = token[5:]
        sys_prefix = f"{sys_tok}_"
        if token.startswith(sys_prefix):
            token = token[len(sys_prefix):]
        token = re.sub(r"_\d+$", "", token)
        token = self._norm_name_token(token).lower()
        return token or self._norm_name_token(fallback_kind).lower()

    def _suggest_zone_name(self, art: str, existing: list[str], width: int = 3) -> str:
        sys_tok = self._system_name_token()
        art_tok = self._norm_name_token(art).lower()
        prefix = f"Zone_{sys_tok}_{art_tok}_"
        nums: list[int] = []
        pat = re.compile(rf"^{re.escape(prefix)}(\d+)$", re.IGNORECASE)
        for name in existing:
            m = pat.match(str(name).strip())
            if m:
                try:
                    nums.append(int(m.group(1)))
                except ValueError:
                    pass
        nxt = (max(nums) + 1) if nums else 1
        return f"{prefix}{nxt:0{width}d}"

    @staticmethod
    def _is_planet_object(obj: SolarObject) -> bool:
        arch = str(obj.data.get("archetype", "")).lower()
        return "planet" in arch

    def _next_auto_object_nickname(self, prefix: str) -> str:
        existing = {o.nickname.lower() for o in self._objects}
        n = 1
        while True:
            candidate = f"{prefix}_{n:03d}"
            if candidate.lower() not in existing:
                return candidate
            n += 1

    def _collect_category_templates(self, arche_keywords: list[str], loadout_keywords: list[str], *, strict: bool = False) -> tuple[list[str], list[str]]:
        archetypes = [self.arch_cb.itemText(i) for i in range(self.arch_cb.count()) if self.arch_cb.itemText(i)]
        loadouts = [self.loadout_cb.itemText(i) for i in range(self.loadout_cb.count()) if self.loadout_cb.itemText(i)]

        if strict:
            arch_filtered = [a for a in archetypes if any(k == a.lower() for k in arche_keywords)]
        else:
            arch_filtered = self._filter_items_by_keywords(archetypes, arche_keywords)
        load_filtered = self._filter_items_by_keywords(loadouts, loadout_keywords)

        if not arch_filtered:
            arch_filtered = sorted(set(archetypes), key=str.lower)
        return arch_filtered, load_filtered

    def _start_category_object_creation(
        self,
        *,
        title: str,
        arche_keywords: list[str],
        loadout_keywords: list[str],
        nick_prefix: str,
        status_key: str,
        placement_key: str,
        show_reputation: bool = False,
        strict_arche: bool = False,
    ):
        if not self._filepath:
            QMessageBox.warning(self, tr("msg.no_system"), tr("msg.no_system_text"))
            return
        factions = list(self._cached_factions) if self._cached_factions else []
        arches, loads = self._collect_category_templates(arche_keywords, loadout_keywords, strict=strict_arche)
        dlg = CategoryObjectDialog(self, title=title, archetypes=arches, loadouts=loads, factions=factions, show_reputation=show_reputation)
        if dlg.exec() != QDialog.Accepted:
            return
        payload = dlg.payload()
        archetype = payload.get("archetype", "").strip()
        if not archetype:
            QMessageBox.warning(self, tr("msg.incomplete"), tr("msg.enter_name"))
            return

        sys_nick = Path(self._filepath).stem.upper()
        prefix = f"{sys_nick}_{nick_prefix}"
        auto_nick = self._next_auto_object_nickname(prefix)
        self._pending_template_object = {
            "nickname": auto_nick,
            "archetype": archetype,
            "loadout": payload.get("loadout", "").strip(),
            "faction": payload.get("faction", "").strip() if show_reputation else None,
            "rep": payload.get("rep", "").strip() if show_reputation else None,
            "status_key": status_key,
        }
        self.statusBar().showMessage(tr(status_key))
        self._set_placement_mode(True, tr(placement_key).format(name=auto_nick))

    def _create_template_object_at_pos(self, pos: QPointF):
        pt = self._pending_template_object
        if not pt:
            return
        nickname = pt.get("nickname", "").strip()
        archetype = pt.get("archetype", "").strip()
        if not nickname or not archetype:
            self._pending_template_object = None
            return

        pos_str = f"{pos.x() / self._scale:.2f}, 0, {pos.y() / self._scale:.2f}"
        entries: list[tuple[str, str]] = [
            ("nickname", nickname),
            ("ids_name", "0"),
            ("ids_info", "0"),
            ("pos", pos_str),
            ("rotate", "0,0,0"),
            ("archetype", archetype),
        ]
        loadout = pt.get("loadout", "").strip()
        if loadout:
            entries.append(("loadout", loadout))
        if pt.get("faction") or pt.get("rep"):
            faction = pt.get("faction", "").strip()
            rep = pt.get("rep", "").strip()
            if faction:
                entries.append(("reputation", f"{faction},{rep}" if rep else faction))

        self._add_object_from_entries(entries, "Object")
        self._pending_template_object = None

    def _start_wreck_creation(self):
        # Wrack/Suprise: alle Archetypen mit "wreck" oder "surprise" im Namen, keine strikte depot-Filterung
        self._start_category_object_creation(
            title=tr("dlg.wreck_create"),
            arche_keywords=["wreck", "surprise", "suprise"],
            loadout_keywords=["surprise", "suprise", "wreck"],
            nick_prefix="Wreck",
            status_key="status.click_place_wreck",
            placement_key="placement.wreck",
            show_reputation=False,
            strict_arche=False,
        )

    def _start_weapon_platform_creation(self):
        self._start_category_object_creation(
            title=tr("dlg.weapon_platform_create"),
            arche_keywords=["weapon", "platform"],
            loadout_keywords=["weapon", "platform"],
            nick_prefix="Weapon_Platform",
            status_key="status.click_place_weapon_platform",
            placement_key="placement.weapon_platform",
            show_reputation=True,
            strict_arche=False,
        )

    def _start_depot_creation(self):
        self._start_category_object_creation(
            title=tr("dlg.depot_create"),
            arche_keywords=["depot"],
            loadout_keywords=["depot"],
            nick_prefix="Depot",
            status_key="status.click_place_depot",
            placement_key="placement.depot",
            show_reputation=True,
            strict_arche=False,
        )

    def _start_buoy_creation(self):
        if not self._filepath:
            QMessageBox.warning(self, tr("msg.no_system"), tr("msg.no_system_text"))
            return
        dlg = BuoyDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        data = dlg.payload()
        self._pending_buoy = {"step": 1, **data}
        if data.get("pattern", "LINE").upper() == "SINGLE":
            self.statusBar().showMessage(tr("status.click_place_buoy_single"))
            self._set_placement_mode(True, tr("placement.buoy_single"))
        else:
            self.statusBar().showMessage(tr("status.click_place_buoy_start"))
            self._set_placement_mode(True, tr("placement.buoy_start"))

    def _create_buoy_entries(self, buoy_type: str, pos: QPointF, index: int) -> list[tuple[str, str]]:
        sys_nick = Path(self._filepath).stem.upper() if self._filepath else "SYS"
        prefix = f"{sys_nick}_{buoy_type.upper()}"
        nickname = self._next_auto_object_nickname(prefix)
        pos_str = f"{pos.x() / self._scale:.2f}, 0, {pos.y() / self._scale:.2f}"
        if buoy_type == "hazard_buoy":
            ids_name = "261163"
            ids_info = "66144"
        elif buoy_type == "nav_buoy":
            ids_name = "261162"
            ids_info = "66147"
        else:
            ids_name = "0"
            ids_info = "0"
        return [
            ("nickname", nickname),
            ("ids_name", ids_name),
            ("ids_info", ids_info),
            ("pos", pos_str),
            ("rotate", "0,0,0"),
            ("archetype", buoy_type),
        ]

    def _create_buoys_line(self, start: QPointF, end: QPointF, buoy_type: str, count: int):
        for i in range(count):
            t = 0.0 if count <= 1 else i / (count - 1)
            p = QPointF(
                start.x() + (end.x() - start.x()) * t,
                start.y() + (end.y() - start.y()) * t,
            )
            self._add_object_from_entries(self._create_buoy_entries(buoy_type, p, i), "Object")

    def _create_buoys_circle(self, center: QPointF, radius_scene: float, buoy_type: str, count: int):
        for i in range(count):
            angle = (2.0 * math.pi * i) / max(1, count)
            p = QPointF(
                center.x() + math.cos(angle) * radius_scene,
                center.y() + math.sin(angle) * radius_scene,
            )
            self._add_object_from_entries(self._create_buoy_entries(buoy_type, p, i), "Object")

    def _on_buoy_click(self, pos: QPointF):
        pb = self._pending_buoy
        if not pb:
            return
        step = pb.get("step", 1)
        pattern = pb.get("pattern", "LINE")
        buoy_type = pb.get("buoy_type", "nav_buoy")
        count = int(pb.get("count", 8))

        if pattern == "SINGLE":
            self._add_object_from_entries(self._create_buoy_entries(buoy_type, pos, 0), "Object")
            self._pending_buoy = None
            self.statusBar().showMessage(tr("status.buoy_created").format(count=1, buoy_type=buoy_type))
            return

        if step == 1:
            pb["start"] = pos
            pb["step"] = 2
            if pattern == "LINE":
                pen = QPen(QColor(80, 180, 220, 180), 2, Qt.DashLine)
                self._tl_rubber_line = self.view._scene.addLine(pos.x(), pos.y(), pos.x(), pos.y(), pen)
                self._tl_rubber_line.setZValue(9999)
                self.view.mouse_moved.connect(self._update_tl_rubber_line)
            else:
                pen = QPen(QColor(80, 180, 220, 200), 2, Qt.DashLine)
                brush = QBrush(QColor(80, 180, 220, 20))
                # Shape aus Dialog holen, falls vorhanden
                shape = None
                if self._pending_zone and "shape" in self._pending_zone:
                    shape = self._pending_zone["shape"].upper()
                elif self._pending_simple_zone and "shape" in self._pending_simple_zone:
                    shape = self._pending_simple_zone["shape"].upper()
                elif self._pending_exclusion_zone and "shape" in self._pending_exclusion_zone:
                    shape = self._pending_exclusion_zone["shape"].upper()
                else:
                    shape = "SPHERE"
                if shape == "BOX":
                    self._zone_rubber_ellipse = QGraphicsRectItem(pos.x(), pos.y(), 0, 0)
                    self._zone_rubber_ellipse.setPen(pen)
                    self._zone_rubber_ellipse.setBrush(brush)
                    self.view._scene.addItem(self._zone_rubber_ellipse)
                else:
                    self._zone_rubber_ellipse = self.view._scene.addEllipse(pos.x(), pos.y(), 0, 0, pen, brush)
                self._zone_rubber_ellipse.setZValue(9999)
                self._zone_rubber_origin = pos
                self.view.mouse_moved.connect(self._update_zone_rubber_ellipse)
            self.statusBar().showMessage(tr("status.click_place_buoy_end"))
            self.mode_lbl.setText(tr("placement.esc").format(text=tr("placement.buoy_end")))
            return

        start = pb.get("start", pos)
        if pattern == "LINE":
            self._remove_tl_rubber_line()
            self._create_buoys_line(start, pos, buoy_type, count)
        else:
            self._remove_zone_rubber_ellipse()
            radius_scene = max(10.0, math.hypot(pos.x() - start.x(), pos.y() - start.y()))
            self._create_buoys_circle(start, radius_scene, buoy_type, count)

        self._pending_buoy = None
        self.statusBar().showMessage(tr("status.buoy_created").format(count=count, buoy_type=buoy_type))

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
        if hasattr(z_item, "set_label_visibility"):
            z_item.set_label_visibility(self._viewer_text_visible)
        self.view._scene.addItem(z_item)
        self._zones.append(z_item)
        self._sections.append(("Zone", list(zone_entries)))

        self._rebuild_object_combo()
        self._select(obj)
        self._set_dirty(True)
        created_typ = tr("type.sun") if spec.get("kind") == "sun" else tr("type.planet")
        self.statusBar().showMessage(tr("status.death_zone_created").format(type=created_typ, nickname=spec['nickname']))
        self._pending_create = None
        self._refresh_3d_scene()

    # ------------------------------------------------------------------
    #  Tradelane-Generator
    # ------------------------------------------------------------------
    def _start_tradelane_creation(self):
        if not self._filepath:
            QMessageBox.warning(self, tr("msg.no_system"), tr("msg.no_system_text"))
            return
        self._pending_tradelane = {"step": 1}
        self.statusBar().showMessage(tr("status.click_tl_start"))
        self._set_placement_mode(True, tr("placement.tl_start"))

    def _on_tradelane_click(self, pos: QPointF):
        step = self._pending_tradelane.get("step", 1) if self._pending_tradelane else 1
        if step == 1:
            self._pending_tradelane["start"] = pos
            self._pending_tradelane["step"] = 2
            # Rubber-Band-Linie starten
            pen = QPen(QColor(255, 200, 50, 180), 2, Qt.DashLine)
            self._tl_rubber_line = self.view._scene.addLine(
                pos.x(), pos.y(), pos.x(), pos.y(), pen
            )
            self._tl_rubber_line.setZValue(9999)
            self.view.mouse_moved.connect(self._update_tl_rubber_line)
            self.statusBar().showMessage(tr("status.click_tl_end"))
            self.mode_lbl.setText(tr("placement.esc").format(text=tr("placement.tl_end")))
        elif step == 2:
            self._pending_tradelane["end"] = pos
            self._remove_tl_rubber_line()
            self._set_placement_mode(False)
            self._show_tradelane_dialog()

    def _update_tl_rubber_line(self, scene_pos: QPointF):
        if self._tl_rubber_line:
            line = self._tl_rubber_line.line()
            self._tl_rubber_line.setLine(
                line.x1(), line.y1(), scene_pos.x(), scene_pos.y()
            )

    def _remove_tl_rubber_line(self):
        if self._tl_rubber_line:
            self.view._scene.removeItem(self._tl_rubber_line)
            self._tl_rubber_line = None
            try:
                self.view.mouse_moved.disconnect(self._update_tl_rubber_line)
            except RuntimeError:
                pass

    # ------------------------------------------------------------------
    #  Zonen-Größen-Vorschau (Rubber-Band-Ellipse)
    # ------------------------------------------------------------------
    def _update_zone_rubber_ellipse(self, scene_pos: QPointF):
        if self._zone_rubber_ellipse and self._zone_rubber_origin:
            ox, oy = self._zone_rubber_origin.x(), self._zone_rubber_origin.y()
            shape = None
            if self._pending_zone and "shape" in self._pending_zone:
                shape = self._pending_zone["shape"].upper()
            elif self._pending_simple_zone and "shape" in self._pending_simple_zone:
                shape = self._pending_simple_zone["shape"].upper()
            elif self._pending_exclusion_zone and "shape" in self._pending_exclusion_zone:
                shape = self._pending_exclusion_zone["shape"].upper()
            else:
                shape = "SPHERE"
            if shape == "BOX" and self._pending_exclusion_zone:
                # Draw rectangle from first click to current mouse position (scene coordinates)
                x0, y0 = ox, oy
                x1, y1 = scene_pos.x(), scene_pos.y()
                left = min(x0, x1)
                top = min(y0, y1)
                width = abs(x1 - x0)
                height = abs(y1 - y0)
                self._zone_rubber_ellipse.setRect(left, top, width, height)
            else:
                dx = abs(scene_pos.x() - ox)
                dy = abs(scene_pos.y() - oy)
                self._zone_rubber_ellipse.setRect(
                    ox - dx, oy - dy, 2 * dx, 2 * dy
                )

    def _remove_zone_rubber_ellipse(self):
        if self._zone_rubber_ellipse:
            self.view._scene.removeItem(self._zone_rubber_ellipse)
            self._zone_rubber_ellipse = None
            self._zone_rubber_origin = None
            try:
                self.view.mouse_moved.disconnect(self._update_zone_rubber_ellipse)
            except RuntimeError:
                pass

    def _show_tradelane_dialog(self):
        tl = self._pending_tradelane
        if not tl:
            return
        start: QPointF = tl["start"]
        end: QPointF = tl["end"]
        sx, sz = start.x() / self._scale, start.y() / self._scale
        ex, ez = end.x() / self._scale, end.y() / self._scale
        dist = math.sqrt((ex - sx) ** 2 + (ez - sz) ** 2)
        spacing = 7500.0
        ring_count = max(2, round(dist / spacing) + 1)

        system_nick = Path(self._filepath).stem
        # Finde nächste freie Ring-Nummer
        max_num = 0
        prefix = f"{system_nick}_Trade_Lane_Ring_".lower()
        for o in self._objects:
            nn = o.nickname.lower()
            if nn.startswith(prefix):
                try:
                    num = int(nn[len(prefix):])
                    max_num = max(max_num, num)
                except ValueError:
                    pass
        start_num = max_num + 1

        # Factions aus Cache
        factions = list(self._cached_factions) if self._cached_factions else []

        dlg = TradeLaneDialog(
            self,
            system_nick=system_nick,
            start_num=start_num,
            ring_count=ring_count,
            distance=dist,
            factions=factions,
        )
        if dlg.exec() != QDialog.Accepted:
            self._pending_tradelane = None
            return
        payload = dlg.payload()
        self._generate_tradelane(sx, sz, ex, ez, payload, system_nick)
        self._pending_tradelane = None

    def _generate_tradelane(self, sx: float, sz: float,
                            ex: float, ez: float,
                            cfg: dict, system_nick: str):
        """Erzeugt alle Trade_Lane_Ring-Objekte zwischen Start und Ende."""
        count = cfg["ring_count"]
        start_num = cfg["start_num"]

        # Richtungsvektor und gleichmäßige Abstände
        dx = ex - sx
        dz = ez - sz

        # Rotation: Y-Winkel = Richtung der Lane (Grad)
        # Freelancer-Konvention: Ring zeigt entgegen der Flugrichtung → +180°
        angle_rad = math.atan2(dx, dz)
        angle_deg = math.degrees(angle_rad) + 180.0
        if angle_deg > 180.0:
            angle_deg -= 360.0
        rotate_str = f"0, {angle_deg:.0f}, 0"

        for i in range(count):
            t = i / max(count - 1, 1)
            px = sx + dx * t
            pz = sz + dz * t
            pos_str = f"{px:.0f}, 0, {pz:.0f}"
            num = start_num + i
            nickname = f"{system_nick}_Trade_Lane_Ring_{num}"

            entries: list[tuple[str, str]] = [
                ("nickname", nickname),
                ("ids_name", cfg["ids_name"]),
                ("pos", pos_str),
                ("rotate", rotate_str),
                ("Archetype", "Trade_Lane_Ring"),
                ("ids_info", "66170"),
            ]

            # prev_ring / next_ring  (doubly linked list)
            if i > 0:
                prev_nick = f"{system_nick}_Trade_Lane_Ring_{start_num + i - 1}"
                entries.append(("prev_ring", prev_nick))
            if i < count - 1:
                next_nick = f"{system_nick}_Trade_Lane_Ring_{start_num + i + 1}"
                entries.append(("next_ring", next_nick))

            entries.append(("behavior", "NOTHING"))
            entries.append(("difficulty_level", str(cfg["difficulty_level"])))
            entries.append(("loadout", cfg["loadout"]))
            entries.append(("pilot", cfg["pilot"]))
            if cfg["reputation"]:
                entries.append(("reputation", cfg["reputation"]))

            # tradelane_space_name nur auf erstem und letztem Ring
            if i == 0 and cfg.get("space_name_start", "0") != "0":
                entries.append(("tradelane_space_name", cfg["space_name_start"]))
            elif i == count - 1 and cfg.get("space_name_end", "0") != "0":
                entries.append(("tradelane_space_name", cfg["space_name_end"]))

            self._add_object_from_entries(entries, "Object")

        self.statusBar().showMessage(
            tr("status.tl_created_detail").format(
                count=count,
                first=f"{system_nick}_Trade_Lane_Ring_{start_num}",
                last=f"{system_nick}_Trade_Lane_Ring_{start_num + count - 1}"
            )
        )

    # ------------------------------------------------------------------
    #  Tradelane-Routen bearbeiten (Erkennung, Löschen, Repositionieren)
    # ------------------------------------------------------------------
    def _find_tradelane_chains(self) -> list[list[dict]]:
        """Erkennt zusammengehörige Trade-Lane-Ringe über prev_ring/next_ring.

        Gibt eine Liste von Ketten zurück; jede Kette ist eine geordnete
        Liste von Dicts mit nickname, pos, rotate, loadout, prev_ring, next_ring,
        und einem Verweis auf das SolarObject (_obj).
        """
        # Alle TL-Ringe nach Nickname indizieren
        tl_map: dict[str, SolarObject] = {}
        for obj in self._objects:
            arch = obj.data.get("archetype", "").lower()
            name = obj.nickname.lower()
            if "trade_lane_ring" in arch or "trade_lane_ring" in name:
                tl_map[obj.nickname.lower()] = obj

        visited: set[str] = set()
        chains: list[list[dict]] = []

        for nick_lc, obj in tl_map.items():
            if nick_lc in visited:
                continue
            # Zum Anfang der Kette laufen
            cur = obj
            while True:
                prev = cur.data.get("prev_ring", "").strip().lower()
                if prev and prev in tl_map and prev not in visited:
                    cur = tl_map[prev]
                else:
                    break
            # Kette vorwärts aufbauen
            chain: list[dict] = []
            while cur:
                nn = cur.nickname.lower()
                if nn in visited:
                    break
                visited.add(nn)
                chain.append({
                    "nickname": cur.nickname,
                    "pos": cur.data.get("pos", ""),
                    "rotate": cur.data.get("rotate", ""),
                    "loadout": cur.data.get("loadout", ""),
                    "prev_ring": cur.data.get("prev_ring", ""),
                    "next_ring": cur.data.get("next_ring", ""),
                    "_obj": cur,
                })
                nxt = cur.data.get("next_ring", "").strip().lower()
                cur = tl_map.get(nxt) if nxt else None
            if chain:
                chains.append(chain)

        return chains

    def _edit_tradelane(self):
        if not self._filepath:
            QMessageBox.warning(self, tr("msg.no_system"), tr("msg.no_system_text"))
            return
        chains = self._find_tradelane_chains()
        if not chains:
            QMessageBox.information(
                self, tr("msg.no_tradelanes"),
                tr("msg.no_tradelanes_text")
            )
            return
        dlg = TradeLaneEditDialog(self, chains=chains)
        if dlg.exec() != QDialog.Accepted:
            return
        idx = dlg.selected_chain_index
        if idx < 0 or idx >= len(chains):
            return
        chain = chains[idx]
        action = dlg.action

        if action == "delete":
            self._delete_tradelane_chain(chain)
        elif action == "reposition":
            self._reposition_tradelane_chain(chain)

    def _delete_tradelane_chain(self, chain: list[dict]):
        nicks = [r["nickname"] for r in chain]
        msg = tr("msg.delete_tl_text").format(
            count=len(chain), first=nicks[0], last=nicks[-1]
        )
        if QMessageBox.warning(
            self, tr("msg.delete_route"), msg,
            QMessageBox.Ok | QMessageBox.Cancel
        ) != QMessageBox.Ok:
            return

        for ring in chain:
            obj: SolarObject = ring["_obj"]
            # Sektion aus _sections entfernen
            obj_idx = None
            try:
                obj_idx = self._objects.index(obj)
            except ValueError:
                continue
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

        self._rebuild_object_combo()
        self._selected = None
        self._clear_selection_ui()
        self._set_dirty(True)
        self._write_to_file(reload=False)
        self.statusBar().showMessage(
            tr("status.tl_deleted_detail").format(
                count=len(chain), first=nicks[0], last=nicks[-1]
            )
        )
        self._refresh_3d_scene()

    def _reposition_tradelane_chain(self, chain: list[dict]):
        """Startet den Zwei-Klick-Modus zum Neusetzen von Start-/Endpunkt."""
        self._pending_tl_reposition = {
            "chain": chain,
            "step": 1,
        }
        self.statusBar().showMessage(tr("status.click_tl_new_start"))
        self._set_placement_mode(True, tr("placement.tl_new_start"))

    def _on_tl_reposition_click(self, pos: QPointF):
        rp = self._pending_tl_reposition
        if not rp:
            return
        step = rp.get("step", 1)
        if step == 1:
            rp["new_start"] = pos
            rp["step"] = 2
            # Rubber-Band-Linie
            pen = QPen(QColor(100, 255, 100, 180), 2, Qt.DashLine)
            self._tl_rubber_line = self.view._scene.addLine(
                pos.x(), pos.y(), pos.x(), pos.y(), pen
            )
            self._tl_rubber_line.setZValue(9999)
            self.view.mouse_moved.connect(self._update_tl_rubber_line)
            self.statusBar().showMessage(tr("status.click_tl_new_end"))
            self.mode_lbl.setText(tr("placement.esc").format(text=tr("placement.tl_new_end")))
        elif step == 2:
            rp["new_end"] = pos
            self._remove_tl_rubber_line()
            self._set_placement_mode(False)
            self._apply_tl_reposition()

    def _apply_tl_reposition(self):
        rp = self._pending_tl_reposition
        if not rp:
            return
        chain = rp["chain"]
        start_pos: QPointF = rp["new_start"]
        end_pos: QPointF = rp["new_end"]

        sx = start_pos.x() / self._scale
        sz = start_pos.y() / self._scale
        ex = end_pos.x() / self._scale
        ez = end_pos.y() / self._scale
        count = len(chain)

        dx = ex - sx
        dz = ez - sz

        # Neue Rotation berechnen
        angle_rad = math.atan2(dx, dz)
        angle_deg = math.degrees(angle_rad) + 180.0
        if angle_deg > 180.0:
            angle_deg -= 360.0
        rotate_str = f"0, {angle_deg:.0f}, 0"

        for i, ring in enumerate(chain):
            obj: SolarObject = ring["_obj"]
            t = i / max(count - 1, 1)
            px = sx + dx * t
            pz = sz + dz * t
            new_pos = f"{px:.0f}, 0, {pz:.0f}"

            # Einträge aktualisieren
            entries = obj.data.get("_entries", [])
            new_entries = []
            for k, v in entries:
                if k.lower() == "pos":
                    new_entries.append((k, new_pos))
                elif k.lower() == "rotate":
                    new_entries.append((k, rotate_str))
                else:
                    new_entries.append((k, v))
            obj.data["_entries"] = new_entries
            obj.data["pos"] = new_pos
            obj.data["rotate"] = rotate_str

            # Grafik-Position aktualisieren
            parts = new_pos.split(",")
            gx = float(parts[0].strip()) * self._scale
            gz = float(parts[2].strip()) * self._scale
            obj.setPos(gx - obj.rect().width() / 2,
                       gz - obj.rect().height() / 2)

            # Sektion in _sections aktualisieren
            obj_idx = None
            try:
                obj_idx = self._objects.index(obj)
            except ValueError:
                continue
            count_s = 0
            for si, (sec_name, sec_entries) in enumerate(self._sections):
                if sec_name.lower() == "object":
                    if count_s == obj_idx:
                        self._sections[si] = (sec_name, list(new_entries))
                        break
                    count_s += 1

        self._pending_tl_reposition = None
        self._set_dirty(True)
        self._write_to_file(reload=False)
        self.statusBar().showMessage(
            tr("status.tl_repositioned_detail").format(count=count)
        )
        self._refresh_3d_scene()

    # ==================================================================
    #  Zone Population bearbeiten
    # ==================================================================
    def _edit_zone_population(self):
        """Öffnet den Zone-Population-Dialog für die ausgewählte Zone."""
        if not self._filepath:
            QMessageBox.warning(self, tr("msg.no_system"), tr("msg.no_system_text"))
            return

        # Ausgewählte Zone aus dem Combo ermitteln
        idx = self.obj_combo.currentIndex()
        if idx < 0:
            self.statusBar().showMessage(tr("status.no_zone_selected"))
            return
        item = self.obj_combo.itemData(idx)
        if not isinstance(item, ZoneItem):
            QMessageBox.information(
                self, tr("msg.no_zone"),
                tr("msg.no_zone_text")
            )
            return
        zone = item

        # Zugehörige Section in _sections finden
        zone_nick = zone.nickname.strip().lower()
        sec_idx: int | None = None
        sec_entries: list[tuple[str, str]] | None = None
        for i, (sec_name, entries) in enumerate(self._sections):
            if sec_name.lower() == "zone":
                nick = ""
                for k, v in entries:
                    if k.lower() == "nickname":
                        nick = v.strip().lower()
                        break
                if nick == zone_nick:
                    sec_idx = i
                    sec_entries = entries
                    break

        if sec_idx is None or sec_entries is None:
            QMessageBox.warning(
                self, tr("msg.not_found"),
                tr("msg.zone_not_found").format(nickname=zone.nickname)
            )
            return

        # Verfügbare EncounterParameters sammeln
        enc_params: list[str] = []
        for sec_name, entries in self._sections:
            if sec_name.lower() == "encounterparameters":
                for k, v in entries:
                    if k.lower() == "nickname":
                        enc_params.append(v.strip())

        # Alle verfügbaren Encounters aus DATA/MISSIONS/ENCOUNTERS laden
        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        all_encounters: list[str] = list(enc_params)  # vorhandene zuerst
        if game_path:
            # ci_resolve gibt nur Dateien zurück → Verzeichnisse manuell auflösen
            enc_dir: Path | None = None
            data_dir = ci_find(Path(game_path), "DATA")
            if data_dir:
                mis_dir = ci_find(data_dir, "MISSIONS")
                if mis_dir:
                    enc_dir = ci_find(mis_dir, "ENCOUNTERS")
            if enc_dir and enc_dir.is_dir():
                for f in sorted(enc_dir.iterdir()):
                    if f.suffix.lower() == ".ini":
                        nick = f.stem
                        if nick not in all_encounters:
                            all_encounters.append(nick)

        # Dialog öffnen
        dlg = ZonePopulationDialog(
            self,
            zone_nickname=zone.nickname,
            entries=sec_entries,
            encounter_params=enc_params,
            all_encounters=all_encounters,
            factions=self._cached_factions,
        )
        if dlg.exec() != QDialog.Accepted:
            return

        # Neue EncounterParameters-Sektionen anlegen (nach [SystemInfo])
        new_enc = dlg.new_encounter_params
        if new_enc:
            # Einfügeposition: direkt nach [SystemInfo]
            insert_pos = 1
            for i, (sn, _) in enumerate(self._sections):
                if sn.lower() == "systeminfo":
                    insert_pos = i + 1
                    break
            for enc_nick in sorted(new_enc):
                enc_entries: list[tuple[str, str]] = [
                    ("nickname", enc_nick),
                    ("filename", f"missions\\encounters\\{enc_nick}.ini"),
                ]
                self._sections.insert(insert_pos, ("EncounterParameters", enc_entries))
                insert_pos += 1
                # sec_idx verschiebt sich durch das Einfügen
                sec_idx += 1

        # Einträge aktualisieren
        new_entries = dlg.build_entries()
        self._sections[sec_idx] = ("Zone", new_entries)
        zone.data["_entries"] = list(new_entries)
        # Einfache Felder im data-dict aktualisieren
        for k, v in new_entries:
            kl = k.lower()
            if kl != "_entries":
                zone.data[kl] = v

        # Text-Editor synchronisieren, damit _write_to_file die neuen
        # Einträge nicht mit dem alten Editor-Text überschreibt
        if self._selected is zone:
            self.editor.setPlainText(zone.raw_text())

        self._set_dirty(True)
        self._write_to_file(reload=False)
        self.statusBar().showMessage(
            tr("status.zone_pop_updated").format(nickname=zone.nickname)
        )

    # ------------------------------------------------------------------
    #  Base bearbeiten  (Attribute + Market-Dateien)
    # ------------------------------------------------------------------
    def _load_market_goods(
        self, game_path: str, market_file: str, base_nick: str
    ) -> list[list[str]]:
        """Liest MarketGood-Einträge aus einer Market-Datei für eine Base."""
        data_dir = ci_find(Path(game_path), "DATA")
        if not data_dir:
            return []
        equip_dir = ci_find(data_dir, "EQUIPMENT")
        if not equip_dir:
            return []
        mf = ci_find(equip_dir, market_file)
        if not mf or not mf.is_file():
            return []
        try:
            sections = self._parser.parse(str(mf))
        except Exception:
            return []
        bn = base_nick.strip().lower()
        for sec_name, entries in sections:
            if sec_name.lower() != "basegood":
                continue
            sec_base = ""
            for k, v in entries:
                if k.lower() == "base":
                    sec_base = v.strip().lower()
                    break
            if sec_base != bn:
                continue
            # MarketGood-Einträge sammeln
            goods: list[list[str]] = []
            for k, v in entries:
                if k.lower() == "marketgood":
                    fields = [f.strip() for f in v.split(",")]
                    goods.append(fields)
            return goods
        return []

    def _save_market_goods(
        self,
        game_path: str,
        market_file: str,
        base_nick: str,
        goods: list[list[str]],
    ) -> bool:
        """Aktualisiert MarketGood-Einträge in einer Market-Datei.

        Falls kein [BaseGood] für *base_nick* existiert, wird einer
        am Ende der Datei angelegt.
        """
        data_dir = ci_find(Path(game_path), "DATA")
        if not data_dir:
            return False
        equip_dir = ci_find(data_dir, "EQUIPMENT")
        if not equip_dir:
            return False
        mf = ci_find(equip_dir, market_file)
        if not mf or not mf.is_file():
            return False
        try:
            sections = self._parser.parse(str(mf))
        except Exception:
            return False

        bn = base_nick.strip().lower()
        found_idx: int | None = None
        for i, (sec_name, entries) in enumerate(sections):
            if sec_name.lower() != "basegood":
                continue
            for k, v in entries:
                if k.lower() == "base":
                    if v.strip().lower() == bn:
                        found_idx = i
                        break
            if found_idx is not None:
                break

        # Neue Einträge aufbauen
        new_entries: list[tuple[str, str]] = [("base", base_nick)]
        for row in goods:
            new_entries.append(("MarketGood", ", ".join(row)))

        if found_idx is not None:
            sections[found_idx] = ("BaseGood", new_entries)
        else:
            # Neuen [BaseGood] am Ende anlegen
            sections.append(("BaseGood", new_entries))

        # Datei schreiben
        lines: list[str] = []
        for sec_name, entries in sections:
            lines.append(f"[{sec_name}]")
            for k, v in entries:
                lines.append(f"{k} = {v}")
            lines.append("")
        try:
            tmp = str(mf) + ".tmp"
            Path(tmp).write_text("\n".join(lines), encoding="utf-8")
            shutil.move(tmp, str(mf))
        except Exception:
            return False
        return True

    def _scan_equip_nicknames(self, game_path: str) -> dict[str, list[str]]:
        """Scannt *_good.ini + goods.ini nach Equipment-Goods, gruppiert nach Quelle.

        Rückgabe: ``{Gruppenname: [nickname, …]}``
        """
        groups: dict[str, list[str]] = {}
        data_dir = ci_find(Path(game_path), "DATA")
        if not data_dir:
            return groups
        equip_dir = ci_find(data_dir, "EQUIPMENT")
        if not equip_dir:
            return groups
        # (Dateiname, Gruppenlabel)
        sources = [
            ("weapon_good.ini", tr("market.weapons")),
            ("st_good.ini", tr("market.shields_thrusters")),
            ("misc_good.ini", tr("market.misc")),
            ("goods.ini", tr("market.general")),
        ]
        seen: set[str] = set()
        for fname, label in sources:
            gf = ci_find(equip_dir, fname)
            if not gf or not gf.is_file():
                continue
            nicks: list[str] = []
            try:
                sections = self._parser.parse(str(gf))
                for sec_name, entries in sections:
                    if sec_name.lower() != "good":
                        continue
                    nick = ""
                    cat = ""
                    for k, v in entries:
                        kl = k.lower()
                        if kl == "nickname":
                            nick = v.strip()
                        elif kl == "category":
                            cat = v.strip().lower()
                    if not nick or cat != "equipment":
                        continue
                    nl = nick.lower()
                    if nl not in seen:
                        seen.add(nl)
                        nicks.append(nick)
            except Exception:
                pass
            if nicks:
                groups[label] = sorted(nicks, key=str.lower)
        return groups

    def _scan_commodity_nicknames(self, game_path: str) -> tuple[list[str], dict[str, int]]:
        """Scannt goods.ini nach commodity-Goods.

        Rückgabe: ``(nicknames, {nickname: base_price})``
        """
        nicks: list[str] = []
        prices: dict[str, int] = {}
        data_dir = ci_find(Path(game_path), "DATA")
        if not data_dir:
            return nicks, prices
        equip_dir = ci_find(data_dir, "EQUIPMENT")
        if not equip_dir:
            return nicks, prices
        gf = ci_find(equip_dir, "goods.ini")
        if not gf or not gf.is_file():
            return nicks, prices
        try:
            sections = self._parser.parse(str(gf))
            for sec_name, entries in sections:
                if sec_name.lower() != "good":
                    continue
                nick = ""
                price = 0
                for k, v in entries:
                    kl = k.lower()
                    if kl == "nickname":
                        nick = v.strip()
                    elif kl == "price":
                        try:
                            price = int(v.strip())
                        except ValueError:
                            pass
                if nick and nick.lower().startswith("commodity"):
                    nicks.append(nick)
                    prices[nick] = price
        except Exception:
            pass
        return nicks, prices

    def _scan_ship_nicknames(self, game_path: str) -> list[str]:
        """Scannt goods.ini nach allen [Good]-Einträgen mit _package im Nickname."""
        nicks: list[str] = []
        data_dir = ci_find(Path(game_path), "DATA")
        if not data_dir:
            return nicks
        equip_dir = ci_find(data_dir, "EQUIPMENT")
        if not equip_dir:
            return nicks
        gf = ci_find(equip_dir, "goods.ini")
        if not gf or not gf.is_file():
            return nicks
        try:
            sections = self._parser.parse(str(gf))
            for sec_name, entries in sections:
                if sec_name.lower() != "good":
                    continue
                for k, v in entries:
                    if k.lower() == "nickname":
                        nick = v.strip()
                        if "_package" in nick.lower():
                            nicks.append(nick)
                        break
        except Exception:
            pass
        return nicks

    def _edit_base(self):
        """Öffnet den Base-Edit-Dialog für das ausgewählte Base-Objekt."""
        if not self._filepath:
            QMessageBox.warning(self, tr("msg.no_system"), tr("msg.no_system_text"))
            return

        idx = self.obj_combo.currentIndex()
        if idx < 0:
            self.statusBar().showMessage(tr("status.no_object_selected"))
            return
        item = self.obj_combo.itemData(idx)
        if not isinstance(item, SolarObject):
            QMessageBox.information(
                self, tr("msg.no_object"),
                tr("msg.no_object_text")
            )
            return

        # Base-Nickname ermitteln (Feld 'base' oder 'dock_with')
        base_nick = ""
        for k, v in item.data.get("_entries", []):
            kl = k.lower()
            if kl == "base":
                base_nick = v.strip()
                break
        if not base_nick:
            for k, v in item.data.get("_entries", []):
                if k.lower() == "dock_with":
                    base_nick = v.strip()
                    break
        if not base_nick:
            QMessageBox.information(
                self, tr("msg.no_base"),
                tr("msg.no_base_text")
            )
            return

        # Objekteinträge aus _sections holen
        obj_nick = item.data.get("nickname", "").strip().lower()
        sec_idx: int | None = None
        obj_entries: list[tuple[str, str]] = []
        for i, (sec_name, entries) in enumerate(self._sections):
            if sec_name.lower() == "object":
                for k, v in entries:
                    if k.lower() == "nickname" and v.strip().lower() == obj_nick:
                        sec_idx = i
                        obj_entries = entries
                        break
                if sec_idx is not None:
                    break
        if sec_idx is None:
            QMessageBox.warning(
                self, tr("msg.not_found"),
                tr("msg.zone_not_found").format(nickname=item.data.get('nickname', ''))
            )
            return

        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        if not game_path:
            QMessageBox.warning(
                self, tr("msg.no_game_path"),
                tr("msg.no_game_path_text")
            )
            return

        # Market-Dateien laden
        misc_goods = self._load_market_goods(game_path, "market_misc.ini", base_nick)
        comm_goods = self._load_market_goods(game_path, "market_commodities.ini", base_nick)
        ship_goods = self._load_market_goods(game_path, "market_ships.ini", base_nick)

        # Listen für Dropdowns
        archetypes = [self.arch_cb.itemText(i) for i in range(self.arch_cb.count()) if self.arch_cb.itemText(i)]
        loadouts = [self.loadout_cb.itemText(i) for i in range(self.loadout_cb.count()) if self.loadout_cb.itemText(i)]
        factions = [self.faction_cb.itemText(i) for i in range(self.faction_cb.count()) if self.faction_cb.itemText(i)]
        pilots = self._scan_pilots(game_path)
        voices = self._scan_voices(game_path)
        heads, bodies = self._scan_bodyparts(game_path)

        # Equipment / Commodity / Ship Nicknames scannen
        all_equip = self._scan_equip_nicknames(game_path)
        all_comms, comm_prices = self._scan_commodity_nicknames(game_path)
        all_ships = self._scan_ship_nicknames(game_path)

        dlg = BaseEditDialog(
            self,
            base_nickname=base_nick,
            obj_entries=obj_entries,
            misc_goods=misc_goods,
            comm_goods=comm_goods,
            ship_goods=ship_goods,
            all_equip_groups=all_equip,
            all_commodity_nicks=all_comms,
            commodity_prices=comm_prices,
            all_ship_nicks=all_ships,
            pilots=pilots,
            voices=voices,
            heads=heads,
            bodies=bodies,
            archetypes=archetypes,
            loadouts=loadouts,
            factions=factions,
        )
        if dlg.exec() != QDialog.Accepted:
            if dlg.delete_requested:
                self._delete_base()
            return

        # ── Eigenschaften übernehmen ──
        props = dlg.get_obj_properties()
        new_entries: list[tuple[str, str]] = []
        handled: set[str] = set()
        # Bestehende Einträge aktualisieren (Reihenfolge beibehalten)
        for k, v in obj_entries:
            kl = k.lower()
            if kl in props and kl not in handled:
                new_entries.append((k, props[kl]))
                handled.add(kl)
            else:
                new_entries.append((k, v))
        # Neue Felder hinzufügen, die vorher nicht existierten
        for key, val in props.items():
            if key not in handled and val:
                new_entries.append((key, val))

        self._sections[sec_idx] = ("Object", new_entries)
        item.data["_entries"] = list(new_entries)
        for k, v in new_entries:
            kl = k.lower()
            if kl != "_entries":
                item.data[kl] = v

        # ── Market-Dateien schreiben ──
        new_misc = dlg.get_equip_market_goods()
        new_comm = dlg.get_commodity_market_goods()
        new_ship = dlg.get_ship_market_goods()

        self._save_market_goods(game_path, "market_misc.ini", base_nick, new_misc)
        self._save_market_goods(game_path, "market_commodities.ini", base_nick, new_comm)
        self._save_market_goods(game_path, "market_ships.ini", base_nick, new_ship)

        # Editor-Text synchronisieren
        if self._selected is item:
            self.editor.setPlainText(item.raw_text())

        self._set_dirty(True)
        self._write_to_file(reload=False)
        self.statusBar().showMessage(
            tr("status.base_updated").format(nickname=base_nick)
        )

    # ------------------------------------------------------------------
    #  Base löschen
    # ------------------------------------------------------------------
    def _delete_base(self):
        """Löscht die ausgewählte Base komplett: Objekt, universe.ini-Eintrag,
        Market-Einträge, Base-INI und Room-Dateien."""
        if not self._filepath:
            QMessageBox.warning(self, tr("msg.no_system"), tr("msg.no_system_text"))
            return

        idx = self.obj_combo.currentIndex()
        if idx < 0:
            self.statusBar().showMessage(tr("status.no_object_selected"))
            return
        item = self.obj_combo.itemData(idx)
        if not isinstance(item, SolarObject):
            QMessageBox.information(
                self, tr("msg.no_object"),
                tr("msg.no_object_text")
            )
            return

        # Base-Nickname ermitteln
        base_nick = ""
        for k, v in item.data.get("_entries", []):
            kl = k.lower()
            if kl == "base":
                base_nick = v.strip()
                break
        if not base_nick:
            for k, v in item.data.get("_entries", []):
                if k.lower() == "dock_with":
                    base_nick = v.strip()
                    break
        if not base_nick:
            QMessageBox.information(
                self, tr("msg.no_base"),
                tr("msg.no_base_text")
            )
            return

        # Bestätigung
        reply = QMessageBox.warning(
            self, tr("msg.delete_base"),
            tr("msg.delete_base_text").format(
                nickname=base_nick,
                details=tr("msg.delete_base_details")
            ),
            QMessageBox.Ok | QMessageBox.Cancel,
        )
        if reply != QMessageBox.Ok:
            return

        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        bn_lower = base_nick.lower()
        result: list[str] = []

        # ── 1) Alle Objekte mit dieser Base aus dem System entfernen ──
        objs_to_remove: list[SolarObject] = []
        for obj in self._objects:
            for k, v in obj.data.get("_entries", []):
                kl = k.lower()
                if kl in ("base", "dock_with") and v.strip().lower() == bn_lower:
                    objs_to_remove.append(obj)
                    break

        for obj in objs_to_remove:
            obj_idx = None
            try:
                obj_idx = self._objects.index(obj)
            except ValueError:
                continue
            # Sektion in _sections entfernen
            count = 0
            for i, (sec_name, entries) in enumerate(list(self._sections)):
                if sec_name.lower() == "object":
                    if count == obj_idx:
                        self._sections.pop(i)
                        break
                    count += 1
            self.view._scene.removeItem(obj)
            self._objects.remove(obj)
            result.append(tr("result.obj_removed").format(nickname=obj.nickname))

        # ── 2) [Base] aus universe.ini entfernen ──
        if hasattr(self, "_uni_sections") and self._uni_sections:
            uni_removed = False
            for i, (sec_name, entries) in enumerate(list(self._uni_sections)):
                if sec_name.lower() != "base":
                    continue
                for k, v in entries:
                    if k.lower() == "nickname" and v.strip().lower() == bn_lower:
                        self._uni_sections.pop(i)
                        uni_removed = True
                        break
                if uni_removed:
                    break

            if uni_removed:
                uni_ini = find_universe_ini(game_path)
                if uni_ini:
                    try:
                        self._write_sections_to_file(str(uni_ini), self._uni_sections)
                        result.append(tr("result.base_removed_uni").format(nickname=base_nick))
                    except Exception as ex:
                        result.append(tr("result.uni_error").format(error=ex))
            else:
                result.append(tr("result.base_not_in_uni").format(nickname=base_nick))
        else:
            # _uni_sections nicht geladen – universe.ini direkt parsen
            uni_ini = find_universe_ini(game_path)
            if uni_ini:
                try:
                    uni_secs = self._parser.parse(str(uni_ini))
                    new_secs = []
                    removed = False
                    for sec_name, entries in uni_secs:
                        if sec_name.lower() == "base":
                            for k, v in entries:
                                if k.lower() == "nickname" and v.strip().lower() == bn_lower:
                                    removed = True
                                    break
                            if removed:
                                removed = True
                                continue
                        new_secs.append((sec_name, entries))
                    if removed:
                        self._write_sections_to_file(str(uni_ini), new_secs)
                        result.append(tr("result.base_removed_uni").format(nickname=base_nick))
                    else:
                        result.append(tr("result.base_not_in_uni").format(nickname=base_nick))
                except Exception as ex:
                    result.append(tr("result.uni_error").format(error=ex))

        # ── 3) Market-Einträge entfernen ──
        for mf_name in ("market_misc.ini", "market_commodities.ini", "market_ships.ini"):
            if self._remove_market_base(game_path, mf_name, base_nick):
                result.append(tr("result.basegood_removed").format(file=mf_name))

        # ── 4) Base-INI und Room-Dateien löschen ──
        if game_path:
            sys_nick = Path(self._filepath).stem
            data_dir = ci_find(Path(game_path), "DATA")
            if data_dir:
                uni_dir = ci_find(data_dir, "UNIVERSE")
                if uni_dir:
                    # Base-INI suchen
                    base_ini = ci_resolve(
                        uni_dir, f"SYSTEMS/{sys_nick}/BASES/{base_nick}.ini"
                    )
                    if base_ini and base_ini.exists():
                        # Room-Dateien aus Base-INI lesen und löschen
                        try:
                            base_secs = self._parser.parse(str(base_ini))
                            for sec_name, entries in base_secs:
                                if sec_name.lower() == "room":
                                    for k, v in entries:
                                        if k.lower() == "file":
                                            room_file = ci_resolve(
                                                data_dir, v.strip()
                                            )
                                            if room_file and room_file.exists():
                                                room_file.unlink()
                                                result.append(
                                                    tr("result.room_deleted").format(file=room_file.name)
                                                )
                        except Exception:
                            pass

                        # Base-INI selbst löschen
                        base_ini.unlink()
                        result.append(tr("result.base_ini_deleted").format(file=base_ini.name))

                        # Verbleibende Room-Dateien im ROOMS-Ordner aufräumen
                        sys_dir = ci_find(uni_dir / "SYSTEMS" if (uni_dir / "SYSTEMS").exists()
                                          else uni_dir, sys_nick) if uni_dir else None
                        if not sys_dir:
                            sys_dir = ci_find(uni_dir, "SYSTEMS")
                            if sys_dir:
                                sys_dir = ci_find(sys_dir, sys_nick)
                        bases_dir = ci_find(sys_dir, "BASES") if sys_dir else None
                        rooms_dir = ci_find(bases_dir, "ROOMS") if bases_dir else None
                        if rooms_dir and rooms_dir.is_dir():
                            remaining = [
                                f for f in rooms_dir.iterdir()
                                if f.name.lower().startswith(base_nick.lower() + "_")
                            ]
                            for rf in remaining:
                                rf.unlink()
                                result.append(tr("result.room_deleted").format(file=rf.name))
                    else:
                        result.append(tr("result.base_ini_not_found").format(nickname=base_nick))

        # ── Abschluss ──
        if self._selected in objs_to_remove:
            self._selected = None
            self._clear_selection_ui()
            self._hide_zone_extra_editors()

        self._rebuild_object_combo()
        self._set_dirty(True)
        self._write_to_file(reload=False)
        self._refresh_3d_scene()

        QMessageBox.information(
            self, tr("msg.base_deleted"),
            tr("msg.base_deleted_text").format(
                nickname=base_nick, details="\n".join(result)
            )
        )
        self.statusBar().showMessage(tr("status.base_deleted").format(nickname=base_nick))

    def _remove_market_base(
        self, game_path: str, market_file: str, base_nick: str
    ) -> bool:
        """Entfernt den [BaseGood]-Eintrag einer Base aus einer Market-Datei."""
        data_dir = ci_find(Path(game_path), "DATA")
        if not data_dir:
            return False
        equip_dir = ci_find(data_dir, "EQUIPMENT")
        if not equip_dir:
            return False
        mf = ci_find(equip_dir, market_file)
        if not mf or not mf.is_file():
            return False
        try:
            sections = self._parser.parse(str(mf))
        except Exception:
            return False

        bn = base_nick.strip().lower()
        new_sections = []
        removed = False
        for sec_name, entries in sections:
            if sec_name.lower() == "basegood":
                is_match = False
                for k, v in entries:
                    if k.lower() == "base" and v.strip().lower() == bn:
                        is_match = True
                        break
                if is_match:
                    removed = True
                    continue  # Diese Sektion überspringen
            new_sections.append((sec_name, entries))

        if not removed:
            return False

        # Datei zurückschreiben
        lines: list[str] = []
        for sec_name, entries in new_sections:
            lines.append(f"[{sec_name}]")
            for k, v in entries:
                lines.append(f"{k} = {v}")
            lines.append("")
        try:
            tmp = str(mf) + ".tmp"
            Path(tmp).write_text("\n".join(lines), encoding="utf-8")
            shutil.move(tmp, str(mf))
        except Exception:
            return False
        return True

    # ------------------------------------------------------------------
    #  Docking Ring an Planet anhängen
    # ------------------------------------------------------------------
    def _attach_docking_ring(self):
        """Startet den Docking-Ring-Workflow: Klick auf Planet → Dialog → Orbit-Platzierung."""
        if not self._filepath:
            QMessageBox.warning(self, tr("msg.no_system"), tr("msg.no_system_text"))
            return
        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        if not game_path:
            QMessageBox.warning(self, tr("msg.error"), tr("msg.no_game_path_set"))
            return
        self._pending_dock_ring = {"step": 1, "game_path": game_path}
        self._set_placement_mode(True, tr("placement.dock_ring"))

    def _on_dock_ring_planet_selected(self, item: SolarObject):
        """Schritt 1: Planet wurde angeklickt – kombinierter Dialog für Ring + Base."""
        dr = self._pending_dock_ring
        if not dr or dr.get("step") != 1:
            return

        planet_nick = item.data.get("nickname", "").strip()
        game_path = dr["game_path"]

        # Prüfe: Hat der Planet ein base-Feld?
        base_nick = ""
        for k, v in item.data.get("_entries", []):
            if k.lower() == "base":
                base_nick = v.strip()
                break

        needs_base = not base_nick

        # Prüfe: Gibt es schon einen Docking Ring mit dock_with auf diese Base?
        if base_nick:
            for sec_name, entries in self._sections:
                if sec_name.lower() != "object":
                    continue
                has_dock_with = False
                for k, v in entries:
                    if k.lower() == "dock_with" and v.strip().lower() == base_nick.lower():
                        has_dock_with = True
                        break
                if has_dock_with:
                    ring_nick = ""
                    for k, v in entries:
                        if k.lower() == "nickname":
                            ring_nick = v.strip()
                            break
                    ret = QMessageBox.question(
                        self, tr("msg.dock_ring_exists"),
                        tr("msg.dock_ring_exists_text").format(
                            nickname=ring_nick, base=base_nick
                        ),
                        QMessageBox.Yes | QMessageBox.No,
                    )
                    if ret != QMessageBox.Yes:
                        self._pending_dock_ring = None
                        self._set_placement_mode(False)
                        return

        # Base-Nickname generieren falls nötig
        sys_nick = Path(self._filepath).stem
        sys_upper = sys_nick.upper()
        if needs_base:
            existing_nums: list[int] = []
            prefix = f"{sys_upper}_"
            for sec_name, entries in self._uni_sections:
                if sec_name.lower() == "base":
                    for k, v in entries:
                        if k.lower() == "nickname":
                            nick = v.strip().upper()
                            if nick.startswith(prefix) and nick.endswith("_BASE"):
                                mid = nick[len(prefix):-len("_BASE")]
                                if mid.isdigit():
                                    existing_nums.append(int(mid))
                            break
            next_num = max(existing_nums, default=0) + 1
            base_nick = f"{sys_upper}_{next_num:02d}_Base"

        # Existierende Bases für Template-Dropdown
        existing_bases: list[str] = []
        for sec_name, entries in self._uni_sections:
            if sec_name.lower() == "base":
                for k, v in entries:
                    if k.lower() == "nickname":
                        existing_bases.append(v.strip())
                        break

        # Listen zusammenbauen
        loadouts = [
            self.loadout_cb.itemText(i)
            for i in range(self.loadout_cb.count())
            if self.loadout_cb.itemText(i)
        ]
        factions = [
            self.faction_cb.itemText(i)
            for i in range(self.faction_cb.count())
            if self.faction_cb.itemText(i)
        ]
        pilots = self._scan_pilots(game_path)
        voices = self._scan_voices(game_path)

        dlg = DockingRingDialog(
            self,
            planet_nickname=planet_nick,
            base_nickname=base_nick,
            loadouts=loadouts,
            factions=factions,
            existing_bases=existing_bases if needs_base else None,
            pilots=pilots,
            voices=voices,
            needs_base=needs_base,
        )
        if dlg.exec() != QDialog.Accepted:
            self._pending_dock_ring = None
            self._set_placement_mode(False)
            return

        data_in = dlg.payload()
        nickname = data_in.get("nickname", "").strip()
        if not nickname:
            QMessageBox.warning(self, tr("msg.incomplete"), tr("msg.enter_nickname"))
            self._pending_dock_ring = None
            self._set_placement_mode(False)
            return

        # Validierung: Rooms (nur wenn Base neu erstellt wird)
        if needs_base:
            if not data_in.get("rooms"):
                QMessageBox.warning(self, tr("msg.incomplete"), tr("msg.min_one_room"))
                self._pending_dock_ring = None
                self._set_placement_mode(False)
                return
            if data_in.get("start_room") not in data_in.get("rooms", []):
                QMessageBox.warning(
                    self, tr("msg.invalid"),
                    tr("msg.start_room_invalid").format(room=data_in.get('start_room'))
                )
                self._pending_dock_ring = None
                self._set_placement_mode(False)
                return

        # Prüfe Nickname-Eindeutigkeit
        for obj in self._objects:
            if obj.data.get("nickname", "").strip().lower() == nickname.lower():
                QMessageBox.warning(
                    self, tr("msg.nickname_exists"),
                    tr("msg.nickname_exists_text").format(nickname=nickname)
                )
                self._pending_dock_ring = None
                self._set_placement_mode(False)
                return

        # Planet-Position (Szenenkoordinaten) und Orbit-Radius bestimmen
        planet_scene_x = item.pos().x()
        planet_scene_y = item.pos().y()

        # atmosphere_range als Orbit-Radius verwenden
        atmo = 0
        for k, v in item.data.get("_entries", []):
            if k.lower() == "atmosphere_range":
                try:
                    atmo = int(v.strip())
                except ValueError:
                    pass
                break
        orbit_world = max(atmo, 1000)  # Minimum 1000 als Sicherheit
        orbit_scene = orbit_world * self._scale

        # Orbit-Kreis zeichnen (gestrichelt, gelb)
        pen = QPen(QColor(255, 200, 50, 180), 2, Qt.DashLine)
        self._dock_ring_orbit_circle = self.view._scene.addEllipse(
            planet_scene_x - orbit_scene,
            planet_scene_y - orbit_scene,
            orbit_scene * 2,
            orbit_scene * 2,
            pen,
        )
        self._dock_ring_orbit_circle.setZValue(9998)

        # Vorschau-Punkt auf dem Kreis (kleiner gefüllter Kreis)
        dot_r = 3
        dot_pen = QPen(QColor(255, 100, 50), 2)
        dot_brush = QBrush(QColor(255, 100, 50, 200))
        self._dock_ring_preview_dot = self.view._scene.addEllipse(
            -dot_r, -dot_r, dot_r * 2, dot_r * 2, dot_pen, dot_brush,
        )
        self._dock_ring_preview_dot.setZValue(9999)

        # Planet-Weltkoordinaten für spätere Berechnung
        planet_pos_str = item.data.get("pos", "0, 0, 0")
        parts = [p.strip() for p in planet_pos_str.split(",")]
        try:
            px, py, pz = float(parts[0]), float(parts[1]), float(parts[2])
        except (ValueError, IndexError):
            px, py, pz = 0.0, 0.0, 0.0

        # State für Schritt 2 speichern
        dr["step"] = 2
        dr["planet_item"] = item
        dr["planet_nick"] = planet_nick
        dr["base_nick"] = data_in.get("base_nickname", base_nick)
        dr["needs_base"] = needs_base
        dr["sys_nick"] = sys_nick
        dr["planet_scene_x"] = planet_scene_x
        dr["planet_scene_y"] = planet_scene_y
        dr["planet_world"] = (px, py, pz)
        dr["orbit_scene"] = orbit_scene
        dr["orbit_world"] = orbit_world
        dr["dialog_data"] = data_in

        self.view.mouse_moved.connect(self._update_dock_ring_preview)
        self.mode_lbl.setText(tr("placement.esc").format(text=tr("status.click_orbit")))
        self.statusBar().showMessage(tr("status.click_orbit"))

    def _update_dock_ring_preview(self, scene_pos: QPointF):
        """Bewegt den Vorschau-Punkt entlang des Orbit-Kreises."""
        dr = self._pending_dock_ring
        if not dr or dr.get("step") != 2:
            return
        cx = dr["planet_scene_x"]
        cy = dr["planet_scene_y"]
        orbit_r = dr["orbit_scene"]
        dx = scene_pos.x() - cx
        dy = scene_pos.y() - cy
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 1:
            return
        # Punkt auf den Kreis projizieren
        snap_x = cx + (dx / dist) * orbit_r
        snap_y = cy + (dy / dist) * orbit_r
        dot_r = 3
        self._dock_ring_preview_dot.setRect(
            snap_x - dot_r, snap_y - dot_r, dot_r * 2, dot_r * 2
        )

    def _on_dock_ring_orbit_click(self, pos: QPointF):
        """Schritt 2: Klick auf der Karte → Ring platzieren + ggf. Base erstellen."""
        dr = self._pending_dock_ring
        if not dr or dr.get("step") != 2:
            return
        cx = dr["planet_scene_x"]
        cy = dr["planet_scene_y"]
        orbit_r = dr["orbit_scene"]
        orbit_world = dr["orbit_world"]
        px, py, pz = dr["planet_world"]
        data_in = dr["dialog_data"]
        needs_base = dr.get("needs_base", False)
        game_path = dr["game_path"]
        sys_nick = dr["sys_nick"]
        base_nick = dr.get("base_nick", data_in.get("base_nickname", ""))
        planet_item = dr["planet_item"]
        planet_nick = dr["planet_nick"]

        # Winkel berechnen (Szenen-Koordinaten → Spielkoordinaten)
        dx = pos.x() - cx
        dy = pos.y() - cy
        angle = math.atan2(dy, dx)  # Szene: X=rechts, Y=unten

        # Ring-Position in Spielkoordinaten (X/Z-Ebene)
        rx = px + orbit_world * math.cos(angle)
        rz = pz + orbit_world * math.sin(angle)
        pos_str = f"{rx:.2f}, {py:.2f}, {rz:.2f}"

        # Ring-Rotation: Öffnung muss vom Planeten weg zeigen.
        angle_deg = math.degrees(angle)
        y_rot = 90.0 - angle_deg
        # Auf [-180, 180] normalisieren
        y_rot = (y_rot + 180) % 360 - 180
        rotate = f"0, {y_rot:.2f}, 0"

        nickname = data_in.get("nickname", "Dock_Ring")

        patch_result: list[str] = []

        # ── Base erstellen (falls Planet noch keine hat) ──────────────
        if needs_base:
            rooms = data_in.get("rooms", [])
            start_room = data_in.get("start_room", "Deck")
            template_base = data_in.get("template_base", "")

            sys_dir = Path(self._filepath).parent
            bases_dir = sys_dir / "BASES"
            rooms_dir = bases_dir / "ROOMS"
            bases_dir.mkdir(parents=True, exist_ok=True)
            rooms_dir.mkdir(parents=True, exist_ok=True)

            # 1) Room-INI-Dateien erstellen
            template_rooms: dict[str, str] = {}
            if template_base:
                template_rooms = self._load_template_rooms(game_path, template_base)

            for room_name in rooms:
                room_lower = room_name.lower()
                room_file = rooms_dir / f"{base_nick}_{room_lower}.ini"
                if room_file.exists():
                    patch_result.append(tr("result.room_exists").format(file=room_file.name))
                    continue
                if room_lower in template_rooms:
                    content = self._adapt_template_room(
                        template_rooms[room_lower], base_nick, rooms
                    )
                else:
                    content = self._generate_room_ini(room_name, rooms, start_room)
                content = MainWindow._normalize_room_navigation(
                    content, room_name, rooms, start_room
                )
                room_file.write_text(content, encoding="utf-8")
                patch_result.append(tr("result.room_created").format(file=room_file.name))

            # 2) Base-INI erstellen
            base_ini_path = bases_dir / f"{base_nick}.ini"
            price_var = data_in.get("price_variance", 0.15)
            base_lines = [
                "[BaseInfo]",
                f"nickname = {base_nick}",
                f"start_room = {start_room}",
                f"price_variance = {price_var:.2f}",
                "",
            ]
            for room_name in rooms:
                room_lower = room_name.lower()
                rel = f"Universe\\Systems\\{sys_nick}\\Bases\\Rooms\\{base_nick}_{room_lower}.ini"
                base_lines.extend([
                    "[Room]",
                    f"nickname = {room_name}",
                    f"file = {rel}",
                    "",
                ])
            base_ini_path.write_text("\n".join(base_lines), encoding="utf-8")
            patch_result.append(tr("result.base_ini_created").format(file=base_ini_path.name))

            # 3) [Base] in universe.ini anhängen
            uni_ini = find_universe_ini(game_path)
            if uni_ini:
                strid_name = data_in.get("strid_name", 0)
                rel_base = f"Universe\\Systems\\{sys_nick}\\Bases\\{base_nick}.ini"
                uni_block_lines = [
                    "",
                    "[Base]",
                    f"nickname = {base_nick}",
                    f"system = {sys_nick}",
                    f"strid_name = {strid_name}",
                    f"file = {rel_base}",
                ]
                uni_block = "\n".join(uni_block_lines) + "\n"
                with open(str(uni_ini), "a", encoding="utf-8") as f:
                    f.write(uni_block)
                base_entries: list[tuple[str, str]] = [
                    ("nickname", base_nick),
                    ("system", sys_nick),
                    ("strid_name", str(strid_name)),
                    ("file", rel_base),
                ]
                self._uni_sections.append(("Base", base_entries))
                patch_result.append(tr("result.base_registered").format(nickname=base_nick))
            else:
                patch_result.append(tr("result.uni_not_found"))

            # 4) 'base = ...' zum Planeten-Objekt hinzufügen
            elist = list(planet_item.data.get("_entries", []))
            elist.append(("base", base_nick))
            planet_item.data["_entries"] = elist
            planet_item.data["base"] = base_nick

            pnick_l = planet_nick.lower()
            for i, (sec_name, sec_entries) in enumerate(self._sections):
                if sec_name.lower() != "object":
                    continue
                for k, v in sec_entries:
                    if k.lower() == "nickname" and v.strip().lower() == pnick_l:
                        sec_entries.append(("base", base_nick))
                        break

        # ── Docking-Ring-Objekt erstellen ─────────────────────────────
        entries: list[tuple[str, str]] = [
            ("nickname", nickname),
            ("ids_name", data_in.get("ids_name", "0")),
            ("ids_info", data_in.get("ids_info", "0")),
            ("pos", pos_str),
            ("rotate", rotate),
            ("Archetype", data_in.get("archetype", "dock_ring")),
            ("dock_with", base_nick),
            ("loadout", data_in.get("loadout", "docking_ring")),
            ("behavior", "NOTHING"),
        ]
        voice = data_in.get("voice", "").strip()
        if voice:
            entries.append(("voice", voice))
        costume = data_in.get("costume", "").strip()
        if costume:
            entries.append(("space_costume", costume))
        pilot = data_in.get("pilot", "").strip()
        if pilot:
            entries.append(("pilot", pilot))
        entries.append(("difficulty_level", str(data_in.get("difficulty", 1))))
        faction = data_in.get("faction", "").strip()
        if faction:
            entries.append(("reputation", faction))

        self._remove_dock_ring_orbit()
        self._add_object_from_entries(entries, "Object")
        patch_result.append(tr("result.dock_ring_created").format(nickname=nickname))

        self._set_dirty(True)
        self._write_to_file(reload=False)

        self._pending_dock_ring = None
        self._set_placement_mode(False)

        msg = tr("msg.dock_ring_created") + ": "
        msg += tr("status.dock_ring_created_detail").format(
            nickname=nickname, planet=planet_nick, base=base_nick
        )
        msg += ":\n\n" + "\n".join(patch_result)
        QMessageBox.information(self, tr("msg.dock_ring_created"), msg)
        self.statusBar().showMessage(
            tr("status.dock_ring_created_detail").format(
                nickname=nickname, planet=planet_nick, base=base_nick
            )
        )

    def _remove_dock_ring_orbit(self):
        """Entfernt Orbit-Kreis und Vorschau-Punkt."""
        if hasattr(self, "_dock_ring_orbit_circle") and self._dock_ring_orbit_circle:
            self.view._scene.removeItem(self._dock_ring_orbit_circle)
            self._dock_ring_orbit_circle = None
        if hasattr(self, "_dock_ring_preview_dot") and self._dock_ring_preview_dot:
            self.view._scene.removeItem(self._dock_ring_preview_dot)
            self._dock_ring_preview_dot = None
        try:
            self.view.mouse_moved.disconnect(self._update_dock_ring_preview)
        except RuntimeError:
            pass

    def _on_zone_click(self, pos: QPointF):
        """Zwei-Klick-Modus für Asteroid/Nebel-Zone: Klick 1 = Position,
        Maus bewegen = Größe, Klick 2 = Bestätigen."""
        pz = self._pending_zone
        if not pz:
            return
        step = pz.get("step", 1)
        if step == 1:
            # Erster Klick: Position merken, Rubber-Band starten
            pz["center"] = pos
            pz["step"] = 2
            pen = QPen(QColor(180, 130, 60, 200), 2, Qt.DashLine)
            brush = QBrush(QColor(160, 120, 50, 30))
            shape = pz.get("shape", "SPHERE").upper()
            if shape == "BOX":
                self._zone_rubber_ellipse = QGraphicsRectItem(pos.x(), pos.y(), 0, 0)
                self._zone_rubber_ellipse.setPen(pen)
                self._zone_rubber_ellipse.setBrush(brush)
                self.view._scene.addItem(self._zone_rubber_ellipse)
            else:
                self._zone_rubber_ellipse = self.view._scene.addEllipse(
                    pos.x(), pos.y(), 0, 0, pen, brush
                )
            self._zone_rubber_ellipse.setZValue(9999)
            self._zone_rubber_origin = pos
            self.view.mouse_moved.connect(self._update_zone_rubber_ellipse)
            self.statusBar().showMessage(tr("status.zone_size"))
            self.mode_lbl.setText(tr("placement.esc").format(text=tr("placement.zone_size")))
        elif step == 2:
            # Zweiter Klick: Größe berechnen und Zone erstellen
            center = pz["center"]
            dx = abs(pos.x() - center.x())
            dy = abs(pos.y() - center.y())
            shape = pz.get("shape", "SPHERE").upper()
            if shape == "BOX":
                size_x = max(2 * dx / self._scale, 500)
                size_z = max(2 * dy / self._scale, 500)
            else:
                size_x = max(dx / self._scale, 500)
                size_z = max(dy / self._scale, 500)
            self._remove_zone_rubber_ellipse()
            self._create_zone_at_pos(center, size_x, size_z)
            self._set_placement_mode(False)

    def _create_zone_at_pos(self, pos: QPointF, size_x: float = 1000, size_z: float = 1000):
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
            QMessageBox.warning(self, tr("msg.error"), tr("msg.solar_dir_not_found").format(path=base))
            return
        if zone_type == "Asteroid Field":
            src_dir = ci_find(solar_dir, "asteroids")
        else:
            src_dir = ci_find(solar_dir, "nebula")
        if not src_dir or not src_dir.is_dir():
            QMessageBox.warning(self, tr("msg.error"), tr("msg.dir_not_found"))
            return
        src_file = src_dir / ref_file
        if not src_file.exists():
            QMessageBox.warning(self, tr("msg.error"), tr("msg.ref_file_not_found").format(file=src_file))
            return

        sys_name = Path(self._filepath).stem.upper()
        art_name = self._zone_art_from_input(zone_name, "asteroid" if zone_type == "Asteroid Field" else "nebula")
        zone_nick = self._suggest_zone_name(art_name, [z.nickname for z in self._zones])
        zparts = zone_nick.split("_")
        num_suffix = zparts[-1] if zparts and zparts[-1].isdigit() else "001"
        new_zone_file = f"{sys_name}_{art_name}_{num_suffix}.ini"
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
            new_lines.append(f"\n; Copied by FL Atlas from file: {src_dir_name}\\{ref_file}")
            new_zone_path.write_text("\n".join(new_lines), encoding="utf-8")
        except Exception as ex:
            QMessageBox.critical(self, tr("msg.copy_error"), str(ex))
            return

        size_y = min(size_x, size_z)
        size_str = f"{size_x:.0f}, {size_y:.0f}, {size_z:.0f}"

        zone_entries = [
            ("nickname", zone_nick),
            ("ids_name", "0"),
            ("pos", f"{pos.x() / self._scale:.2f}, 0, {pos.y() / self._scale:.2f}"),
            ("rotate", "0,0,0"),
            ("shape", "ELLIPSOID"),
            ("size", size_str),
            ("property_flags", "0"),
            ("ids_info", "66146"),
            ("visit", "0"),
            ("damage", str(int(pz.get("damage", 0)))),
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
        self._push_undo_action(
            {
                "type": "create_zone",
                "label": f"Zone erstellt: {zone_nick}",
                "filepath": self._filepath or "",
                "nickname": zone_nick,
                "linked_section": section_name,
                "linked_file_abs": str(new_zone_path),
            }
        )
        self._append_change_log(f"Zone erstellt: {zone_nick}")
        self._set_dirty(True)
        self._pending_zone = None
        self.statusBar().showMessage(
            tr("status.zone_created_detail").format(
                nickname=zone_name,
                size=f"{size_x:.0f} × {size_y:.0f} × {size_z:.0f}"
            )
        )
        self._refresh_3d_scene()

    # ------------------------------------------------------------------
    #  Jump-Verbindung
    # ------------------------------------------------------------------
    def _start_zone_creation(self):
        if not self._filepath:
            QMessageBox.warning(self, tr("msg.no_system"), tr("msg.no_system_text"))
            return
        game_path = self.browser.path_edit.text().strip()
        if not game_path:
            QMessageBox.warning(self, tr("msg.no_game_path"), tr("msg.no_game_path_config"))
            return
        base = Path(game_path)
        if not (base / "solar").exists() and not (base / "SOLAR").exists():
            data_dir = ci_find(base, "DATA")
            if data_dir and data_dir.is_dir():
                base = data_dir
        solar_dir = ci_find(base, "solar")
        if not solar_dir or not solar_dir.is_dir():
            QMessageBox.warning(self, tr("msg.error"), tr("msg.solar_dir_not_found").format(path=base))
            return
        ast_dir = ci_find(solar_dir, "asteroids")
        neb_dir = ci_find(solar_dir, "nebula")
        asteroids = sorted([f.name for f in ast_dir.glob("*.ini")]) if ast_dir and ast_dir.is_dir() else []
        nebulas = sorted([f.name for f in neb_dir.glob("*.ini")]) if neb_dir and neb_dir.is_dir() else []
        dlg = ZoneCreationDialog(self, asteroids, nebulas)
        existing_zone_nicks = [z.nickname for z in self._zones]
        last_auto_name = [""]

        def _auto_zone_name(typ: str) -> str:
            kind = "asteroid" if str(typ).strip().lower() == "asteroid field" else "nebula"
            return self._suggest_zone_name(kind, existing_zone_nicks)

        first_auto = _auto_zone_name(dlg.type_cb.currentText())
        dlg.name_edit.setText(first_auto)
        last_auto_name[0] = first_auto

        def _update_auto_name(typ: str):
            cur = dlg.name_edit.text().strip()
            if not cur or cur == last_auto_name[0]:
                nxt = _auto_zone_name(typ)
                dlg.name_edit.setText(nxt)
                last_auto_name[0] = nxt

        dlg.type_cb.currentTextChanged.connect(_update_auto_name)
        if dlg.exec() != QDialog.Accepted:
            return
        zone_type = dlg.type_cb.currentText()
        ref_file = dlg.ref_cb.currentText()
        zone_name = dlg.name_edit.text().strip()
        if not zone_name or not ref_file:
            QMessageBox.warning(self, tr("msg.incomplete"), tr("msg.enter_name_ref"))
            return
        self._pending_zone = {
            "type": zone_type, "ref_file": ref_file,
            "name": zone_name, "game_path": game_path,
            "damage": int(dlg.damage_spin.value()),
            "step": 1,
        }
        self._set_placement_mode(True, tr("placement.zone").format(name=zone_name))

    # ------------------------------------------------------------------
    #  Einfache Zone erstellen (Population-Zone)
    # ------------------------------------------------------------------
    def _start_simple_zone_creation(self):
        if not self._filepath:
            QMessageBox.warning(self, tr("msg.no_system"), tr("msg.no_system_text"))
            return
        dlg = SimpleZoneDialog(self)
        dlg.name_edit.setText(
            self._suggest_zone_name("zone", [z.nickname for z in self._zones])
        )
        if dlg.exec() != QDialog.Accepted:
            return
        zone_name = dlg.name_edit.text().strip()
        if not zone_name:
            QMessageBox.warning(self, tr("msg.incomplete"), tr("msg.enter_name"))
            return
        self._pending_simple_zone = {
            "name": zone_name,
            "comment": dlg.comment_edit.text().strip(),
            "shape": dlg.shape_cb.currentText(),
            "sort": dlg.sort_spin.value(),
            "damage": int(dlg.damage_spin.value()),
            "step": 1,
        }
        self._set_placement_mode(True, tr("placement.zone").format(name=zone_name))

    def _on_simple_zone_click(self, pos: QPointF):
        """Zwei-Klick-Modus für einfache Zone: Klick 1 = Position,
        Maus bewegen = Größe, Klick 2 = Bestätigen."""
        pz = self._pending_simple_zone
        if not pz:
            return
        step = pz.get("step", 1)
        if step == 1:
            pz["center"] = pos
            pz["step"] = 2
            pen = QPen(QColor(80, 160, 200, 200), 2, Qt.DashLine)
            brush = QBrush(QColor(60, 140, 180, 30))
            shape = pz.get("shape", "SPHERE").upper()
            if shape == "BOX":
                self._zone_rubber_ellipse = QGraphicsRectItem(pos.x(), pos.y(), 0, 0)
                self._zone_rubber_ellipse.setPen(pen)
                self._zone_rubber_ellipse.setBrush(brush)
                self.view._scene.addItem(self._zone_rubber_ellipse)
            else:
                self._zone_rubber_ellipse = self.view._scene.addEllipse(
                    pos.x(), pos.y(), 0, 0, pen, brush
                )
            self._zone_rubber_ellipse.setZValue(9999)
            self._zone_rubber_origin = pos
            self.view.mouse_moved.connect(self._update_zone_rubber_ellipse)
            self.statusBar().showMessage(tr("status.zone_size"))
            self.mode_lbl.setText(tr("placement.esc").format(text=tr("placement.zone_size")))
        elif step == 2:
            center = pz["center"]
            dx = abs(pos.x() - center.x())
            dy = abs(pos.y() - center.y())
            shape = pz.get("shape", "SPHERE").upper()
            if shape == "BOX":
                size_x = max(2 * dx / self._scale, 500)
                size_z = max(2 * dy / self._scale, 500)
            else:
                size_x = max(dx / self._scale, 500)
                size_z = max(dy / self._scale, 500)
            self._remove_zone_rubber_ellipse()
            self._create_simple_zone(center, size_x, size_z)
            self._set_placement_mode(False)

    def _create_simple_zone(self, pos: QPointF, size_x: float, size_z: float):
        pz = self._pending_simple_zone
        if not pz:
            return
        zone_name = pz["name"]
        comment = pz["comment"]
        shape = pz["shape"]
        sort_val = pz["sort"]
        damage_val = int(pz.get("damage", 0))

        art_name = self._zone_art_from_input(zone_name, "zone")
        zone_nick = self._suggest_zone_name(art_name, [z.nickname for z in self._zones])

        size_y = min(size_x, size_z)
        if shape == "SPHERE":
            r = max(size_x, size_z)
            size_str = f"{r:.0f}"
        else:
            size_str = f"{size_x:.0f}, {size_y:.0f}, {size_z:.0f}"

        zone_entries: list[tuple[str, str]] = [
            ("nickname", zone_nick),
        ]
        if comment:
            zone_entries.append(("comment", comment))
        zone_entries.extend([
            ("pos", f"{pos.x() / self._scale:.0f}, 0, {pos.y() / self._scale:.0f}"),
            ("rotate", "0,0,0"),
            ("shape", shape),
            ("size", size_str),
            ("sort", str(sort_val)),
            ("damage", str(max(0, damage_val))),
        ])

        zone_data: dict = {"_entries": list(zone_entries)}
        for k, v in zone_entries:
            zone_data[k.lower()] = v
        zone = ZoneItem(zone_data, self._scale)
        self.view._scene.addItem(zone)
        self._zones.append(zone)
        self._rebuild_object_combo()
        self._select_zone(zone)

        self._sections.append(("Zone", list(zone_entries)))
        self._push_undo_action(
            {
                "type": "create_zone",
                "label": f"Zone erstellt: {zone_nick}",
                "filepath": self._filepath or "",
                "nickname": zone_nick,
            }
        )
        self._append_change_log(f"Zone erstellt: {zone_nick}")
        self._set_dirty(True)
        self._pending_simple_zone = None
        self.statusBar().showMessage(
            tr("status.zone_created_detail").format(
                nickname=zone_nick, size=size_str
            )
        )
        self._write_to_file(reload=False)
        self._refresh_3d_scene()

    def _is_field_zone(self, zone_nickname: str) -> bool:
        return is_field_zone_nickname(self._sections, zone_nickname)

    @staticmethod
    def _find_nickname_in_entries(entries: list[tuple[str, str]]) -> str:
        for k, v in entries:
            if k.lower() == "nickname":
                return v.strip()
        return ""

    def _find_zone_entries_index(self, zone_nickname: str) -> int | None:
        target = zone_nickname.strip().lower()
        for idx, (sec_name, entries) in enumerate(self._sections):
            if sec_name.lower() != "zone":
                continue
            nick = self._find_nickname_in_entries(entries)
            if nick.lower() == target:
                return idx
        return None

    @staticmethod
    def _zone_default_pos_size(zone: ZoneItem) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        pos = zone.data.get("pos", "0, 0, 0")
        pparts = [p.strip() for p in pos.split(",")]
        px = float(pparts[0]) if len(pparts) > 0 and pparts[0] else 0.0
        py = float(pparts[1]) if len(pparts) > 1 and pparts[1] else 0.0
        pz = float(pparts[2]) if len(pparts) > 2 and pparts[2] else 0.0

        size = zone.data.get("size", "1000")
        sparts = [s.strip() for s in size.split(",")]
        sx = float(sparts[0]) if len(sparts) > 0 and sparts[0] else 1000.0
        sy = float(sparts[1]) if len(sparts) > 1 and sparts[1] else sx
        sz = float(sparts[2]) if len(sparts) > 2 and sparts[2] else sx
        return (px, py, pz), (max(1.0, sx), max(1.0, sy), max(1.0, sz))

    def _start_exclusion_zone_creation(self):
        if not self._filepath:
            QMessageBox.warning(self, tr("msg.no_system"), tr("msg.no_system_text"))
            return
        if not isinstance(self._selected, ZoneItem):
            QMessageBox.warning(self, tr("msg.error"), tr("msg.exclusion_select_field_zone"))
            return
        field_zone = self._selected
        if not self._is_field_zone(field_zone.nickname):
            QMessageBox.warning(self, tr("msg.error"), tr("msg.exclusion_not_field_zone"))
            return

        system_nick = Path(self._filepath).stem
        existing = [z.nickname for z in self._zones]
        suggested = generate_exclusion_nickname(system_nick, field_zone.nickname, existing)
        default_pos, default_size = self._zone_default_pos_size(field_zone)

        dlg = ExclusionZoneDialog(self, suggested, default_pos, default_size)
        if dlg.exec() != QDialog.Accepted:
            return
        data = dlg.get_data()
        nickname = data.get("nickname", "").strip()
        if not nickname:
            QMessageBox.warning(self, tr("msg.error"), tr("msg.exclusion_nickname_empty"))
            return

        params = {
            "shape": data.get("shape", "SPHERE"),
            "comment": data.get("comment", ""),
            "sort": data.get("sort", 99),
            "nickname": nickname,
            "link_to_field_zone": data.get("link_to_field_zone", True),
        }
        self._pending_exclusion_zone = {
            "system": system_nick,
            "field_zone_nickname": field_zone.nickname,
            "params": params,
            "step": 1,
        }
        self._set_placement_mode(True, tr("placement.exclusion_pos").format(name=nickname))

    def _on_exclusion_zone_click(self, pos: QPointF):
        """Zwei-Klick-Modus für Exclusion-Zone: Klick 1 = Position,
        Maus bewegen = Größe, Klick 2 = Erstellen."""
        pe = self._pending_exclusion_zone
        if not pe:
            return
        step = pe.get("step", 1)
        if step == 1:
            pe["center"] = pos
            pe["step"] = 2
            pen = QPen(QColor(220, 90, 90, 220), 2, Qt.DashLine)
            brush = QBrush(QColor(200, 60, 60, 35))
            # Check shape for exclusion zone
            shape = None
            if "params" in pe and "shape" in pe["params"]:
                shape = str(pe["params"]["shape"]).upper()
            else:
                shape = "SPHERE"
            if shape == "BOX":
                self._zone_rubber_ellipse = QGraphicsRectItem(pos.x(), pos.y(), 0, 0)
                self._zone_rubber_ellipse.setPen(pen)
                self._zone_rubber_ellipse.setBrush(brush)
                self.view._scene.addItem(self._zone_rubber_ellipse)
            else:
                self._zone_rubber_ellipse = self.view._scene.addEllipse(
                    pos.x(), pos.y(), 0, 0, pen, brush
                )
            self._zone_rubber_ellipse.setZValue(9999)
            self._zone_rubber_origin = pos
            self.view.mouse_moved.connect(self._update_zone_rubber_ellipse)
            self.statusBar().showMessage(tr("status.exclusion_size"))
            self.mode_lbl.setText(tr("placement.esc").format(text=tr("placement.exclusion_size")))
        elif step == 2:
            # Use the same logic as the preview: get both points in scene coordinates
            center0 = pe["center"]
            x0, y0 = center0.x(), center0.y()
            x1, y1 = pos.x(), pos.y()
            left = min(x0, x1)
            top = min(y0, y1)
            width = abs(x1 - x0)
            height = abs(y1 - y0)
            # Calculate center and size in scaled coordinates
            mid_x = left + width / 2
            mid_y = top + height / 2
            center = QPointF(mid_x, mid_y)
            size_x = max(width / self._scale, 500)
            size_z = max(height / self._scale, 500)
            self._remove_zone_rubber_ellipse()
            self._create_exclusion_zone_at_pos(center, size_x, size_z)
            self._set_placement_mode(False)

    def _create_exclusion_zone_at_pos(self, pos: QPointF, size_x: float, size_z: float):
        pe = self._pending_exclusion_zone
        if not pe:
            return
        params = dict(pe.get("params", {}))
        old_pos = params.get("pos", (0.0, 0.0, 0.0))
        y_pos = float(old_pos[1]) if isinstance(old_pos, tuple) and len(old_pos) > 1 else 0.0
        params["pos"] = (pos.x() / self._scale, y_pos, pos.y() / self._scale)

        shape = str(params.get("shape", "SPHERE")).upper()
        old_size = params.get("size", (1000.0, 1000.0, 1000.0))
        size_y = 1000.0
        if isinstance(old_size, tuple) and len(old_size) > 1:
            size_y = max(1.0, float(old_size[1]))
        if shape == "SPHERE":
            params["size"] = max(size_x, size_z)
        elif shape == "BOX":
            params["size"] = (size_x * 2.0, size_y, size_z * 2.0)
        else:
            params["size"] = (size_x, size_y, size_z)

        try:
            result = self.CreateExclusionZone(
                pe["system"],
                pe["field_zone_nickname"],
                params,
            )
        except Exception as ex:
            QMessageBox.critical(self, tr("msg.error"), str(ex))
            self._pending_exclusion_zone = None
            return

        self._pending_exclusion_zone = None
        linked_files = result.get("linked_files", [])
        self._push_undo_action(
            {
                "type": "create_exclusion_zone",
                "label": f"Exclusion-Zone erstellt: {result['zone_nickname']}",
                "filepath": self._filepath or "",
                "nickname": result["zone_nickname"],
                "linked_files": [dict(x) for x in linked_files if isinstance(x, dict)],
            }
        )
        self._append_change_log(f"Exclusion-Zone erstellt: {result['zone_nickname']}")
        self.statusBar().showMessage(
            tr("status.exclusion_created").format(nickname=result["zone_nickname"])
        )

    def LinkExclusionToFieldZone(
        self,
        system: str,
        field_zone_nickname: str,
        exclusion_zone_nickname: str,
    ) -> dict:
        if not self._filepath:
            raise ValueError("No system loaded")
        if Path(self._filepath).stem.lower() != system.strip().lower():
            raise ValueError("System mismatch")

        field_zone = next(
            (z for z in self._zones if z.nickname.lower() == field_zone_nickname.strip().lower()),
            None,
        )
        if field_zone is None:
            raise ValueError(f"Field zone not found: {field_zone_nickname}")
        if not self._is_field_zone(field_zone.nickname):
            raise ValueError("Selected field zone is not nebula/asteroid linked")

        exclusion_nick = exclusion_zone_nickname.strip()
        if not exclusion_nick:
            raise ValueError("Exclusion zone nickname is empty")

        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        if not game_path:
            raise ValueError("No game path configured")

        file_rel = ""
        for sec_name, entries in self._sections:
            if sec_name.lower() not in ("nebula", "asteroids"):
                continue
            zone_val = ""
            for k, v in entries:
                if k.lower() == "zone":
                    zone_val = v.strip().lower()
                elif k.lower() == "file":
                    file_rel = v.strip()
            if zone_val == field_zone.nickname.strip().lower():
                break
            file_rel = ""

        if not file_rel:
            raise ValueError(f"Linked field ini file not found for zone: {field_zone.nickname}")

        linked_file = self._resolve_game_path_case_insensitive(game_path, file_rel)
        if not linked_file or not linked_file.is_file():
            raise ValueError(f"Field ini file not found: {file_rel}")

        original = linked_file.read_text(encoding="utf-8", errors="ignore")
        patched, changed = patch_field_ini_exclusion_section(original, exclusion_nick)
        if changed:
            tmp = str(linked_file) + ".tmp"
            Path(tmp).write_text(patched, encoding="utf-8")
            shutil.move(tmp, linked_file)
            self._set_dirty(True)
        return {
            "changed": bool(changed),
            "rel": file_rel,
            "original": original,
        }

    def CreateExclusionZone(self, system: str, field_zone_nickname: str, params: dict) -> dict:
        if not self._filepath:
            raise ValueError("No system loaded")
        if Path(self._filepath).stem.lower() != system.strip().lower():
            raise ValueError("System mismatch")

        field_zone = next(
            (z for z in self._zones if z.nickname.lower() == field_zone_nickname.strip().lower()),
            None,
        )
        if field_zone is None:
            raise ValueError(f"Field zone not found: {field_zone_nickname}")
        if not self._is_field_zone(field_zone.nickname):
            raise ValueError("Selected zone is not a nebula/asteroid field zone")

        zone_nickname = params.get("nickname", "").strip()
        existing_nicks = [z.nickname.lower() for z in self._zones]
        if not zone_nickname:
            zone_nickname = generate_exclusion_nickname(system, field_zone.nickname, [z.nickname for z in self._zones])
        if zone_nickname.lower() in existing_nicks:
            raise ValueError(f"Zone nickname already exists: {zone_nickname}")

        shape = params.get("shape", "SPHERE")
        pos = params.get("pos", (0.0, 0.0, 0.0))
        size_raw = params.get("size", (1000.0, 1000.0, 1000.0))
        rotate = params.get("rotate", (0.0, 0.0, 0.0))
        comment = params.get("comment", "")
        sort_val = params.get("sort", 99)
        link_to_field = bool(params.get("link_to_field_zone", True))

        shape_up = str(shape).upper()
        if shape_up == "SPHERE":
            if isinstance(size_raw, tuple):
                size_value: float | tuple[float, float, float] = float(size_raw[0])
            else:
                size_value = float(size_raw)
        else:
            if isinstance(size_raw, tuple):
                if len(size_raw) != 3:
                    raise ValueError("Size tuple must have 3 values for ELLIPSOID/BOX")
                size_value = (float(size_raw[0]), float(size_raw[1]), float(size_raw[2]))
            else:
                size_num = float(size_raw)
                size_value = (size_num, size_num, size_num)

        exclusion_entries = build_exclusion_zone_entries(
            nickname=zone_nickname,
            shape=shape_up,
            pos=(float(pos[0]), float(pos[1]), float(pos[2])),
            size=size_value,
            rotate=(float(rotate[0]), float(rotate[1]), float(rotate[2])),
            comment=comment,
            sort=int(sort_val),
        )

        ini_path = Path(self._filepath)
        original_text = ini_path.read_text(encoding="utf-8", errors="ignore")
        patched = patch_system_ini_for_exclusion(
            original_text,
            field_zone_nickname=field_zone.nickname,
            exclusion_zone_nickname=zone_nickname,
            exclusion_zone_entries=exclusion_entries,
            link_to_field_zone=False,
        )

        tmp = str(ini_path) + ".tmp"
        Path(tmp).write_text(patched, encoding="utf-8")
        shutil.move(tmp, ini_path)

        linked_files: list[dict] = []
        if link_to_field:
            link_info = self.LinkExclusionToFieldZone(system, field_zone.nickname, zone_nickname)
            if isinstance(link_info, dict) and link_info.get("changed"):
                linked_files.append(
                    {
                        "rel": str(link_info.get("rel", "")).strip(),
                        "content": str(link_info.get("original", "")),
                    }
                )

        self._set_dirty(False)
        self._load(self._filepath, restore=self.view.transform())
        self.browser.highlight_current(self._filepath)

        created_zone = next(
            (z for z in self._zones if z.nickname.lower() == zone_nickname.lower()),
            None,
        )
        if created_zone is not None:
            self._select_zone(created_zone)

        return {
            "zone": created_zone,
            "zone_nickname": zone_nickname,
            "ini_block": "\n".join(["[Zone]"] + [f"{k} = {v}" for k, v in exclusion_entries]),
            "linked_files": linked_files,
        }

    # ==================================================================
    #  Base erstellen
    # ==================================================================
    def _start_base_creation(self):
        if not self._filepath:
            QMessageBox.warning(self, tr("msg.no_system"), tr("msg.no_system_text"))
            return
        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        if not game_path:
            QMessageBox.warning(self, tr("msg.error"), tr("msg.no_game_path_set"))
            return
        sys_nick = Path(self._filepath).stem
        sys_upper = sys_nick.upper()
        archetypes = [self.arch_cb.itemText(i) for i in range(self.arch_cb.count()) if self.arch_cb.itemText(i)]
        loadouts = [self.loadout_cb.itemText(i) for i in range(self.loadout_cb.count()) if self.loadout_cb.itemText(i)]
        factions = [self.faction_cb.itemText(i) for i in range(self.faction_cb.count()) if self.faction_cb.itemText(i)]

        # Nächste freie Base-Nummer ermitteln
        existing_nums: list[int] = []
        prefix = f"{sys_upper}_"
        for sec_name, entries in self._uni_sections:
            if sec_name.lower() == "base":
                for k, v in entries:
                    if k.lower() == "nickname":
                        nick = v.strip().upper()
                        if nick.startswith(prefix) and nick.endswith("_BASE"):
                            mid = nick[len(prefix):-len("_BASE")]
                            if mid.isdigit():
                                existing_nums.append(int(mid))
                        break
        next_num = max(existing_nums, default=0) + 1

        # Existierende Bases sammeln (für Template-Dropdown)
        existing_bases: list[str] = []
        for sec_name, entries in self._uni_sections:
            if sec_name.lower() == "base":
                for k, v in entries:
                    if k.lower() == "nickname":
                        existing_bases.append(v.strip())
                        break

        # Piloten, Voices und Kostüme aus Spieldaten laden
        pilots = self._scan_pilots(game_path)
        voices = self._scan_voices(game_path)
        heads, bodies = self._scan_bodyparts(game_path)

        dlg = BaseCreationDialog(
            self, sys_nick, archetypes, loadouts, factions, existing_bases,
            next_base_num=next_num, pilots=pilots, voices=voices,
            heads=heads, bodies=bodies,
        )
        if dlg.exec() != QDialog.Accepted:
            return
        payload = dlg.payload()
        base_nick = payload["base_nickname"]
        obj_nick = payload["obj_nickname"]
        if not base_nick or not obj_nick:
            QMessageBox.warning(self, tr("msg.incomplete"), tr("msg.base_obj_required"))
            return
        if not payload["rooms"]:
            QMessageBox.warning(self, tr("msg.incomplete"), tr("msg.min_one_room"))
            return
        # Validierung: start_room muss in Rooms enthalten sein
        if payload["start_room"] not in payload["rooms"]:
            QMessageBox.warning(
                self, tr("msg.invalid"),
                tr("msg.start_room_invalid").format(room=payload['start_room'])
            )
            return
        self._pending_base = {
            "game_path": game_path,
            "sys_nick": sys_nick,
            **payload,
        }
        self._set_placement_mode(True, tr("placement.base").format(name=base_nick))

    def _create_base_at_pos(self, pos: QPointF):
        """Erstellt alle Dateien und Einträge für eine neue Base."""
        info = self._pending_base
        if not info:
            return
        self._pending_base = None

        game_path = info["game_path"]
        sys_nick = info["sys_nick"]
        base_nick = info["base_nickname"]
        obj_nick = info["obj_nickname"]
        rooms = info["rooms"]
        start_room = info["start_room"]
        template_base = info.get("template_base", "")

        sys_dir = Path(self._filepath).parent
        bases_dir = sys_dir / "BASES"
        rooms_dir = bases_dir / "ROOMS"
        bases_dir.mkdir(parents=True, exist_ok=True)
        rooms_dir.mkdir(parents=True, exist_ok=True)

        patch_result: list[str] = []

        # ----- 1) Room-INI-Dateien erstellen -----
        template_rooms: dict[str, str] = {}
        if template_base:
            template_rooms = self._load_template_rooms(game_path, template_base)

        for room_name in rooms:
            room_lower = room_name.lower()
            room_file = rooms_dir / f"{base_nick}_{room_lower}.ini"
            if room_file.exists():
                patch_result.append(tr("result.room_exists").format(file=room_file.name))
                continue

            if room_lower in template_rooms:
                content = self._adapt_template_room(
                    template_rooms[room_lower], base_nick, rooms
                )
            else:
                content = self._generate_room_ini(room_name, rooms, start_room)
            content = MainWindow._normalize_room_navigation(
                content, room_name, rooms, start_room
            )

            room_file.write_text(content, encoding="utf-8")
            patch_result.append(tr("result.room_created").format(file=room_file.name))

        # ----- 2) Base-INI erstellen -----
        base_ini_path = bases_dir / f"{base_nick}.ini"
        base_lines = [
            "[BaseInfo]",
            f"nickname = {base_nick}",
            f"start_room = {start_room}",
            f"price_variance = {info['price_variance']:.2f}",
            "",
        ]
        for room_name in rooms:
            room_lower = room_name.lower()
            rel = f"Universe\\Systems\\{sys_nick}\\Bases\\Rooms\\{base_nick}_{room_lower}.ini"
            base_lines.extend([
                "[Room]",
                f"nickname = {room_name}",
                f"file = {rel}",
                "",
            ])
        base_ini_path.write_text("\n".join(base_lines), encoding="utf-8")
        patch_result.append(tr("result.base_ini_created").format(file=base_ini_path.name))

        # ----- 3) [Object] ins System-INI einfügen -----
        pos_str = f"{pos.x() / self._scale:.2f}, 0.00, {pos.y() / self._scale:.2f}"
        obj_entries: list[tuple[str, str]] = [
            ("nickname", obj_nick),
            ("pos", pos_str),
            ("rotate", "0, 0, 0"),
            ("ids_name", str(info["ids_name"])),
            ("ids_info", str(info["ids_info"])),
            ("Archetype", info["archetype"]),
            ("dock_with", base_nick),
            ("base", base_nick),
            ("behavior", "NOTHING"),
            ("difficulty_level", "1"),
        ]
        if info["loadout"]:
            obj_entries.append(("loadout", info["loadout"]))
        if info["pilot"]:
            obj_entries.append(("pilot", info["pilot"]))
        if info["reputation"]:
            obj_entries.append(("reputation", info["reputation"]))
        if info["voice"]:
            obj_entries.append(("voice", info["voice"]))
        if info["space_costume"]:
            obj_entries.append(("space_costume", info["space_costume"]))

        self._add_object_from_entries(obj_entries, "Object")
        patch_result.append(tr("result.obj_inserted").format(nickname=obj_nick))

        # ----- 4) [Base] in universe.ini anhängen -----
        uni_ini = find_universe_ini(game_path)
        if uni_ini:
            rel_base = f"Universe\\Systems\\{sys_nick}\\Bases\\{base_nick}.ini"
            uni_block_lines = [
                "",
                "[Base]",
                f"nickname = {base_nick}",
                f"system = {sys_nick}",
                f"strid_name = {info['strid_name']}",
                f"file = {rel_base}",
            ]
            if info["bgcs_base_run_by"]:
                uni_block_lines.append(f"BGCS_base_run_by = {info['bgcs_base_run_by']}")
            uni_block = "\n".join(uni_block_lines) + "\n"
            with open(str(uni_ini), "a", encoding="utf-8") as f:
                f.write(uni_block)
            # _uni_sections aktualisieren
            base_entries: list[tuple[str, str]] = [
                ("nickname", base_nick),
                ("system", sys_nick),
                ("strid_name", str(info["strid_name"])),
                ("file", rel_base),
            ]
            if info["bgcs_base_run_by"]:
                base_entries.append(("BGCS_base_run_by", info["bgcs_base_run_by"]))
            self._uni_sections.append(("Base", base_entries))
            patch_result.append(tr("result.base_registered").format(nickname=base_nick))
        else:
            patch_result.append(tr("result.uni_not_found_base"))

        # ----- 5) Validierung -----
        errors: list[str] = []
        # Prüfe Room-Dateien
        for room_name in rooms:
            room_lower = room_name.lower()
            rf = rooms_dir / f"{base_nick}_{room_lower}.ini"
            if not rf.exists():
                errors.append(tr("audit.room_not_found").format(file=rf.name))
        # Prüfe Konsistenz
        if not base_ini_path.exists():
            errors.append(tr("audit.base_ini_not_found").format(path=base_ini_path.name))

        # ----- Ergebnis anzeigen -----
        self._set_dirty(True)
        self._write_to_file(reload=False)
        self._refresh_3d_scene()

        result_msg = tr("msg.base_creation_done") + "\n".join(patch_result)
        if errors:
            result_msg += "\n\n" + tr("msg.validation_errors") + "\n".join(f"  • {e}" for e in errors)
        QMessageBox.information(self, tr("msg.base_created"), result_msg)
        self.statusBar().showMessage(tr("status.base_created").format(nickname=base_nick))

    # ------------------------------------------------------------------
    #  Room-Template-Hilfsfunktionen
    # ------------------------------------------------------------------
    def _load_template_rooms(self, game_path: str, template_base_nick: str) -> dict[str, str]:
        """Lädt Room-INI-Dateien einer existierenden Base als Templates.
        Gibt {room_lower: content} zurück."""
        result: dict[str, str] = {}
        # Base-INI in universe.ini finden
        base_file_rel = ""
        for sec_name, entries in self._uni_sections:
            if sec_name.lower() != "base":
                continue
            nick = ""
            for k, v in entries:
                if k.lower() == "nickname":
                    nick = v.strip()
                elif k.lower() == "file":
                    base_file_rel = v.strip()
            if nick.lower() == template_base_nick.lower():
                break
            base_file_rel = ""
        if not base_file_rel:
            return result
        base_ini = self._resolve_game_path_case_insensitive(game_path, base_file_rel)
        if not base_ini or not base_ini.exists():
            return result
        # Base-INI parsen, um Room-Dateien zu finden
        try:
            base_sections = self._parser.parse(str(base_ini))
        except Exception:
            return result
        for sec_name, entries in base_sections:
            if sec_name.lower() != "room":
                continue
            room_nick = ""
            room_file_rel = ""
            for k, v in entries:
                if k.lower() == "nickname":
                    room_nick = v.strip()
                elif k.lower() == "file":
                    room_file_rel = v.strip()
            if not room_nick or not room_file_rel:
                continue
            room_path = self._resolve_game_path_case_insensitive(game_path, room_file_rel)
            if room_path and room_path.exists():
                try:
                    content = room_path.read_text(encoding="utf-8", errors="ignore")
                    result[room_nick.lower()] = content
                except Exception:
                    pass
        return result

    def _adapt_template_room(
        self, content: str, new_base_nick: str, rooms: list[str]
    ) -> str:
        """Passt ein kopiertes Room-Template an: room_switch-Referenzen prüfen."""
        # Kein tiefgreifendes Umbenennen nötig – die Room-Nicknames bleiben
        # standardisiert (Deck, Bar, etc.). Nur sicherstellen, dass room_switch
        # nicht auf Rooms verweist, die wir nicht erstellen.
        lines = content.splitlines()
        result_lines: list[str] = []
        rooms_lower = {r.lower() for r in rooms}
        skip_section = False
        for line in lines:
            stripped = line.strip().lower()
            if stripped.startswith("["):
                skip_section = False
            if stripped.startswith("room_switch"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    target = parts[1].strip()
                    if target.lower() not in rooms_lower:
                        skip_section = True
                        # Ganzen Hotspot-Block überspringen
                        # Rückwärts [Hotspot]-Header entfernen
                        while result_lines and result_lines[-1].strip().lower() in ("", "[hotspot]"):
                            if result_lines[-1].strip().lower() == "[hotspot]":
                                result_lines.pop()
                                break
                            result_lines.pop()
                        continue
            if skip_section:
                if stripped.startswith("["):
                    skip_section = False
                else:
                    continue
            result_lines.append(line)
        return "\n".join(result_lines)

    @staticmethod
    def _generate_room_ini(room_name: str, all_rooms: list[str], start_room: str) -> str:
        """Generiert eine minimale Room-INI-Datei."""
        room_lower = room_name.lower()
        lines: list[str] = []

        # Room_Info
        if room_lower == "deck":
            lines.extend([
                "[Room_Info]",
                "set_script = Scripts\\Bases\\Li_08_Deck_hardpoint_01.thn",
                "scene = all, ambient, Scripts\\Bases\\Li_08_Deck_ambi_int_01.thn",
                "animation = Sc_loop",
            ])
        elif room_lower == "bar":
            lines.extend([
                "[Room_Info]",
                "set_script = Scripts\\Bases\\Li_09_bar_hardpoint_s020x.thn",
                "scene = all, ambient, Scripts\\Bases\\Li_09_bar_ambi_int_s020x.thn",
            ])
        elif room_lower == "trader":
            lines.extend([
                "[Room_Info]",
                "set_script = Scripts\\Bases\\Li_01_Trader_hardpoint_01.thn",
                "scene = all, ambient, Scripts\\Bases\\Li_01_Trader_ambi_int_01.thn",
            ])
        elif room_lower == "equipment":
            lines.extend([
                "[Room_Info]",
                "set_script = scripts\\bases\\Li_01_equipment_hardpoint_01.thn",
                "scene = all, ambient, Scripts\\Bases\\Li_01_equipment_ambi_int_01.thn",
            ])
        elif room_lower == "shipdealer":
            lines.extend([
                "[Room_Info]",
                "set_script = Scripts\\Bases\\Li_01_shipdealer_hardpoint_01.thn",
                "scene = all, ambient, Scripts\\Bases\\Li_01_shipdealer_ambi_int_01.thn",
            ])
        elif room_lower == "cityscape":
            lines.extend([
                "[Room_Info]",
                "set_script = Scripts\\Bases\\Li_01_cityscape_hardpoint_01.thn",
                "animation = Sc_loop",
                "scene = all, ambient, Scripts\\Bases\\Li_01_cityscape_ambi_day_01.thn",
            ])
        else:
            lines.extend([
                "[Room_Info]",
                f"set_script = Scripts\\Bases\\Li_08_Deck_hardpoint_01.thn",
                f"scene = all, ambient, Scripts\\Bases\\Li_08_Deck_ambi_int_01.thn",
            ])

        lines.append("")

        # Spiels (Dealer-Räume)
        if room_lower == "trader":
            lines.extend(["[Spiels]", "CommodityDealer = manhattan_commodity_spiel", ""])
        elif room_lower == "equipment":
            lines.extend(["[Spiels]", "EquipmentDealer = manhattan_equipment_spiel", ""])
        elif room_lower == "shipdealer":
            lines.extend(["[Spiels]", "ShipDealer = manhattan_ship_spiel", ""])

        # Room_Sound
        if room_lower == "bar":
            lines.extend(["[Room_Sound]", "ambient = ambience_deck_space_smaller", ""])
        elif room_lower in ("deck", "cityscape"):
            lines.extend(["[Room_Sound]", "ambient = ambience_deck_space_smaller", ""])
        elif room_lower == "equipment":
            lines.extend(["[Room_Sound]", "ambient = ambience_equip_ground_larger", ""])
        elif room_lower == "shipdealer":
            lines.extend(["[Room_Sound]", "ambient = ambience_shipbuy", ""])
        elif room_lower == "trader":
            lines.extend(["[Room_Sound]", "ambient = ambience_comm", ""])
        else:
            lines.extend(["[Room_Sound]", "ambient = ambience_deck_space_smaller", ""])

        # Camera
        lines.extend(["[Camera]", "name = Camera_0", ""])

        # CharacterPlacement (für Räume, die man betritt)
        if room_lower in ("bar", "trader", "equipment", "shipdealer"):
            lines.extend(["[CharacterPlacement]", "name = Zg/PC/Player/01/A/Stand", ""])

        # PlayerShipPlacement (Deck / Cityscape / Equipment)
        if room_lower in ("deck", "cityscape", "equipment"):
            lines.extend(["[PlayerShipPlacement]", "name = X/Shipcentre/01", ""])

        # ForSaleShipPlacement (ShipDealer)
        if room_lower == "shipdealer":
            lines.extend([
                "[ForSaleShipPlacement]", "name = X/Shipcentre/01", "",
                "[ForSaleShipPlacement]", "name = X/Shipcentre/02", "",
                "[ForSaleShipPlacement]", "name = X/Shipcentre/03", "",
            ])

        # Hotspots – Navigation zwischen Räumen (Vanilla-Muster)
        # Jeder Room bekommt denselben Satz an ExitDoor-Hotspots:
        #   • IDS_HOTSPOT_EXIT → room_switch = hub  (Hub-Selbstreferenz = Launch)
        #   • Ein benannter Hotspot pro Nicht-Hub-Room → room_switch = Room
        # Selbstreferenzen sind gewollt (zeigt den aktiven Room-Button).
        nav_hotspots = MainWindow._build_nav_hotspots(all_rooms, start_room)
        for hotspot_name, target in nav_hotspots:
            lines.extend([
                "[Hotspot]",
                f"name = {hotspot_name}",
                "behavior = ExitDoor",
                f"room_switch = {target}",
                "",
            ])

        # Raum-spezifische Hotspots (Dealer, Repair, News, Mission)
        if room_lower == "bar":
            lines.extend([
                "[Hotspot]", "name = IDS_HOTSPOT_NEWSVENDOR",
                "behavior = NewsVendor", "",
                "[Hotspot]", "name = IDS_HOTSPOT_MISSIONVENDOR",
                "behavior = MissionVendor", "",
            ])
        elif room_lower == "trader":
            lines.extend([
                "[Hotspot]", "name = IDS_DEALER_FRONT_DESK",
                "behavior = FrontDesk", "state_read = 1", "state_send = 2", "",
                "[Hotspot]", "name = IDS_HOTSPOT_COMMODITYTRADER",
                "behavior = StartDealer", "state_read = 2", "state_send = 1", "",
            ])
        elif room_lower == "equipment":
            lines.extend([
                "[Hotspot]", "name = IDS_NN_REPAIR_YOUR_SHIP",
                "behavior = Repair", "",
                "[Hotspot]", "name = IDS_DEALER_FRONT_DESK",
                "behavior = FrontDesk", "state_read = 1", "state_send = 2", "",
                "[Hotspot]", "name = IDS_HOTSPOT_EQUIPMENTDEALER",
                "behavior = StartEquipDealer", "state_read = 2", "state_send = 1", "",
            ])
        elif room_lower == "shipdealer":
            lines.extend([
                "[Hotspot]", "name = IDS_NN_REPAIR_YOUR_SHIP",
                "behavior = Repair", "",
                "[Hotspot]", "name = IDS_DEALER_FRONT_DESK",
                "behavior = FrontDesk", "state_read = 1", "state_send = 2", "",
                "[Hotspot]", "name = IDS_HOTSPOT_SHIPDEALER",
                "behavior = StartShipDealer", "state_read = 2", "state_send = 1", "",
            ])
        elif room_lower in ("deck", "cityscape"):
            lines.extend([
                "[Hotspot]", "name = IDS_NN_REPAIR_YOUR_SHIP",
                "behavior = Repair", "",
            ])

        return "\n".join(lines)

    # Mapping Room-Typ → IDS-Hotspot-Name (für Nicht-Hub-Rooms)
    _ROOM_HOTSPOT_MAP: dict[str, str] = {
        "bar":        "IDS_HOTSPOT_BAR",
        "trader":     "IDS_HOTSPOT_COMMODITYTRADER_ROOM",
        "equipment":  "IDS_HOTSPOT_EQUIPMENTDEALER_ROOM",
        "shipdealer": "IDS_HOTSPOT_SHIPDEALER_ROOM",
        "cityscape":  "IDS_HOTSPOT_CITYSCAPE",
        "deck":       "IDS_HOTSPOT_DECK",
    }

    @staticmethod
    def _build_nav_hotspots(
        all_rooms: list[str], start_room: str
    ) -> list[tuple[str, str]]:
        """Erzeugt die vollständige Navigation-Hotspot-Liste für eine Base.

        Rückgabe: [(hotspot_name, room_switch_target), ...]

        Vanilla-Muster:
          • IDS_HOTSPOT_EXIT → start_room  (Launch/Undock im Hub,
                                            Rückkehr zum Hub sonst)
          • Ein benannter Hotspot pro Nicht-Hub-Room

        Dieser identische Satz erscheint in JEDEM Room der Base
        (inkl. Selbstreferenzen → das Spiel blendet den eigenen Button
        entsprechend ein/aus).
        """
        nav: list[tuple[str, str]] = []
        nav.append(("IDS_HOTSPOT_EXIT", start_room))
        for room in all_rooms:
            if room.lower() == start_room.lower():
                continue  # Hub wird bereits über EXIT abgedeckt
            name = MainWindow._ROOM_HOTSPOT_MAP.get(
                room.lower(), f"IDS_HOTSPOT_{room.upper()}"
            )
            nav.append((name, room))
        return nav

    @staticmethod
    def _normalize_room_navigation(
        content: str,
        room_name: str,
        all_rooms: list[str],
        start_room: str,
    ) -> str:
        """Normalisiert die Navigation-Hotspots in einer Room-INI.

        1. Entfernt ALLE bestehenden ExitDoor-Hotspots.
        2. Fügt den korrekten Satz (vanilla-konform) wieder ein.
        3. Behält alle Nicht-ExitDoor-Hotspots (Repair, Dealer, etc.).
        Idempotent – mehrfaches Aufrufen ändert nichts.
        """
        nav_expected = MainWindow._build_nav_hotspots(all_rooms, start_room)

        lines = content.splitlines()
        result: list[str] = []
        i = 0
        insertion_point: int | None = None

        while i < len(lines):
            stripped = lines[i].strip().lower()
            if stripped == "[hotspot]":
                block: list[str] = [lines[i]]
                i += 1
                while i < len(lines) and not lines[i].strip().lower().startswith("["):
                    block.append(lines[i])
                    i += 1
                is_exit_door = any(
                    l.strip().lower().replace(" ", "") == "behavior=exitdoor"
                    for l in block
                )
                if is_exit_door:
                    if insertion_point is None:
                        insertion_point = len(result)
                    continue  # ExitDoor-Block entfernen
                result.extend(block)
                continue
            result.append(lines[i])
            i += 1

        # Einfügepunkt bestimmen
        if insertion_point is None:
            while result and result[-1].strip() == "":
                result.pop()
            result.append("")
            insertion_point = len(result)

        # Navigation-Hotspots einfügen
        nav_lines: list[str] = []
        for hotspot_name, target in nav_expected:
            nav_lines.extend([
                "[Hotspot]",
                f"name = {hotspot_name}",
                "behavior = ExitDoor",
                f"room_switch = {target}",
                "",
            ])
        result[insertion_point:insertion_point] = nav_lines

        return "\n".join(result)

    def normalize_base_rooms(
        self, base_ini_path: str, game_path: str
    ) -> list[str]:
        """Liest eine Base-INI, patcht alle Room-INIs idempotent.

        Stellt sicher:
          • Jeder Room enthält den vollständigen Satz an Navigation-Hotspots
            (inkl. Self-Button).
          • Launch/Abflug funktioniert korrekt (EXIT → room_switch = Hub,
            Selbstreferenz im Hub = Launch).
          • Keine überflüssigen oder fehlenden ExitDoor-Hotspots.

        Gibt einen Patch-Report zurück (Liste von Strings).
        """
        report: list[str] = []
        base_path = Path(base_ini_path)

        if not base_path.exists():
            report.append(tr("audit.base_ini_not_found").format(path=base_ini_path))
            return report

        try:
            sections = self._parser.parse(str(base_path))
        except Exception as exc:
            report.append(tr("audit.parse_error").format(error=exc))
            return report

        start_room = ""
        rooms: list[tuple[str, str]] = []  # (nickname, file_rel)
        for sec_name, entries in sections:
            if sec_name.lower() == "baseinfo":
                for k, v in entries:
                    if k.lower() == "start_room":
                        start_room = v.strip()
            elif sec_name.lower() == "room":
                nick = ""
                file_rel = ""
                for k, v in entries:
                    if k.lower() == "nickname":
                        nick = v.strip()
                    elif k.lower() == "file":
                        file_rel = v.strip()
                if nick and file_rel:
                    rooms.append((nick, file_rel))

        if not start_room:
            report.append(tr("audit.no_start_room"))
            return report
        if not rooms:
            report.append(tr("audit.no_rooms"))
            return report

        all_room_names = [r[0] for r in rooms]
        report.append(f"Base: {base_path.name}")
        report.append(f"  Hub (start_room): {start_room}")
        report.append(f"  Rooms: {', '.join(all_room_names)}")
        report.append("")

        for nick, file_rel in rooms:
            room_path = self._resolve_game_path_case_insensitive(
                game_path, file_rel
            )
            if not room_path or not room_path.exists():
                report.append(tr("audit.room_not_found").format(file=file_rel))
                continue

            try:
                content = room_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as exc:
                report.append(tr("audit.room_read_error").format(file=room_path.name, error=exc))
                continue

            new_content = MainWindow._normalize_room_navigation(
                content, nick, all_room_names, start_room
            )

            if content == new_content:
                report.append(tr("audit.unchanged").format(file=room_path.name))
            else:
                room_path.write_text(new_content, encoding="utf-8")
                # Detailbericht: welche Hotspots wurden gesetzt?
                nav = MainWindow._build_nav_hotspots(all_room_names, start_room)
                nav_names = [n for n, _ in nav]
                report.append(
                    tr("audit.patched").format(file=room_path.name, hotspots=", ".join(nav_names))
                )

        return report

    # ------------------------------------------------------------------
    #  Scan-Helfer für Base-Dialog Dropdowns
    # ------------------------------------------------------------------
    def _scan_pilots(self, game_path: str) -> list[str]:
        """Scannt pilots_population.ini nach allen [Pilot]-Nicknames."""
        pilots: list[str] = []
        data_dir = ci_find(Path(game_path), "DATA")
        if not data_dir:
            return pilots
        missions_dir = ci_find(data_dir, "MISSIONS")
        if not missions_dir:
            return pilots
        pp = ci_find(missions_dir, "pilots_population.ini")
        if not pp or not pp.is_file():
            return pilots
        try:
            sections = self._parser.parse(str(pp))
            for sec_name, entries in sections:
                if sec_name.lower() == "pilot":
                    for k, v in entries:
                        if k.lower() == "nickname":
                            pilots.append(v.strip())
                            break
        except Exception:
            pass
        return pilots

    def _scan_voices(self, game_path: str) -> list[str]:
        """Scannt Voice-INIs unter DATA/AUDIO nach allen [Voice]-Nicknames."""
        voices: list[str] = []
        data_dir = ci_find(Path(game_path), "DATA")
        if not data_dir:
            return voices
        audio_dir = ci_find(data_dir, "AUDIO")
        if not audio_dir or not audio_dir.is_dir():
            return voices
        voice_files = [
            "voices_space_male.ini", "voices_space_female.ini",
            "voices_base_male.ini", "voices_base_female.ini",
            "voices_recognizable.ini",
        ]
        for fname in voice_files:
            vf = ci_find(audio_dir, fname)
            if not vf or not vf.is_file():
                continue
            try:
                sections = self._parser.parse(str(vf))
                for sec_name, entries in sections:
                    if sec_name.lower() == "voice":
                        for k, v in entries:
                            if k.lower() == "nickname":
                                voices.append(v.strip())
                                break
            except Exception:
                pass
        return voices

    def _scan_bodyparts(self, game_path: str) -> tuple[list[str], list[str]]:
        """Scannt DATA/CHARACTERS/bodyparts.ini nach Head- und Body-Teilen."""
        heads: list[str] = []
        bodies: list[str] = []
        data_dir = ci_find(Path(game_path), "DATA")
        if not data_dir:
            return heads, bodies
        chars_dir = ci_find(data_dir, "CHARACTERS")
        if not chars_dir:
            return heads, bodies
        bp = ci_find(chars_dir, "bodyparts.ini")
        if not bp or not bp.is_file():
            return heads, bodies
        try:
            sections = self._parser.parse(str(bp))
            for sec_name, entries in sections:
                if sec_name.lower() not in ("body", "head"):
                    continue
                for k, v in entries:
                    if k.lower() == "nickname":
                        nick = v.strip()
                        if sec_name.lower() == "head":
                            heads.append(nick)
                        else:
                            bodies.append(nick)
                        break
        except Exception:
            pass
        return heads, bodies

    def _start_connection_dialog(self):
        if not self._filepath:
            QMessageBox.warning(self, tr("msg.no_system"), tr("msg.no_system_text"))
            return
        if self._pending_snapshots:
            QMessageBox.warning(self, tr("msg.open_changes"), tr("msg.save_connections_first"))
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
        self.statusBar().showMessage(tr("status.click_conn_origin"))
        self._set_placement_mode(True, tr("placement.conn_origin"))

    # ------------------------------------------------------------------
    #  Neues System erstellen
    # ------------------------------------------------------------------
    def _start_new_system(self):
        """Öffnet Dialog und aktiviert Platzierungsmodus auf der Karte."""
        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        if not game_path:
            QMessageBox.warning(self, tr("msg.no_path"), tr("msg.no_path_enter"))
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
            QMessageBox.warning(self, tr("msg.error"), tr("msg.name_prefix_required"))
            return

        self._pending_new_system = {**payload, "game_path": game_path}
        self._set_placement_mode(True, tr("placement.new_system"))
        self.statusBar().showMessage(tr("status.click_system_place"))

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
            QMessageBox.critical(self, tr("msg.error"), tr("msg.universe_not_found_2"))
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
            tr("status.system_created").format(
                name=name, nickname=nickname, path=sys_file
            )
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
            self._on_zone_click(pos)
            return
        if self._pending_simple_zone:
            self._on_simple_zone_click(pos)
            return
        if self._pending_exclusion_zone:
            self._on_exclusion_zone_click(pos)
            return
        if self._pending_base:
            self._create_base_at_pos(pos)
            self._set_placement_mode(False)
            return
        if self._pending_template_object:
            self._create_template_object_at_pos(pos)
            self._set_placement_mode(False)
            return
        if self._pending_buoy:
            self._on_buoy_click(pos)
            if not self._pending_buoy:
                self._set_placement_mode(False)
            return
        if self._pending_light_source:
            self._create_light_source_at_pos(pos)
            self._set_placement_mode(False)
            return
        if self._pending_create:
            self._create_solar_at_pos(pos)
            self._set_placement_mode(False)
            return
        if self._pending_tradelane:
            self._on_tradelane_click(pos)
            return
        if self._pending_tl_reposition:
            self._on_tl_reposition_click(pos)
            return
        if self._pending_dock_ring and self._pending_dock_ring.get("step") == 2:
            self._on_dock_ring_orbit_click(pos)
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
            self.statusBar().showMessage(tr("status.conn_origin_placed"))
            self._set_placement_mode(True, tr("placement.conn_dest"))
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
            self.statusBar().showMessage(tr("status.conn_dest_placed"))
            self._set_placement_mode(False)

    # ==================================================================
    #  Löschen
    # ==================================================================
    def _delete_object(self):
        if self._flight_lock_active:
            return
        if self._multi_selected:
            targets = [it for it in self._multi_selected if isinstance(it, (SolarObject, ZoneItem))]
            self._clear_multi_selection()
            deleted = 0
            for it in list(targets):
                if isinstance(it, ZoneItem):
                    if it in self._zones:
                        self._delete_zone(it)
                        deleted += 1
                else:
                    if it in self._objects:
                        self._delete_solar_object(it)
                        deleted += 1
            if deleted:
                self.statusBar().showMessage(tr("status.multi_deleted").format(count=deleted))
            return
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
        z_sec_idx = self._section_index_for_zone_index(z_idx) if z_idx is not None else None
        # --- 1) [Zone]-Sektion aus _sections entfernen ---
        if z_idx is not None:
            count = 0
            for i, (sec_name, entries) in enumerate(list(self._sections)):
                if sec_name.lower() == "zone":
                    if count == z_idx:
                        self._sections.pop(i)
                        break
                    count += 1

        # --- 2) Verknüpfte [Asteroids]/[Nebula]-Sektion + externe Datei entfernen ---
        zone_nick = zone.nickname.strip().lower()
        linked_sec_idx = None
        linked_section_name = None
        linked_section_entries = None
        linked_file_rel = ""
        linked_file_content = ""
        exclusion_linked_files: list[dict] = []
        exclusion_seen_files: set[str] = set()
        linked_exclusion_nicks: list[str] = []
        deleted_exclusion_zones: list[dict] = []
        for idx, (sec_name, entries) in enumerate(self._sections):
            if sec_name.lower() not in ("nebula", "asteroids"):
                continue
            zone_val = ""
            file_val = ""
            for k, v in entries:
                if k.lower() == "zone":
                    zone_val = v.strip().lower()
                elif k.lower() == "file":
                    file_val = v.strip()

            if file_val:
                file_key = file_val.strip().lower()
                if file_key not in exclusion_seen_files:
                    exclusion_seen_files.add(file_key)
                    game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
                    linked_file = self._resolve_game_path_case_insensitive(game_path, file_val)
                    if linked_file and linked_file.is_file():
                        try:
                            original_text = linked_file.read_text(encoding="utf-8", errors="ignore")
                        except Exception:
                            original_text = ""
                        if original_text:
                            patched_text, changed = patch_field_ini_remove_exclusion(original_text, zone.nickname)
                            if changed:
                                try:
                                    tmp = str(linked_file) + ".tmp"
                                    Path(tmp).write_text(patched_text, encoding="utf-8")
                                    shutil.move(tmp, linked_file)
                                    exclusion_linked_files.append({"rel": file_val, "content": original_text})
                                except Exception:
                                    pass
            if zone_val == zone_nick and linked_sec_idx is None:
                linked_sec_idx = idx
                linked_section_name = sec_name
                linked_section_entries = list(entries)
                for k, v in entries:
                    if k.lower() == "file":
                        linked_file_rel = v.strip()
                        break
                if linked_file_rel:
                    game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
                    linked_file = self._resolve_game_path_case_insensitive(game_path, linked_file_rel)
                    if linked_file and linked_file.is_file():
                        try:
                            linked_file_content = linked_file.read_text(encoding="utf-8", errors="ignore")
                        except Exception:
                            linked_file_content = ""
                        if linked_file_content:
                            linked_exclusion_nicks = self._parse_exclusion_nicks_from_field_ini(linked_file_content)
                    known_excl = {n.lower() for n in linked_exclusion_nicks}
                    prefix = f"{zone_nick}_exclusion_"
                    for z in self._zones:
                        zn = z.nickname.strip()
                        if zn.lower().startswith(prefix) and zn.lower() not in known_excl:
                            linked_exclusion_nicks.append(zn)
                            known_excl.add(zn.lower())

        if linked_exclusion_nicks:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Question)
            msg.setWindowTitle("Verknüpfte Exclusion-Zonen")
            msg.setText("Für dieses Asteroiden-/Nebel-Feld wurden Exclusion-Zonen gefunden.")
            msg.setInformativeText(
                "Sollen diese ebenfalls gelöscht werden?\n\n"
                + "\n".join(f"- {n}" for n in linked_exclusion_nicks)
            )
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            if msg.exec() == QMessageBox.Yes:
                for ex_nick in linked_exclusion_nicks:
                    removed = self._remove_zones_by_nickname(ex_nick)
                    if removed:
                        deleted_exclusion_zones.extend(removed)

        if linked_sec_idx is not None:
            self._sections.pop(linked_sec_idx)
        # Externe .ini-Datei löschen
        if linked_file_rel:
            game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
            linked_file = self._resolve_game_path_case_insensitive(game_path, linked_file_rel)
            if linked_file and linked_file.is_file():
                try:
                    linked_file.unlink()
                except Exception as ex:
                    QMessageBox.warning(self, tr("msg.file_error"),
                                        tr("msg.file_delete_error").format(error=ex))

        if z_idx is not None:
            action = {
                "type": "delete_zone",
                "label": f"Zone gelöscht: {zone.nickname}",
                "filepath": self._filepath or "",
                "zone": {
                    "nickname": zone.nickname,
                    "entries": [list(p) for p in zone.data.get("_entries", [])],
                    "zone_index": int(z_idx),
                    "section_index": int(z_sec_idx) if z_sec_idx is not None else None,
                },
            }
            if linked_sec_idx is not None and linked_section_name and linked_section_entries:
                action["linked_section"] = {
                    "section_index": int(linked_sec_idx),
                    "name": linked_section_name,
                    "entries": [list(p) for p in linked_section_entries],
                }
            if linked_file_rel:
                action["linked_file"] = {
                    "rel": linked_file_rel,
                    "content": linked_file_content,
                }
            if exclusion_linked_files:
                action["exclusion_linked_files"] = exclusion_linked_files
            if deleted_exclusion_zones:
                action["deleted_exclusion_zones"] = deleted_exclusion_zones
            self._push_undo_action(action)

        self.view._scene.removeItem(zone)
        if zone in self._zones:
            self._zones.remove(zone)
        self._rebuild_object_combo()
        self._selected = None
        self._clear_selection_ui()
        self._hide_zone_extra_editors()
        self._set_dirty(True)
        self._write_to_file(reload=False)
        extra = ""
        if linked_sec_idx is not None:
            extra += tr("status.zone_extra_section")
        if linked_file_rel:
            extra += tr("status.zone_extra_linked")
        self.statusBar().showMessage(tr("status.zone_deleted").format(nickname=zone.nickname, extra=extra))
        self._refresh_3d_scene()

    def _delete_solar_object(self, obj: SolarObject):
        nick = obj.nickname.lower()
        arch = obj.data.get("archetype", "").lower()
        base_nick = obj.data.get("base", "").strip()

        if "planet" in arch and base_nick:
            has_dock_ring = any(
                o is not obj and o.data.get("dock_with", "").strip().lower() == base_nick.lower()
                for o in self._objects
            )
            if has_dock_ring:
                self._delete_base()
                return

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

        msg = tr("msg.confirm_delete_text").format(nickname=obj.nickname)
        if counterpart_nick and counterpart_file:
            msg = tr("msg.confirm_delete_gate").format(
                nickname=obj.nickname, counterpart=counterpart_nick
            )
            if QMessageBox.warning(self, tr("msg.confirm_delete"), msg,
                                   QMessageBox.Ok | QMessageBox.Cancel) != QMessageBox.Ok:
                return
        elif counterpart_nick and not counterpart_file:
            err = tr("msg.counterpart_not_found_text").format(
                counterpart=counterpart_nick, system=counterpart_sys
            )
            if QMessageBox.question(self, tr("msg.counterpart_not_found"), err,
                                    QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                return

        # Sektion entfernen
        obj_idx = None
        try:
            obj_idx = self._objects.index(obj)
        except ValueError:
            pass
        obj_sec_idx = self._section_index_for_object_index(obj_idx) if obj_idx is not None else None

        linked_zone_action = None
        if "sun" in arch or "planet" in arch:
            target_zone_nick = f"zone_{nick}_death"
            linked_zone = next(
                (z for z in self._zones if z.nickname.lower() == target_zone_nick), None
            )
            if linked_zone is not None:
                try:
                    lz_idx = self._zones.index(linked_zone)
                except ValueError:
                    lz_idx = None
                lz_sec_idx = self._section_index_for_zone_index(lz_idx) if lz_idx is not None else None
                linked_zone_action = {
                    "nickname": linked_zone.nickname,
                    "entries": [list(p) for p in linked_zone.data.get("_entries", [])],
                    "zone_index": int(lz_idx) if lz_idx is not None else None,
                    "section_index": int(lz_sec_idx) if lz_sec_idx is not None else None,
                }

        if obj_idx is not None:
            action = {
                "type": "delete_object",
                "label": f"Objekt gelöscht: {obj.nickname}",
                "filepath": self._filepath or "",
                "object": {
                    "nickname": obj.nickname,
                    "entries": [list(p) for p in obj.data.get("_entries", [])],
                    "object_index": int(obj_idx),
                    "section_index": int(obj_sec_idx) if obj_sec_idx is not None else None,
                },
            }
            if linked_zone_action:
                action["linked_zone"] = linked_zone_action
            self._push_undo_action(action)

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
                QMessageBox.warning(self, tr("msg.counterpart_delete_error"),
                                    tr("msg.counterpart_delete_error_text").format(error=ex))
        self.statusBar().showMessage(tr("status.object_deleted").format(nickname=nick))
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
        old_entries = [(str(k), str(v)) for k, v in self._selected.data.get("_entries", [])]
        old_nickname = str(getattr(self._selected, "nickname", ""))
        self._selected.apply_text(self.editor.toPlainText())
        self._refresh_3d_scene(preserve_camera=True)

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
                    QMessageBox.warning(self, tr("msg.zone_file_error"),
                                        tr("msg.zone_file_error_text").format(error=ex))

        self.name_lbl.setText(f"📍 {self._selected.nickname}")
        if isinstance(self._selected, SolarObject) and not hasattr(self._selected, "sys_path"):
            new_entries = [(str(k), str(v)) for k, v in self._selected.data.get("_entries", [])]
            if new_entries != old_entries:
                try:
                    obj_idx = self._objects.index(self._selected)
                except ValueError:
                    obj_idx = None
                self._push_undo_action(
                    {
                        "type": "edit_object",
                        "label": f"Objekt bearbeitet: {self._selected.nickname}",
                        "filepath": self._filepath or "",
                        "object_index": obj_idx,
                        "old_nickname": old_nickname,
                        "new_nickname": self._selected.nickname,
                        "old_entries": [list(p) for p in old_entries],
                        "new_entries": [list(p) for p in new_entries],
                    }
                )
                self._append_change_log(f"Objekt bearbeitet: {old_nickname} -> {self._selected.nickname}")
        self._set_dirty(True)
        self.statusBar().showMessage(
            tr("status.changes_applied").format(nickname=self._selected.nickname)
        )

    def _capture_selection_ref(self):
        if isinstance(self._selected, ZoneItem):
            return ("zone", self._selected.nickname)
        if isinstance(self._selected, SolarObject) and not hasattr(self._selected, "sys_path"):
            return ("obj", self._selected.nickname)
        return None

    def _restore_selection_ref(self, sel_ref):
        if not sel_ref:
            return
        kind, nick = sel_ref
        nick_low = str(nick).lower()
        if kind == "zone":
            for z in self._zones:
                if z.nickname.lower() == nick_low:
                    self._select_zone(z)
                    return
            return
        for o in self._objects:
            if o.nickname.lower() == nick_low:
                self._select(o)
                return

    def _write_to_file(self, reload: bool = True):
        if not self._filepath:
            # Universum-Ansicht: Positionen in universe.ini speichern
            self._save_universe_positions()
            return
        cam_state = None
        keep_cam = bool(
            hasattr(self, "view3d")
            and self.view3d_switch.isVisible()
            and self.view3d_switch.isChecked()
            and hasattr(self.view3d, "get_camera_state")
        )
        if keep_cam:
            cam_state = self.view3d.get_camera_state()
        sel_ref = self._capture_selection_ref()
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
            QMessageBox.critical(self, tr("msg.save_error"), str(ex))
            return

        if reload:
            self.statusBar().showMessage(tr("status.saved_reloading"))
            self._load(self._filepath, restore=self.view.transform())
            self.browser.highlight_current(self._filepath)
            self._restore_selection_ref(sel_ref)
            if cam_state and hasattr(self.view3d, "set_camera_state"):
                self.view3d.set_camera_state(cam_state)
        else:
            self._set_dirty(False)
            self.statusBar().showMessage(tr("status.saved"))

    def _on_universe_system_moved(self, obj: SolarObject):
        """Callback wenn ein System auf der Universumskarte verschoben wird."""
        self._set_dirty(True)
        x = obj.pos().x() / self._scale
        y = obj.pos().y() / self._scale
        self.statusBar().showMessage(tr("status.system_position").format(nickname=obj.nickname, x=x, y=y))
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
            QMessageBox.warning(self, tr("msg.error"), tr("msg.no_valid_entries"))
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
            QMessageBox.warning(self, tr("msg.error"), tr("msg.system_not_found").format(nickname=self._uni_selected_nick))
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
            self.statusBar().showMessage(tr("status.uni_system_saved").format(nickname=self._uni_selected_nick))
        except Exception as ex:
            QMessageBox.critical(self, tr("msg.save_error"), str(ex))

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
        if self._flight_lock_active:
            return
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
        self.statusBar().showMessage(tr("status.undo_done"))

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
            self.statusBar().showMessage(tr("status.uni_positions_saved"))
        except Exception as ex:
            QMessageBox.critical(self, tr("msg.save_error"), str(ex))

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
            QMessageBox.critical(self, tr("msg.save_error"), str(ex))

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

        # Shortest-Path-Dateien neu generieren
        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        if game_path:
            from .pathgen import regenerate_shortest_paths
            try:
                msg = regenerate_shortest_paths(game_path, self._parser)
                self.statusBar().showMessage(tr("status.connections_saved") + f" – {msg}")
            except Exception as ex:
                self.statusBar().showMessage(tr("status.connections_saved") + f" ({ex})")
        else:
            self.statusBar().showMessage(tr("status.connections_saved"))

    # ==================================================================
    #  Dirty-Flag  &  Diverse Toggler
    # ==================================================================
    def _set_dirty(self, d: bool):
        self._dirty = d
        # Im Universe-Modus den Universe-Save-Button aktivieren
        is_universe = self._filepath is None and hasattr(self, '_uni_save_action')
        self.write_btn.setEnabled(bool(self._filepath) and d and not self._flight_lock_active)
        if is_universe and hasattr(self, 'uni_save_btn'):
            self._uni_save_action.setVisible(d)
            self._uni_undo_action.setVisible(d)
        t = self.windowTitle()
        if d and not t.startswith("*"):
            self.setWindowTitle("* " + t)
        elif not d and t.startswith("* "):
            self.setWindowTitle(t[2:])

    def _toggle_move(self, checked: bool):
        if self._flight_lock_active:
            return
        for obj in self._objects:
            obj.setFlag(QGraphicsItem.ItemIsMovable, checked)
        self.view3d.set_move_mode(checked)
        self.statusBar().showMessage(
            tr("status.move_on")
            if checked else tr("status.move_off")
        )

    def _toggle_zones(self, checked: bool):
        for z in self._zones:
            z.setVisible(checked)
        self._refresh_3d_scene(preserve_camera=True)

    def _fit(self):
        r = self.view._scene.itemsBoundingRect()
        pad = 20 if self._filepath is None else 80
        self.view.fitInView(r.adjusted(-pad, -pad, pad, pad), Qt.KeepAspectRatio)
        self._sync_zoom_slider_from_view(self.view.current_zoom_factor())

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

    def _target_game_path_for_rel(self, game_path: str, rel_path: str) -> Path | None:
        """Resolve existing file case-insensitively; otherwise build target under DATA/."""
        if not game_path or not rel_path:
            return None
        hit = self._resolve_game_path_case_insensitive(game_path, rel_path)
        if hit is not None:
            return hit
        base = Path(game_path)
        rel = rel_path.replace("\\", "/").strip().lstrip("/")
        if not rel:
            return None
        data_dir = ci_find(base, "DATA")
        if data_dir is None:
            data_dir = base / "DATA"
        if rel.lower().startswith("data/"):
            rel = rel.split("/", 1)[1] if "/" in rel else ""
            if not rel:
                return data_dir
        return data_dir / rel

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
            QMessageBox.information(self, tr("msg.3d_preview"), tr("msg.3d_select_first"))
            return
        archetype = obj.data.get("archetype", "").strip()
        if not archetype:
            QMessageBox.warning(self, tr("msg.3d_preview"), tr("msg.3d_no_archetype"))
            return
        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        if not game_path:
            QMessageBox.warning(self, tr("msg.3d_preview"), tr("msg.3d_no_game_path"))
            return
        model_path, da_arch = self._resolve_model_for_archetype(archetype, game_path)
        if not da_arch:
            QMessageBox.warning(self, tr("msg.3d_preview"),
                                tr("msg.3d_no_da").format(archetype=archetype))
            return
        if not model_path:
            QMessageBox.warning(self, tr("msg.3d_preview"),
                                tr("msg.3d_da_not_resolved").format(da_arch=da_arch))
            return
        preview_mesh = self._find_preview_mesh_candidate(model_path)
        if not QT3D_AVAILABLE:
            QMessageBox.information(
                self, tr("msg.3d_preview"),
                tr("msg.3d_not_available").format(path=f"{archetype} / {da_arch} / {model_path}"),
            )
            return
        if not preview_mesh:
            prim = self._primitive_for_model(obj, model_path)
            dlg = MeshPreviewDialog(
                self, None, f"3D Preview — {obj.nickname} (Fallback)",
                primitive=prim,
                info_text=tr("msg.3d_original_not_renderable").format(
                    archetype=archetype, file=f"{da_arch} → {model_path}", fallback=prim),
            )
            dlg.exec()
            return
        MeshPreviewDialog(self, preview_mesh, f"3D Preview — {obj.nickname}").exec()

    def _open_model_file(self):
        start_dir = self.browser.path_edit.text().strip() or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self, tr("msg.open_model"), start_dir,
            "Freelancer/3D (*.cmp *.3db *.sph *.obj *.stl *.ply "
            f"*.gltf *.glb *.dae *.fbx *.3ds);;{tr('msg.all_files')}",
        )
        if not path:
            return
        model_path = Path(path)
        preview_mesh = self._find_preview_mesh_candidate(model_path)
        if not QT3D_AVAILABLE:
            QMessageBox.information(self, tr("msg.3d_preview"), tr("msg.3d_not_available").format(path=model_path))
            return
        if preview_mesh:
            MeshPreviewDialog(self, preview_mesh, f"3D Preview — {model_path.name}").exec()
            return
        prim = "sphere" if model_path.suffix.lower() == ".sph" else "cube"
        MeshPreviewDialog(
            self, None, f"3D Preview — {model_path.name} (Fallback)",
            primitive=prim,
            info_text=tr("msg.3d_not_renderable").format(
                file=model_path, format=model_path.suffix.lower(), fallback=prim),
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
        section_l = section.lower()
        key_l = key.lower()
        matching_indices: list[int] = []
        updated_any_key = False

        for idx, (sec_name, entries) in enumerate(self._sections):
            if sec_name.lower() != section_l:
                continue
            matching_indices.append(idx)
            changed = False
            for j, (k, v) in enumerate(entries):
                if k.lower() == key_l:
                    entries[j] = (k, value)
                    changed = True
                    updated_any_key = True
            if changed:
                self._sections[idx] = (sec_name, entries)

        if matching_indices and not updated_any_key:
            first_idx = matching_indices[0]
            sec_name, entries = self._sections[first_idx]
            entries.append((key, value))
            self._sections[first_idx] = (sec_name, entries)
            return

        if not matching_indices:
            self._sections.append((section, [(key, value)]))

    def _open_system_settings(self):
        """Öffnet den System-Einstellungen-Dialog."""
        if not self._filepath:
            return
        current = {
            "nickname": Path(self._filepath).stem.upper(),
            "music_space": self._get_section_value("Music", "space"),
            "music_danger": self._get_section_value("Music", "danger"),
            "music_battle": self._get_section_value("Music", "battle"),
            "space_color": self._get_section_value("SystemInfo", "space_color"),
            "local_faction": self._get_section_value("SystemInfo", "local_faction"),
            "ambient_color": self._get_section_value("Ambient", "color"),
            "dust": self._get_section_value("Dust", "spacedust"),
            "bg_basic": self._get_section_value("Background", "basic_stars"),
            "bg_complex": self._get_section_value("Background", "complex_stars"),
            "bg_nebulae": self._get_section_value("Background", "nebulae"),
        }
        dlg = SystemSettingsDialog(
            self,
            current=current,
            music_options=self._cached_music_opts,
            bg_options=self._cached_bg_opts,
            factions=self._cached_factions,
            dust_options=self._cached_dust_opts,
        )
        if dlg.exec() != QDialog.Accepted:
            return
        data = dlg.result_data()
        self._set_section_value("Music", "space", data["music_space"])
        self._set_section_value("Music", "danger", data["music_danger"])
        self._set_section_value("Music", "battle", data["music_battle"])
        self._set_section_value("SystemInfo", "space_color", data["space_color"])
        self._set_section_value("SystemInfo", "local_faction", data["local_faction"])
        self._set_section_value("Ambient", "color", data["ambient_color"])
        self._set_section_value("Dust", "spacedust", data["dust"])
        self._set_section_value("Background", "basic_stars", data["bg_basic"])
        self._set_section_value("Background", "complex_stars", data["bg_complex"])
        self._set_section_value("Background", "nebulae", data["bg_nebulae"])
        self._set_dirty(True)
        self._write_to_file(reload=True)

    def _populate_system_options(self):
        """Scannt alle Systeme und cached Dropdown-Optionen für den Einstellungen-Dialog."""
        game_path = self._cfg.get("game_path", "")
        music_vals = {"space": set(), "danger": set(), "battle": set()}
        bg_vals = {"basic_stars": set(), "complex_stars": set(), "nebulae": set()}
        dust_vals: set[str] = set()
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
                        elif low == "system":
                            for k, v in entries:
                                if k.lower() == "dust" and v:
                                    dust_vals.add(v)
            except Exception:
                pass
        self._cached_music_opts = {
            "space": sorted(music_vals["space"], key=str.lower),
            "danger": sorted(music_vals["danger"], key=str.lower),
            "battle": sorted(music_vals["battle"], key=str.lower),
        }
        self._cached_bg_opts = {
            "basic_stars": sorted(bg_vals["basic_stars"], key=str.lower),
            "complex_stars": sorted(bg_vals["complex_stars"], key=str.lower),
            "nebulae": sorted(bg_vals["nebulae"], key=str.lower),
        }
        self._cached_dust_opts = sorted(dust_vals, key=str.lower)

        # Local Factions
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
        self._cached_factions = factions

    def _refresh_system_fields(self):
        """Aktualisiert den Button-Text mit dem System-Kürzel."""
        if self._filepath:
            nickname = Path(self._filepath).stem.upper()
            self.sys_settings_btn.setText(f"⚙️  {tr('dlg.system_settings').format(nickname=nickname)}")

    def _search_nickname(self):
        term = self.search_edit.text().strip().lower()
        if not term:
            return
        for o in self._objects:
            if o.nickname.lower() == term:
                self.view.centerOn(o)
                self._select(o)
                return
        QMessageBox.information(self, tr("msg.not_found"), tr("msg.not_found_nickname").format(term=term))

    # ── Fehlende IDS scannen & CSV-Export ─────────────────────────
    def _scan_missing_ids(self):
        """Durchsucht alle System-INI-Dateien nach Objekten/Zonen mit
        ``ids_name = 0`` oder ``ids_info = 0`` und exportiert zwei
        getrennte CSV-Dateien direkt im Spielverzeichnis.
        """
        import csv

        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        if not game_path:
            QMessageBox.warning(self, tr("msg.no_game_path"),
                                tr("msg.no_game_loaded"))
            return

        systems = find_all_systems(game_path, self._parser)
        if not systems:
            QMessageBox.warning(self, tr("msg.no_game_path"),
                                tr("msg.no_systems_scan"))
            return

        missing_name: list[dict] = []  # ids_name = 0
        missing_info: list[dict] = []  # ids_info = 0

        for sys_entry in systems:
            sys_nick = sys_entry["nickname"]
            sys_path = sys_entry["path"]
            try:
                sections = self._parser.parse(sys_path)
            except Exception:
                continue

            for sec_name, entries in sections:
                sec_lower = sec_name.lower()
                if sec_lower not in ("object", "zone"):
                    continue

                d: dict[str, str] = {}
                for k, v in entries:
                    kl = k.lower()
                    if kl not in d:
                        d[kl] = v

                nickname = d.get("nickname", "")
                archetype = d.get("archetype", "")

                # Nur prüfen wenn das Feld explizit vorhanden ist
                if "ids_name" in d and d["ids_name"].strip() == "0":
                    missing_name.append({
                        "System": sys_nick,
                        "Sektion": sec_name,
                        "Nickname": nickname,
                        "Archetype": archetype,
                        "ids_name": "",
                        "givenname": "",
                    })
                if "ids_info" in d and d["ids_info"].strip() == "0":
                    missing_info.append({
                        "System": sys_nick,
                        "Sektion": sec_name,
                        "Nickname": nickname,
                        "Archetype": archetype,
                        "ids_info": "",
                        "xmlinfo": "",
                    })

        if not missing_name and not missing_info:
            QMessageBox.information(
                self, tr("msg.no_matches"),
                tr("msg.no_ids_found")
            )
            return

        folder = Path(game_path)
        written: list[str] = []

        if missing_name:
            name_path = folder / "missing_ids_name.csv"
            with open(name_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["System", "Sektion", "Nickname", "Archetype",
                                "ids_name", "givenname"],
                    delimiter=";",
                )
                writer.writeheader()
                writer.writerows(missing_name)
            written.append(tr("ids.name_entries").format(count=len(missing_name), file=name_path.name))

        if missing_info:
            info_path = folder / "missing_ids_info.csv"
            with open(info_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["System", "Sektion", "Nickname", "Archetype",
                                "ids_info", "xmlinfo"],
                    delimiter=";",
                )
                writer.writeheader()
                writer.writerows(missing_info)
            written.append(tr("ids.info_entries").format(count=len(missing_info), file=info_path.name))

        QMessageBox.information(
            self, tr("msg.csv_export_done"),
            tr("msg.csv_export_text").format(files="\n".join(written) + "\n\n" + tr("ids.target_folder").format(folder=folder))
        )

    # ── IDS aus CSV importieren ───────────────────────────────────
    def _import_ids_from_csv(self):
        """Liest die CSV-Dateien, trägt ausgefüllte ids_name/ids_info
        Nummern in die jeweiligen System-INI-Dateien ein und entfernt
        verarbeitete Zeilen aus den CSVs.
        """
        import csv

        game_path = self.browser.path_edit.text().strip() or self._cfg.get("game_path", "")
        if not game_path:
            QMessageBox.warning(self, tr("msg.no_game_path"),
                                tr("msg.no_game_loaded"))
            return

        folder = Path(game_path)
        name_csv = folder / "missing_ids_name.csv"
        info_csv = folder / "missing_ids_info.csv"

        if not name_csv.exists() and not info_csv.exists():
            QMessageBox.information(
                self, tr("msg.no_csv_files"),
                tr("msg.no_csv_text")
            )
            return

        systems = find_all_systems(game_path, self._parser)
        sys_map: dict[str, str] = {s["nickname"].lower(): s["path"] for s in systems}

        updated_name = 0
        updated_info = 0

        # ── ids_name CSV verarbeiten ─────────────────────────────
        remaining_name: list[dict] = []
        if name_csv.exists():
            with open(name_csv, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=";")
                rows = list(reader)

            for row in rows:
                ids_val = row.get("ids_name", "").strip()
                if not ids_val:
                    remaining_name.append(row)
                    continue

                sys_nick = row.get("System", "").strip()
                obj_nick = row.get("Nickname", "").strip()
                sec_type = row.get("Sektion", "Object").strip().lower()
                sys_path = sys_map.get(sys_nick.lower())
                if not sys_path:
                    remaining_name.append(row)
                    continue

                if self._update_ids_in_file(sys_path, sec_type, obj_nick,
                                            "ids_name", ids_val):
                    updated_name += 1
                else:
                    remaining_name.append(row)

            # CSV aktualisieren oder löschen
            if remaining_name:
                with open(name_csv, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=["System", "Sektion", "Nickname", "Archetype",
                                    "ids_name", "givenname"],
                        delimiter=";",
                    )
                    writer.writeheader()
                    writer.writerows(remaining_name)
            else:
                name_csv.unlink(missing_ok=True)

        # ── ids_info CSV verarbeiten ─────────────────────────────
        remaining_info: list[dict] = []
        if info_csv.exists():
            with open(info_csv, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=";")
                rows = list(reader)

            for row in rows:
                ids_val = row.get("ids_info", "").strip()
                if not ids_val:
                    remaining_info.append(row)
                    continue

                sys_nick = row.get("System", "").strip()
                obj_nick = row.get("Nickname", "").strip()
                sec_type = row.get("Sektion", "Object").strip().lower()
                sys_path = sys_map.get(sys_nick.lower())
                if not sys_path:
                    remaining_info.append(row)
                    continue

                if self._update_ids_in_file(sys_path, sec_type, obj_nick,
                                            "ids_info", ids_val):
                    updated_info += 1
                else:
                    remaining_info.append(row)

            # CSV aktualisieren oder löschen
            if remaining_info:
                with open(info_csv, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=["System", "Sektion", "Nickname", "Archetype",
                                    "ids_info", "xmlinfo"],
                        delimiter=";",
                    )
                    writer.writeheader()
                    writer.writerows(remaining_info)
            else:
                info_csv.unlink(missing_ok=True)

        if updated_name == 0 and updated_info == 0:
            QMessageBox.information(
                self, tr("msg.no_changes"),
                tr("msg.no_csv_entries")
            )
            return

        parts: list[str] = []
        if updated_name:
            rest_n = len(remaining_name)
            parts.append(tr("ids.name_updated").format(count=updated_name)
                         + (tr("ids.remaining").format(count=rest_n) if rest_n else tr("ids.csv_deleted")))
        if updated_info:
            rest_i = len(remaining_info)
            parts.append(tr("ids.info_updated").format(count=updated_info)
                         + (tr("ids.remaining").format(count=rest_i) if rest_i else tr("ids.csv_deleted")))

        QMessageBox.information(
            self, tr("msg.ids_import_done"),
            "\n".join(parts)
        )

    def _update_ids_in_file(self, sys_path: str, sec_type: str,
                            obj_nick: str, key: str, value: str) -> bool:
        """Aktualisiert einen ``ids_name`` oder ``ids_info`` Wert in einer
        System-INI-Datei.  Gibt ``True`` zurück wenn erfolgreich.
        """
        try:
            sections = self._parser.parse(sys_path)
        except Exception:
            return False

        found = False
        for sec_name, entries in sections:
            if sec_name.lower() != sec_type:
                continue
            nick = ""
            for k, v in entries:
                if k.lower() == "nickname":
                    nick = v
                    break
            if nick.lower() != obj_nick.lower():
                continue

            # Eintrag gefunden – key aktualisieren
            for i, (k, v) in enumerate(entries):
                if k.lower() == key.lower():
                    entries[i] = (k, value)
                    found = True
                    break
            if found:
                break

        if not found:
            return False

        # Datei zurückschreiben
        try:
            self._write_sections_to_file(sys_path, sections)
        except Exception:
            return False
        return True

    def _write_sections_to_file(self, filepath: str, sections: list) -> None:
        """Schreibt geparste Sektionen zurück in eine INI-Datei."""
        lines: list[str] = []
        for i, (sec_name, entries) in enumerate(sections):
            if i > 0:
                lines.append("")
            lines.append(f"[{sec_name}]")
            for k, v in entries:
                lines.append(f"{k} = {v}")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
