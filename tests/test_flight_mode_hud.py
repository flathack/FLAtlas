from __future__ import annotations

from fl_editor.flight_mode_hud import (
    build_hud_bundle,
    build_hud_snapshot,
    build_overlay_text,
    charge_progress,
    ship_tilt_degrees,
)


def test_charge_progress_and_ship_tilt_are_clamped():
    assert charge_progress(5.0, 4.0) == 1.0
    assert round(ship_tilt_degrees(1.0), 2) == 9.17


def test_build_hud_snapshot_contains_expected_fields():
    snap = build_hud_snapshot(
        mode="AUTOPILOT",
        speed=120.0,
        max_speed=80.0,
        ship_pos_xyz=(1.0, 2.0, 3.0),
        yaw=1.0,
        pitch=0.5,
        pitch_rate=0.4,
        forward_xyz=(0.0, 0.0, 1.0),
        sel_name="target_a",
        sel_dist=250.0,
        charge_elapsed=2.0,
        cruise_charge_time=4.0,
        auto_cruise_charging=True,
        orbit_cam_active=True,
        error="",
        autopilot_mode="AUTOPILOT",
        cruise_charging_mode="CRUISE_CHARGING",
    )

    assert snap["mode"] == "AUTOPILOT"
    assert snap["target_name"] == "target_a"
    assert snap["target_distance"] == 250.0
    assert snap["charge_progress"] == 0.5
    assert snap["charge_active"] is True
    assert snap["orbit_cam_active"] is True


def test_build_overlay_text_includes_charge_and_target_lines():
    text = build_overlay_text(
        mode="AUTOPILOT",
        speed=120.0,
        max_speed=80.0,
        ship_pos_xyz=(1.0, 2.0, 3.0),
        selection_name="sel_a",
        selection_distance=300.0,
        charge_elapsed=2.0,
        cruise_charge_time=4.0,
        auto_cruise_charging=True,
        auto_cruise_active=True,
        auto_target_name="auto_a",
        auto_target_distance=1234.0,
        autopilot_mode="AUTOPILOT",
        cruise_charging_mode="CRUISE_CHARGING",
    )

    assert "Flight | AUTOPILOT" in text
    assert "Target: sel_a | Dist: 300.0 m" in text
    assert "Auto Cruise Charge: 50%" in text
    assert "Auto Cruise: ACTIVE" in text
    assert "Target: auto_a (1234 m)" in text


def test_build_hud_bundle_shares_target_context_for_snapshot_and_overlay():
    bundle = build_hud_bundle(
        mode="AUTOPILOT",
        speed=120.0,
        max_speed=80.0,
        ship_pos_xyz=(1.0, 2.0, 3.0),
        yaw=1.0,
        pitch=0.5,
        pitch_rate=0.4,
        forward_xyz=(0.0, 0.0, 1.0),
        target_context={
            "selection": {"name": "sel_a", "distance": 300.0},
            "autopilot": {"name": "auto_a", "distance": 1234.0},
        },
        charge_elapsed=2.0,
        cruise_charge_time=4.0,
        auto_cruise_charging=True,
        auto_cruise_active=True,
        orbit_cam_active=True,
        error="boom",
        autopilot_mode="AUTOPILOT",
        cruise_charging_mode="CRUISE_CHARGING",
    )

    assert bundle["snapshot"]["target_name"] == "sel_a"
    assert bundle["snapshot"]["target_distance"] == 300.0
    assert bundle["snapshot"]["error"] == "boom"
    assert "Target: sel_a | Dist: 300.0 m" in bundle["overlay_text"]
    assert "Target: auto_a (1234 m)" in bundle["overlay_text"]
