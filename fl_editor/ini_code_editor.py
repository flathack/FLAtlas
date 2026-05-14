"""INI editor widgets used by the main window."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QRectF, QTimer, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import QPlainTextEdit, QSlider, QTextEdit, QWidget

from .themes import current_theme, get_palette


class _IniLineNumberArea(QWidget):
    def __init__(self, editor: "_IniCodeEditor"):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor.line_number_area_paint_event(event)


class _IniMiniMap(QWidget):
    def __init__(self, editor: "_IniCodeEditor", parent=None):
        super().__init__(parent)
        self._editor = editor
        self._dragging = False
        self._content_cache = QPixmap()
        self._cache_key: tuple[int, int, int, int, str] | None = None
        self._cache_dirty = True
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(90)
        self._refresh_timer.timeout.connect(self._rebuild_cache)
        self.setMinimumWidth(72)
        self.setMaximumWidth(96)
        self.setMouseTracking(True)
        self._editor.blockCountChanged.connect(lambda _count: self.schedule_refresh())
        self._editor.updateRequest.connect(lambda _rect, _dy: self.update())
        self._editor.cursorPositionChanged.connect(self.update)
        self._editor.textChanged.connect(self.schedule_refresh)
        self._editor.verticalScrollBar().valueChanged.connect(lambda _value: self.update())

    def refresh_theme(self) -> None:
        self.schedule_refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.schedule_refresh()

    def schedule_refresh(self) -> None:
        self._cache_dirty = True
        self._refresh_timer.start()

    def _rebuild_cache(self) -> None:
        size = self.size()
        if size.width() <= 0 or size.height() <= 0:
            self._content_cache = QPixmap()
            self._cache_key = None
            self.update()
            return

        doc = self._editor.document()
        block_count = max(1, int(doc.blockCount()))
        palette = get_palette(current_theme())
        cache_key = (
            int(doc.revision()),
            int(size.width()),
            int(size.height()),
            block_count,
            str(current_theme()),
        )
        if not self._cache_dirty and self._cache_key == cache_key and not self._content_cache.isNull():
            self.update()
            return

        pixmap = QPixmap(size)
        bg = QColor(palette.get("bg_toolbar", palette.get("bg", "#1a1d24")))
        pixmap.fill(bg)

        painter = QPainter(pixmap)
        height = max(1, size.height())
        width = max(1, size.width())
        content_left = 4
        content_width = max(8, width - 8)

        if block_count <= height * 2:
            scale_y = float(height) / float(block_count)
            block = doc.firstBlock()
            while block.isValid():
                block_number = int(block.blockNumber())
                top = int(block_number * scale_y)
                bottom = max(top + 1, int((block_number + 1) * scale_y))
                self._paint_cache_line(
                    painter,
                    line_text=str(block.text() or ""),
                    top=top,
                    bottom=bottom,
                    content_left=content_left,
                    content_width=content_width,
                    palette=palette,
                )
                block = block.next()
        else:
            rows = max(1, height)
            max_block_index = max(0, block_count - 1)
            for row in range(rows):
                block_number = min(max_block_index, int((row / rows) * block_count))
                block = doc.findBlockByNumber(block_number)
                if not block.isValid():
                    continue
                self._paint_cache_line(
                    painter,
                    line_text=str(block.text() or ""),
                    top=row,
                    bottom=row + 1,
                    content_left=content_left,
                    content_width=content_width,
                    palette=palette,
                )
        painter.end()
        self._content_cache = pixmap
        self._cache_key = cache_key
        self._cache_dirty = False
        self.update()

    def _paint_cache_line(
        self,
        painter: QPainter,
        *,
        line_text: str,
        top: int,
        bottom: int,
        content_left: int,
        content_width: int,
        palette: dict[str, str],
    ) -> None:
        stripped = line_text.lstrip()
        indent = len(line_text) - len(stripped)
        indent_px = min(content_width - 4, int(indent * 0.8))
        text_len = len(stripped)
        line_width = max(4, min(content_width - indent_px, int((min(text_len, 120) / 120.0) * content_width)))
        color = self._line_color_for_text(line_text, palette)
        painter.fillRect(content_left + indent_px, top, line_width, max(1, bottom - top), color)

    def _line_color_for_text(self, text: str, palette: dict[str, str]) -> QColor:
        stripped = str(text or "").strip()
        if not stripped:
            return QColor(palette.get("fg_dim", "#8b93a6"))
        if stripped.startswith(";") or stripped.startswith("#"):
            return QColor(palette.get("fg_dim", "#8b93a6"))
        if stripped.startswith("[") and stripped.endswith("]"):
            return QColor(palette.get("fg_accent", "#6cb6ff"))
        if "=" in stripped:
            return QColor("#8a5a00" if current_theme() in ("light", "xp") else "#d7ba7d")
        return QColor(palette.get("fg", "#dde3f0"))

    def _scroll_to_ratio(self, ratio: float) -> None:
        scrollbar = self._editor.verticalScrollBar()
        maximum = max(0, int(scrollbar.maximum()))
        scrollbar.setValue(int(maximum * max(0.0, min(1.0, ratio))))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._scroll_to_ratio(event.position().y() / max(1.0, float(self.height())))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._scroll_to_ratio(event.position().y() / max(1.0, float(self.height())))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        palette = get_palette(current_theme())
        bg = QColor(palette.get("bg_toolbar", palette.get("bg", "#1a1d24")))
        painter.fillRect(event.rect(), bg)
        if self._cache_dirty or self._content_cache.isNull():
            self._rebuild_cache()
        if not self._content_cache.isNull():
            painter.drawPixmap(0, 0, self._content_cache)

        doc = self._editor.document()
        block_count = max(1, int(doc.blockCount()))
        width = max(1, self.width())
        height = max(1, self.height())
        scale_y = float(height) / float(block_count)

        first_visible = self._editor.firstVisibleBlock()
        first_block_num = max(0, int(first_visible.blockNumber()))
        last_visible_num = first_block_num
        block = first_visible
        top = self._editor.blockBoundingGeometry(block).translated(self._editor.contentOffset()).top()
        while block.isValid() and top <= self._editor.viewport().height():
            last_visible_num = int(block.blockNumber())
            block = block.next()
            top += self._editor.blockBoundingRect(block).height()

        viewport_top = int(first_block_num * scale_y)
        viewport_bottom = max(viewport_top + 8, int((last_visible_num + 1) * scale_y))
        viewport_rect = QRectF(1, viewport_top, width - 2, max(8, viewport_bottom - viewport_top))
        painter.setPen(QPen(QColor(palette.get("sel_bg", "#2f7dd1")), 1))
        overlay = QColor(palette.get("sel_bg", "#2f7dd1"))
        overlay.setAlpha(40 if current_theme() in ("light", "xp") else 55)
        painter.fillRect(viewport_rect, overlay)
        painter.drawRect(viewport_rect)


class _TextOverviewMiniMap(QWidget):
    def __init__(self, *, source_provider, scroll_provider, parent=None):
        super().__init__(parent)
        self._source_provider = source_provider
        self._scroll_provider = scroll_provider
        self._dragging = False
        self._content_cache = QPixmap()
        self._cache_key: tuple[int, int, int, int, str, int] | None = None
        self._cache_dirty = True
        self._highlight_lines: set[int] = set()
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(90)
        self._refresh_timer.timeout.connect(self._rebuild_cache)
        self.setMinimumWidth(72)
        self.setMaximumWidth(96)
        self.setMouseTracking(True)
        self._connect_scrollbar()

    def _connect_scrollbar(self) -> None:
        scrollbar = self._scrollbar()
        if scrollbar is None or bool(getattr(scrollbar, "_time_machine_minimap_connected", False)):
            return
        scrollbar.valueChanged.connect(lambda _value: self.update())
        setattr(scrollbar, "_time_machine_minimap_connected", True)

    def _scrollbar(self):
        try:
            scrollbar = self._scroll_provider()
        except Exception:
            scrollbar = None
        return scrollbar

    def set_highlight_lines(self, lines: set[int] | list[int] | tuple[int, ...]) -> None:
        normalized: set[int] = set()
        for line in lines or ():
            try:
                normalized.add(max(0, int(line)))
            except Exception:
                continue
        if normalized == self._highlight_lines:
            return
        self._highlight_lines = normalized
        self.schedule_refresh()

    def refresh_theme(self) -> None:
        self.schedule_refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.schedule_refresh()

    def schedule_refresh(self) -> None:
        self._connect_scrollbar()
        self._cache_dirty = True
        self._refresh_timer.start()

    def _source_lines(self) -> list[str]:
        try:
            text = str(self._source_provider() or "")
        except Exception:
            text = ""
        lines = text.splitlines()
        return lines if lines else [""]

    def _rebuild_cache(self) -> None:
        size = self.size()
        if size.width() <= 0 or size.height() <= 0:
            self._content_cache = QPixmap()
            self._cache_key = None
            self.update()
            return

        palette = get_palette(current_theme())
        lines = self._source_lines()
        line_count = max(1, len(lines))
        cache_key = (
            int(size.width()),
            int(size.height()),
            line_count,
            len(self._highlight_lines),
            str(current_theme()),
            hash(tuple(sorted(self._highlight_lines))) if self._highlight_lines else 0,
        )
        if not self._cache_dirty and self._cache_key == cache_key and not self._content_cache.isNull():
            self.update()
            return

        pixmap = QPixmap(size)
        bg = QColor(palette.get("bg_toolbar", palette.get("bg", "#1a1d24")))
        pixmap.fill(bg)

        painter = QPainter(pixmap)
        height = max(1, size.height())
        width = max(1, size.width())
        content_left = 4
        content_width = max(8, width - 8)
        diff_color = QColor("#2f7dd1")

        if line_count <= height * 2:
            scale_y = float(height) / float(line_count)
            for line_index, line_text in enumerate(lines):
                top = int(line_index * scale_y)
                bottom = max(top + 1, int((line_index + 1) * scale_y))
                self._paint_cache_line(
                    painter,
                    line_text=line_text,
                    top=top,
                    bottom=bottom,
                    content_left=content_left,
                    content_width=content_width,
                    palette=palette,
                )
                if line_index in self._highlight_lines:
                    painter.fillRect(0, top, 3, max(1, bottom - top), diff_color)
        else:
            rows = max(1, height)
            max_line_index = max(0, line_count - 1)
            for row in range(rows):
                line_index = min(max_line_index, int((row / rows) * line_count))
                self._paint_cache_line(
                    painter,
                    line_text=lines[line_index],
                    top=row,
                    bottom=row + 1,
                    content_left=content_left,
                    content_width=content_width,
                    palette=palette,
                )
                if line_index in self._highlight_lines:
                    painter.fillRect(0, row, 3, 1, diff_color)
        painter.end()
        self._content_cache = pixmap
        self._cache_key = cache_key
        self._cache_dirty = False
        self.update()

    def _paint_cache_line(
        self,
        painter: QPainter,
        *,
        line_text: str,
        top: int,
        bottom: int,
        content_left: int,
        content_width: int,
        palette: dict[str, str],
    ) -> None:
        stripped = line_text.lstrip()
        indent = len(line_text) - len(stripped)
        indent_px = min(content_width - 4, int(indent * 0.8))
        text_len = len(stripped)
        line_width = max(4, min(content_width - indent_px, int((min(text_len, 120) / 120.0) * content_width)))
        color = self._line_color_for_text(line_text, palette)
        painter.fillRect(content_left + indent_px, top, line_width, max(1, bottom - top), color)

    def _line_color_for_text(self, text: str, palette: dict[str, str]) -> QColor:
        stripped = str(text or "").strip()
        if not stripped:
            return QColor(palette.get("fg_dim", "#8b93a6"))
        if stripped.startswith(";") or stripped.startswith("#"):
            return QColor(palette.get("fg_dim", "#8b93a6"))
        if stripped.startswith("[") and stripped.endswith("]"):
            return QColor(palette.get("fg_accent", "#6cb6ff"))
        if "=" in stripped:
            return QColor("#8a5a00" if current_theme() in ("light", "xp") else "#d7ba7d")
        return QColor(palette.get("fg", "#dde3f0"))

    def _scroll_to_ratio(self, ratio: float) -> None:
        scrollbar = self._scrollbar()
        if scrollbar is None:
            return
        maximum = max(0, int(scrollbar.maximum()))
        scrollbar.setValue(int(maximum * max(0.0, min(1.0, ratio))))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._scroll_to_ratio(event.position().y() / max(1.0, float(self.height())))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._scroll_to_ratio(event.position().y() / max(1.0, float(self.height())))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        palette = get_palette(current_theme())
        bg = QColor(palette.get("bg_toolbar", palette.get("bg", "#1a1d24")))
        painter.fillRect(event.rect(), bg)
        if self._cache_dirty or self._content_cache.isNull():
            self._rebuild_cache()
        if not self._content_cache.isNull():
            painter.drawPixmap(0, 0, self._content_cache)

        scrollbar = self._scrollbar()
        if scrollbar is None:
            return
        width = max(1, self.width())
        height = max(1, self.height())
        maximum = max(0, int(scrollbar.maximum()))
        page_step = max(1, int(scrollbar.pageStep()))
        value = max(0, int(scrollbar.value()))
        total = maximum + page_step
        if total <= 0:
            total = 1
        viewport_top = int((value / total) * height)
        viewport_height = max(8, int((page_step / total) * height))
        if viewport_top + viewport_height > height:
            viewport_top = max(0, height - viewport_height)
        viewport_rect = QRectF(1, viewport_top, width - 2, max(8, viewport_height))
        painter.setPen(QPen(QColor(palette.get("sel_bg", "#2f7dd1")), 1))
        overlay = QColor(palette.get("sel_bg", "#2f7dd1"))
        overlay.setAlpha(40 if current_theme() in ("light", "xp") else 55)
        painter.fillRect(viewport_rect, overlay)
        painter.drawRect(viewport_rect)


class _RevisionTimelineStrip(QWidget):
    def __init__(self, slider: QSlider, entries: list[dict[str, object]], parent=None):
        super().__init__(parent)
        self._slider = slider
        self._entries = list(entries or [])
        self._dragging = False
        self.setMinimumHeight(46)
        self.setMaximumHeight(58)
        self.setMouseTracking(True)
        self._slider.valueChanged.connect(lambda _value: self.update())

    def _entry_count(self) -> int:
        return max(1, len(self._entries))

    def _marker_x(self, index: int) -> int:
        count = self._entry_count()
        left = 10
        right = max(left + 1, self.width() - 10)
        if count <= 1:
            return int((left + right) / 2)
        ratio = max(0.0, min(1.0, float(index) / float(count - 1)))
        return int(left + ((right - left) * ratio))

    def _index_at_x(self, x_pos: float) -> int:
        count = self._entry_count()
        if count <= 1:
            return 0
        left = 10.0
        right = max(left + 1.0, float(self.width() - 10))
        ratio = (float(x_pos) - left) / max(1.0, (right - left))
        return max(0, min(count - 1, int(round(ratio * (count - 1)))))

    def _selected_timestamp(self) -> str:
        index = max(0, min(int(self._slider.value()), len(self._entries) - 1))
        raw = str(self._entries[index].get("timestamp", "") or "").strip() if self._entries else ""
        if not raw:
            return "-"
        try:
            dt = datetime.fromisoformat(raw)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return raw

    def _set_slider_index_from_x(self, x_pos: float) -> None:
        if not self._entries:
            return
        self._slider.setValue(self._index_at_x(x_pos))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._set_slider_index_from_x(event.position().x())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._set_slider_index_from_x(event.position().x())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self._set_slider_index_from_x(event.position().x())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        palette = get_palette(current_theme())
        bg = QColor(palette.get("bg_toolbar", palette.get("bg", "#1a1d24")))
        painter.fillRect(self.rect(), bg)

        line_y = 15
        left = 10
        right = max(left + 1, self.width() - 10)
        painter.setPen(QPen(QColor(palette.get("border", "#4b5563")), 1))
        painter.drawLine(left, line_y, right, line_y)

        selected_index = max(0, min(int(self._slider.value()), self._entry_count() - 1))
        tick_pen = QPen(QColor(palette.get("fg_dim", "#8b93a6")), 1)
        selected_pen = QPen(QColor(palette.get("sel_bg", "#2f7dd1")), 2)
        for index in range(self._entry_count()):
            x_pos = self._marker_x(index)
            painter.setPen(selected_pen if index == selected_index else tick_pen)
            marker_top = 6 if index == selected_index else 9
            marker_bottom = 25 if index == selected_index else 21
            painter.drawLine(x_pos, marker_top, x_pos, marker_bottom)
            if index == selected_index:
                painter.setBrush(QColor(palette.get("sel_bg", "#2f7dd1")))
                painter.drawEllipse(QRectF(x_pos - 4, line_y - 4, 8, 8))

        painter.setPen(QColor(palette.get("fg", "#dde3f0")))
        date_rect = QRectF(8, 28, max(10, self.width() - 16), max(14, self.height() - 30))
        painter.drawText(date_rect, Qt.AlignLeft | Qt.AlignVCenter, self._selected_timestamp())


class _IniCodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_number_area = _IniLineNumberArea(self)
        self._changed_lines: set[int] = set()
        self._line_history: dict[str, str] = {}
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self._update_line_number_area_width(0)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setTabStopDistance(32.0)
        self.refresh_theme()

    def set_changed_lines(self, changed: set[int]) -> None:
        self._changed_lines = set(changed)
        self._line_number_area.update()

    def set_line_history(self, history: dict[str, str]) -> None:
        self._line_history = dict(history)

    def refresh_theme(self) -> None:
        pal = get_palette(current_theme())
        self.setStyleSheet(
            "QPlainTextEdit {"
            f" background: {pal.get('bg_textedit', pal.get('bg_input', '#ffffff'))};"
            f" color: {pal.get('fg', '#1f2937')};"
            f" border: 1px solid {pal.get('border', '#cfd7e3')};"
            " padding-left: 4px;"
            f" selection-background-color: {pal.get('sel_bg', '#2f7dd1')};"
            "}"
        )
        self._highlight_current_line()
        self._line_number_area.update()
        self.viewport().update()

    def line_number_area_width(self) -> int:
        digits = 1
        maximum = max(1, self.blockCount())
        while maximum >= 10:
            maximum //= 10
            digits += 1
        marker_width = 4
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits + marker_width

    def _update_line_number_area_width(self, _block_count: int):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy: int):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(QRectF(cr.left(), cr.top(), self.line_number_area_width(), cr.height()).toRect())

    def line_number_area_paint_event(self, event):
        painter = QPainter(self._line_number_area)
        pal = get_palette(current_theme())
        painter.fillRect(event.rect(), QColor(pal.get("bg_toolbar", pal.get("bg", "#1a1d24"))))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        area_width = self._line_number_area.width()
        changed_color = QColor("#e2b714")
        history_color = QColor("#4a90d9")
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                # Changed-line marker (yellow bar on the left edge)
                if block_number in self._changed_lines:
                    painter.fillRect(0, top, 3, bottom - top, changed_color)
                elif str(block_number) in self._line_history:
                    painter.fillRect(0, top, 3, bottom - top, history_color)
                painter.setPen(QColor(pal.get("fg_dim", "#8b93a6")))
                painter.drawText(4, top, area_width - 10, self.fontMetrics().height(), Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def _highlight_current_line(self):
        extra = []
        if not self.isReadOnly():
            sel = QTextEdit.ExtraSelection()
            pal = get_palette(current_theme())
            sel.format.setBackground(QColor(pal.get("bg_alt", pal.get("bg_list", "#222834"))))
            sel.format.setProperty(QTextCharFormat.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            extra.append(sel)
        self.setExtraSelections(extra)


class _IniSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.refresh_theme()

    def refresh_theme(self) -> None:
        pal = get_palette(current_theme())
        light_theme = current_theme() in ("light", "xp")
        self._fmt_section = QTextCharFormat()
        self._fmt_section.setForeground(QColor(pal.get("fg_accent", "#6cb6ff")))
        self._fmt_section.setFontWeight(QFont.Bold)
        self._fmt_key = QTextCharFormat()
        self._fmt_key.setForeground(QColor("#8a5a00" if light_theme else "#d7ba7d"))
        self._fmt_value = QTextCharFormat()
        self._fmt_value.setForeground(QColor(pal.get("fg", "#dde3f0")))
        self._fmt_comment = QTextCharFormat()
        self._fmt_comment.setForeground(QColor(pal.get("fg_dim", "#8b93a6")))
        self._fmt_comment.setFontItalic(True)
        self.rehighlight()

    def highlightBlock(self, text: str):
        stripped = text.strip()
        if not stripped:
            return
        if stripped.startswith(";") or stripped.startswith("#"):
            self.setFormat(0, len(text), self._fmt_comment)
            return
        if stripped.startswith("[") and stripped.endswith("]"):
            self.setFormat(0, len(text), self._fmt_section)
            return
        if "=" in text:
            key, _, value = text.partition("=")
            self.setFormat(0, len(key), self._fmt_key)
            self.setFormat(len(key), 1, self._fmt_comment)
            self.setFormat(len(key) + 1, len(value), self._fmt_value)
