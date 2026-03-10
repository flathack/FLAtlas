from __future__ import annotations

import math

from fl_editor.flight_mode_mode_paths import (
    autopilot_motion_state,
    tradelane_docking_state,
    tradelane_start_state,
    tradelane_travel_state,
)


def test_autopilot_motion_state_marks_invalid_and_arrival():
    invalid = autopilot_motion_state(
        dt=0.1,
        ship_pos_xyz=(0.0, 0.0, 0.0),
        target_pos_xyz=None,
        yaw=0.0,
        pitch=0.0,
        speed=20.0,
        arrival_radius=100.0,
        auto_cruise_distance=9000.0,
        cruise_charge_time=4.0,
        cruise_speed=300.0,
        max_speed=80.0,
        accel=90.0,
        brake=160.0,
        yaw_rate_max=1.0,
        pitch_rate_max=1.0,
        auto_cruise_charging=False,
        auto_cruise_active=False,
        charge_elapsed=0.0,
    )
    arrived = autopilot_motion_state(
        dt=0.1,
        ship_pos_xyz=(0.0, 0.0, 0.0),
        target_pos_xyz=(10.0, 0.0, 0.0),
        yaw=0.0,
        pitch=0.0,
        speed=20.0,
        arrival_radius=100.0,
        auto_cruise_distance=9000.0,
        cruise_charge_time=4.0,
        cruise_speed=300.0,
        max_speed=80.0,
        accel=90.0,
        brake=160.0,
        yaw_rate_max=1.0,
        pitch_rate_max=1.0,
        auto_cruise_charging=False,
        auto_cruise_active=False,
        charge_elapsed=0.0,
    )

    assert invalid["status"] == "invalid_target"
    assert arrived["status"] == "arrived"


def test_autopilot_motion_state_charges_and_limits_speed_near_arrival():
    charging = autopilot_motion_state(
        dt=1.0,
        ship_pos_xyz=(0.0, 0.0, 0.0),
        target_pos_xyz=(0.0, 0.0, 10000.0),
        yaw=0.0,
        pitch=0.0,
        speed=10.0,
        arrival_radius=260.0,
        auto_cruise_distance=9000.0,
        cruise_charge_time=4.0,
        cruise_speed=300.0,
        max_speed=80.0,
        accel=90.0,
        brake=160.0,
        yaw_rate_max=1.0,
        pitch_rate_max=1.0,
        auto_cruise_charging=False,
        auto_cruise_active=False,
        charge_elapsed=0.0,
    )
    active = autopilot_motion_state(
        dt=1.0,
        ship_pos_xyz=(0.0, 0.0, 0.0),
        target_pos_xyz=(0.0, 0.0, 10000.0),
        yaw=0.0,
        pitch=0.0,
        speed=80.0,
        arrival_radius=260.0,
        auto_cruise_distance=9000.0,
        cruise_charge_time=4.0,
        cruise_speed=300.0,
        max_speed=80.0,
        accel=90.0,
        brake=160.0,
        yaw_rate_max=1.0,
        pitch_rate_max=1.0,
        auto_cruise_charging=True,
        auto_cruise_active=False,
        charge_elapsed=3.5,
    )
    slowing = autopilot_motion_state(
        dt=1.0,
        ship_pos_xyz=(0.0, 0.0, 0.0),
        target_pos_xyz=(0.0, 0.0, 300.0),
        yaw=0.0,
        pitch=0.0,
        speed=300.0,
        arrival_radius=100.0,
        auto_cruise_distance=9000.0,
        cruise_charge_time=4.0,
        cruise_speed=300.0,
        max_speed=80.0,
        accel=90.0,
        brake=160.0,
        yaw_rate_max=1.0,
        pitch_rate_max=1.0,
        auto_cruise_charging=False,
        auto_cruise_active=True,
        charge_elapsed=1.0,
    )

    assert charging["status"] == "continue"
    assert charging["auto_cruise_charging"] is True
    assert round(float(charging["speed"]), 1) == 80.0
    assert active["auto_cruise_active"] is True
    assert active["auto_cruise_charging"] is False
    assert round(float(active["speed"]), 1) == 170.0
    assert slowing["auto_cruise_active"] is False
    assert round(float(slowing["target_speed"]), 1) == 80.0
    assert round(float(slowing["speed"]), 1) == 140.0


