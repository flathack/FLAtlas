#!/usr/bin/env python3
"""
FL Atlas - Freelancer System Editor
Autor: Steven

Dieses Skript dient als Einstiegspunkt.
Die gesamte Logik befindet sich im Paket ``fl_editor``.
"""

APP_VERSION = "0.7.0"
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

from PySide6.QtWidgets import QApplication, QLabel, QProgressBar, QSplashScreen, QVBoxLayout, QWidget
from PySide6.QtCore import QRect, QTimer, Qt
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtGui import QIcon, QPixmap
from fl_editor.config import Config
from fl_editor.dev_status import default_dev_status_by_nav, default_dev_status_states
from fl_editor.i18n import available_languages, set_language
from fl_editor.themes import THEME_NAMES
from fl_editor.main_window import MainWindow

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


class StartupSplashScreen(QSplashScreen):
    def __init__(self, pixmap: QPixmap):
        super().__init__(pixmap, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.SplashScreen)
        overlay = QWidget(self)
        overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        overlay.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(overlay)
        layout.setContentsMargins(22, max(22, pixmap.height() - 82), 22, 18)
        layout.setSpacing(8)
        self._status_lbl = QLabel("Starting FL Atlas…", overlay)
        self._status_lbl.setStyleSheet(
            "color:#e7f4ff; font-size:10pt; font-weight:600; background:transparent;"
        )
        layout.addWidget(self._status_lbl)
        self._progress = QProgressBar(overlay)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFormat("%p%")
        self._progress.setFixedHeight(12)
        self._progress.setStyleSheet(
            """
            QProgressBar {
                color: #eff8ff;
                background: rgba(10, 28, 48, 0.55);
                border: 1px solid rgba(120, 190, 255, 0.35);
                border-radius: 6px;
                text-align: center;
                font-weight: 700;
            }
            QProgressBar::chunk {
                border-radius: 5px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1686ff,
                    stop:0.55 #31b4ff,
                    stop:1 #75dcff
                );
            }
            """
        )
        layout.addWidget(self._progress)
        overlay.setGeometry(self.rect())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        for child in self.findChildren(QWidget):
            if child.parent() is self:
                child.setGeometry(self.rect())

    def set_progress(self, percent: int, message: str = ""):
        self._progress.setValue(max(0, min(int(percent), 100)))
        if message:
            self._status_lbl.setText(str(message))
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
