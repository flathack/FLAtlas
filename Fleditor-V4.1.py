#!/usr/bin/env python3
"""
Freelancer System Editor  –  Version 4.1

Zeigt Freelancer-Systemdateien (INI) als interaktive 2-D/3-D-Karte an.
Objekte/Zonen können verschoben und bearbeitet werden; Änderungen lassen
sich zurück in die Datei schreiben.

Dieses Skript dient als Einstiegspunkt.
Die gesamte Logik befindet sich im Paket ``fl_editor``.
"""
import sys
from PySide6.QtWidgets import QApplication
from fl_editor.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
