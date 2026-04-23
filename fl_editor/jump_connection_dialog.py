"""Dialog zum Platzieren von Jump Holes / Gates in zwei Systemen gleichzeitig.

Zeigt beide Systeme nebeneinander als Mini-2D-Karten an.
Typ-Auswahl, Zielsystem und Gate-Parameter sind direkt im Dialog integriert.
Der User klickt in jedes System, um die Position zu setzen.
Beim Speichern werden beide System-Dateien atomar geschrieben.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, QPointF, QRectF, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QRadialGradient, QWheelEvent

from .i18n import tr
from .models import SolarObject, ZoneItem
from .themes import current_theme, get_palette
from .ui_helpers import configure_contains_completer


# ── Mini-2D-View ──────────────────────────────────────────────────────

class _MiniSystemView(QGraphicsView):
    """Einfache 2D-Kartenansicht mit Zoom + Pan zum Platzieren."""

    clicked = Signal(QPointF)  # Szenen-Koordinate

    def __init__(self) -> None:
        super().__init__()
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        palette = get_palette(current_theme())
        bg = QColor(palette.get("bg_list", "#101018"))
        self.setBackgroundBrush(QBrush(bg))
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.NoDrag)
        self._panning = False
        self._pan_start = QPointF()
        self._marker: QGraphicsEllipseItem | None = None
        self._placement_enabled = True

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        self.scale(factor, factor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.LeftButton and self._placement_enabled:
            scene_pos = self.mapToScene(event.position().toPoint())
            self.clicked.emit(scene_pos)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MiddleButton and self._panning:
            self._panning = False
            self.setCursor(Qt.CrossCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def set_marker(self, pos: QPointF, color: QColor) -> None:
        if self._marker is not None:
            self._scene.removeItem(self._marker)
        r = 6.0
        self._marker = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r)
        self._marker.setBrush(QBrush(color))
        self._marker.setPen(QPen(color.lighter(150), 1.5))
        self._marker.setPos(pos)
        self._marker.setZValue(9999)
        self._scene.addItem(self._marker)

    def clear_marker(self) -> None:
        if self._marker is not None:
            self._scene.removeItem(self._marker)
            self._marker = None

    def fit_contents(self) -> None:
        rect = self._scene.itemsBoundingRect()
        if rect.isNull():
            return
        margin = max(rect.width(), rect.height()) * 0.1
        rect.adjust(-margin, -margin, margin, margin)
        self.fitInView(rect, Qt.KeepAspectRatio)

    def draw_grid(self, half_extent_world: float, scale: float) -> None:
        """Zeichnet ein 8×8-Gitter mit Spalten A–H und Zeilen 1–8."""
        r = half_extent_world * scale
        if r <= 0:
            return
        grid_pen = QPen(QColor(255, 255, 255, 35), 0)
        grid_pen.setCosmetic(True)
        # Outer box
        box = QGraphicsRectItem(-r, -r, 2 * r, 2 * r)
        box.setPen(QPen(QColor(255, 255, 255, 60), 0))
        box.setBrush(Qt.NoBrush)
        box.setZValue(-250)
        self._scene.addItem(box)
        cell = 2 * r / 8.0
        # Inner lines
        for i in range(1, 8):
            off = -r + cell * i
            vl = QGraphicsLineItem(off, -r, off, r)
            vl.setPen(grid_pen)
            vl.setZValue(-240)
            self._scene.addItem(vl)
            hl = QGraphicsLineItem(-r, off, r, off)
            hl.setPen(grid_pen)
            hl.setZValue(-240)
            self._scene.addItem(hl)
        # Labels
        label_font = QFont("Sans", 6)
        label_color = QColor(255, 255, 255, 100)
        margin = cell * 0.35
        for idx, letter in enumerate("ABCDEFGH"):
            x = -r + cell * (idx + 0.5)
            lbl = QGraphicsTextItem(letter)
            lbl.setFont(label_font)
            lbl.setDefaultTextColor(label_color)
            lbl.setZValue(-230)
            lbl.setPos(x - lbl.boundingRect().width() / 2, r + margin * 0.3)
            self._scene.addItem(lbl)
        for idx in range(8):
            y = -r + cell * (idx + 0.5)
            lbl = QGraphicsTextItem(str(idx + 1))
            lbl.setFont(label_font)
            lbl.setDefaultTextColor(label_color)
            lbl.setZValue(-230)
            lbl.setPos(-r - margin - lbl.boundingRect().width(), y - lbl.boundingRect().height() / 2)
            self._scene.addItem(lbl)


# ── Mini-Universe-View (read-only) ────────────────────────────────────

class _MiniUniverseView(QGraphicsView):
    """Kleine Universum-Übersicht (nur lesen, Zoom + Pan)."""

    def __init__(self) -> None:
        super().__init__()
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        palette = get_palette(current_theme())
        bg = QColor(palette.get("bg_list", "#101018"))
        self.setBackgroundBrush(QBrush(bg))
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.NoDrag)
        self._panning = False
        self._pan_start = QPointF()

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        self.scale(factor, factor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MiddleButton and self._panning:
            self._panning = False
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def fit_contents(self) -> None:
        rect = self._scene.itemsBoundingRect()
        if rect.isNull():
            return
        margin = max(rect.width(), rect.height()) * 0.1
        rect.adjust(-margin, -margin, margin, margin)
        self.fitInView(rect, Qt.KeepAspectRatio)


# ── Hauptdialog ───────────────────────────────────────────────────────

_GATE_TYPES = {"Jump Gate", "Nomad Gate"}


class JumpConnectionPlacementDialog(QDialog):
    """Alles-in-einem-Dialog: Typ + Ziel wählen, platzieren, speichern."""

    def __init__(
        self,
        parent,
        *,
        origin_path: str,
        origin_nick: str,
        origin_display: str,
        systems: list[tuple[str, str]],
        jumphole_archetypes: list[str],
        gate_loadouts: list[str],
        factions: list[str],
        parser,
        faction_from_ui,
        universe_coord_map: dict[str, tuple[float, float]],
        universe_edges: dict,
        universe_scale: float,
        navmap_scale_fn,
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.jump_placement_title"))
        self.setMinimumSize(1400, 650)
        self.resize(1700, 780)

        self._origin_path = origin_path
        self._origin_nick = origin_nick.upper()
        self._origin_display = origin_display
        self._systems = systems  # [(display, path), ...]
        self._parser = parser
        self._faction_from_ui = faction_from_ui
        self._navmap_scale_fn = navmap_scale_fn

        self._uni_coord_map = universe_coord_map
        self._uni_edges = universe_edges
        self._uni_scale = universe_scale

        self._origin_pos: QPointF | None = None
        self._dest_pos: QPointF | None = None
        self._origin_scale = 1.0
        self._dest_scale = 1.0

        self._new_conn_line: QGraphicsLineItem | None = None

        # ── Layout ────────────────────────────────────────────────
        root = QVBoxLayout(self)

        # ── Top bar: Typ + Zielsystem ─────────────────────────────
        top_row = QHBoxLayout()

        # Type
        top_row.addWidget(QLabel(tr("dlg.type") + ":"))
        self._type_cb = QComboBox()
        for jh_arch in jumphole_archetypes:
            self._type_cb.addItem(f"Jump Hole ({jh_arch})", jh_arch)
        if not jumphole_archetypes:
            self._type_cb.addItem("Jump Hole (jumphole)", "jumphole")
        self._type_cb.addItem("Jump Gate", "jumpgate")
        self._type_cb.addItem("Nomad Gate", "nomad_gate")
        self._type_cb.currentIndexChanged.connect(self._on_type_changed)
        top_row.addWidget(self._type_cb)

        top_row.addSpacing(20)

        # Target system
        top_row.addWidget(QLabel(tr("dlg.target_system") + ":"))
        self._dest_cb = QComboBox()
        self._dest_cb.setEditable(True)
        self._dest_cb.setMinimumWidth(300)
        for display, path in systems:
            self._dest_cb.addItem(display, path)
        configure_contains_completer(self._dest_cb)
        self._dest_cb.currentIndexChanged.connect(self._on_dest_changed)
        top_row.addWidget(self._dest_cb)

        top_row.addStretch()
        root.addLayout(top_row)

        # ── Gate-Info-Bereich (nur bei Gates sichtbar) ────────────
        self._gate_grp = QGroupBox("Gate-Parameter")
        gate_layout = QFormLayout(self._gate_grp)
        gate_layout.setContentsMargins(8, 4, 8, 4)

        self._behavior_edit = QLineEdit("NOTHING")
        gate_layout.addRow("behavior:", self._behavior_edit)

        self._difficulty_spin = QSpinBox()
        self._difficulty_spin.setRange(0, 10)
        self._difficulty_spin.setValue(1)
        gate_layout.addRow("difficulty:", self._difficulty_spin)

        self._loadout_cb = QComboBox()
        self._loadout_cb.addItems(gate_loadouts)
        gate_layout.addRow("loadout:", self._loadout_cb)

        self._pilot_edit = QLineEdit("pilot_solar_hardest")
        gate_layout.addRow("pilot:", self._pilot_edit)

        self._rep_cb = QComboBox()
        self._rep_cb.setEditable(True)
        self._rep_cb.addItems(factions)
        configure_contains_completer(self._rep_cb)
        gate_layout.addRow("reputation:", self._rep_cb)

        self._gate_grp.setVisible(False)
        root.addWidget(self._gate_grp)

        # ── Three-column views ────────────────────────────────────
        views_row = QHBoxLayout()

        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(header_font.pointSize() + 2)

        # Origin
        origin_col = QVBoxLayout()
        self._origin_lbl = QLabel(f"⬅  {self._origin_display}  ({self._origin_nick})")
        self._origin_lbl.setAlignment(Qt.AlignCenter)
        self._origin_lbl.setFont(header_font)
        origin_col.addWidget(self._origin_lbl)
        self._origin_view = _MiniSystemView()
        self._origin_view.setCursor(Qt.CrossCursor)
        self._origin_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        origin_col.addWidget(self._origin_view)
        self._origin_status = QLabel(tr("dlg.jump_click_to_place"))
        self._origin_status.setAlignment(Qt.AlignCenter)
        origin_col.addWidget(self._origin_status)
        views_row.addLayout(origin_col, 2)

        # Destination
        dest_col = QVBoxLayout()
        self._dest_lbl = QLabel("")
        self._dest_lbl.setAlignment(Qt.AlignCenter)
        self._dest_lbl.setFont(header_font)
        dest_col.addWidget(self._dest_lbl)
        self._dest_view = _MiniSystemView()
        self._dest_view.setCursor(Qt.CrossCursor)
        self._dest_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        dest_col.addWidget(self._dest_view)
        self._dest_status = QLabel(tr("dlg.jump_click_to_place"))
        self._dest_status.setAlignment(Qt.AlignCenter)
        dest_col.addWidget(self._dest_status)
        views_row.addLayout(dest_col, 2)

        # Universe preview
        uni_col = QVBoxLayout()
        uni_lbl = QLabel("Universe")
        uni_lbl.setAlignment(Qt.AlignCenter)
        uni_lbl.setFont(header_font)
        uni_col.addWidget(uni_lbl)
        self._uni_view = _MiniUniverseView()
        self._uni_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        uni_col.addWidget(self._uni_view)
        uni_status = QLabel("")
        uni_col.addWidget(uni_status)
        views_row.addLayout(uni_col, 1)

        root.addLayout(views_row)

        # ── Buttons ───────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._save_btn = QPushButton(tr("dlg.jump_save"))
        self._save_btn.setEnabled(False)
        self._save_btn.setMinimumWidth(180)
        self._save_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._save_btn)
        cancel_btn = QPushButton(tr("btn.cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # ── Connections ───────────────────────────────────────────
        self._origin_view.clicked.connect(self._on_origin_click)
        self._dest_view.clicked.connect(self._on_dest_click)

        # ── Universe laden ────────────────────────────────────────
        self._populate_universe()

        # ── Origin laden ──────────────────────────────────────────
        origin_sections = self._parser.parse(origin_path)
        origin_objects = self._parser.get_objects(origin_sections)
        origin_zones = self._parser.get_zones(origin_sections)
        self._origin_navmap_scale = self._navmap_scale_fn(origin_path)
        # Grid half-extent in FL world units:
        #   cell       = 30 000 * (1.36 / navMapScale)
        #   halfExtent = 4 * cell = 163 200 / navMapScale
        # At the vanilla reference value 1.36 this yields 120 000, at 2.0 it
        # yields 81 600 (cell = 20 400), matching Freelancer's in-game map.
        self._origin_half_extent = 163_200.0 / self._origin_navmap_scale
        self._origin_scale = self._compute_scale(origin_objects, self._origin_half_extent)
        self._populate_scene(self._origin_view, origin_objects, origin_zones, self._origin_scale)
        self._origin_view.draw_grid(self._origin_half_extent, self._origin_scale)

        # ── Dest laden (erstes System in Liste) ───────────────────
        self._on_dest_changed()

        QTimer.singleShot(0, self._fit_views)

    # ── Type changed ─────────────────────────────────────────────

    def _on_type_changed(self) -> None:
        arch = str(self._type_cb.currentData() or "")
        is_gate = arch in ("jumpgate", "nomad_gate")
        self._gate_grp.setVisible(is_gate)

    # ── Dest changed ─────────────────────────────────────────────

    def _on_dest_changed(self) -> None:
        dest_path = str(self._dest_cb.currentData() or "").strip()
        if not dest_path:
            return
        dest_nick = Path(dest_path).stem.upper()
        dest_display = dest_nick
        for display, path in self._systems:
            if path == dest_path:
                parts = display.split(" - ", 1)
                if len(parts) == 2:
                    dest_display = parts[1]
                break

        self._dest_lbl.setText(f"➡  {dest_display}  ({dest_nick})")

        # Marker + Position zurücksetzen
        self._dest_pos = None
        self._dest_view.clear_marker()
        self._dest_status.setText(tr("dlg.jump_click_to_place"))
        self._update_save_btn()

        # Dest-System laden
        try:
            dest_sections = self._parser.parse(dest_path)
            dest_objects = self._parser.get_objects(dest_sections)
            dest_zones = self._parser.get_zones(dest_sections)
        except Exception:
            dest_objects, dest_zones = [], []

        dest_navmap_scale = self._navmap_scale_fn(dest_path)
        dest_half_extent = 163_200.0 / dest_navmap_scale
        self._dest_scale = self._compute_scale(dest_objects, dest_half_extent)
        self._dest_view._scene.clear()
        self._populate_scene(self._dest_view, dest_objects, dest_zones, self._dest_scale)
        self._dest_view.draw_grid(dest_half_extent, self._dest_scale)

        # Universe: neue Verbindung anzeigen
        self._update_universe_new_connection(dest_nick)

        QTimer.singleShot(0, lambda: self._dest_view.fit_contents())

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _compute_scale(raw_objects: list[dict], half_extent: float = 0.0) -> float:
        rmax = 0.0
        for data in raw_objects:
            pp = [float(c.strip()) for c in str(data.get("pos", "0,0,0")).split(",")]
            fx = pp[0] if len(pp) > 0 else 0.0
            fz = pp[2] if len(pp) > 2 else (pp[1] if len(pp) > 1 else 0.0)
            dist = (fx * fx + fz * fz) ** 0.5
            rmax = max(rmax, dist)
        extent = max(rmax, half_extent, 10000.0)
        return 500.0 / extent

    @staticmethod
    def _populate_scene(
        view: _MiniSystemView,
        raw_objects: list[dict],
        raw_zones: list[dict],
        scale: float,
    ) -> None:
        scene = view._scene
        for zd in raw_zones:
            try:
                zone = ZoneItem(zd, scale)
                zone.setFlag(QGraphicsItem.ItemIsMovable, False)
                scene.addItem(zone)
            except Exception:
                pass
        for od in raw_objects:
            try:
                obj = SolarObject(od, scale)
                obj.setFlag(QGraphicsItem.ItemIsMovable, False)
                scene.addItem(obj)
            except Exception:
                pass

    def _populate_universe(self) -> None:
        """Füllt die Universe-Mini-Ansicht mit System-Punkten und Verbindungen."""
        scene = self._uni_view._scene
        coord_map = self._uni_coord_map
        edges = self._uni_edges

        # Bestehende Verbindungen
        for key, typ in edges.items():
            nicks = list(key)
            if len(nicks) != 2:
                continue
            a, b = nicks
            if a not in coord_map or b not in coord_map:
                continue
            ax, ay = coord_map[a]
            bx, by = coord_map[b]
            if typ == "gate":
                col = QColor(100, 180, 255, 140)
                width = 1.5
            elif typ == "alien_gate":
                col = QColor(90, 230, 120, 180)
                width = 1.5
            else:
                col = QColor(180, 180, 180, 100)
                width = 1.0
            pen = QPen(col, width)
            pen.setCosmetic(True)
            line = scene.addLine(ax, ay, bx, by, pen)
            line.setZValue(-2)

        # System-Punkte
        for nick, (sx, sy) in coord_map.items():
            r = 4.0
            dot = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r)
            gradient = QRadialGradient(0, 0, r)
            is_origin = nick == self._origin_nick
            if is_origin:
                gradient.setColorAt(0, QColor(100, 255, 100, 230))
                gradient.setColorAt(1, QColor(60, 180, 60, 80))
            else:
                gradient.setColorAt(0, QColor(220, 240, 255, 200))
                gradient.setColorAt(1, QColor(80, 160, 220, 60))
            dot.setBrush(QBrush(gradient))
            dot.setPen(QPen(Qt.NoPen))
            dot.setPos(sx, sy)
            dot.setZValue(5)
            scene.addItem(dot)

    def _update_universe_new_connection(self, dest_nick: str) -> None:
        """Zeichnet die neue Verbindung rot in der Universe-Ansicht."""
        if self._new_conn_line is not None:
            self._uni_view._scene.removeItem(self._new_conn_line)
            self._new_conn_line = None

        origin = self._origin_nick
        dest = dest_nick.upper()
        if origin == dest:
            return
        if origin not in self._uni_coord_map or dest not in self._uni_coord_map:
            return

        ax, ay = self._uni_coord_map[origin]
        bx, by = self._uni_coord_map[dest]
        pen = QPen(QColor(255, 60, 60, 240), 2.5)
        pen.setCosmetic(True)
        self._new_conn_line = self._uni_view._scene.addLine(ax, ay, bx, by, pen)
        self._new_conn_line.setZValue(10)

    def _fit_views(self) -> None:
        self._origin_view.fit_contents()
        self._dest_view.fit_contents()
        self._uni_view.fit_contents()

    def _update_save_btn(self) -> None:
        self._save_btn.setEnabled(
            self._origin_pos is not None and self._dest_pos is not None
        )

    # ── Click-Handler ────────────────────────────────────────────

    def _on_origin_click(self, scene_pos: QPointF) -> None:
        self._origin_pos = scene_pos
        self._origin_view.set_marker(scene_pos, QColor("#44ff44"))
        world_x = scene_pos.x() / self._origin_scale
        world_z = scene_pos.y() / self._origin_scale
        self._origin_status.setText(f"✓  pos = {world_x:.0f}, 0, {world_z:.0f}")
        self._update_save_btn()

    def _on_dest_click(self, scene_pos: QPointF) -> None:
        self._dest_pos = scene_pos
        self._dest_view.set_marker(scene_pos, QColor("#44aaff"))
        world_x = scene_pos.x() / self._dest_scale
        world_z = scene_pos.y() / self._dest_scale
        self._dest_status.setText(f"✓  pos = {world_x:.0f}, 0, {world_z:.0f}")
        self._update_save_btn()

    # ── Public Getters ───────────────────────────────────────────

    def origin_world_pos(self) -> tuple[float, float, float]:
        """Gibt (x, y, z) in FL-Weltkoordinaten zurück."""
        if self._origin_pos is None:
            return (0.0, 0.0, 0.0)
        return (
            self._origin_pos.x() / self._origin_scale,
            0.0,
            self._origin_pos.y() / self._origin_scale,
        )

    def dest_world_pos(self) -> tuple[float, float, float]:
        if self._dest_pos is None:
            return (0.0, 0.0, 0.0)
        return (
            self._dest_pos.x() / self._dest_scale,
            0.0,
            self._dest_pos.y() / self._dest_scale,
        )

    def dest_path(self) -> str:
        return str(self._dest_cb.currentData() or "").strip()

    def archetype(self) -> str:
        return str(self._type_cb.currentData() or "jumphole")

    def conn_type_label(self) -> str:
        """Gibt den Anzeigenamen des Typs zurück (z.B. 'Jump Gate')."""
        text = self._type_cb.currentText()
        if text.startswith("Jump Hole"):
            return "Jump Hole"
        return text

    def gate_info(self) -> dict | None:
        arch = self.archetype()
        if arch not in ("jumpgate", "nomad_gate"):
            return None
        return {
            "behavior": self._behavior_edit.text().strip(),
            "difficulty": self._difficulty_spin.value(),
            "loadout": self._loadout_cb.currentText().strip(),
            "pilot": self._pilot_edit.text().strip(),
            "reputation": self._faction_from_ui(self._rep_cb.currentText().strip()),
        }
