#!/usr/bin/env python3
"""
FL Atlas - Freelancer System Editor
Autor: Steven

Dieses Skript dient als Einstiegspunkt.
Die gesamte Logik befindet sich im Paket ``fl_editor``.
"""

APP_VERSION = "0.7.5"
__version__ = APP_VERSION
__author__ = "Aldenmar Odin - flathack"
import os
import sys
import argparse
from pathlib import Path

# Qt3D kann auf manchen Windows-Setups den RHI-Renderer nicht laden.
# Fallback auf OpenGL nur dann, wenn der Nutzer nichts explizit gesetzt hat.
if sys.platform.startswith("win"):
    os.environ.setdefault("QT3D_RENDERER", "opengl")

from fl_editor.config import Config
from fl_editor.dev_status import default_dev_status_by_nav, default_dev_status_states
from fl_editor.i18n import available_languages, set_language
from fl_editor.main_window import MainWindow
from fl_editor.themes import THEME_NAMES
from PySide6.QtWidgets import QApplication, QSplashScreen, QWidget
from PySide6.QtCore import QRect, QTimer, Qt
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap

# ---------------------------------------------------------------------------
# Startvorgaben
# ---------------------------------------------------------------------------
# True: Startsprache/-theme werden bei jedem Start in die Config geschrieben.
# False: Nutzer-Konfiguration bleibt unverändert.
FORCE_STARTUP_SETTINGS = False

# Gültige Sprache: siehe available_languages() / translations.json
STARTUP_LANGUAGE = "en"

# Gültiges Theme: founder, dark, light, xp, custom
STARTUP_THEME = "dark"

# ---------------------------------------------------------------------------
# DEV-Status
# ---------------------------------------------------------------------------
DEV_STATUS_STATES = default_dev_status_states()

# Status je Haupt-Navigationspunkt.
DEV_STATUS_BY_NAV = default_dev_status_by_nav()

# ---------------------------------------------------------------------------
# Update-Check-Verhalten (zentral)
# ---------------------------------------------------------------------------
# True: In den Einstellungen wird eine zusätzliche Option angezeigt:
# "Check auf Alpha release". Dann kann der Nutzer Pre-Releases ein-/ausschalten.
# False: Nur stabile Releases (kein Alpha/Pre-Release) prüfen.
ALLOW_PRERELEASE_UPDATE_TOGGLE = True

# Standardwert für die Nutzer-Option "Check auf Alpha release" (nur wenn oben True).
DEFAULT_CHECK_PRERELEASE = True


def _apply_startup_settings() -> None:
    if not FORCE_STARTUP_SETTINGS:
        return

    cfg = Config()
    lang = str(STARTUP_LANGUAGE or "").strip().lower()
    theme = str(STARTUP_THEME or "").strip().lower()

    supported_langs = set(available_languages() or ["en"])
    if lang not in supported_langs:
        lang = "en"
    if theme not in THEME_NAMES:
        theme = "dark"

    set_language(lang)
    cfg.set("language", lang)
    cfg.set("theme", theme)

