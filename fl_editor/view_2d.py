"""2D-Kartenansicht (QGraphicsView mit Zoom + Pan)."""

from __future__ import annotations

from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsTextItem
from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QBrush, QColor, QPainter

from .models import ZoneItem, SolarObject


class SystemView(QGraphicsView):
    """2D-Systemkarte mit Orbit-Zoom und Mittelklick-Pan."""

    object_selected = Signal(object)
    background_clicked = Signal(QPointF)
    zone_clicked = Signal(object)
    system_double_clicked = Signal(str)  # Pfad des Systems bei Doppelklick

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
