from __future__ import annotations

from fl_editor.view_3d_flight_ui import flight_mode_toggle_state, flight_visual_entity_state


def test_flight_mode_toggle_state_for_enable_and_disable():
    enabled_state = flight_mode_toggle_state(enabled=True)
    assert enabled_state == {
        "focus_container": True,
        "start_flight": True,
        "stop_flight": False,
        "help_overlay_visible": False,
        "reset_dust_distribution": True,
        "reposition_overlays": True,
        "sync_orbit_from_camera": False,
        "clear_flight_visuals": False,
    }

    disabled_state = flight_mode_toggle_state(enabled=False)
    assert disabled_state == {
        "focus_container": False,
        "start_flight": False,
        "stop_flight": True,
        "help_overlay_visible": False,
        "reset_dust_distribution": False,
        "reposition_overlays": False,
        "sync_orbit_from_camera": True,
        "clear_flight_visuals": True,
    }


def test_flight_visual_entity_state_for_empty_and_active_snapshots():
    empty_state = flight_visual_entity_state(has_snapshot=False, has_ship_entity=True, dust_count=2)
    assert empty_state == {
        "ship_enabled": False,
        "dust_enabled": [False, False],
        "charge_bar_visible": False,
        "update_ship_pose": False,
        "update_space_dust": False,
        "update_charge_bar": False,
    }

    active_state = flight_visual_entity_state(has_snapshot=True, has_ship_entity=True, dust_count=2)
    assert active_state == {
        "ship_enabled": True,
        "dust_enabled": [True, True],
        "charge_bar_visible": False,
        "update_ship_pose": True,
        "update_space_dust": True,
        "update_charge_bar": True,
    }
