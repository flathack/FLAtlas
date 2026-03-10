from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtGui import QVector3D

from fl_editor.flight_mode_editor_context import (
    autopilot_target_context,
    editor_target_context,
    selected_target_context,
)


def test_selected_target_context_returns_name_and_distance():
    item = SimpleNamespace(nickname="li01_planet")

    def item_world_pos(_item):
        return QVector3D(3.0, 4.0, 0.0)

    state = selected_target_context(
        selected_item=item,
        ship_pos=QVector3D(0.0, 0.0, 0.0),
        item_world_pos=item_world_pos,
    )

    assert state == {"name": "li01_planet", "distance": 5.0}


def test_selected_target_context_returns_empty_when_missing_position():
    state = selected_target_context(
        selected_item=SimpleNamespace(nickname="missing"),
        ship_pos=QVector3D(0.0, 0.0, 0.0),
        item_world_pos=lambda _item: None,
    )

    assert state == {"name": "", "distance": None}


def test_autopilot_target_context_returns_distance_in_autopilot_mode():
    state = autopilot_target_context(
        mode="AUTOPILOT",
        autopilot_mode="AUTOPILOT",
        auto_target=SimpleNamespace(),
        target_name="dock_ring",
        ship_pos=QVector3D(0.0, 0.0, 0.0),
        item_world_pos=lambda _item: QVector3D(0.0, 6.0, 8.0),
    )

    assert state == {"name": "dock_ring", "distance": 10.0}


def test_autopilot_target_context_ignores_distance_outside_autopilot_mode():
    state = autopilot_target_context(
        mode="NORMAL",
        autopilot_mode="AUTOPILOT",
        auto_target=SimpleNamespace(),
        target_name="dock_ring",
        ship_pos=QVector3D(0.0, 0.0, 0.0),
        item_world_pos=lambda _item: QVector3D(0.0, 6.0, 8.0),
    )

    assert state == {"name": "dock_ring", "distance": None}


def test_editor_target_context_combines_selection_and_autopilot():
    selected_item = SimpleNamespace(nickname="planet")
    auto_target = SimpleNamespace(nickname="dock")

    def item_world_pos(item):
        if item is selected_item:
            return QVector3D(3.0, 4.0, 0.0)
        if item is auto_target:
            return QVector3D(0.0, 0.0, 10.0)
        return None

    state = editor_target_context(
        selected_item=selected_item,
        mode="AUTOPILOT",
        autopilot_mode="AUTOPILOT",
        auto_target=auto_target,
        target_name="dock_ring",
        ship_pos=QVector3D(0.0, 0.0, 0.0),
        item_world_pos=item_world_pos,
    )

    assert state == {
        "selection": {"name": "planet", "distance": 5.0},
        "autopilot": {"name": "dock_ring", "distance": 10.0},
    }
