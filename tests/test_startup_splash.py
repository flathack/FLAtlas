from __future__ import annotations

from PySide6.QtGui import QColor, QPixmap

from fl_atlas import StartupSplashScreen


def test_startup_splash_overlay_clamps_progress_and_renders(qapp):
    pixmap = QPixmap(500, 281)
    pixmap.fill(QColor(4, 12, 24))
    splash = StartupSplashScreen(pixmap)

    splash.set_progress(142, "Loading Freelancer data")

    overlay = splash._overlay
    assert overlay._percent == 100
    assert overlay._message == "Loading Freelancer data"

    rendered = QPixmap(splash.size())
    splash.render(rendered)

    assert not rendered.isNull()
