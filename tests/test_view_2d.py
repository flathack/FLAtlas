from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF
import pytest

from fl_editor.view_2d import SystemView


def test_pan_by_delta_uses_scene_center_for_smooth_panning(qtbot, monkeypatch):
    view = SystemView()
    qtbot.addWidget(view)
    view.resize(200, 100)
    view.show()

    centered: list[QPointF] = []
    monkeypatch.setattr(view, "mapToScene", lambda point: QPointF(float(point.x()), float(point.y())))
    monkeypatch.setattr(view, "centerOn", lambda point: centered.append(QPointF(point)))
    view._pan_start = QPointF(10.0, 20.0)

    view._pan_by_delta(QPointF(3.0, 4.0))

    expected_center = QPointF(float(view.viewport().rect().center().x()) - 3.0, float(view.viewport().rect().center().y()) - 4.0)
    assert centered == [expected_center]


def test_wheel_zoom_factor_uses_gentler_step_curve():
    assert SystemView._zoom_factor_for_wheel_delta(0) == 1.0
    assert SystemView._zoom_factor_for_wheel_delta(120) == pytest.approx(1.08)
    assert SystemView._zoom_factor_for_wheel_delta(-120) == pytest.approx(1.0 / 1.08)
    assert SystemView._zoom_factor_for_wheel_delta(60) == pytest.approx(1.08 ** 0.5)
