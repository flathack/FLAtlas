"""Dialog zum Platzieren von Jump Holes / Gates in zwei Systemen gleichzeitig.

Zeigt beide Systeme nebeneinander als Mini-2D-Karten an.
Der User klickt in jedes System, um die Position zu setzen.
Beim Speichern werden beide System-Dateien atomar geschrieben.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QWheelEvent

from .i18n import tr
from .models import SolarObject, ZoneItem
from .themes import current_theme, get_palette


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


# ── Hauptdialog ───────────────────────────────────────────────────────

class JumpConnectionPlacementDialog(QDialog):
    """Zwei-System-Karte zum gleichzeitigen Platzieren von JH/JG."""

    def __init__(
        self,
        parent,
        *,
        origin_path: str,
        dest_path: str,
        origin_nick: str,
        dest_nick: str,
        origin_display: str,
        dest_display: str,
        origin_sections: list[tuple[str, list[tuple[str, str]]]],
        dest_sections: list[tuple[str, list[tuple[str, str]]]],
        origin_objects: list[dict],
        dest_objects: list[dict],
        origin_zones: list[dict],
        dest_zones: list[dict],
        conn_type: str,
        gate_info: dict | None,
        is_inner: bool,
        inner_alias_origin: str,
        inner_alias_dest: str,
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.jump_placement_title"))
        self.setMinimumSize(1100, 600)
        self.resize(1400, 700)

        self._origin_path = origin_path
        self._dest_path = dest_path
        self._origin_nick = origin_nick.upper()
        self._dest_nick = dest_nick.upper()
        self._origin_display = origin_display
        self._dest_display = dest_display
        self._origin_sections = origin_sections
        self._dest_sections = dest_sections
        self._conn_type = conn_type
        self._gate_info = gate_info or {}
        self._is_inner = is_inner
        self._inner_alias_origin = inner_alias_origin
        self._inner_alias_dest = inner_alias_dest

        self._origin_pos: QPointF | None = None
        self._dest_pos: QPointF | None = None

        # Scales berechnen
        self._origin_scale = self._compute_scale(origin_objects)
        self._dest_scale = self._compute_scale(dest_objects)

        # Layout
        root = QVBoxLayout(self)

        # Header
        header = QLabel(self._header_text())
        header.setWordWrap(True)
        root.addWidget(header)

        # Side-by-side views
        views_row = QHBoxLayout()

        # Origin
        origin_col = QVBoxLayout()
        self._origin_lbl = QLabel(f"⬅  {self._origin_display}  ({self._origin_nick})")
        self._origin_lbl.setAlignment(Qt.AlignCenter)
        font = self._origin_lbl.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 2)
        self._origin_lbl.setFont(font)
        origin_col.addWidget(self._origin_lbl)
        self._origin_view = _MiniSystemView()
        self._origin_view.setCursor(Qt.CrossCursor)
        self._origin_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        origin_col.addWidget(self._origin_view)
        self._origin_status = QLabel(tr("dlg.jump_click_to_place"))
        self._origin_status.setAlignment(Qt.AlignCenter)
        origin_col.addWidget(self._origin_status)
        views_row.addLayout(origin_col)

        # Destination
        dest_col = QVBoxLayout()
        self._dest_lbl = QLabel(f"➡  {self._dest_display}  ({self._dest_nick})")
        self._dest_lbl.setAlignment(Qt.AlignCenter)
        self._dest_lbl.setFont(font)
        dest_col.addWidget(self._dest_lbl)
        self._dest_view = _MiniSystemView()
        self._dest_view.setCursor(Qt.CrossCursor)
        self._dest_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        dest_col.addWidget(self._dest_view)
        self._dest_status = QLabel(tr("dlg.jump_click_to_place"))
        self._dest_status.setAlignment(Qt.AlignCenter)
        dest_col.addWidget(self._dest_status)
        views_row.addLayout(dest_col)

        root.addLayout(views_row)

        # Buttons
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

        # Populate scenes
        self._populate_scene(
            self._origin_view, origin_objects, origin_zones, self._origin_scale,
        )
        self._populate_scene(
            self._dest_view, dest_objects, dest_zones, self._dest_scale,
        )

        # Connections
        self._origin_view.clicked.connect(self._on_origin_click)
        self._dest_view.clicked.connect(self._on_dest_click)

        # Fit after show
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._fit_views)

    # ── Helpers ───────────────────────────────────────────────────

    def _header_text(self) -> str:
        kind = self._conn_type
        if self._is_inner:
            return f"{kind}: innerhalb von {self._origin_display}"
        return f"{kind}: {self._origin_display}  ↔  {self._dest_display}"

    @staticmethod
    def _compute_scale(raw_objects: list[dict]) -> float:
        rmax = 0.0
        for data in raw_objects:
            pp = [float(c.strip()) for c in str(data.get("pos", "0,0,0")).split(",")]
            fx = pp[0] if len(pp) > 0 else 0.0
            fz = pp[2] if len(pp) > 2 else (pp[1] if len(pp) > 1 else 0.0)
            dist = (fx * fx + fz * fz) ** 0.5
            rmax = max(rmax, dist)
        extent = max(rmax, 10000.0)
        return 500.0 / extent

    @staticmethod
    def _populate_scene(
        view: _MiniSystemView,
        raw_objects: list[dict],
        raw_zones: list[dict],
        scale: float,
    ) -> None:
        scene = view._scene
        # Zones
        for zd in raw_zones:
            try:
                zone = ZoneItem(zd, scale)
                zone.setFlag(QGraphicsItem.ItemIsMovable, False)
                scene.addItem(zone)
            except Exception:
                pass
        # Objects
        for od in raw_objects:
            try:
                obj = SolarObject(od, scale)
                obj.setFlag(QGraphicsItem.ItemIsMovable, False)
                scene.addItem(obj)
            except Exception:
                pass

    def _fit_views(self) -> None:
        self._origin_view.fit_contents()
        self._dest_view.fit_contents()

    def _update_save_btn(self) -> None:
        self._save_btn.setEnabled(
            self._origin_pos is not None and self._dest_pos is not None
        )

    # ── Click-Handler ─────────────────────────────────────────────

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

    # ── Public Getters ────────────────────────────────────────────

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
