from __future__ import annotations

from fl_editor.dev_status import (
    build_dev_status_legend_lines,
    default_dev_status_states,
    dev_status_nav_items,
    normalize_dev_status_config,
)


class _FakeApp:
    def __init__(self, mapping):
        self._mapping = mapping

    def property(self, key):
        return self._mapping.get(key)


def test_default_states_and_nav_items_are_defined():
    assert default_dev_status_states()
    assert ("mod_manager", "dev_status.nav.mod_manager") in dev_status_nav_items()


def test_normalize_dev_status_config_filters_invalid_rows():
    app = _FakeApp(
        {
            "dev_status_states": [
                {"id": "alpha", "label": "Alpha", "description": "Ready for testing"},
                {"id": "", "label": "Broken"},
                "ignored",
            ],
            "dev_status_by_nav": {"Universe": "BETA", "": "ignored"},
        }
    )

    states, status_by_nav = normalize_dev_status_config(app)

    assert states == [{"id": "alpha", "label": "Alpha", "description": "Ready for testing"}]
    assert status_by_nav == {"universe": "beta"}


def test_build_dev_status_legend_lines_skips_empty_labels():
    lines = build_dev_status_legend_lines(
        [
            {"id": "alpha", "label": "Alpha", "description": "Core exists"},
            {"id": "ghost", "label": "", "description": "ignored"},
        ]
    )

    assert lines == ["- Alpha: Core exists"]
