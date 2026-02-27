"""2D-Kartenansicht (QGraphicsView mit Zoom + Pan)."""

from __future__ import annotations

from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsTextItem
from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen

from .models import ZoneItem, SolarObject


class SystemView(QGraphicsView):
    """2D-Systemkarte mit Orbit-Zoom und Mittelklick-Pan."""

    object_selected = Signal(object)
    background_clicked = Signal(QPointF)
    zone_clicked = Signal(object)
    system_double_clicked = Signal(str)  # Pfad des Systems bei Doppelklick
    mouse_moved = Signal(QPointF)        # Szenen-Koordinaten bei Mausbewegung

    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        self.setBackgroundBrush(QBrush(QColor(6, 6, 20)))
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self._panning = False
        self._pan_start = QPointF()
        self._placement_passthrough = False
        self._world_scale = 1.0

    def set_placement_passthrough(self, enabled: bool):
        self._placement_passthrough = bool(enabled)

    def set_world_scale(self, scale: float):
        self._world_scale = max(float(scale), 1e-6)

    @staticmethod
    def _fmt_world_dist(value: float) -> str:
        if value >= 100000:
            return f"{value:,.0f}".replace(",", ".")
        if value >= 1000:
            return f"{value:,.1f}".replace(",", ".")
        return f"{value:.0f}"

    # ------------------------------------------------------------------
    #  Events
    # ------------------------------------------------------------------
    def wheelEvent(self, e):
        f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        self.scale(f, f)

    def mousePressEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start = e.position()
            self.setCursor(Qt.ClosedHandCursor)
            return
        if e.button() == Qt.LeftButton:
            item = self.itemAt(e.pos())
            if item is not None and self._placement_passthrough:
                self.background_clicked.emit(self.mapToScene(e.pos()))
                e.accept()
                return
            if isinstance(item, QGraphicsTextItem):
                item = item.parentItem()
            if isinstance(item, ZoneItem):
                self.zone_clicked.emit(item)
            elif isinstance(item, SolarObject):
                self.object_selected.emit(item)
            else:
                self.background_clicked.emit(self.mapToScene(e.pos()))
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._panning:
            d = e.position() - self._pan_start
            self._pan_start = e.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(d.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(d.y()))
            return
        self.mouse_moved.emit(self.mapToScene(e.pos()))
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            return
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            item = self.itemAt(e.pos())
            if isinstance(item, QGraphicsTextItem):
                item = item.parentItem()
            if item and hasattr(item, "sys_path"):
                self.system_double_clicked.emit(item.sys_path)
                return
        super().mouseDoubleClickEvent(e)

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        sx = abs(self.transform().m11())
        sy = abs(self.transform().m22())
        if sx < 1e-9 or sy < 1e-9 or self._world_scale <= 0:
            return

        margin = 16
        bar_w_px = 140
        bar_h_px = 100

        world_w = bar_w_px / (sx * self._world_scale)
        world_h = bar_h_px / (sy * self._world_scale)

        vrect = self.viewport().rect()
        x0 = margin
        y0 = vrect.height() - margin

        painter.save()
        painter.resetTransform()
        pen = QPen(QColor(210, 210, 230, 200), 1)
        painter.setPen(pen)

        # Horizontaler Maßstabsbalken (unten links)
        painter.drawLine(x0, y0, x0 + bar_w_px, y0)
        painter.drawLine(x0, y0 - 4, x0, y0 + 4)
        painter.drawLine(x0 + bar_w_px, y0 - 4, x0 + bar_w_px, y0 + 4)
        painter.drawText(
            x0,
            y0 - 8,
            f"{self._fmt_world_dist(world_w)} u",
        )

        # Vertikaler Maßstabsbalken (linker Rand)
        vx = margin
        vy0 = margin
        painter.drawLine(vx, vy0, vx, vy0 + bar_h_px)
        painter.drawLine(vx - 4, vy0, vx + 4, vy0)
        painter.drawLine(vx - 4, vy0 + bar_h_px, vx + 4, vy0 + bar_h_px)
        painter.drawText(
            vx + 8,
            vy0 + bar_h_px,
            f"{self._fmt_world_dist(world_h)} u",
        )
        painter.restore()