def _set_windows_app_user_model_id() -> None:
    """Ensure Windows taskbar uses this app identity/icon instead of python.exe."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FLAtlas.FLAtlas")
    except Exception:
        pass


def _fit_window_to_active_screen(window: MainWindow) -> None:
    """Clamp window geometry to the currently active/available screen."""
    try:
        screen = QGuiApplication.screenAt(QCursor.pos())
    except Exception:
        screen = None
    if screen is None:
        try:
            wh = window.windowHandle()
            screen = wh.screen() if wh is not None else None
        except Exception:
            screen = None
    if screen is None:
        screen = QGuiApplication.primaryScreen()
    if screen is None:
        return
    avail = QRect(screen.availableGeometry())
    if avail.width() <= 0 or avail.height() <= 0:
        return
    g = QRect(window.geometry())
    try:
        min_size = window.minimumSizeHint()
    except Exception:
        min_size = None
    horizontal_padding = 24
    vertical_padding = 28
    max_width = min(avail.width(), max(640, avail.width() - horizontal_padding))
    max_height = min(avail.height(), max(480, avail.height() - vertical_padding))
    if min_size is not None:
        max_width = min(avail.width(), max(min_size.width(), max_width))
        max_height = min(avail.height(), max(min_size.height(), max_height))
    # Never exceed usable display area and keep the window fully on-screen.
    if g.width() > max_width or g.height() > max_height:
        g.setSize(g.size().boundedTo(QRect(0, 0, max_width, max_height).size()))
    if g.left() < avail.left():
        g.moveLeft(avail.left())
    if g.top() < avail.top():
        g.moveTop(avail.top())
    if g.right() > avail.left() + max_width - 1:
        g.moveLeft(max(avail.left(), avail.left() + max_width - g.width()))
    if g.bottom() > avail.top() + max_height - 1:
        g.moveTop(max(avail.top(), avail.top() + max_height - g.height()))
    window.setGeometry(g)


def _set_normal_start_geometry(window: MainWindow) -> None:
    """Start as a normal framed window, centered on the active screen."""
    try:
        screen = QGuiApplication.screenAt(QCursor.pos())
    except Exception:
        screen = None
    if screen is None:
        screen = QGuiApplication.primaryScreen()
    if screen is None:
        return
    avail = QRect(screen.availableGeometry())
    if avail.width() <= 0 or avail.height() <= 0:
        return

    try:
        min_size = window.minimumSizeHint()
    except Exception:
        min_size = None

    max_w = min(avail.width(), max(900, int(avail.width() * 0.90)))
    max_h = min(avail.height(), max(620, int(avail.height() * 0.88)))
    if min_size is not None:
        max_w = min(avail.width(), max(min_size.width(), max_w))
        max_h = min(avail.height(), max(min_size.height(), max_h))
    w = min(1600, max_w)
    h = min(900, max_h)
    x = avail.x() + (avail.width() - w) // 2
    y = avail.y() + (avail.height() - h) // 2
    window.setGeometry(x, y, w, h)


def _force_normal_framed_window(window: MainWindow) -> None:
    """Hard-reset any stale fullscreen/borderless state."""
    window.setWindowFlag(Qt.FramelessWindowHint, False)
    window.setWindowFlag(Qt.Window, True)
    window.setWindowState(Qt.WindowNoState)
    window.showNormal()


class StartupSplashOverlay(QWidget):
    """Paints startup status in the same visual language as the splash art."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._percent = 0
        self._message = "Starting FL Atlas..."

    def set_progress(self, percent: int, message: str = "") -> None:
        self._percent = max(0, min(int(percent), 100))
        if message:
            self._message = str(message)
        self.update()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        try:
            self._paint_status_text(painter)
            self._paint_progress_bar(painter)
        finally:
            painter.end()

    def _paint_status_text(self, painter: QPainter) -> None:
        width = max(1, self.width())
        height = max(1, self.height())
        font = self._status_font()
        font.setPointSize(max(8, int(height * 0.035)))
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        rect = self.rect().adjusted(int(width * 0.18), int(height * 0.682), -int(width * 0.18), -int(height * 0.275))
        text = str(self._message or "").strip()
        painter.setPen(QColor(0, 10, 20, 180))
        painter.drawText(rect.adjusted(0, 1, 0, 1), Qt.AlignHCenter | Qt.AlignVCenter, text)
        painter.setPen(QColor(224, 246, 255, 235))
        painter.drawText(rect, Qt.AlignHCenter | Qt.AlignVCenter, text)

    @staticmethod
    def _status_font() -> QFont:
        families = {str(family).lower(): str(family) for family in QFontDatabase.families()}
        for name in ("Bahnschrift", "Orbitron", "Eurostile", "BankGothic Md BT", "Segoe UI", "Arial"):
            family = families.get(name.lower())
            if family:
                return QFont(family)

        fonts_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        for file_name in ("bahnschrift.ttf", "segoeui.ttf", "arial.ttf"):
            font_id = QFontDatabase.addApplicationFont(str(fonts_dir / file_name))
            if font_id < 0:
                continue
            loaded = QFontDatabase.applicationFontFamilies(font_id)
            if loaded:
                return QFont(str(loaded[0]))
        return QFontDatabase.systemFont(QFontDatabase.GeneralFont)

    def _paint_progress_bar(self, painter: QPainter) -> None:
        width = max(1.0, float(self.width()))
        height = max(1.0, float(self.height()))
        x_pos = width * 0.175
        y_pos = height * 0.862
        bar_width = width * 0.660
        bar_height = max(10.0, height * 0.038)
        bevel = bar_height * 1.15
        inner_margin = max(2.0, bar_height * 0.20)

        outer = QPainterPath()
        outer.moveTo(x_pos + bevel, y_pos)
        outer.lineTo(x_pos + bar_width - bevel, y_pos)
        outer.lineTo(x_pos + bar_width, y_pos + bar_height * 0.5)
        outer.lineTo(x_pos + bar_width - bevel, y_pos + bar_height)
        outer.lineTo(x_pos + bevel, y_pos + bar_height)
        outer.lineTo(x_pos, y_pos + bar_height * 0.5)
        outer.closeSubpath()

        glow = QColor(24, 190, 255, 70)
        painter.setBrush(Qt.NoBrush)
        for grow in (5.0, 3.0):
            pen = QPen(glow, grow)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.drawPath(outer)

        painter.setPen(QPen(QColor(57, 214, 255, 210), max(1.0, bar_height * 0.10)))
        painter.setBrush(QColor(4, 21, 38, 215))
        painter.drawPath(outer)

        inner_x = x_pos + bevel * 0.63
        inner_y = y_pos + inner_margin
        inner_w = bar_width - bevel * 1.26
        inner_h = bar_height - inner_margin * 2.0
        fill_w = max(0.0, inner_w * (float(self._percent) / 100.0))
        if fill_w <= 0.5:
            return

        segment_count = 36
        gap = max(1.0, width * 0.002)
        segment_w = (inner_w - (gap * (segment_count - 1))) / segment_count
        gradient = QLinearGradient(inner_x, inner_y, inner_x + max(1.0, fill_w), inner_y)
        gradient.setColorAt(0.0, QColor(33, 201, 236))
        gradient.setColorAt(0.62, QColor(78, 234, 255))
        gradient.setColorAt(1.0, QColor(184, 255, 255))
        painter.setPen(QPen(QColor(5, 93, 135, 180), 0.7))
        painter.setBrush(gradient)
        remaining = fill_w
        current_x = inner_x
        for _index in range(segment_count):
            draw_w = min(segment_w, remaining)
            if draw_w <= 0:
                break
            painter.drawRoundedRect(current_x, inner_y, draw_w, inner_h, inner_h * 0.18, inner_h * 0.18)
            remaining -= segment_w + gap
            current_x += segment_w + gap

        cap_x = inner_x + fill_w
        painter.setPen(QPen(QColor(165, 248, 255, 220), max(1.0, inner_h * 0.22)))
        painter.drawLine(int(cap_x), int(inner_y - 1), int(cap_x), int(inner_y + inner_h + 1))


