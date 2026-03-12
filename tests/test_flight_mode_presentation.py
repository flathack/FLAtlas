from __future__ import annotations

from PySide6.QtGui import QVector3D

from fl_editor.flight_mode_presentation import editor_hud_bundle


class _Item:
    def __init__(self, nickname: str, pos: QVector3D):
        self.nickname = nickname
        self._pos = pos


def test_editor_hud_bundle_builds_snapshot_and_overlay_from_selection_and_autopilot():
    selected = _Item("sel_a", QVector3D(10.0, 0.0, 0.0))
    auto_target = _Item("auto_obj", QVector3D(0.0, 0.0, 20.0))

    def item_world_pos(item):
        return item._pos

    bundle = editor_hud_bundle(
        selected_item=selected,
        mode="AUTOPILOT",
        autopilot_mode="AUTOPILOT",
        auto_target=auto_target,
        target_name="auto_a",
        ship_pos=QVector3D(0.0, 0.0, 0.0),
        item_world_pos=item_world_pos,
        speed=120.0,
        max_speed=80.0,
        yaw=1.0,
        pitch=0.5,
        pitch_rate=0.4,
        forward_xyz=(0.0, 0.0, 1.0),
        charge_elapsed=2.0,
        cruise_charge_time=4.0,
        auto_cruise_charging=True,
        auto_cruise_active=True,
        orbit_cam_active=True,
        error="boom",
        cruise_charging_mode="CRUISE_CHARGING",
    )

    assert bundle["snapshot"]["target_name"] == "sel_a"
    assert bundle["snapshot"]["target_distance"] == 10.0
    assert bundle["snapshot"]["error"] == "boom"
    assert "Target: sel_a | Dist: 10.0 m" in bundle["overlay_text"]
    assert "Target: auto_a (20 m)" in bundle["overlay_text"]
