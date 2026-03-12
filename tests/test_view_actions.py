from __future__ import annotations

from fl_editor.view_actions import non_universe_toolbar_state


def test_non_universe_toolbar_state_hides_universe_actions():
    assert non_universe_toolbar_state() == {
        "new_system_visible": False,
        "uni_save_visible": False,
        "uni_undo_visible": False,
        "uni_delete_visible": False,
        "ids_scan_visible": False,
        "ids_import_visible": False,
        "mode_text": "",
    }
