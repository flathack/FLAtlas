from __future__ import annotations

from types import SimpleNamespace

from fl_editor.flight_mode_viewport_input import viewport_mouse_offset_state


def test_viewport_mouse_offset_state_passes_viewport_size_to_builder():
    calls: list[tuple[tuple[int, int] | None, tuple[float, float], bool]] = []

    def offset_builder(*, viewport_size, mouse_pos_xy, mouse_flight_active):
        calls.append((viewport_size, mouse_pos_xy, mouse_flight_active))
        return (0.1, 0.2, 0.3)

    viewport = SimpleNamespace(width=lambda: 1000, height=lambda: 800)
    state = viewport_mouse_offset_state(
        viewport=viewport,
        mouse_pos_xy=(123.0, 456.0),
        mouse_flight_active=True,
        offset_builder=offset_builder,
    )

    assert state == (0.1, 0.2, 0.3)
    assert calls == [((1000, 800), (123.0, 456.0), True)]


def test_viewport_mouse_offset_state_handles_missing_viewport():
    calls: list[tuple[tuple[int, int] | None, tuple[float, float], bool]] = []

    def offset_builder(*, viewport_size, mouse_pos_xy, mouse_flight_active):
        calls.append((viewport_size, mouse_pos_xy, mouse_flight_active))
        return (0.0, 0.0, 0.0)

    state = viewport_mouse_offset_state(
        viewport=None,
        mouse_pos_xy=(0.0, 0.0),
        mouse_flight_active=False,
        offset_builder=offset_builder,
    )

    assert state == (0.0, 0.0, 0.0)
    assert calls == [(None, (0.0, 0.0), False)]
