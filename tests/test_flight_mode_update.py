from __future__ import annotations

from fl_editor.flight_mode_update import (
    autopilot_interrupt_state,
    cruise_update_state,
    drive_input_state,
    steer_activation_state,
    updated_speed,
)


def test_steer_activation_state_activates_after_hold_delay():
    state = steer_activation_state(
        lmb_down=True,
        mouse_flight_active=False,
        lmb_hold_time=0.1,
        dt=0.1,
        steer_activation_delay=0.18,
    )

    assert round(float(state["lmb_hold_time"]), 2) == 0.2
    assert state["mouse_flight_active"] is True


def test_drive_input_state_tracks_w_s_and_hold_time():
    state = drive_input_state(keys_down={1, 2}, key_w=1, key_s=2, s_hold_time=0.3, dt=0.2)
    idle = drive_input_state(keys_down=set(), key_w=1, key_s=2, s_hold_time=0.3, dt=0.2)

    assert state["w_down"] is True
    assert state["s_down"] is True
    assert round(float(state["s_hold_time"]), 2) == 0.5
    assert idle["s_hold_time"] == 0.0


def test_autopilot_interrupt_and_cruise_update_states():
    interrupt = autopilot_interrupt_state(
        mode="AUTOPILOT",
        autopilot_mode="AUTOPILOT",
        normal_mode="NORMAL",
        w_down=False,
        s_down=True,
        mouse_flight_active=False,
    )
    charging = cruise_update_state(
        mode="CRUISE_CHARGING",
        cruise_charging_mode="CRUISE_CHARGING",
        cruise_active_mode="CRUISE_ACTIVE",
        normal_mode="NORMAL",
        charge_elapsed=3.9,
        dt=0.2,
        cruise_charge_time=4.0,
        should_abort_cruise=False,
    )
    aborting = cruise_update_state(
        mode="CRUISE_ACTIVE",
        cruise_charging_mode="CRUISE_CHARGING",
        cruise_active_mode="CRUISE_ACTIVE",
        normal_mode="NORMAL",
        charge_elapsed=1.0,
        dt=0.2,
        cruise_charge_time=4.0,
        should_abort_cruise=True,
    )

    assert interrupt["interrupt_autopilot"] is True
    assert interrupt["next_mode"] == "NORMAL"
    assert charging["next_mode"] == "CRUISE_ACTIVE"
    assert aborting["next_mode"] == "NORMAL"


def test_updated_speed_handles_cruise_normal_and_braking():
    cruise = updated_speed(
        mode="CRUISE_ACTIVE",
        autopilot_mode="AUTOPILOT",
        tradelane_active_mode="TRADELANE_ACTIVE",
        cruise_active_mode="CRUISE_ACTIVE",
        normal_mode="NORMAL",
        speed=100.0,
        max_speed=80.0,
        cruise_speed=300.0,
        accel=90.0,
        brake=160.0,
        dt=1.0,
        w_down=False,
        s_down=False,
    )
    accel = updated_speed(
        mode="NORMAL",
        autopilot_mode="AUTOPILOT",
        tradelane_active_mode="TRADELANE_ACTIVE",
        cruise_active_mode="CRUISE_ACTIVE",
        normal_mode="NORMAL",
        speed=10.0,
        max_speed=80.0,
        cruise_speed=300.0,
        accel=90.0,
        brake=160.0,
        dt=1.0,
        w_down=True,
        s_down=False,
    )
    brake = updated_speed(
        mode="NORMAL",
        autopilot_mode="AUTOPILOT",
        tradelane_active_mode="TRADELANE_ACTIVE",
        cruise_active_mode="CRUISE_ACTIVE",
        normal_mode="NORMAL",
        speed=100.0,
        max_speed=80.0,
        cruise_speed=300.0,
        accel=90.0,
        brake=160.0,
        dt=1.0,
        w_down=False,
        s_down=True,
    )

    assert cruise == 190.0
    assert accel == 80.0
    assert brake == 0.0
