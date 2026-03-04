#!/usr/bin/env python3
"""
FL Atlas - Freelancer System Editor

Autor: Steven

Zeigt Freelancer-Systemdateien (INI) als interaktive 2-D/3-D-Karte an.
Objekte/Zonen können verschoben und bearbeitet werden; Änderungen lassen
sich zurück in die Datei schreiben.

Dieses Skript dient als Einstiegspunkt.
Die gesamte Logik befindet sich im Paket ``fl_editor``.
"""

APP_VERSION = "0.6.2.1"
__version__ = APP_VERSION
__author__ = "Steven"
import os
import sys
from pathlib import Path

# Qt3D kann auf manchen Windows-Setups den RHI-Renderer nicht laden.
# Fallback auf OpenGL nur dann, wenn der Nutzer nichts explizit gesetzt hat.
if sys.platform.startswith("win"):
    os.environ.setdefault("QT3D_RENDERER", "opengl")

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from fl_editor.config import Config
from fl_editor.i18n import available_languages, set_language
from fl_editor.themes import THEME_NAMES
from fl_editor.main_window import MainWindow

# ---------------------------------------------------------------------------
# Startvorgaben (hier direkt anpassen)
# ---------------------------------------------------------------------------
# True: Startsprache/-theme werden bei jedem Start in die Config geschrieben.
# False: Nutzer-Konfiguration bleibt unverändert.
FORCE_STARTUP_SETTINGS = False

# Gültige Sprache: siehe available_languages() / translations.json
STARTUP_LANGUAGE = "en"

# Gültiges Theme: founder, dark, light, xp, custom
STARTUP_THEME = "dark"


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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("FL Atlas")
    app.setApplicationVersion(APP_VERSION)
    _apply_startup_settings()

    # App-Icon setzen (Taskleiste / Dock / Fenstertitel)
    _icon_dir = Path(__file__).resolve().parent / "fl_editor" / "images"
    app_icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        app_icon.addFile(str(_icon_dir / f"FLAtlas-Logo-{size}.png"))
    app.setWindowIcon(app_icon)

    w = MainWindow()
    w.showMaximized()
    sys.exit(app.exec())
