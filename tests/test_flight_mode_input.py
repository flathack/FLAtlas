from __future__ import annotations

from fl_editor.flight_mode_input import key_press_action, key_release_action


KEY_W = 1
KEY_S = 2
KEY_SHIFT = 3
KEY_ESC = 4
KEY_F2 = 5
KEY_F3 = 6
KEY_H = 7


def test_shift_w_toggles_cruise_mode():
    start = key_press_action(
        active=True,
        key=KEY_W,
        shift_modifier_active=True,
        mode="NORMAL",
        key_w=KEY_W,
        key_s=KEY_S,
        key_shift=KEY_SHIFT,
        key_esc=KEY_ESC,
        key_f2=KEY_F2,
        key_f3=KEY_F3,
        key_h=KEY_H,
        normal_mode="NORMAL",
        cruise_charging_mode="CRUISE_CHARGING",
        cruise_active_mode="CRUISE_ACTIVE",
        autopilot_mode="AUTOPILOT",
        tradelane_docking_mode="TRADELANE_DOCKING",
        tradelane_active_mode="TRADELANE_ACTIVE",
    )
    stop = key_press_action(
        active=True,
        key=KEY_W,
        shift_modifier_active=True,
        mode="CRUISE_ACTIVE",
        key_w=KEY_W,
        key_s=KEY_S,
        key_shift=KEY_SHIFT,
        key_esc=KEY_ESC,
        key_f2=KEY_F2,
        key_f3=KEY_F3,
        key_h=KEY_H,
        normal_mode="NORMAL",
        cruise_charging_mode="CRUISE_CHARGING",
        cruise_active_mode="CRUISE_ACTIVE",
        autopilot_mode="AUTOPILOT",
        tradelane_docking_mode="TRADELANE_DOCKING",
        tradelane_active_mode="TRADELANE_ACTIVE",
    )

    assert start["handled"] is True
    assert start["next_mode"] == "CRUISE_CHARGING"
    assert start["add_key"] is False
    assert stop["next_mode"] == "NORMAL"


def test_key_press_action_routes_special_actions():
    esc = key_press_action(
        active=True,
        key=KEY_ESC,
        shift_modifier_active=False,
        mode="NORMAL",
        key_w=KEY_W,
        key_s=KEY_S,
        key_shift=KEY_SHIFT,
        key_esc=KEY_ESC,
        key_f2=KEY_F2,
        key_f3=KEY_F3,
        key_h=KEY_H,
        normal_mode="NORMAL",
        cruise_charging_mode="CRUISE_CHARGING",
        cruise_active_mode="CRUISE_ACTIVE",
        autopilot_mode="AUTOPILOT",
        tradelane_docking_mode="TRADELANE_DOCKING",
        tradelane_active_mode="TRADELANE_ACTIVE",
    )
    f2 = key_press_action(
        active=True,
        key=KEY_F2,
        shift_modifier_active=False,
        mode="NORMAL",
        key_w=KEY_W,
        key_s=KEY_S,
        key_shift=KEY_SHIFT,
        key_esc=KEY_ESC,
        key_f2=KEY_F2,
        key_f3=KEY_F3,
        key_h=KEY_H,
        normal_mode="NORMAL",
        cruise_charging_mode="CRUISE_CHARGING",
        cruise_active_mode="CRUISE_ACTIVE",
        autopilot_mode="AUTOPILOT",
        tradelane_docking_mode="TRADELANE_DOCKING",
        tradelane_active_mode="TRADELANE_ACTIVE",
    )
    h = key_press_action(
        active=True,
        key=KEY_H,
        shift_modifier_active=False,
        mode="NORMAL",
        key_w=KEY_W,
        key_s=KEY_S,
        key_shift=KEY_SHIFT,
        key_esc=KEY_ESC,
        key_f2=KEY_F2,
        key_f3=KEY_F3,
        key_h=KEY_H,
        normal_mode="NORMAL",
        cruise_charging_mode="CRUISE_CHARGING",
        cruise_active_mode="CRUISE_ACTIVE",
        autopilot_mode="AUTOPILOT",
        tradelane_docking_mode="TRADELANE_DOCKING",
        tradelane_active_mode="TRADELANE_ACTIVE",
    )

    assert esc["disable_flight"] is True
    assert f2["start_autopilot"] is True
    assert h["toggle_orbit"] is True
    assert h["emit_hud"] is True


def test_key_press_action_handles_tradelane_modes_and_drive_keys():
    docking = key_press_action(
        active=True,
        key=KEY_W,
        shift_modifier_active=False,
        mode="TRADELANE_DOCKING",
        key_w=KEY_W,
        key_s=KEY_S,
        key_shift=KEY_SHIFT,
        key_esc=KEY_ESC,
        key_f2=KEY_F2,
        key_f3=KEY_F3,
        key_h=KEY_H,
        normal_mode="NORMAL",
        cruise_charging_mode="CRUISE_CHARGING",
        cruise_active_mode="CRUISE_ACTIVE",
        autopilot_mode="AUTOPILOT",
        tradelane_docking_mode="TRADELANE_DOCKING",
        tradelane_active_mode="TRADELANE_ACTIVE",
    )
    active = key_press_action(
        active=True,
        key=99,
        shift_modifier_active=False,
        mode="TRADELANE_ACTIVE",
        key_w=KEY_W,
        key_s=KEY_S,
        key_shift=KEY_SHIFT,
        key_esc=KEY_ESC,
        key_f2=KEY_F2,
        key_f3=KEY_F3,
        key_h=KEY_H,
        normal_mode="NORMAL",
        cruise_charging_mode="CRUISE_CHARGING",
        cruise_active_mode="CRUISE_ACTIVE",
        autopilot_mode="AUTOPILOT",
        tradelane_docking_mode="TRADELANE_DOCKING",
        tradelane_active_mode="TRADELANE_ACTIVE",
    )

    assert docking["next_mode"] == "NORMAL"
    assert active["handled"] is True


def test_key_release_action_handles_shift_and_drive_keys():
    shift = key_release_action(active=True, key=KEY_SHIFT, key_shift=KEY_SHIFT, key_w=KEY_W, key_s=KEY_S)
    drive = key_release_action(active=True, key=KEY_W, key_shift=KEY_SHIFT, key_w=KEY_W, key_s=KEY_S)
    other = key_release_action(active=True, key=99, key_shift=KEY_SHIFT, key_w=KEY_W, key_s=KEY_S)

    assert shift["clear_shift_down"] is True
    assert drive["handled"] is True
    assert other["handled"] is False