class StartupSplashScreen(QSplashScreen):
    def __init__(self, pixmap: QPixmap):
        super().__init__(pixmap, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.SplashScreen)
        self._overlay = StartupSplashOverlay(self)
        self._overlay.setGeometry(self.rect())
        self._overlay.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._overlay.setGeometry(self.rect())

    def set_progress(self, percent: int, message: str = ""):
        self._overlay.set_progress(percent, message)
        QApplication.processEvents()


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(add_help=False)
    arg_parser.add_argument("--open-system", dest="open_system", default="")
    arg_parser.add_argument("--test-updater-zip", dest="test_updater_zip", default="")
    cli_args, qt_args = arg_parser.parse_known_args(sys.argv[1:])
    _set_windows_app_user_model_id()
    app = QApplication([sys.argv[0], *qt_args])
    app.setStyle("Fusion")
    app.setApplicationName("FL Atlas")
    app.setApplicationVersion(APP_VERSION)
    app.setProperty("dev_status_states", DEV_STATUS_STATES)
    app.setProperty("dev_status_by_nav", DEV_STATUS_BY_NAV)
    app.setProperty("updates_allow_prerelease_toggle", ALLOW_PRERELEASE_UPDATE_TOGGLE)
    app.setProperty("updates_default_check_prerelease", DEFAULT_CHECK_PRERELEASE)
    app.setProperty("isolated_system_window", bool(str(getattr(cli_args, "open_system", "") or "").strip()))
    _apply_startup_settings()
    cfg_runtime = Config()

    # App-Icon setzen (Taskleiste / Dock / Fenstertitel)
    _icon_dir = Path(__file__).resolve().parent / "fl_editor" / "images"
    app_icon = QIcon()
    ico_path = _icon_dir / "FLAtlas-Suite-Dreadnought-Front-Logo.ico"
    if ico_path.exists():
        app_icon.addFile(str(ico_path))
    for size in (16, 24, 32, 48, 64, 128, 256):
        app_icon.addFile(str(_icon_dir / f"FLAtlas-Suite-Dreadnought-Front-Logo-{size}.png"))
    app.setWindowIcon(app_icon)

    splash = None
    splash_path = _icon_dir / "Splash-Screen.png"
    if bool(cfg_runtime.get("settings.show_splash", True)) and splash_path.exists():
        splash_pix = QPixmap(str(splash_path))
        if not splash_pix.isNull():
            splash_pix = splash_pix.scaled(
                500,
                1400,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            splash = StartupSplashScreen(splash_pix)
            splash.show()
            splash.set_progress(6, "Initializing runtime")
            app.processEvents()

    def _startup_progress(percent: int, message: str):
        if splash is not None:
            splash.set_progress(percent, message)

    w = MainWindow(startup_progress_callback=_startup_progress)
    w.complete_startup()
    w.setWindowIcon(app_icon)
    open_system_path = str(getattr(cli_args, "open_system", "") or "").strip()
    if open_system_path:
        if splash is not None:
            splash.set_progress(97, "Opening system")
        w._startup_blocking_loads = True
        try:
            w._open_system_tab(open_system_path, new_tab=True)
        finally:
            w._startup_blocking_loads = False
    # Always start in normal window mode (with title bar/frame).
    _force_normal_framed_window(w)
    _set_normal_start_geometry(w)
    w.show()
    if splash is not None:
        splash.set_progress(100, "Ready")
        splash.finish(w)
    # Apply a second-pass hard reset after show (important after monitor hotplug changes).
    QTimer.singleShot(0, lambda: (_force_normal_framed_window(w), _fit_window_to_active_screen(w)))
    test_updater_zip = str(getattr(cli_args, "test_updater_zip", "") or "").strip()
    if test_updater_zip:
        QTimer.singleShot(250, lambda zp=test_updater_zip: w.start_local_zip_self_update_test(zp))
    w.schedule_startup_update_check(1400)
    sys.exit(app.exec())
