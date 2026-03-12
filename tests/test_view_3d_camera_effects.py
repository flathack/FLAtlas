from __future__ import annotations

from fl_editor.view_3d_camera_effects import camera_update_effects_state, synced_orbit_camera_state


def test_camera_update_effects_state_returns_camera_pos_label_scales_and_sky_translation():
    state = camera_update_effects_state(
        target_xyz=(0.0, 0.0, 0.0),
        distance=10.0,
        yaw=0.0,
        pitch=0.0,
        label_positions_xyz=[(10.0, 0.0, 0.0), (0.0, 0.0, 0.0)],
        scale_factor=0.1,
        scale_min=0.2,
        scale_max=3.0,
    )

    assert state["camera_pos_xyz"] == (0.0, 0.0, 10.0)
    assert state["sky_translation_xyz"] == (0.0, 0.0, 10.0)
    assert len(state["label_scales"]) == 2
    assert round(float(state["label_scales"][0]), 4) == 1.4142
    assert state["label_scales"][1] == 1.0


def test_synced_orbit_camera_state_proxies_runtime_orbit_state():
    state = synced_orbit_camera_state(
        camera_pos_xyz=(10.0, 0.0, 0.0),
        view_center_xyz=(0.0, 0.0, 0.0),
    )

    assert state is not None
    assert state["target_xyz"] == (0.0, 0.0, 0.0)
    assert state["distance"] == 10.0
