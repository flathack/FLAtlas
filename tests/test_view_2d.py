from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, Qt
import pytest

from fl_editor.models import SolarObject, UniverseSystem
from fl_editor.view_2d import SystemView


def test_pan_by_delta_uses_scene_center_for_smooth_panning(qapp, monkeypatch):
    view = SystemView()
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


def test_placement_mode_can_still_select_objects_when_allowed(qapp, monkeypatch):
    view = SystemView()
    selected: list[object] = []
    background: list[QPointF] = []
    obj = SolarObject(
        {
            "nickname": "test_object",
            "archetype": "space_police01",
            "pos": "0,0,0",
            "_entries": [("nickname", "test_object"), ("archetype", "space_police01"), ("pos", "0,0,0")],
        },
        1.0,
    )
    view.object_selected.connect(lambda item: selected.append(item))
    view.background_clicked.connect(lambda pos: background.append(pos))
    monkeypatch.setattr(view, "_pick_interactive_item", lambda _pos: obj)
    monkeypatch.setattr(view, "mapToScene", lambda _pos: QPointF(12.0, 34.0))
    view.set_placement_passthrough(True, allow_item_clicks=True)

    class _Event:
        def pos(self):
            return QPoint(0, 0)

        def modifiers(self):
            return Qt.NoModifier

        def accept(self):
            pass

    view._handle_left_click(_Event())

    assert selected == [obj]
    assert background == []


def test_solar_object_hover_pen_is_cosmetic_and_bounding_rect_has_padding(qapp):
    obj = SolarObject(
        {
            "nickname": "test_station",
            "archetype": "space_police01",
            "pos": "0,0,0",
            "_entries": [("nickname", "test_station"), ("archetype", "space_police01"), ("pos", "0,0,0")],
        },
        1.0,
    )

    pen = obj._hover_pen()
    rect = obj.rect()
    bounds = obj.boundingRect()

    assert pen.isCosmetic()
    assert pen.widthF() == pytest.approx(2.0)
    assert bounds.left() < rect.left()
    assert bounds.right() > rect.right()
    assert bounds.top() < rect.top()
    assert bounds.bottom() > rect.bottom()


def test_universe_system_bounding_rect_includes_halo_and_hover_padding(qapp):
    system = UniverseSystem("Li01", "Universe\\Systems\\LI01\\LI01.ini", (0.0, 0.0), 1.0)

    bounds = system.boundingRect()

    assert bounds.width() > system.rect().width()
    assert bounds.height() > system.rect().height()
    assert bounds.left() <= -(system._uni_halo + system._HOVER_OUTLINE_PADDING)
