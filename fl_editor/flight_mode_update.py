from __future__ import annotations


def steer_activation_state(*, lmb_down: bool, mouse_flight_active: bool, lmb_hold_time: float, dt: float, steer_activation_delay: float) -> dict[str, object]:
    next_hold = float(lmb_hold_time)
    next_active = bool(mouse_flight_active)
    if lmb_down and not next_active:
        next_hold += float(dt)
        if next_hold >= float(steer_activation_delay):
            next_active = True
    return {
        "lmb_hold_time": next_hold,
        "mouse_flight_active": next_active,
    }


def drive_input_state(*, keys_down: set[int], key_w: int, key_s: int, s_hold_time: float, dt: float) -> dict[str, object]:
    w_down = int(key_w) in keys_down
    s_down = int(key_s) in keys_down
    return {
        "w_down": w_down,
        "s_down": s_down,
        "s_hold_time": float(s_hold_time) + float(dt) if s_down else 0.0,
    }


def autopilot_interrupt_state(*, mode: str, autopilot_mode: str, normal_mode: str, w_down: bool, s_down: bool, mouse_flight_active: bool) -> dict[str, object]:
    if mode != autopilot_mode:
        return {"interrupt_autopilot": False}
    if w_down or s_down or mouse_flight_active:
        return {"interrupt_autopilot": True, "next_mode": normal_mode}
    return {"interrupt_autopilot": False}


def cruise_update_state(
    *,
    mode: str,
    cruise_charging_mode: str,
    cruise_active_mode: str,
    normal_mode: str,
    charge_elapsed: float,
    dt: float,
    cruise_charge_time: float,
    should_abort_cruise: bool,
) -> dict[str, object]:
    if mode == cruise_charging_mode:
        next_charge = float(charge_elapsed) + float(dt)
        if should_abort_cruise:
            return {"next_mode": normal_mode, "charge_elapsed": next_charge}
        if next_charge >= float(cruise_charge_time):
            return {"next_mode": cruise_active_mode, "charge_elapsed": next_charge}
        return {"next_mode": None, "charge_elapsed": next_charge}
    if mode == cruise_active_mode and should_abort_cruise:
        return {"next_mode": normal_mode, "charge_elapsed": float(charge_elapsed)}
    return {"next_mode": None, "charge_elapsed": float(charge_elapsed)}


def updated_speed(
    *,
    mode: str,
    autopilot_mode: str,
    tradelane_active_mode: str,
    cruise_active_mode: str,
    normal_mode: str,
    speed: float,
    max_speed: float,
    cruise_speed: float,
    accel: float,
    brake: float,
    dt: float,
    w_down: bool,
    s_down: bool,
) -> float:
    next_speed = float(speed)
    if mode in (autopilot_mode, tradelane_active_mode):
        return next_speed
    if mode == cruise_active_mode:
        return min(float(cruise_speed), next_speed + float(accel) * float(dt))
    if w_down and not s_down:
        next_speed = min(float(max_speed), next_speed + float(accel) * float(dt))
    if s_down:
        next_speed = max(0.0, next_speed - float(brake) * float(dt))
    return next_speed
