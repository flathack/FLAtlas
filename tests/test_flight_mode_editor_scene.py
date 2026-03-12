from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtGui import QVector3D

from fl_editor.flight_mode_editor_scene import (
    autopilot_selection_from_editor,
    tradelane_selection_from_editor,
)


def test_autopilot_selection_from_editor_returns_target_state():
    target = SimpleNamespace(nickname="planet_li01", data={"pos": "0,0,0"})
    editor = SimpleNamespace(_selected=target)

    state = autopilot_selection_from_editor(editor=editor, autopilot_mode="AUTOPILOT")

    assert state == {
        "target": target,
        "target_name": "planet_li01",
        "mode": "AUTOPILOT",
    }


def test_autopilot_selection_from_editor_returns_none_without_valid_selection():
    editor = SimpleNamespace(_selected=None)

    assert autopilot_selection_from_editor(editor=editor, autopilot_mode="AUTOPILOT") is None


def test_tradelane_selection_from_editor_returns_lane_state():
    lane_a = SimpleNamespace(
        nickname="lane_a",
        type="object",
        data={"pos": "0,0,0", "goto": "lane_b", "archetype": "trade_lane_ring"},
    )
    lane_b = SimpleNamespace(
        nickname="lane_b",
        type="object",
        data={"pos": "1000,0,0", "prev_ring": "lane_a", "next_ring": ""},
    )
    editor = SimpleNamespace(_selected=lane_a, _objects=[lane_a, lane_b])

    state = tradelane_selection_from_editor(
        editor=editor,
        ship_pos=QVector3D(0.0, 0.0, -1000.0),
        yaw=0.0,
        pitch=0.0,
        dock_radius=450.0,
        tradelane_speed=2500.0,
        forward_xyz=(0.0, 0.0, 1.0),
    )

    assert state is not None
    assert state["status"] in {"docking", "active", "invalid_path"}
    assert len(state["lane_path"]) >= 1


def test_tradelane_selection_from_editor_returns_none_for_non_tradelane():
    editor = SimpleNamespace(_selected=SimpleNamespace(type="zone", data={}), _objects=[])

    assert (
        tradelane_selection_from_editor(
            editor=editor,
            ship_pos=QVector3D(),
            yaw=0.0,
            pitch=0.0,
            dock_radius=450.0,
            tradelane_speed=2500.0,
            forward_xyz=(0.0, 0.0, 1.0),
        )
        is None
    )
