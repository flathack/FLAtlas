from __future__ import annotations

from fl_editor.sidebar_layout import left_sidebar_width_state, normalized_browser_compact_width


def test_normalized_browser_compact_width_clamps_and_falls_back():
    assert normalized_browser_compact_width("bad") == 240
    assert normalized_browser_compact_width(100) == 210
    assert normalized_browser_compact_width(900) == 620


def test_left_sidebar_width_state_for_non_browser_resets_limits():
    state = left_sidebar_width_state(
        is_browser=False,
        compact_width=300,
        splitter_sizes=[300, 700, 250],
    )

    assert state == {
        "min_width": 0,
        "max_width": 16777215,
        "splitter_sizes": None,
    }


def test_left_sidebar_width_state_for_browser_computes_splitter_sizes():
    state = left_sidebar_width_state(
        is_browser=True,
        compact_width=280,
        splitter_sizes=[240, 800, 260],
    )

    assert state["min_width"] == 280
    assert state["max_width"] == 280
    assert state["splitter_sizes"] == [280, 769, 251]
