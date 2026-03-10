from __future__ import annotations

from fl_editor.view_3d_interaction import (
    axis_scroll_delta,
    mouse_move_interaction,
    mouse_press_interaction,
    mouse_release_interaction,
    wheel_interaction,
)


def test_axis_scroll_delta_maps_to_locked_axis():
    assert axis_scroll_delta(delta=120, axis_step_world=100.0, locked_axis="x") == (100.0, 0.0, 0.0)
    assert axis_scroll_delta(delta=-120, axis_step_world=100.0, locked_axis="z") == (0.0, 0.0, -100.0)


def test_mouse_press_and_release_interaction_handle_drag_states():
    clear_lock = mouse_press_interaction(button="left", locked_axis="x")
    orbit = mouse_press_interaction(button="left", locked_axis=None)
    pan = mouse_press_interaction(button="right", locked_axis=None)
    release = mouse_release_interaction(button="left")

    assert clear_lock["clear_locked_axis"] is True
    assert orbit["drag_mode"] == "orbit"
    assert pan["drag_mode"] == "pan"
    assert release["clear_drag_state"] is True


def test_mouse_move_interaction_updates_orbit_or_pan():
    orbit = mouse_move_interaction(drag_mode="orbit", delta_x=10.0, delta_y=-10.0, cam_yaw=1.0, cam_pitch=0.0)
    pan = mouse_move_interaction(drag_mode="pan", delta_x=5.0, delta_y=7.0, cam_yaw=1.0, cam_pitch=0.0)

    assert round(float(orbit["cam_yaw"]), 3) == 0.92
    assert round(float(orbit["cam_pitch"]), 3) == -0.08
    assert pan["pan_dx"] == 5.0
    assert pan["pan_dy"] == 7.0


def test_wheel_interaction_routes_axis_height_and_zoom():
    axis = wheel_interaction(
        delta=120,
        locked_axis="y",
        has_selected_obj=True,
        control_modifier_active=False,
        cam_distance=100.0,
        axis_step_world=100.0,
    )
    height = wheel_interaction(
        delta=240,
        locked_axis=None,
        has_selected_obj=True,
        control_modifier_active=True,
        cam_distance=100.0,
        axis_step_world=100.0,
    )
    zoom = wheel_interaction(
        delta=-120,
        locked_axis=None,
        has_selected_obj=False,
        control_modifier_active=False,
        cam_distance=100.0,
        axis_step_world=100.0,
    )

    assert axis["axis_delta"] == (0.0, 100.0, 0.0)
    assert height["height_delta"] == 200.0
    assert round(float(zoom["cam_distance"]), 1) == 110.0
