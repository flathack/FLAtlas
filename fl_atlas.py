#!/usr/bin/env python3
"""
FL Atlas - Freelancer System Editor
Autor: Steven

Dieses Skript dient als Einstiegspunkt.
Die gesamte Logik befindet sich im Paket ``fl_editor``.
"""

APP_VERSION = "0.6.2.4"
__version__ = APP_VERSION
__author__ = "Steven"
import os
import sys
from pathlib import Path

# Qt3D kann auf manchen Windows-Setups den RHI-Renderer nicht laden.
# Fallback auf OpenGL nur dann, wenn der Nutzer nichts explizit gesetzt hat.
if sys.platform.startswith("win"):
    os.environ.setdefault("QT3D_RENDERER", "opengl")

from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtCore import QRect, QTimer, Qt
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtGui import QIcon, QPixmap
from fl_editor.config import Config
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
DEV_STATUS_STATES = [
    {"id": "pre_alpha", "label": "Pre Alpha", "description": "Very buggy, major changes expected."},
    {"id": "alpha", "label": "Alpha", "description": "Core exists, still unstable and incomplete."},
    {"id": "beta", "label": "Beta", "description": "Feature complete enough, testing and polish ongoing."},
    {"id": "release_candidate", "label": "Release Candidate", "description": "Near release, only critical fixes expected."},
    {"id": "gold", "label": "Gold", "description": "Release quality and considered stable."},
]

# Status je Haupt-Navigationspunkt.
DEV_STATUS_BY_NAV = {
    "universe": "beta",
    "trade_routes": "beta",
    "name_editor": "beta",
    "mod_manager": "beta",
    "npc_editor": "alpha",
    "rumor_editor": "alpha",
    "news_editor": "alpha",
    "settings": "beta",
}

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
    # Never exceed usable display area and keep the window fully on-screen.
    if g.width() > avail.width() or g.height() > avail.height():
        g.setSize(avail.size())
    if g.left() < avail.left():
        g.moveLeft(avail.left())
    if g.top() < avail.top():
        g.moveTop(avail.top())
    if g.right() > avail.right():
        g.moveRight(avail.right())
    if g.bottom() > avail.bottom():
        g.moveBottom(avail.bottom())
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

    max_w = max(900, int(avail.width() * 0.92))
    max_h = max(620, int(avail.height() * 0.92))
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


if __name__ == "__main__":
    _set_windows_app_user_model_id()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("FL Atlas")
    app.setApplicationVersion(APP_VERSION)
    app.setProperty("dev_status_states", DEV_STATUS_STATES)
    app.setProperty("dev_status_by_nav", DEV_STATUS_BY_NAV)
    app.setProperty("updates_allow_prerelease_toggle", ALLOW_PRERELEASE_UPDATE_TOGGLE)
    app.setProperty("updates_default_check_prerelease", DEFAULT_CHECK_PRERELEASE)
    _apply_startup_settings()
    cfg_runtime = Config()

    # App-Icon setzen (Taskleiste / Dock / Fenstertitel)
    _icon_dir = Path(__file__).resolve().parent / "fl_editor" / "images"
    app_icon = QIcon()
    ico_path = _icon_dir / "FLAtlas-Logo.ico"
    if ico_path.exists():
        app_icon.addFile(str(ico_path))
    for size in (16, 24, 32, 48, 64, 128, 256):
        app_icon.addFile(str(_icon_dir / f"FLAtlas-Logo-{size}.png"))
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
            splash = QSplashScreen(
                splash_pix,
                Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.SplashScreen,
            )
            splash.show()
            app.processEvents()

    w = MainWindow()
    w.setWindowIcon(app_icon)
    # Always start in normal window mode (with title bar/frame).
    _force_normal_framed_window(w)
    _set_normal_start_geometry(w)
    w.show()
    if splash is not None:
        splash.finish(w)
    # Apply a second-pass hard reset after show (important after monitor hotplug changes).
    QTimer.singleShot(0, lambda: (_force_normal_framed_window(w), _fit_window_to_active_screen(w)))
    sys.exit(app.exec())
