"""Center tab bar widget helpers."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtWidgets import QApplication, QTabBar


class CenterTabBar(QTabBar):
    """Tab bar that exposes whether a tab reorder drag is currently active."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._drag_start_pos: QPointF | None = None
        self._drag_start_index = -1
        self._reordering = False

    def is_reordering(self) -> bool:
        return bool(self._reordering)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = QPointF(event.position())
            self._drag_start_index = int(self.tabAt(event.position().toPoint()))
            self._reordering = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            self._drag_start_pos is not None
            and self._drag_start_index >= 0
            and bool(event.buttons() & Qt.LeftButton)
        ):
            if (event.position() - self._drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                self._reordering = True
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        was_reordering = bool(self._reordering)
        super().mouseReleaseEvent(event)
        self._drag_start_pos = None
        self._drag_start_index = -1
        if was_reordering:
            QTimer.singleShot(0, self._finish_reordering)
        else:
            self._reordering = False

    def _finish_reordering(self):
        self._reordering = False
