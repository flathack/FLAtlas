"""2D-Kartenansicht (QGraphicsView mit Zoom + Pan)."""

from __future__ import annotations

import math

from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsTextItem
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
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
    wheel_scrolled = Signal(QPointF, int)  # Szenen-Koordinaten + vertikaler Wheel-Delta
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
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        self.setOptimizationFlag(QGraphicsView.DontSavePainterState, True)
        self._panning = False
        self._pan_start = QPointF()
        self._placement_passthrough = False
        self._allow_item_clicks_in_placement = False
        self._world_scale = 1.0
        self._bg_pixmap: QPixmap | None = None
        self._bg_color = QColor(theme_bg)
        self._bg_darken_alpha = 0 if self._bg_color.lightness() >= 130 else 180
        self._limit_zoom_to_scene = False
        self._zoom_out_reference_rect = QRectF()
        self._zoom_in_limit_multiplier = 40.0
        self._unbounded_pan = False
        self._left_drag_pan_enabled = False
        self._left_pan_pending = False
        self._default_mouse_tracking = bool(self.hasMouseTracking())
        self._default_viewport_mouse_tracking = bool(self.viewport().hasMouseTracking())

    def current_zoom_factor(self) -> float:
        return abs(float(self.transform().m11()))

    def set_zoom_factor(self, target: float):
        current = max(self.current_zoom_factor(), 1e-9)
        target = self.clamp_zoom_factor(float(target))
        self.scale(target / current, target / current)
        self.zoom_factor_changed.emit(self.current_zoom_factor())

    def set_placement_passthrough(self, enabled: bool, allow_item_clicks: bool = False):
        self._placement_passthrough = bool(enabled)
        self._allow_item_clicks_in_placement = bool(allow_item_clicks)
        if enabled:
            self.setMouseTracking(True)
            self.viewport().setMouseTracking(True)
        else:
            self.setMouseTracking(self._default_mouse_tracking)
            self.viewport().setMouseTracking(self._default_viewport_mouse_tracking)

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

    def set_zoom_out_reference_rect(self, rect: QRectF | None):
        if rect is None or rect.isNull() or rect.width() <= 0.0 or rect.height() <= 0.0:
            self._zoom_out_reference_rect = QRectF()
        else:
            self._zoom_out_reference_rect = QRectF(rect)

    def set_zoom_in_limit_multiplier(self, multiplier: float):
        self._zoom_in_limit_multiplier = max(1.0, float(multiplier))

    def minimum_zoom_factor(self) -> float:
        if not self._limit_zoom_to_scene:
            return 1e-6
        srect = QRectF(self._zoom_out_reference_rect)
        if srect.isNull() or srect.width() <= 0.0 or srect.height() <= 0.0:
            srect = self.sceneRect()
        if srect.isNull() or srect.width() <= 0.0 or srect.height() <= 0.0:
            return 1e-6
        vrect = self.viewport().rect()
        if vrect.width() <= 1 or vrect.height() <= 1:
            return 1e-6
        fit_scale = min(vrect.width() / srect.width(), vrect.height() / srect.height())
        return max(1e-6, float(fit_scale) * 0.995)

    def maximum_zoom_factor(self) -> float:
        min_zoom = self.minimum_zoom_factor()
        if not self._limit_zoom_to_scene:
            return max(1.0, float(self._zoom_in_limit_multiplier))
        return max(min_zoom, min_zoom * max(1.0, float(self._zoom_in_limit_multiplier)))

    def clamp_zoom_factor(self, target: float) -> float:
        target = max(float(target), 1e-6)
        min_zoom = self.minimum_zoom_factor()
        max_zoom = self.maximum_zoom_factor()
        return max(min_zoom, min(max_zoom, target))

    def set_unbounded_pan(self, enabled: bool):
        self._unbounded_pan = bool(enabled)

    def set_left_drag_pan_enabled(self, enabled: bool):
        self._left_drag_pan_enabled = bool(enabled)

    def _pan_by_delta(self, d):
        prev_view = self._pan_start.toPoint()
        cur_view = (self._pan_start + d).toPoint()
        prev_scene = self.mapToScene(prev_view)
        cur_scene = self.mapToScene(cur_view)
        delta_scene = cur_scene - prev_scene
        center_scene = self.mapToScene(self.viewport().rect().center())
        self.centerOn(center_scene - delta_scene)

    def _handle_left_click(self, e):
        item = self._pick_interactive_item(e.pos())
        if item is not None and self._placement_passthrough and not self._allow_item_clicks_in_placement:
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

    def _pick_interactive_item(self, view_pos):
        # Only marker geometry is interactive.
        # Labels must neither select their parent object nor block picks below.
        scene_pos = self.mapToScene(view_pos)
        first_zone = None
        for it in self._scene.items(scene_pos):
            if isinstance(it, QGraphicsTextItem):
                continue
            if isinstance(it, SolarObject):
                if getattr(it, "_base_child_locked", False):
                    continue
                return it
            if first_zone is None and isinstance(it, ZoneItem):
                first_zone = it
        return first_zone

    @staticmethod
    def _fmt_world_dist(value: float) -> str:
        return f"{float(value) / 1000.0:,.2f}".replace(",", ".")

    @staticmethod
    def _zoom_factor_for_wheel_delta(delta_y: int) -> float:
        if delta_y == 0:
            return 1.0
        steps = float(delta_y) / 120.0
        return math.pow(1.08, steps)

    # ------------------------------------------------------------------
    #  Events
    # ------------------------------------------------------------------
    def wheelEvent(self, e):
        if self._placement_passthrough:
            self.wheel_scrolled.emit(self.mapToScene(e.position().toPoint()), int(e.angleDelta().y()))
            e.accept()
            return
        f = self._zoom_factor_for_wheel_delta(int(e.angleDelta().y()))
        current = abs(float(self.transform().m11()))
        target = self.clamp_zoom_factor(current * f)
        f = target / max(1e-9, current)
        self.scale(f, f)
        self.zoom_factor_changed.emit(self.current_zoom_factor())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._limit_zoom_to_scene:
            current = self.current_zoom_factor()
            target = self.clamp_zoom_factor(current)
            if abs(target - current) > 1e-6:
                self.set_zoom_factor(target)

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
            if self._left_drag_pan_enabled and not self._placement_passthrough:
                self._left_pan_pending = True
                self._pan_start = e.position()
                e.accept()
                return
            self._handle_left_click(e)
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        try:
            if self._panning:
                d = e.position() - self._pan_start
                self._pan_start = e.position()
                self._pan_by_delta(d)
                return
            if self._left_pan_pending:
                d = e.position() - self._pan_start
                if not self._panning and (abs(float(d.x())) > 3.0 or abs(float(d.y())) > 3.0):
                    self._panning = True
                    self.setCursor(Qt.ClosedHandCursor)
                if self._panning:
                    self._pan_by_delta(d)
                    self._pan_start = e.position()
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
        if e.button() == Qt.LeftButton and self._left_pan_pending:
            moved = self._panning
            self._left_pan_pending = False
            self._panning = False
            self.setCursor(Qt.CrossCursor if self._placement_passthrough else Qt.ArrowCursor)
            if not moved:
                self._handle_left_click(e)
            return
        if e.button() == Qt.MiddleButton:
            self._panning = False
            self.setCursor(Qt.CrossCursor if self._placement_passthrough else Qt.ArrowCursor)
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
