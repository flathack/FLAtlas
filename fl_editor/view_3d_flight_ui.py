from __future__ import annotations


def flight_mode_toggle_state(*, enabled: bool) -> dict[str, object]:
    if enabled:
        return {
            "focus_container": True,
            "start_flight": True,
            "stop_flight": False,
            "help_overlay_visible": False,
            "reset_dust_distribution": True,
            "reposition_overlays": True,
            "sync_orbit_from_camera": False,
            "clear_flight_visuals": False,
        }
    return {
        "focus_container": False,
        "start_flight": False,
        "stop_flight": True,
        "help_overlay_visible": False,
        "reset_dust_distribution": False,
        "reposition_overlays": False,
        "sync_orbit_from_camera": True,
        "clear_flight_visuals": True,
    }


def flight_visual_entity_state(*, has_snapshot: bool, has_ship_entity: bool, dust_count: int) -> dict[str, object]:
    if not has_snapshot:
        return {
            "ship_enabled": bool(False if has_ship_entity else False),
            "dust_enabled": [False] * max(0, int(dust_count)),
            "charge_bar_visible": False,
            "update_ship_pose": False,
            "update_space_dust": False,
            "update_charge_bar": False,
        }
    return {
        "ship_enabled": bool(has_ship_entity),
        "dust_enabled": [True] * max(0, int(dust_count)),
        "charge_bar_visible": False,
        "update_ship_pose": bool(has_ship_entity),
        "update_space_dust": dust_count > 0,
        "update_charge_bar": True,
    }
