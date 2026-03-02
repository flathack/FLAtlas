#!/usr/bin/env python3
"""
FL Atlas  –  Freelancer System Editor

Autor: Steven

Zeigt Freelancer-Systemdateien (INI) als interaktive 2-D/3-D-Karte an.
Objekte/Zonen können verschoben und bearbeitet werden; Änderungen lassen
sich zurück in die Datei schreiben.

Dieses Skript dient als Einstiegspunkt.
Die gesamte Logik befindet sich im Paket ``fl_editor``.
"""

APP_VERSION = "0.6.1"
__version__ = APP_VERSION
__author__ = "Steven"
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from fl_editor.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("FL Atlas")
    app.setApplicationVersion(APP_VERSION)

    # App-Icon setzen (Taskleiste / Dock / Fenstertitel)
    _icon_dir = Path(__file__).resolve().parent / "fl_editor" / "images"
    app_icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        app_icon.addFile(str(_icon_dir / f"FLAtlas-Logo-{size}.png"))
    app.setWindowIcon(app_icon)

    w = MainWindow()
    w.show()
    sys.exit(app.exec())
