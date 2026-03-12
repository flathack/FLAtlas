"""Helpers for common toolbar/action state in view switches."""

from __future__ import annotations


def non_universe_toolbar_state() -> dict[str, object]:
    return {
        "new_system_visible": False,
        "uni_save_visible": False,
        "uni_undo_visible": False,
        "uni_delete_visible": False,
        "ids_scan_visible": False,
        "ids_import_visible": False,
        "mode_text": "",
    }
