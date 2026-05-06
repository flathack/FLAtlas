"""Faction Editor page – full UI for viewing, editing, creating and
analysing Freelancer factions and their relationships.

This module is designed to be called from main_window via
``build_faction_editor_page(parent, tr, callbacks)`` and follows the same
patterns as the trade-routes page or NPC editor.
"""
from __future__ import annotations

import logging
import math
import os
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import Qt, QPointF, QRectF, QTimer, Signal
from PySide6.QtGui import (
    QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QWheelEvent,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFormLayout,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .faction_data import (
    EmpathyEvent,
    EmpathyRate,
    Faction,
    FactionPropData,
    FactionRep,
    FactionWorld,
)
from .i18n import tr

_log = logging.getLogger(__name__)


# ====================================================================
#  Relationship Graph View
# ====================================================================

class _FactionNode(QGraphicsEllipseItem):
    """A circle node in the faction relationship graph."""

    def __init__(self, nickname: str, display_name: str, x: float, y: float, radius: float = 22.0):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.nickname = nickname
        self.radius = radius
        self.setPos(x, y)
        self.setBrush(QBrush(QColor(70, 130, 180)))
        self.setPen(QPen(QColor(40, 80, 120), 1.5))
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setZValue(10)
        self.setCursor(Qt.PointingHandCursor)
        self._label = QGraphicsSimpleTextItem(display_name, self)
        font = QFont()
        font.setPixelSize(9)
        self._label.setFont(font)
        self._label.setBrush(QBrush(QColor(255, 255, 255)))
        br = self._label.boundingRect()
        self._label.setPos(-br.width() / 2, -br.height() / 2)
        self._edges: list[_FactionEdge] = []
        self._selected_visual = False

    def add_edge(self, edge: _FactionEdge) -> None:
        self._edges.append(edge)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            for edge in self._edges:
                edge.update_position()
        return super().itemChange(change, value)

    def set_highlight(self, active: bool) -> None:
        self._selected_visual = active
        if active:
            self.setBrush(QBrush(QColor(255, 200, 60)))
            self.setPen(QPen(QColor(200, 150, 0), 2.5))
            self.setZValue(20)
        else:
            self.setBrush(QBrush(QColor(70, 130, 180)))
            self.setPen(QPen(QColor(40, 80, 120), 1.5))
            self.setZValue(10)


class _FactionEdge(QGraphicsLineItem):
    """A line connecting two faction nodes, colored by reputation."""

    def __init__(self, source: _FactionNode, target: _FactionNode, rep_value: float):
        super().__init__()
        self.source = source
        self.target = target
        self.rep_value = rep_value
        self.setZValue(1)
        self._apply_style()
        self.update_position()
        source.add_edge(self)
        target.add_edge(self)

    def _apply_style(self) -> None:
        v = self.rep_value
        if v > 0.59:
            color = QColor(60, 180, 75)    # friendly: green
            width = 1.0 + abs(v) * 2.0
        elif v < -0.59:
            color = QColor(220, 50, 50)    # hostile: red
            width = 1.0 + abs(v) * 2.0
        else:
            color = QColor(160, 160, 160)  # neutral: gray
            width = 0.8
        self.setPen(QPen(color, width))

    def update_position(self) -> None:
        self.setLine(
            self.source.pos().x(), self.source.pos().y(),
            self.target.pos().x(), self.target.pos().y(),
        )

    def set_highlight(self, active: bool) -> None:
        if active:
            pen = self.pen()
            pen.setWidth(pen.widthF() + 1.5)
            self.setPen(pen)
            self.setZValue(5)
        else:
            self._apply_style()
            self.setZValue(1)


class FactionGraphView(QGraphicsView):
    """Interactive graph showing faction relationships."""

    node_selected = Signal(str)  # emits faction nickname

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self._nodes: dict[str, _FactionNode] = {}
        self._edges: list[_FactionEdge] = []
        self._selected_nick: str = ""
        self._rep_threshold: float = 0.0

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        self.scale(factor, factor)

    def build_graph(self, world: FactionWorld, threshold: float = 0.0,
                    display_name_fn: Callable[[str], str] | None = None) -> None:
        """Build the graph from the faction world model."""
        self._scene.clear()
        self._nodes.clear()
        self._edges.clear()
        self._rep_threshold = threshold

        nicks = world.sorted_nicknames()
        count = len(nicks)
        if count == 0:
            return

        # Layout: circular arrangement
        radius = max(200.0, count * 28.0)
        for i, nick in enumerate(nicks):
            angle = 2.0 * math.pi * i / count - math.pi / 2
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            display = display_name_fn(nick) if display_name_fn else nick
            node = _FactionNode(nick, display, x, y)
            self._scene.addItem(node)
            self._nodes[nick] = node

        # Edges: only draw one line per pair, using the average rep
        drawn: set[tuple[str, str]] = set()
        for nick, fac in world.factions.items():
            for rep in fac.reputations:
                target_lower = rep.target.lower()
                pair = tuple(sorted((nick, target_lower)))
                if pair in drawn or target_lower not in self._nodes:
                    continue
                # Get average of both directions
                avg_rep = rep.value
                reverse = world.get_reputation(target_lower, nick)
                if reverse is not None:
                    avg_rep = (rep.value + reverse) / 2.0
                if abs(avg_rep) < threshold:
                    continue
                edge = _FactionEdge(self._nodes[nick], self._nodes[target_lower], avg_rep)
                self._scene.addItem(edge)
                self._edges.append(edge)
                drawn.add(pair)

        self.fitInView(self._scene.sceneRect().adjusted(-50, -50, 50, 50), Qt.KeepAspectRatio)

    def highlight_faction(self, nickname: str) -> None:
        """Highlight a faction and its connections."""
        nick_lower = nickname.lower()
        if nick_lower == self._selected_nick:
            return
        # Reset old
        for node in self._nodes.values():
            node.set_highlight(False)
            node.setOpacity(1.0)
        for edge in self._edges:
            edge.set_highlight(False)
            edge.setOpacity(1.0)

        self._selected_nick = nick_lower
        if nick_lower not in self._nodes:
            return

        # Dim all, highlight selected + connected
        connected = set()
        for edge in self._edges:
            src = edge.source.nickname
            tgt = edge.target.nickname
            if src == nick_lower or tgt == nick_lower:
                edge.set_highlight(True)
                connected.add(src)
                connected.add(tgt)

        for nick, node in self._nodes.items():
            if nick == nick_lower:
                node.set_highlight(True)
            elif nick in connected:
                node.setOpacity(1.0)
            else:
                node.setOpacity(0.25)

        for edge in self._edges:
            src = edge.source.nickname
            tgt = edge.target.nickname
            if src not in connected or tgt not in connected:
                edge.setOpacity(0.1)
            elif src != nick_lower and tgt != nick_lower:
                edge.setOpacity(0.3)

    def mousePressEvent(self, event) -> None:
        item = self.itemAt(event.pos())
        if isinstance(item, _FactionNode):
            self.node_selected.emit(item.nickname)
        elif isinstance(item, QGraphicsSimpleTextItem) and isinstance(item.parentItem(), _FactionNode):
            self.node_selected.emit(item.parentItem().nickname)
        super().mousePressEvent(event)


# ====================================================================
#  Reputation Matrix Table
# ====================================================================

class RepMatrixWidget(QTableWidget):
    """Table showing faction-to-faction reputation values as a matrix."""

    cell_selected = Signal(str, str)  # from_nick, to_nick

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.cellClicked.connect(self._on_cell_clicked)

    def load_matrix(self, world: FactionWorld,
                    display_name_fn: Callable[[str], str] | None = None) -> None:
        nicks = world.sorted_nicknames()
        count = len(nicks)
        self.clear()
        self.setRowCount(count)
        self.setColumnCount(count)
        labels = [display_name_fn(n) if display_name_fn else world.factions[n].nickname for n in nicks]
        self.setHorizontalHeaderLabels(labels)
        self.setVerticalHeaderLabels(labels)

        for row_idx, from_nick in enumerate(nicks):
            for col_idx, to_nick in enumerate(nicks):
                if from_nick == to_nick:
                    item = QTableWidgetItem("—")
                    item.setBackground(QBrush(QColor(60, 60, 60)))
                else:
                    rep = world.get_reputation(from_nick, to_nick)
                    val = rep if rep is not None else 0.0
                    item = QTableWidgetItem(f"{val:.2f}")
                    item.setTextAlignment(Qt.AlignCenter)
                    # Color coding
                    if val > 0.59:
                        item.setForeground(QBrush(QColor(60, 200, 80)))
                    elif val < -0.59:
                        item.setForeground(QBrush(QColor(220, 60, 60)))
                    else:
                        item.setForeground(QBrush(QColor(170, 170, 170)))
                self.setItem(row_idx, col_idx, item)

        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def _on_cell_clicked(self, row: int, col: int) -> None:
        from_label = self.verticalHeaderItem(row)
        to_label = self.horizontalHeaderItem(col)
        if from_label and to_label:
            self.cell_selected.emit(
                from_label.text().lower(),
                to_label.text().lower(),
            )


# ====================================================================
#  Nickname Usage Search
# ====================================================================

def search_nickname_in_files(game_path: str, nickname: str) -> list[dict[str, Any]]:
    """Search for a faction nickname across all INI files under game_path.

    Returns list of dicts: {file, section, line, context, rel_path}
    """
    results: list[dict[str, Any]] = []
    base = Path(game_path)
    nick_lower = nickname.lower()

    data_dir = None
    for candidate in ["DATA", "data", "Data"]:
        p = base / candidate
        if p.is_dir():
            data_dir = p
            break
    if data_dir is None:
        return results

    for root, _dirs, files in os.walk(str(data_dir)):
        for fname in files:
            if not fname.lower().endswith(".ini"):
                continue
            fpath = Path(root) / fname
            try:
                raw = fpath.read_bytes()
                # Skip BINI files (binary) - they start with "BINI"
                if raw[:4] == b"BINI":
                    continue
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    text = raw.decode("cp1252", errors="ignore")
            except Exception:
                continue

            current_section = ""
            for line_no, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("[") and stripped.endswith("]"):
                    current_section = stripped[1:-1]
                    continue
                if stripped.startswith(";") or stripped.startswith("//"):
                    continue
                if nick_lower in stripped.lower():
                    try:
                        rel_path = str(fpath.relative_to(base))
                    except ValueError:
                        rel_path = str(fpath)
                    results.append({
                        "file": str(fpath),
                        "rel_path": rel_path,
                        "section": current_section,
                        "line": line_no,
                        "context": stripped[:120],
                    })
    return results


# ====================================================================
#  Main Faction Editor Page
# ====================================================================

class FactionEditorPage(QWidget):
    """Top-level widget for the Faction Editor tab."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        game_path: str = "",
        open_file_callback: Callable[[str, int], None] | None = None,
        resolve_ids: Callable[[str | int | None], str] | None = None,
        resolve_ids_info: Callable[[str | int | None], str] | None = None,
        write_ids_name: Callable[[str | int | None, str], str] | None = None,
        write_ids_info: Callable[[str | int | None, str], str] | None = None,
    ):
        super().__init__(parent)
        self._game_path = game_path
        self._open_file_callback = open_file_callback
        self._resolve_ids = resolve_ids or (lambda x: "")
        self._resolve_ids_info = resolve_ids_info or (lambda x: "")
        self._write_ids_name = write_ids_name
        self._write_ids_info = write_ids_info
        self._world = FactionWorld()
        self._selected_nick: str = ""
        self._dirty = False
        self._build_ui()

    # ------------------------------------------------------------------
    #  UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 6, 8, 6)
        toolbar.setSpacing(8)
        self._btn_new = QPushButton(tr("fac.btn.new_faction"))
        self._btn_new.clicked.connect(self._on_new_faction)
        toolbar.addWidget(self._btn_new)
        self._btn_save = QPushButton(tr("fac.btn.save"))
        self._btn_save.clicked.connect(self._on_save)
        self._btn_save.setEnabled(False)
        toolbar.addWidget(self._btn_save)
        self._btn_validate = QPushButton(tr("fac.btn.validate"))
        self._btn_validate.clicked.connect(self._on_validate)
        toolbar.addWidget(self._btn_validate)
        self._btn_reload = QPushButton(tr("fac.btn.reload"))
        self._btn_reload.clicked.connect(self._reload_data)
        toolbar.addWidget(self._btn_reload)
        self._btn_delete = QPushButton(tr("fac.btn.delete") if tr("fac.btn.delete") != "fac.btn.delete" else "Delete Faction")
        self._btn_delete.setStyleSheet("color: #e05c5c;")
        self._btn_delete.clicked.connect(self._on_delete_faction)
        toolbar.addWidget(self._btn_delete)
        toolbar.addStretch(1)
        self._status_label = QLabel("")
        toolbar.addWidget(self._status_label)
        root.addLayout(toolbar)

        # Main splitter: left (list) | center (details) | right (relations+refs)
        main_split = QSplitter(Qt.Horizontal, self)
        root.addWidget(main_split, 1)

        # ── Left: Faction list ──
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(4)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(tr("fac.placeholder.search"))
        self._search_edit.textChanged.connect(self._filter_faction_list)
        left_layout.addWidget(self._search_edit)
        self._faction_list = QListWidget()
        self._faction_list.currentItemChanged.connect(self._on_faction_selected)
        left_layout.addWidget(self._faction_list, 1)
        self._faction_count_label = QLabel("")
        left_layout.addWidget(self._faction_count_label)
        main_split.addWidget(left)

        # ── Center: Detail view ──
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(4, 4, 4, 4)
        center_layout.setSpacing(4)
        self._detail_tabs = QTabWidget()
        center_layout.addWidget(self._detail_tabs, 1)

        # Tab 1: General properties
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        general_layout.setContentsMargins(8, 8, 8, 8)
        self._edit_nickname = QLineEdit()
        self._edit_nickname.setReadOnly(True)
        general_layout.addRow(tr("fac.field.nickname"), self._edit_nickname)
        self._edit_ids_name = QLineEdit()
        self._edit_ids_name.editingFinished.connect(self._on_field_changed)
        ids_name_row = QHBoxLayout()
        ids_name_row.addWidget(self._edit_ids_name, 1)
        self._edit_ids_name_text = QLineEdit()
        self._edit_ids_name_text.setPlaceholderText(tr("fac.ids_name_text.placeholder") if tr("fac.ids_name_text.placeholder") != "fac.ids_name_text.placeholder" else "Display name")
        self._edit_ids_name_text.setStyleSheet("color: #80b0e0; font-style: italic;")
        self._edit_ids_name_text.editingFinished.connect(self._on_ids_name_text_edited)
        ids_name_row.addWidget(self._edit_ids_name_text, 2)
        general_layout.addRow("ids_name", ids_name_row)
        self._edit_ids_info = QLineEdit()
        self._edit_ids_info.editingFinished.connect(self._on_field_changed)
        general_layout.addRow("ids_info", self._edit_ids_info)
        ids_info_text_row = QHBoxLayout()
        self._edit_ids_info_text = QTextEdit()
        self._edit_ids_info_text.setPlaceholderText(tr("fac.ids_info_text.placeholder") if tr("fac.ids_info_text.placeholder") != "fac.ids_info_text.placeholder" else "Info text")
        self._edit_ids_info_text.setStyleSheet("color: #80b0e0; font-style: italic;")
        self._edit_ids_info_text.setMaximumHeight(90)
        ids_info_text_row.addWidget(self._edit_ids_info_text, 1)
        self._btn_apply_ids_info = QPushButton("✔")
        self._btn_apply_ids_info.setFixedWidth(32)
        self._btn_apply_ids_info.setToolTip("Apply info text")
        self._btn_apply_ids_info.clicked.connect(self._on_ids_info_text_edited)
        ids_info_text_row.addWidget(self._btn_apply_ids_info, 0, Qt.AlignTop)
        general_layout.addRow("", ids_info_text_row)
        self._edit_ids_short_name = QLineEdit()
        self._edit_ids_short_name.editingFinished.connect(self._on_field_changed)
        ids_short_row = QHBoxLayout()
        ids_short_row.addWidget(self._edit_ids_short_name, 1)
        self._edit_ids_short_text = QLineEdit()
        self._edit_ids_short_text.setPlaceholderText(tr("fac.ids_short_text.placeholder") if tr("fac.ids_short_text.placeholder") != "fac.ids_short_text.placeholder" else "Short name")
        self._edit_ids_short_text.setStyleSheet("color: #80b0e0; font-style: italic;")
        self._edit_ids_short_text.editingFinished.connect(self._on_ids_short_text_edited)
        ids_short_row.addWidget(self._edit_ids_short_text, 2)
        general_layout.addRow("ids_short_name", ids_short_row)

        # File presence indicators
        self._lbl_in_iw = QLabel("—")
        general_layout.addRow("initialworld.ini", self._lbl_in_iw)
        self._lbl_in_emp = QLabel("—")
        general_layout.addRow("empathy.ini", self._lbl_in_emp)
        self._lbl_in_fp = QLabel("—")
        general_layout.addRow("faction_prop.ini", self._lbl_in_fp)
        self._detail_tabs.addTab(general_tab, tr("fac.tab.general"))

        # Tab 2: Faction Properties (faction_prop.ini fields)
        props_tab = QWidget()
        props_layout = QFormLayout(props_tab)
        props_layout.setContentsMargins(8, 8, 8, 8)
        self._edit_legality = QComboBox()
        self._edit_legality.addItems(["lawful", "unlawful"])
        self._edit_legality.currentTextChanged.connect(self._on_field_changed)
        props_layout.addRow(tr("fac.field.legality"), self._edit_legality)
        self._edit_plurality = QComboBox()
        self._edit_plurality.addItems(["singular", "plural"])
        self._edit_plurality.currentTextChanged.connect(self._on_field_changed)
        props_layout.addRow(tr("fac.field.plurality"), self._edit_plurality)
        self._edit_msg_prefix = QLineEdit()
        self._edit_msg_prefix.editingFinished.connect(self._on_field_changed)
        props_layout.addRow("msg_id_prefix", self._edit_msg_prefix)
        self._edit_jump_pref = QComboBox()
        self._edit_jump_pref.addItems(["jumpgate", "jumphole", "any"])
        self._edit_jump_pref.currentTextChanged.connect(self._on_field_changed)
        props_layout.addRow(tr("fac.field.jump_pref"), self._edit_jump_pref)
        self._edit_mc_costume = QLineEdit()
        self._edit_mc_costume.editingFinished.connect(self._on_field_changed)
        props_layout.addRow("mc_costume", self._edit_mc_costume)
        self._edit_npc_ships = QTextEdit()
        self._edit_npc_ships.setMaximumHeight(80)
        props_layout.addRow(tr("fac.field.npc_ships"), self._edit_npc_ships)
        self._edit_voices = QTextEdit()
        self._edit_voices.setMaximumHeight(60)
        props_layout.addRow(tr("fac.field.voices"), self._edit_voices)
        self._edit_space_costumes = QTextEdit()
        self._edit_space_costumes.setMaximumHeight(60)
        props_layout.addRow(tr("fac.field.space_costumes"), self._edit_space_costumes)
        self._edit_formations = QTextEdit()
        self._edit_formations.setMaximumHeight(60)
        props_layout.addRow(tr("fac.field.formations"), self._edit_formations)
        self._detail_tabs.addTab(props_tab, tr("fac.tab.properties"))

        # Tab 3: Reputations (editable table with sliders)
        rep_tab = QWidget()
        rep_layout = QVBoxLayout(rep_tab)
        rep_layout.setContentsMargins(4, 4, 4, 4)
        self._rep_table = QTableWidget()
        self._rep_table.setColumnCount(3)
        self._rep_table.setHorizontalHeaderLabels([tr("fac.col.faction"), tr("fac.col.reputation"), ""])
        self._rep_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._rep_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._rep_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._rep_table.setEditTriggers(QAbstractItemView.DoubleClicked)
        self._rep_table.cellChanged.connect(self._on_rep_cell_changed)
        self._rep_sliders: list[QSlider] = []
        rep_layout.addWidget(self._rep_table, 1)
        # Reputation presets
        preset_group = QGroupBox(tr("fac.group.rep_presets") if tr("fac.group.rep_presets") != "fac.group.rep_presets" else "Reputation Presets")
        preset_layout = QHBoxLayout(preset_group)
        self._btn_preset_friendly = QPushButton(tr("fac.preset.friendly") if tr("fac.preset.friendly") != "fac.preset.friendly" else "All Friendly (0.91)")
        self._btn_preset_friendly.clicked.connect(lambda: self._apply_rep_preset(0.91))
        preset_layout.addWidget(self._btn_preset_friendly)
        self._btn_preset_neutral = QPushButton(tr("fac.preset.neutral") if tr("fac.preset.neutral") != "fac.preset.neutral" else "All Neutral (0.0)")
        self._btn_preset_neutral.clicked.connect(lambda: self._apply_rep_preset(0.0))
        preset_layout.addWidget(self._btn_preset_neutral)
        self._btn_preset_hostile = QPushButton(tr("fac.preset.hostile") if tr("fac.preset.hostile") != "fac.preset.hostile" else "All Hostile (-0.91)")
        self._btn_preset_hostile.clicked.connect(lambda: self._apply_rep_preset(-0.91))
        preset_layout.addWidget(self._btn_preset_hostile)
        self._btn_preset_hostile_lawful = QPushButton(tr("fac.preset.hostile_lawful") if tr("fac.preset.hostile_lawful") != "fac.preset.hostile_lawful" else "Hostile to Lawful")
        self._btn_preset_hostile_lawful.clicked.connect(self._apply_preset_hostile_lawful)
        preset_layout.addWidget(self._btn_preset_hostile_lawful)
        rep_layout.addWidget(preset_group)
        self._detail_tabs.addTab(rep_tab, tr("fac.tab.reputations"))

        # Tab 4: Empathy
        emp_tab = QWidget()
        emp_layout = QVBoxLayout(emp_tab)
        emp_layout.setContentsMargins(4, 4, 4, 4)
        emp_events_group = QGroupBox(tr("fac.group.empathy_events"))
        emp_events_layout = QFormLayout(emp_events_group)
        self._emp_event_fields: dict[str, QLineEdit] = {}
        for evt in ("object_destruction", "random_mission_success", "random_mission_failure", "random_mission_abortion"):
            edit = QLineEdit()
            edit.editingFinished.connect(self._on_field_changed)
            self._emp_event_fields[evt] = edit
            emp_events_layout.addRow(evt, edit)
        emp_layout.addWidget(emp_events_group)
        emp_rates_lbl = QLabel(tr("fac.label.empathy_rates"))
        emp_layout.addWidget(emp_rates_lbl)
        self._emp_rate_table = QTableWidget()
        self._emp_rate_table.setColumnCount(3)
        self._emp_rate_table.setHorizontalHeaderLabels([tr("fac.col.faction"), tr("fac.col.empathy_rate"), ""])
        self._emp_rate_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._emp_rate_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._emp_rate_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._emp_rate_table.setEditTriggers(QAbstractItemView.DoubleClicked)
        self._emp_rate_table.cellChanged.connect(self._on_emp_rate_cell_changed)
        self._emp_rate_sliders: list[QSlider] = []
        emp_layout.addWidget(self._emp_rate_table, 1)
        self._detail_tabs.addTab(emp_tab, tr("fac.tab.empathy"))

        main_split.addWidget(center)

        # ── Right: Relations & References ──
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(4)
        right_tabs = QTabWidget()

        # Right Tab 1: Graph
        graph_tab = QWidget()
        graph_layout = QVBoxLayout(graph_tab)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        graph_controls = QHBoxLayout()
        graph_controls.addWidget(QLabel(tr("fac.label.threshold")))
        self._threshold_slider = QSlider(Qt.Horizontal)
        self._threshold_slider.setRange(0, 90)
        self._threshold_slider.setValue(0)
        self._threshold_slider.valueChanged.connect(self._on_threshold_changed)
        graph_controls.addWidget(self._threshold_slider, 1)
        self._threshold_label = QLabel("0.00")
        graph_controls.addWidget(self._threshold_label)
        graph_layout.addLayout(graph_controls)
        self._graph_view = FactionGraphView()
        self._graph_view.node_selected.connect(self._on_graph_node_selected)
        graph_layout.addWidget(self._graph_view, 1)
        right_tabs.addTab(graph_tab, tr("fac.tab.graph"))

        # Right Tab 2: Matrix
        matrix_tab = QWidget()
        matrix_layout = QVBoxLayout(matrix_tab)
        matrix_layout.setContentsMargins(0, 0, 0, 0)
        self._matrix_widget = RepMatrixWidget()
        self._matrix_widget.cell_selected.connect(self._on_matrix_cell_selected)
        matrix_layout.addWidget(self._matrix_widget, 1)
        right_tabs.addTab(matrix_tab, tr("fac.tab.matrix"))

        # Right Tab 3: References (nickname usage search)
        ref_tab = QWidget()
        ref_layout = QVBoxLayout(ref_tab)
        ref_layout.setContentsMargins(4, 4, 4, 4)
        ref_controls = QHBoxLayout()
        self._btn_search_refs = QPushButton(tr("fac.btn.search_refs"))
        self._btn_search_refs.clicked.connect(self._on_search_refs)
        ref_controls.addWidget(self._btn_search_refs)
        self._ref_count_label = QLabel("")
        ref_controls.addWidget(self._ref_count_label)
        ref_controls.addStretch(1)
        ref_layout.addLayout(ref_controls)
        self._ref_tree = QTreeWidget()
        self._ref_tree.setHeaderLabels([
            tr("fac.col.file"), tr("fac.col.section"),
            tr("fac.col.line"), tr("fac.col.context"),
        ])
        self._ref_tree.setColumnCount(4)
        self._ref_tree.itemDoubleClicked.connect(self._on_ref_double_clicked)
        ref_layout.addWidget(self._ref_tree, 1)
        right_tabs.addTab(ref_tab, tr("fac.tab.references"))

        # Right Tab 4: Validation
        val_tab = QWidget()
        val_layout = QVBoxLayout(val_tab)
        val_layout.setContentsMargins(4, 4, 4, 4)
        self._val_tree = QTreeWidget()
        self._val_tree.setHeaderLabels([
            tr("fac.col.severity"), tr("fac.col.faction"), tr("fac.col.message"),
        ])
        self._val_tree.setColumnCount(3)
        val_layout.addWidget(self._val_tree, 1)
        right_tabs.addTab(val_tab, tr("fac.tab.validation"))

        # Right Tab 5: Deactivation / Safe Remove
        deact_tab = QWidget()
        deact_layout = QVBoxLayout(deact_tab)
        deact_layout.setContentsMargins(8, 8, 8, 8)
        deact_layout.setSpacing(8)
        deact_warn = QLabel(tr("fac.deactivate.warning"))
        deact_warn.setWordWrap(True)
        deact_warn.setStyleSheet("color: #e0a030; font-weight: bold;")
        deact_layout.addWidget(deact_warn)
        self._btn_deactivate = QPushButton(tr("fac.btn.deactivate"))
        self._btn_deactivate.clicked.connect(self._on_deactivate)
        deact_layout.addWidget(self._btn_deactivate)
        self._deact_status = QTextEdit()
        self._deact_status.setReadOnly(True)
        deact_layout.addWidget(self._deact_status, 1)
        right_tabs.addTab(deact_tab, tr("fac.tab.deactivate"))

        # Right Tab 6: Diff preview
        diff_tab = QWidget()
        diff_layout = QVBoxLayout(diff_tab)
        diff_layout.setContentsMargins(4, 4, 4, 4)
        self._diff_text = QTextEdit()
        self._diff_text.setReadOnly(True)
        self._diff_text.setFont(QFont("Consolas", 9))
        diff_layout.addWidget(self._diff_text, 1)
        self._btn_refresh_diff = QPushButton(tr("fac.btn.refresh_diff"))
        self._btn_refresh_diff.clicked.connect(self._refresh_diff)
        diff_layout.addWidget(self._btn_refresh_diff)
        right_tabs.addTab(diff_tab, tr("fac.tab.diff"))

        right_layout.addWidget(right_tabs, 1)
        main_split.addWidget(right)

        main_split.setSizes([220, 400, 460])

    # ------------------------------------------------------------------
    #  Data loading
    # ------------------------------------------------------------------
    def load_data(self, game_path: str) -> None:
        """Load faction data from game files."""
        self._game_path = game_path
        self._reload_data()

    def _reload_data(self) -> None:
        self._world = FactionWorld()
        warnings = self._world.load(self._game_path)
        self._snapshot = self._world.snapshot()
        self._dirty = False
        self._btn_save.setEnabled(False)

        if warnings:
            self._status_label.setText("; ".join(warnings))
            self._status_label.setStyleSheet("color: #e0a030;")
        else:
            count = len(self._world.factions)
            self._status_label.setText(tr("fac.status.loaded").format(count=count))
            self._status_label.setStyleSheet("color: #58d076;")

        self._rebuild_faction_list()
        self._rebuild_graph()
        self._matrix_widget.load_matrix(self._world, self._display_name)

    def _rebuild_faction_list(self, select_nick: str = "") -> None:
        self._faction_list.blockSignals(True)
        self._faction_list.clear()
        nicks = self._world.sorted_nicknames()
        filter_text = self._search_edit.text().strip().lower()
        target_row = -1
        for nick in nicks:
            fac = self._world.factions[nick]
            ingame = self._resolve_ids_name(fac)
            display = f"{fac.nickname} - {ingame}" if ingame else fac.nickname
            # Presence indicators
            flags: list[str] = []
            if not fac.in_initialworld:
                flags.append("!IW")
            if not fac.in_empathy:
                flags.append("!EMP")
            if not fac.in_faction_prop:
                flags.append("!FP")
            if flags:
                display += f"  [{', '.join(flags)}]"
            if filter_text and filter_text not in display.lower():
                continue
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, nick)
            if flags:
                item.setForeground(QBrush(QColor(220, 160, 40)))
            self._faction_list.addItem(item)
            if nick == select_nick.lower():
                target_row = self._faction_list.count() - 1
        self._faction_count_label.setText(
            tr("fac.label.faction_count").format(count=self._faction_list.count())
        )
        if target_row >= 0:
            self._faction_list.setCurrentRow(target_row)
        elif self._faction_list.count() > 0:
            self._faction_list.setCurrentRow(0)
        self._faction_list.blockSignals(False)
        # Trigger selection for current row
        if self._faction_list.currentItem() is not None:
            self._on_faction_selected(self._faction_list.currentItem(), None)

    def _filter_faction_list(self) -> None:
        self._rebuild_faction_list(select_nick=self._selected_nick)

    def _resolve_ids_name(self, fac: Faction) -> str:
        """Return the resolved in-game name for a faction, or empty string."""
        if fac.ids_name:
            name = self._resolve_ids(fac.ids_name)
            if name:
                return name
        return ""

    def _display_name(self, nick: str) -> str:
        """Return 'nickname - InGameName' or just 'nickname'."""
        fac = self._world.factions.get(nick.lower())
        if fac is None:
            return nick
        ingame = self._resolve_ids_name(fac)
        return f"{fac.nickname} - {ingame}" if ingame else fac.nickname

    def _rebuild_graph(self) -> None:
        threshold = self._threshold_slider.value() / 100.0
        self._graph_view.build_graph(self._world, threshold, self._display_name)

    # ------------------------------------------------------------------
    #  Selection handling
    # ------------------------------------------------------------------
    def _on_faction_selected(self, current: QListWidgetItem | None, _previous) -> None:
        if current is None:
            self._selected_nick = ""
            return
        nick = str(current.data(Qt.UserRole) or "").strip()
        self._selected_nick = nick
        self._load_faction_detail(nick)
        self._graph_view.highlight_faction(nick)

    def _on_graph_node_selected(self, nickname: str) -> None:
        nick_lower = nickname.lower()
        for row in range(self._faction_list.count()):
            item = self._faction_list.item(row)
            if item and str(item.data(Qt.UserRole) or "").strip() == nick_lower:
                self._faction_list.setCurrentRow(row)
                break

    def _on_matrix_cell_selected(self, from_nick: str, to_nick: str) -> None:
        self._on_graph_node_selected(from_nick)

    # ------------------------------------------------------------------
    #  Detail loading
    # ------------------------------------------------------------------
    def _load_faction_detail(self, nick: str) -> None:
        fac = self._world.factions.get(nick.lower())
        if fac is None:
            return

        # General tab
        self._edit_nickname.setText(fac.nickname)
        self._edit_ids_name.setText(fac.ids_name)
        self._edit_ids_name_text.setText(self._resolve_ids(fac.ids_name) if fac.ids_name else "")
        self._edit_ids_info.setText(fac.ids_info)
        self._edit_ids_info_text.setPlainText(self._resolve_ids_info(fac.ids_info) if fac.ids_info else "")
        self._edit_ids_short_name.setText(fac.ids_short_name)
        self._edit_ids_short_text.setText(self._resolve_ids(fac.ids_short_name) if fac.ids_short_name else "")

        self._lbl_in_iw.setText("✓" if fac.in_initialworld else "✗")
        self._lbl_in_iw.setStyleSheet("color: #58d076;" if fac.in_initialworld else "color: #e05c5c;")
        self._lbl_in_emp.setText("✓" if fac.in_empathy else "✗")
        self._lbl_in_emp.setStyleSheet("color: #58d076;" if fac.in_empathy else "color: #e05c5c;")
        self._lbl_in_fp.setText("✓" if fac.in_faction_prop else "✗")
        self._lbl_in_fp.setStyleSheet("color: #58d076;" if fac.in_faction_prop else "color: #e05c5c;")

        # Properties tab
        props = fac.props
        if props:
            self._edit_legality.setCurrentText(props.legality or "unlawful")
            self._edit_plurality.setCurrentText(props.nickname_plurality or "singular")
            self._edit_msg_prefix.setText(props.msg_id_prefix)
            self._edit_jump_pref.setCurrentText(props.jump_preference or "jumpgate")
            self._edit_mc_costume.setText(props.mc_costume)
            self._edit_npc_ships.setPlainText("\n".join(props.npc_ships))
            self._edit_voices.setPlainText("\n".join(props.voices))
            self._edit_space_costumes.setPlainText("\n".join(props.space_costumes))
            self._edit_formations.setPlainText("\n".join(props.formations))
        else:
            for w in (self._edit_msg_prefix, self._edit_mc_costume):
                w.setText("")
            for w in (self._edit_npc_ships, self._edit_voices,
                      self._edit_space_costumes, self._edit_formations):
                w.setPlainText("")

        # Reputations tab
        self._rep_table.blockSignals(True)
        self._rep_sliders.clear()
        self._rep_table.setRowCount(len(fac.reputations))
        for i, rep in enumerate(fac.reputations):
            nick_item = QTableWidgetItem(self._display_name(rep.target))
            nick_item.setFlags(nick_item.flags() & ~Qt.ItemIsEditable)
            nick_item.setData(Qt.UserRole, rep.target)
            self._rep_table.setItem(i, 0, nick_item)
            val_item = QTableWidgetItem(f"{rep.value:.4f}")
            val_item.setTextAlignment(Qt.AlignCenter)
            if rep.value > 0.59:
                val_item.setForeground(QBrush(QColor(60, 200, 80)))
            elif rep.value < -0.59:
                val_item.setForeground(QBrush(QColor(220, 60, 60)))
            self._rep_table.setItem(i, 1, val_item)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(-10000, 10000)
            slider.setValue(int(rep.value * 10000))
            slider.setStyleSheet(self._rep_slider_stylesheet(rep.value))
            row_idx = i
            slider.valueChanged.connect(lambda v, r=row_idx: self._on_rep_slider_changed(r, v))
            self._rep_table.setCellWidget(i, 2, slider)
            self._rep_sliders.append(slider)
        self._rep_table.blockSignals(False)

        # Empathy tab
        for evt_type, edit in self._emp_event_fields.items():
            val = ""
            for ev in fac.empathy_events:
                if ev.event_type == evt_type:
                    val = str(ev.value)
                    break
            edit.setText(val)
        self._emp_rate_table.blockSignals(True)
        self._emp_rate_sliders.clear()
        self._emp_rate_table.setRowCount(len(fac.empathy_rates))
        for i, er in enumerate(fac.empathy_rates):
            nick_item = QTableWidgetItem(self._display_name(er.target))
            nick_item.setFlags(nick_item.flags() & ~Qt.ItemIsEditable)
            nick_item.setData(Qt.UserRole, er.target)
            self._emp_rate_table.setItem(i, 0, nick_item)
            rate_item = QTableWidgetItem(f"{er.rate:.4f}")
            rate_item.setTextAlignment(Qt.AlignCenter)
            if er.rate > 0:
                rate_item.setForeground(QBrush(QColor(60, 200, 80)))
            elif er.rate < 0:
                rate_item.setForeground(QBrush(QColor(220, 60, 60)))
            self._emp_rate_table.setItem(i, 1, rate_item)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(-10000, 10000)
            slider.setValue(int(max(-1.0, min(1.0, er.rate)) * 10000))
            slider.setStyleSheet(self._emp_slider_stylesheet(er.rate))
            row_idx = i
            slider.valueChanged.connect(lambda v, r=row_idx: self._on_emp_rate_slider_changed(r, v))
            self._emp_rate_table.setCellWidget(i, 2, slider)
            self._emp_rate_sliders.append(slider)
        self._emp_rate_table.blockSignals(False)

    # ------------------------------------------------------------------
    #  Editing callbacks
    # ------------------------------------------------------------------
    def _mark_dirty(self) -> None:
        self._dirty = True
        self._btn_save.setEnabled(True)

    def _on_field_changed(self) -> None:
        if not self._selected_nick:
            return
        fac = self._world.factions.get(self._selected_nick)
        if fac is None:
            return
        fac.ids_name = self._edit_ids_name.text().strip()
        fac.ids_info = self._edit_ids_info.text().strip()
        fac.ids_short_name = self._edit_ids_short_name.text().strip()
        if fac.props is None:
            fac.props = FactionPropData(affiliation=fac.nickname)
            fac.in_faction_prop = True
        fac.props.legality = self._edit_legality.currentText()
        fac.props.nickname_plurality = self._edit_plurality.currentText()
        fac.props.msg_id_prefix = self._edit_msg_prefix.text().strip()
        fac.props.jump_preference = self._edit_jump_pref.currentText()
        fac.props.mc_costume = self._edit_mc_costume.text().strip()
        # Empathy events
        for evt_type, edit in self._emp_event_fields.items():
            text = edit.text().strip()
            if not text:
                continue
            try:
                val = float(text)
            except ValueError:
                continue
            found = False
            for ev in fac.empathy_events:
                if ev.event_type == evt_type:
                    ev.value = val
                    found = True
                    break
            if not found:
                fac.empathy_events.append(EmpathyEvent(evt_type, val))
        self._mark_dirty()

    def _on_ids_name_text_edited(self) -> None:
        """Write the display name text directly to the user resource DLL."""
        if not self._selected_nick or self._write_ids_name is None:
            return
        fac = self._world.factions.get(self._selected_nick)
        if fac is None:
            return
        new_text = self._edit_ids_name_text.text().strip()
        if not new_text:
            return
        try:
            new_gid = self._write_ids_name(fac.ids_name or "0", new_text)
        except Exception as exc:
            _log.warning("Failed to write ids_name text: %s", exc)
            return
        if new_gid and str(new_gid) != str(fac.ids_name):
            fac.ids_name = str(new_gid)
            self._edit_ids_name.setText(str(new_gid))
            self._mark_dirty()

    def _on_ids_info_text_edited(self) -> None:
        """Write the info text directly to the user resource DLL as infocard."""
        if not self._selected_nick or self._write_ids_info is None:
            return
        fac = self._world.factions.get(self._selected_nick)
        if fac is None:
            return
        new_text = self._edit_ids_info_text.toPlainText().strip()
        if not new_text:
            return
        try:
            new_gid = self._write_ids_info(fac.ids_info or "0", new_text)
        except Exception as exc:
            _log.warning("Failed to write ids_info text: %s", exc)
            return
        if new_gid and str(new_gid) != str(fac.ids_info):
            fac.ids_info = str(new_gid)
            self._edit_ids_info.setText(str(new_gid))
            self._mark_dirty()

    def _on_ids_short_text_edited(self) -> None:
        """Write the short name text directly to the user resource DLL."""
        if not self._selected_nick or self._write_ids_name is None:
            return
        fac = self._world.factions.get(self._selected_nick)
        if fac is None:
            return
        new_text = self._edit_ids_short_text.text().strip()
        if not new_text:
            return
        try:
            new_gid = self._write_ids_name(fac.ids_short_name or "0", new_text)
        except Exception as exc:
            _log.warning("Failed to write ids_short_name text: %s", exc)
            return
        if new_gid and str(new_gid) != str(fac.ids_short_name):
            fac.ids_short_name = str(new_gid)
            self._edit_ids_short_name.setText(str(new_gid))
            self._mark_dirty()

    @staticmethod
    def _rep_slider_stylesheet(value: float) -> str:
        if value > 0.59:
            color = "#3cc850"
        elif value < -0.59:
            color = "#dc3c3c"
        else:
            color = "#888888"
        return (
            f"QSlider::groove:horizontal {{ background: #2a2a2a; height: 6px; border-radius: 3px; }}"
            f"QSlider::handle:horizontal {{ background: {color}; width: 14px; margin: -4px 0; border-radius: 7px; }}"
            f"QSlider::sub-page:horizontal {{ background: {color}; border-radius: 3px; }}"
        )

    def _on_rep_slider_changed(self, row: int, slider_value: int) -> None:
        if not self._selected_nick:
            return
        fac = self._world.factions.get(self._selected_nick)
        if fac is None or row >= len(fac.reputations):
            return
        new_val = max(-1.0, min(1.0, slider_value / 10000.0))
        fac.reputations[row].value = new_val
        self._rep_table.blockSignals(True)
        item = self._rep_table.item(row, 1)
        if item is not None:
            item.setText(f"{new_val:.4f}")
            if new_val > 0.59:
                item.setForeground(QBrush(QColor(60, 200, 80)))
            elif new_val < -0.59:
                item.setForeground(QBrush(QColor(220, 60, 60)))
            else:
                item.setForeground(QBrush(QColor(170, 170, 170)))
        self._rep_table.blockSignals(False)
        if row < len(self._rep_sliders):
            self._rep_sliders[row].setStyleSheet(self._rep_slider_stylesheet(new_val))
        self._mark_dirty()

    def _on_rep_cell_changed(self, row: int, col: int) -> None:
        if col != 1 or not self._selected_nick:
            return
        fac = self._world.factions.get(self._selected_nick)
        if fac is None or row >= len(fac.reputations):
            return
        item = self._rep_table.item(row, col)
        if item is None:
            return
        try:
            new_val = max(-1.0, min(1.0, float(item.text())))
        except ValueError:
            item.setText(f"{fac.reputations[row].value:.4f}")
            return
        fac.reputations[row].value = new_val
        item.setText(f"{new_val:.4f}")
        if new_val > 0.59:
            item.setForeground(QBrush(QColor(60, 200, 80)))
        elif new_val < -0.59:
            item.setForeground(QBrush(QColor(220, 60, 60)))
        else:
            item.setForeground(QBrush(QColor(170, 170, 170)))
        if row < len(self._rep_sliders):
            self._rep_sliders[row].blockSignals(True)
            self._rep_sliders[row].setValue(int(new_val * 10000))
            self._rep_sliders[row].setStyleSheet(self._rep_slider_stylesheet(new_val))
            self._rep_sliders[row].blockSignals(False)
        self._mark_dirty()

    def _on_emp_rate_cell_changed(self, row: int, col: int) -> None:
        if col != 1 or not self._selected_nick:
            return
        fac = self._world.factions.get(self._selected_nick)
        if fac is None or row >= len(fac.empathy_rates):
            return
        item = self._emp_rate_table.item(row, col)
        if item is None:
            return
        try:
            new_val = max(-1.0, min(1.0, float(item.text())))
        except ValueError:
            item.setText(f"{fac.empathy_rates[row].rate:.4f}")
            return
        fac.empathy_rates[row].rate = new_val
        item.setText(f"{new_val:.4f}")
        if new_val > 0:
            item.setForeground(QBrush(QColor(60, 200, 80)))
        elif new_val < 0:
            item.setForeground(QBrush(QColor(220, 60, 60)))
        else:
            item.setForeground(QBrush(QColor(170, 170, 170)))
        if row < len(self._emp_rate_sliders):
            self._emp_rate_sliders[row].blockSignals(True)
            self._emp_rate_sliders[row].setValue(int(new_val * 10000))
            self._emp_rate_sliders[row].setStyleSheet(self._emp_slider_stylesheet(new_val))
            self._emp_rate_sliders[row].blockSignals(False)
        self._mark_dirty()

    @staticmethod
    def _emp_slider_stylesheet(value: float) -> str:
        if value > 0:
            color = "#3cc850"
        elif value < 0:
            color = "#dc3c3c"
        else:
            color = "#888888"
        return (
            f"QSlider::groove:horizontal {{ background: #2a2a2a; height: 6px; border-radius: 3px; }}"
            f"QSlider::handle:horizontal {{ background: {color}; width: 14px; margin: -4px 0; border-radius: 7px; }}"
            f"QSlider::sub-page:horizontal {{ background: {color}; border-radius: 3px; }}"
        )

    def _on_emp_rate_slider_changed(self, row: int, slider_value: int) -> None:
        if not self._selected_nick:
            return
        fac = self._world.factions.get(self._selected_nick)
        if fac is None or row >= len(fac.empathy_rates):
            return
        new_val = max(-1.0, min(1.0, slider_value / 10000.0))
        fac.empathy_rates[row].rate = new_val
        self._emp_rate_table.blockSignals(True)
        item = self._emp_rate_table.item(row, 1)
        if item is not None:
            item.setText(f"{new_val:.4f}")
            if new_val > 0:
                item.setForeground(QBrush(QColor(60, 200, 80)))
            elif new_val < 0:
                item.setForeground(QBrush(QColor(220, 60, 60)))
            else:
                item.setForeground(QBrush(QColor(170, 170, 170)))
        self._emp_rate_table.blockSignals(False)
        if row < len(self._emp_rate_sliders):
            self._emp_rate_sliders[row].setStyleSheet(self._emp_slider_stylesheet(new_val))
        self._mark_dirty()

    # ------------------------------------------------------------------
    #  Reputation presets
    # ------------------------------------------------------------------
    def _apply_rep_preset(self, value: float) -> None:
        if not self._selected_nick:
            return
        fac = self._world.factions.get(self._selected_nick)
        if fac is None:
            return
        answer = QMessageBox.question(
            self,
            tr("fac.preset.confirm_title") if tr("fac.preset.confirm_title") != "fac.preset.confirm_title" else "Apply Preset",
            (tr("fac.preset.confirm_msg") if tr("fac.preset.confirm_msg") != "fac.preset.confirm_msg"
             else f"Set reputation toward ALL factions to {value:.2f}?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        for rep in fac.reputations:
            rep.value = value
        self._mark_dirty()
        self._load_faction_detail(self._selected_nick)
        self._rebuild_graph()
        self._matrix_widget.load_matrix(self._world, self._display_name)
        self._status_label.setText(f"Preset applied: all reps → {value:.2f}")
        self._status_label.setStyleSheet("color: #58d076;")

    def _apply_preset_hostile_lawful(self) -> None:
        if not self._selected_nick:
            return
        fac = self._world.factions.get(self._selected_nick)
        if fac is None:
            return
        answer = QMessageBox.question(
            self,
            tr("fac.preset.confirm_title") if tr("fac.preset.confirm_title") != "fac.preset.confirm_title" else "Apply Preset",
            (tr("fac.preset.hostile_lawful_msg") if tr("fac.preset.hostile_lawful_msg") != "fac.preset.hostile_lawful_msg"
             else "Set hostile (-0.91) to all lawful factions and friendly (0.91) to all unlawful?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        for rep in fac.reputations:
            other = self._world.factions.get(rep.target.lower())
            if other is not None and other.props is not None:
                if other.props.legality.lower() == "lawful":
                    rep.value = -0.91
                else:
                    rep.value = 0.91
        self._mark_dirty()
        self._load_faction_detail(self._selected_nick)
        self._rebuild_graph()
        self._matrix_widget.load_matrix(self._world, self._display_name)
        self._status_label.setText("Preset applied: hostile to lawful, friendly to unlawful")
        self._status_label.setStyleSheet("color: #58d076;")

    # ------------------------------------------------------------------
    #  Delete faction
    # ------------------------------------------------------------------
    def _on_delete_faction(self) -> None:
        if not self._selected_nick:
            return
        fac = self._world.factions.get(self._selected_nick)
        if fac is None:
            return

        # Count external references
        refs = search_nickname_in_files(self._game_path, fac.nickname) if self._game_path else []
        external_refs = [
            r for r in refs if
            "initialworld.ini" not in r.get("rel_path", "").lower()
            and "empathy.ini" not in r.get("rel_path", "").lower()
            and "faction_prop.ini" not in r.get("rel_path", "").lower()
        ]

        # Build dialog
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("fac.delete.title") if tr("fac.delete.title") != "fac.delete.title" else "Delete Faction")
        dlg.setMinimumWidth(500)
        layout = QVBoxLayout(dlg)

        # Warning
        warn = QLabel(
            tr("fac.delete.warning") if tr("fac.delete.warning") != "fac.delete.warning"
            else "⚠ WARNING: Deleting factions can cause stability issues!\n"
                 "Freelancer expects all referenced factions to exist.\n"
                 "Only delete if you know exactly what you are doing."
        )
        warn.setWordWrap(True)
        warn.setStyleSheet("color: #e05c5c; font-weight: bold; font-size: 12px; padding: 8px;")
        layout.addWidget(warn)

        # Info
        info_text = (
            f"Faction: {fac.nickname}\n"
            f"References in other files: {len(external_refs)}"
        )
        if external_refs:
            info_text += "\n\nExternal references found in:"
            shown = external_refs[:15]
            for r in shown:
                info_text += f"\n  • {r.get('rel_path', '')}:{r.get('line', '')} [{r.get('section', '')}]"
            if len(external_refs) > 15:
                info_text += f"\n  ... and {len(external_refs) - 15} more"
        info_lbl = QLabel(info_text)
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("font-family: Consolas; font-size: 10px; padding: 4px;")
        layout.addWidget(info_lbl)

        # Replacement option
        replace_group = QGroupBox(
            tr("fac.delete.replace_group") if tr("fac.delete.replace_group") != "fac.delete.replace_group"
            else "Reference handling"
        )
        replace_layout = QVBoxLayout(replace_group)
        replace_lbl = QLabel(
            tr("fac.delete.replace_label") if tr("fac.delete.replace_label") != "fac.delete.replace_label"
            else "Replace reputation/empathy references with another faction:"
        )
        replace_lbl.setWordWrap(True)
        replace_layout.addWidget(replace_lbl)
        replace_combo = QComboBox()
        replace_combo.addItem(
            tr("fac.delete.no_replace") if tr("fac.delete.no_replace") != "fac.delete.no_replace"
            else "— Remove references (no replacement) —",
            ""
        )
        for nick in sorted(self._world.factions.keys()):
            if nick != self._selected_nick:
                other = self._world.factions[nick]
                label = self._display_name(nick)
                replace_combo.addItem(label, nick)
        replace_layout.addWidget(replace_combo)
        layout.addWidget(replace_group)

        # Buttons
        btn_row = QHBoxLayout()
        btn_delete = QPushButton(
            tr("fac.delete.confirm_btn") if tr("fac.delete.confirm_btn") != "fac.delete.confirm_btn"
            else "Delete Faction"
        )
        btn_delete.setStyleSheet("color: #e05c5c; font-weight: bold;")
        btn_delete.clicked.connect(dlg.accept)
        btn_cancel = QPushButton(tr("fac.btn.cancel") if tr("fac.btn.cancel") != "fac.btn.cancel" else "Cancel")
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_delete)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        if dlg.exec() != QDialog.Accepted:
            return

        replace_nick = str(replace_combo.currentData() or "").strip()
        self._execute_delete_faction(fac.nickname, replace_nick)

    def _execute_delete_faction(self, nickname: str, replace_nick: str) -> None:
        nick_lower = nickname.lower()
        replace_lower = replace_nick.lower() if replace_nick else ""

        # Remove reputation/empathy references from other factions
        for other_nick, other_fac in list(self._world.factions.items()):
            if other_nick == nick_lower:
                continue
            if replace_lower and replace_lower != other_nick:
                # Replace rep targets pointing to the deleted faction
                for rep in other_fac.reputations:
                    if rep.target.lower() == nick_lower:
                        rep.target = self._world.factions[replace_lower].nickname
                for er in other_fac.empathy_rates:
                    if er.target.lower() == nick_lower:
                        er.target = self._world.factions[replace_lower].nickname
            else:
                # Remove references
                other_fac.reputations = [r for r in other_fac.reputations if r.target.lower() != nick_lower]
                other_fac.empathy_rates = [r for r in other_fac.empathy_rates if r.target.lower() != nick_lower]

        # Remove the faction itself
        if nick_lower in self._world.factions:
            del self._world.factions[nick_lower]

        self._selected_nick = ""
        self._mark_dirty()
        self._rebuild_faction_list()
        self._rebuild_graph()
        self._matrix_widget.load_matrix(self._world, self._display_name)
        self._status_label.setText(f"Faction '{nickname}' deleted" +
                                   (f", references replaced with '{replace_nick}'" if replace_nick else ""))
        self._status_label.setStyleSheet("color: #e0a030;")

    # ------------------------------------------------------------------
    #  New faction
    # ------------------------------------------------------------------
    def _on_new_faction(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("fac.dlg.new_faction"))
        dlg.setMinimumWidth(350)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(tr("fac.dlg.enter_nickname")))
        edit = QLineEdit(dlg)
        edit.setPlaceholderText("my_new_faction_grp")
        layout.addWidget(edit)
        warn = QLabel(tr("fac.dlg.new_info"))
        warn.setWordWrap(True)
        warn.setStyleSheet("color: #a0a0a0; font-size: 11px;")
        layout.addWidget(warn)
        btn_row = QHBoxLayout()
        btn_ok = QPushButton(tr("fac.btn.create"))
        btn_ok.clicked.connect(dlg.accept)
        btn_cancel = QPushButton(tr("fac.btn.cancel"))
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)
        if dlg.exec() != QDialog.Accepted:
            return
        nickname = edit.text().strip()
        if not nickname:
            return
        if nickname.lower() in self._world.factions:
            QMessageBox.warning(self, tr("fac.error.title"),
                                tr("fac.error.duplicate").format(nickname=nickname))
            return
        self._world.add_faction(nickname)
        self._mark_dirty()
        self._rebuild_faction_list(select_nick=nickname)
        self._rebuild_graph()
        self._matrix_widget.load_matrix(self._world, self._display_name)
        self._status_label.setText(tr("fac.status.created").format(nickname=nickname))
        self._status_label.setStyleSheet("color: #58d076;")

    # ------------------------------------------------------------------
    #  Save
    # ------------------------------------------------------------------
    def _on_save(self) -> None:
        from .ini_section_writes import serialize_sections_to_ini_text_for_file
        from .text_write_utils import write_text_with_fallback

        if not self._dirty:
            return

        files_changed: list[str] = []

        # initialworld.ini
        if self._world._iw_path:
            sections = self._world.build_initialworld_sections()
            text = serialize_sections_to_ini_text_for_file(self._world._iw_path, sections)
            write_text_with_fallback(self._world._iw_path, text)
            files_changed.append("initialworld.ini")

        # empathy.ini
        if self._world._emp_path:
            sections = self._world.build_empathy_sections()
            text = serialize_sections_to_ini_text_for_file(self._world._emp_path, sections)
            write_text_with_fallback(self._world._emp_path, text)
            files_changed.append("empathy.ini")

        # faction_prop.ini
        if self._world._fp_path:
            sections = self._world.build_faction_prop_sections()
            text = serialize_sections_to_ini_text_for_file(self._world._fp_path, sections)
            write_text_with_fallback(self._world._fp_path, text)
            files_changed.append("faction_prop.ini")

        self._dirty = False
        self._btn_save.setEnabled(False)
        self._snapshot = self._world.snapshot()
        self._status_label.setText(
            tr("fac.status.saved").format(files=", ".join(files_changed))
        )
        self._status_label.setStyleSheet("color: #58d076;")

    # ------------------------------------------------------------------
    #  Validate
    # ------------------------------------------------------------------
    def _on_validate(self) -> None:
        issues = self._world.validate()
        self._val_tree.clear()
        severity_colors = {
            "critical": QColor(220, 50, 50),
            "warning": QColor(220, 160, 40),
            "info": QColor(120, 160, 220),
        }
        for issue in issues:
            item = QTreeWidgetItem([
                issue.get("severity", "info"),
                issue.get("faction", ""),
                issue.get("message", ""),
            ])
            color = severity_colors.get(issue.get("severity", ""), QColor(170, 170, 170))
            item.setForeground(0, QBrush(color))
            self._val_tree.addTopLevelItem(item)
        for col in range(3):
            self._val_tree.resizeColumnToContents(col)
        # Switch to validation tab
        parent_tabs = self._val_tree.parent()
        while parent_tabs and not isinstance(parent_tabs, QTabWidget):
            parent_tabs = parent_tabs.parent()
        if isinstance(parent_tabs, QTabWidget):
            for i in range(parent_tabs.count()):
                if parent_tabs.widget(i) is self._val_tree.parent():
                    parent_tabs.setCurrentIndex(i)
                    break
        self._status_label.setText(
            tr("fac.status.validated").format(count=len(issues))
        )
        self._status_label.setStyleSheet(
            "color: #e05c5c;" if any(i["severity"] == "critical" for i in issues) else "color: #58d076;"
        )

    # ------------------------------------------------------------------
    #  Nickname usage search
    # ------------------------------------------------------------------
    def _on_search_refs(self) -> None:
        if not self._selected_nick or not self._game_path:
            return
        fac = self._world.factions.get(self._selected_nick)
        if fac is None:
            return
        self._ref_tree.clear()
        self._ref_count_label.setText(tr("fac.status.searching"))
        # Use a timer to keep UI responsive
        QTimer.singleShot(10, lambda: self._do_search_refs(fac.nickname))

    def _do_search_refs(self, nickname: str) -> None:
        results = search_nickname_in_files(self._game_path, nickname)
        self._ref_tree.clear()
        for r in results:
            item = QTreeWidgetItem([
                r.get("rel_path", ""),
                r.get("section", ""),
                str(r.get("line", "")),
                r.get("context", ""),
            ])
            item.setData(0, Qt.UserRole, r.get("file", ""))
            item.setData(2, Qt.UserRole, r.get("line", 0))
            self._ref_tree.addTopLevelItem(item)
        for col in range(4):
            self._ref_tree.resizeColumnToContents(col)
        self._ref_count_label.setText(
            tr("fac.status.refs_found").format(count=len(results))
        )

    def _on_ref_double_clicked(self, item: QTreeWidgetItem, _col: int) -> None:
        file_path = str(item.data(0, Qt.UserRole) or "")
        line_no = int(item.data(2, Qt.UserRole) or 0)
        if file_path and self._open_file_callback:
            self._open_file_callback(file_path, line_no)

    # ------------------------------------------------------------------
    #  Graph controls
    # ------------------------------------------------------------------
    def _on_threshold_changed(self, value: int) -> None:
        threshold = value / 100.0
        self._threshold_label.setText(f"{threshold:.2f}")
        self._rebuild_graph()
        if self._selected_nick:
            self._graph_view.highlight_faction(self._selected_nick)

    # ------------------------------------------------------------------
    #  Safe deactivation
    # ------------------------------------------------------------------
    def _on_deactivate(self) -> None:
        if not self._selected_nick:
            return
        fac = self._world.factions.get(self._selected_nick)
        if fac is None:
            return

        answer = QMessageBox.warning(
            self,
            tr("fac.deactivate.title"),
            tr("fac.deactivate.confirm").format(nickname=fac.nickname),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        lines: list[str] = []
        lines.append(tr("fac.deactivate.step1").format(nickname=fac.nickname))

        # Step 1: Show all references
        refs = search_nickname_in_files(self._game_path, fac.nickname)
        # Exclude the three faction definition files themselves
        external_refs = [
            r for r in refs if
            "initialworld.ini" not in r.get("rel_path", "").lower()
            and "empathy.ini" not in r.get("rel_path", "").lower()
            and "faction_prop.ini" not in r.get("rel_path", "").lower()
        ]
        if external_refs:
            lines.append("")
            lines.append(tr("fac.deactivate.external_refs").format(count=len(external_refs)))
            for r in external_refs[:50]:
                lines.append(f"  • {r['rel_path']}:{r['line']}  [{r['section']}]  {r['context'][:60]}")
            if len(external_refs) > 50:
                lines.append(f"  ... {len(external_refs) - 50} more")
            lines.append("")
            lines.append(tr("fac.deactivate.manual_note"))
        else:
            lines.append(tr("fac.deactivate.no_external"))

        # Step 2: Remove rep entries from all other factions
        lines.append("")
        lines.append(tr("fac.deactivate.step2"))
        removed_reps = 0
        removed_rates = 0
        for other_nick, other_fac in self._world.factions.items():
            if other_nick == self._selected_nick:
                continue
            before_reps = len(other_fac.reputations)
            other_fac.reputations = [r for r in other_fac.reputations if r.target.lower() != fac.nickname.lower()]
            removed_reps += before_reps - len(other_fac.reputations)
            before_rates = len(other_fac.empathy_rates)
            other_fac.empathy_rates = [r for r in other_fac.empathy_rates if r.target.lower() != fac.nickname.lower()]
            removed_rates += before_rates - len(other_fac.empathy_rates)
        lines.append(f"  {tr('fac.deactivate.removed_reps').format(count=removed_reps)}")
        lines.append(f"  {tr('fac.deactivate.removed_rates').format(count=removed_rates)}")

        # Step 3: Mark as inactive (remove from all three files)
        lines.append("")
        lines.append(tr("fac.deactivate.step3"))
        fac.in_initialworld = False
        fac.in_empathy = False
        fac.in_faction_prop = False

        self._deact_status.setPlainText("\n".join(lines))
        self._mark_dirty()
        self._rebuild_faction_list(select_nick=self._selected_nick)
        self._rebuild_graph()
        self._matrix_widget.load_matrix(self._world, self._display_name)
        self._status_label.setText(
            tr("fac.status.deactivated").format(nickname=fac.nickname)
        )
        self._status_label.setStyleSheet("color: #e0a030;")

    # ------------------------------------------------------------------
    #  Diff preview
    # ------------------------------------------------------------------
    def _refresh_diff(self) -> None:
        from .ini_section_writes import serialize_sections_to_ini_text

        if not hasattr(self, "_snapshot"):
            self._diff_text.setPlainText(tr("fac.diff.no_snapshot"))
            return

        lines: list[str] = []
        # Compare each file
        for label, build_func, snap_build in [
            ("initialworld.ini", self._world.build_initialworld_sections,
             self._snapshot.build_initialworld_sections),
            ("empathy.ini", self._world.build_empathy_sections,
             self._snapshot.build_empathy_sections),
            ("faction_prop.ini", self._world.build_faction_prop_sections,
             self._snapshot.build_faction_prop_sections),
        ]:
            current = serialize_sections_to_ini_text(build_func())
            original = serialize_sections_to_ini_text(snap_build())
            if current == original:
                lines.append(f"═══ {label}: {tr('fac.diff.no_changes')}")
            else:
                lines.append(f"═══ {label}: {tr('fac.diff.changed')}")
                # Simple line-count diff
                cur_lines = current.splitlines()
                orig_lines = original.splitlines()
                lines.append(f"    {tr('fac.diff.lines')}: {len(orig_lines)} → {len(cur_lines)}")
            lines.append("")

        self._diff_text.setPlainText("\n".join(lines))
