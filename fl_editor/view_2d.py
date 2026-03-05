"""2D-Kartenansicht (QGraphicsView mit Zoom + Pan)."""

from __future__ import annotations

from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsTextItem
from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPixmap

from .models import ZoneItem, SolarObject
from .themes import current_theme, get_palette


class SystemView(QGraphicsView):
    """2D-Systemkarte mit Orbit-Zoom und Mittelklick-Pan."""

    object_selected = Signal(object)
    background_clicked = Signal(QPointF)
    zone_clicked = Signal(object)
    system_double_clicked = Signal(str)  # Pfad des Systems bei Doppelklick
    mouse_moved = Signal(QPointF)        # Szenen-Koordinaten bei Mausbewegung
    context_menu_requested = Signal(QPointF, object)  # Szenen-Position + Item (oder None)
    item_clicked = Signal(object, bool)  # Item + ctrl_held
    zoom_factor_changed = Signal(float)

    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        theme_bg = QColor(get_palette(current_theme()).get("bg_list", "#101018"))
        self.setBackgroundBrush(QBrush(theme_bg))
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self._panning = False
        self._pan_start = QPointF()
        self._placement_passthrough = False
        self._world_scale = 1.0
        self._bg_pixmap: QPixmap | None = None
        self._bg_color = QColor(theme_bg)
        self._bg_darken_alpha = 0 if self._bg_color.lightness() >= 130 else 180
        self._limit_zoom_to_scene = False

    def current_zoom_factor(self) -> float:
        return abs(float(self.transform().m11()))

    def set_zoom_factor(self, target: float):
        current = max(self.current_zoom_factor(), 1e-9)
        target = max(float(target), 1e-6)
        self.scale(target / current, target / current)
        self.zoom_factor_changed.emit(self.current_zoom_factor())

    def set_placement_passthrough(self, enabled: bool):
        self._placement_passthrough = bool(enabled)

    def set_world_scale(self, scale: float):
        self._world_scale = max(float(scale), 1e-6)

    def set_background_pixmap(self, pixmap: QPixmap | None, fallback: QColor):
        self._bg_pixmap = pixmap
        self._bg_color = QColor(fallback)
        # Light themes should not be heavily darkened by the star wallpaper overlay.
        self._bg_darken_alpha = 0 if self._bg_color.lightness() >= 130 else 180
        self.viewport().update()

    def set_zoom_out_limit_to_scene(self, enabled: bool):
        self._limit_zoom_to_scene = bool(enabled)

    def _pick_interactive_item(self, view_pos):
        # Only marker geometry is interactive.
        # Labels must neither select their parent object nor block picks below.
        scene_pos = self.mapToScene(view_pos)
        first_zone = None
        for it in self._scene.items(scene_pos):
            if isinstance(it, QGraphicsTextItem):
                continue
            if isinstance(it, SolarObject):
                return it
            if first_zone is None and isinstance(it, ZoneItem):
                first_zone = it
        return first_zone

    @staticmethod
    def _fmt_world_dist(value: float) -> str:
        return f"{float(value) / 1000.0:,.2f}".replace(",", ".")

    # ------------------------------------------------------------------
    #  Events
    # ------------------------------------------------------------------
    def wheelEvent(self, e):
        f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        current = abs(float(self.transform().m11()))
        target = current * f
        if self._limit_zoom_to_scene and f < 1.0:
            srect = self.sceneRect()
            if not srect.isNull() and srect.width() > 0 and srect.height() > 0:
                vrect = self.viewport().rect()
                if vrect.width() > 1 and vrect.height() > 1:
                    fit_scale = min(vrect.width() / srect.width(), vrect.height() / srect.height())
                    min_scale = max(1e-6, fit_scale * 0.98)
                    if target < min_scale:
                        f = min_scale / max(1e-9, current)
        self.scale(f, f)
        self.zoom_factor_changed.emit(self.current_zoom_factor())

    def mousePressEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start = e.position()
            self.setCursor(Qt.ClosedHandCursor)
            return
        if e.button() == Qt.RightButton:
            item = self._pick_interactive_item(e.pos())
            self.context_menu_requested.emit(self.mapToScene(e.pos()), item)
            e.accept()
            return
        if e.button() == Qt.LeftButton:
            item = self._pick_interactive_item(e.pos())
            if item is not None and self._placement_passthrough:
                self.background_clicked.emit(self.mapToScene(e.pos()))
                e.accept()
                return
            ctrl_held = bool(e.modifiers() & Qt.ControlModifier)
            if isinstance(item, ZoneItem):
                self.item_clicked.emit(item, ctrl_held)
                self.zone_clicked.emit(item)
            elif isinstance(item, SolarObject):
                self.item_clicked.emit(item, ctrl_held)
                self.object_selected.emit(item)
            else:
                self.background_clicked.emit(self.mapToScene(e.pos()))
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        try:
            if self._panning:
                d = e.position() - self._pan_start
                self._pan_start = e.position()
                self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(d.x()))
                self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(d.y()))
                return
            self.mouse_moved.emit(self.mapToScene(e.pos()))
            super().mouseMoveEvent(e)
        except KeyboardInterrupt:
            # Ctrl+C in Terminal soll die App sauber beenden, ohne Qt-Traceback.
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is not None:
                app.quit()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            return
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            item = self._pick_interactive_item(e.pos())
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
            f"{self._fmt_world_dist(world_w)} km",
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
            f"{self._fmt_world_dist(world_h)} km",
        )
        painter.restore()

    def drawBackground(self, painter, rect):
        _ = rect
        painter.save()
        painter.resetTransform()
        vp_rect = self.viewport().rect()
        if self._bg_pixmap is not None and not self._bg_pixmap.isNull():
            painter.drawTiledPixmap(vp_rect, self._bg_pixmap)
            painter.fillRect(vp_rect, QColor(0, 0, 0, self._bg_darken_alpha))
        else:
            painter.fillRect(vp_rect, self._bg_color)
        painter.restore()
