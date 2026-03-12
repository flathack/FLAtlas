from __future__ import annotations


def key_press_action(
    *,
    active: bool,
    key: int,
    shift_modifier_active: bool,
    mode: str,
    key_w: int,
    key_s: int,
    key_shift: int,
    key_esc: int,
    key_f2: int,
    key_f3: int,
    key_h: int,
    normal_mode: str,
    cruise_charging_mode: str,
    cruise_active_mode: str,
    autopilot_mode: str,
    tradelane_docking_mode: str,
    tradelane_active_mode: str,
) -> dict[str, object]:
    if not active:
        return {"handled": False}
    if key == key_w and shift_modifier_active:
        next_mode = normal_mode if mode in (cruise_charging_mode, cruise_active_mode) else None
        if next_mode is None and mode not in (autopilot_mode, tradelane_active_mode):
            next_mode = cruise_charging_mode
        return {
            "handled": True,
            "add_key": False,
            "next_mode": next_mode,
            "emit_hud": True,
        }

    state: dict[str, object] = {"handled": False, "add_key": True}
    if key == key_shift:
        state["handled"] = True
        state["set_shift_down"] = True
        return state
    if key == key_esc:
        state["handled"] = True
        state["disable_flight"] = True
        return state
    if key == key_f2:
        state["handled"] = True
        state["start_autopilot"] = True
        return state
    if key == key_f3:
        state["handled"] = True
        state["start_tradelane"] = True
        return state
    if key == key_h:
        state["handled"] = True
        state["toggle_orbit"] = True
        state["emit_hud"] = True
        return state
    if mode == tradelane_docking_mode and key in (key_w, key_s):
        state["handled"] = True
        state["next_mode"] = normal_mode
        state["emit_hud"] = True
        return state
    if mode == tradelane_active_mode:
        state["handled"] = True
        return state
    if key in (key_w, key_s):
        state["handled"] = True
        return state
    return state


def key_release_action(*, active: bool, key: int, key_shift: int, key_w: int, key_s: int) -> dict[str, object]:
    if not active:
        return {"handled": False}
    if key == key_shift:
        return {"handled": True, "clear_shift_down": True}
    if key in (key_w, key_s):
        return {"handled": True}
    return {"handled": False}
