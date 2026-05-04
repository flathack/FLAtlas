from __future__ import annotations

import pytest

from fl_editor.models import ZoneItem


def _zone_data(*, nickname: str, shape: str, size: str, rotate: str) -> dict:
    entries = [
        ("nickname", nickname),
        ("shape", shape),
        ("size", size),
        ("rotate", rotate),
        ("pos", "0,0,0"),
    ]
    data = {"_entries": entries}
    for key, value in entries:
        data[key.lower()] = value
    return data


def test_vanilla_tradelane_box_rotation_matches_lane_direction(qapp):
    zone = ZoneItem(
        _zone_data(
            nickname="Zone_Li01_Tradelane_19",
            shape="BOX",
            size="1598, 1598, 46598",
            rotate="-179.999985, 71, -179.999985",
        ),
        1.0,
    )

    assert zone.rotation() == pytest.approx(71.0, abs=0.2)


def test_editor_box_rotation_stays_horizontal_for_zero_yaw(qapp):
    zone = ZoneItem(
        _zone_data(
            nickname="editor_box_zone",
            shape="BOX",
            size="4000, 1000, 1200",
            rotate="0,0,0",
        ),
        1.0,
    )

    assert zone.rotation() == pytest.approx(0.0, abs=0.01)


def test_ellipsoid_rotation_uses_zone_yaw_in_2d(qapp):
    zone = ZoneItem(
        _zone_data(
            nickname="editor_ellipsoid_zone",
            shape="ELLIPSOID",
            size="4000, 1000, 1200",
            rotate="0,45,0",
        ),
        1.0,
    )

    assert zone.rotation() == pytest.approx(-45.0, abs=0.01)


def test_sphere_rotation_uses_zone_yaw_for_orientation_marker(qapp):
    zone = ZoneItem(
        _zone_data(
            nickname="editor_sphere_zone",
            shape="SPHERE",
            size="4000",
            rotate="0,45,0",
        ),
        1.0,
    )

    assert zone.rotation() == pytest.approx(-45.0, abs=0.01)


def test_zone_visual_refresh_updates_rotation_after_rotate_change(qapp):
    zone = ZoneItem(
        _zone_data(
            nickname="editor_ellipsoid_zone",
            shape="ELLIPSOID",
            size="4000, 1000, 1200",
            rotate="0,0,0",
        ),
        1.0,
    )
    zone.data["rotate"] = "0,30,0"

    zone._refresh_visual_from_data()

    assert zone.rotation() == pytest.approx(-30.0, abs=0.01)
