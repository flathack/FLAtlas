from __future__ import annotations

from types import SimpleNamespace

from fl_editor.flight_mode_editor_seed import selection_seed_state


def test_selection_seed_state_returns_none_without_selection():
    assert selection_seed_state(
        selected_item=None,
        parse_position=lambda value: (0.0, 0.0, 0.0),
        seed_builder=lambda pos: {"ship_pos_xyz": pos},
    ) is None


def test_selection_seed_state_ignores_system_nodes():
    item = SimpleNamespace(sys_path="li01.ini", data={"pos": "1,2,3"})

    assert selection_seed_state(
        selected_item=item,
        parse_position=lambda value: (1.0, 2.0, 3.0),
        seed_builder=lambda pos: {"ship_pos_xyz": pos},
    ) is None


def test_selection_seed_state_builds_seed_from_selected_position():
    item = SimpleNamespace(data={"pos": "1,2,3"})

    state = selection_seed_state(
        selected_item=item,
        parse_position=lambda value: (1.0, 2.0, 3.0) if value == "1,2,3" else None,
        seed_builder=lambda pos: None if pos is None else {"ship_pos_xyz": pos, "yaw": 0.0},
    )

    assert state == {"ship_pos_xyz": (1.0, 2.0, 3.0), "yaw": 0.0}


def test_selection_seed_state_returns_none_on_parse_error():
    item = SimpleNamespace(data={"pos": "bad"})

    state = selection_seed_state(
        selected_item=item,
        parse_position=lambda value: (_ for _ in ()).throw(ValueError("bad pos")),
        seed_builder=lambda pos: {"ship_pos_xyz": pos},
    )

    assert state is None