def test_tradelane_start_state_switches_between_docking_and_active():
    docking = tradelane_start_state(
        lane_points_xyz=[(1000.0, 0.0, 0.0), (2000.0, 0.0, 0.0)],
        ship_pos_xyz=(0.0, 0.0, 0.0),
        forward_xyz=(0.0, 0.0, 1.0),
        dock_radius=450.0,
        tradelane_speed=2500.0,
    )
    active = tradelane_start_state(
        lane_points_xyz=[(100.0, 0.0, 0.0), (200.0, 0.0, 0.0)],
        ship_pos_xyz=(0.0, 0.0, 0.0),
        forward_xyz=(1.0, 0.0, 0.0),
        dock_radius=450.0,
        tradelane_speed=2500.0,
    )

    assert docking["status"] == "docking"
    assert active["status"] == "active"
    assert active["lane_index"] == 1
    assert active["ship_pos_xyz"] == (100.0, 0.0, 0.0)


def test_tradelane_docking_state_handles_activation_and_motion():
    activated = tradelane_docking_state(
        dt=0.1,
        lane_points_xyz=[(10.0, 0.0, 0.0), (20.0, 0.0, 0.0)],
        ship_pos_xyz=(0.0, 0.0, 0.0),
        yaw=0.0,
        pitch=0.0,
        speed=0.0,
        arrival_radius=20.0,
        cruise_speed=300.0,
        max_speed=80.0,
        accel=90.0,
        brake=160.0,
        tradelane_speed=2500.0,
        yaw_rate_max=1.0,
        pitch_rate_max=1.0,
        forward_xyz=(1.0, 0.0, 0.0),
    )
    moving = tradelane_docking_state(
        dt=0.5,
        lane_points_xyz=[(1000.0, 0.0, 0.0), (1200.0, 0.0, 0.0)],
        ship_pos_xyz=(0.0, 0.0, 0.0),
        yaw=0.0,
        pitch=0.0,
        speed=0.0,
        arrival_radius=20.0,
        cruise_speed=300.0,
        max_speed=80.0,
        accel=90.0,
        brake=160.0,
        tradelane_speed=2500.0,
        yaw_rate_max=10.0,
        pitch_rate_max=10.0,
        forward_xyz=(1.0, 0.0, 0.0),
    )

    assert activated["status"] == "active"
    assert activated["lane_index"] == 1
    assert moving["status"] == "continue"
    assert round(float(moving["ship_pos_xyz"][0]), 1) == 22.5
    assert round(float(moving["yaw"]), 3) == round(math.pi / 2.0, 3)


def test_tradelane_travel_state_moves_across_segments_and_finishes():
    moving = tradelane_travel_state(
        dt=0.05,
        lane_points_xyz=[(0.0, 0.0, 0.0), (100.0, 0.0, 0.0), (200.0, 0.0, 0.0)],
        lane_index=1,
        ship_pos_xyz=(0.0, 0.0, 0.0),
        tradelane_speed=1000.0,
        max_speed=80.0,
    )
    finished = tradelane_travel_state(
        dt=0.5,
        lane_points_xyz=[(0.0, 0.0, 0.0), (100.0, 0.0, 0.0)],
        lane_index=1,
        ship_pos_xyz=(0.0, 0.0, 0.0),
        tradelane_speed=1000.0,
        max_speed=80.0,
    )

    assert moving["status"] == "continue"
    assert moving["lane_index"] == 1
    assert moving["ship_pos_xyz"] == (50.0, 0.0, 0.0)
    assert finished["status"] == "finished"
    assert finished["lane_index"] == 2
    assert finished["ship_pos_xyz"] == (100.0, 0.0, 0.0)
    assert finished["speed"] == 80.0
