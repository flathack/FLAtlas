from __future__ import annotations

from fl_editor.view_3d_object_logic import (
    extract_arch_size,
    is_trade_lane_object,
    object_rotation_quaternion,
    parse_pos,
    parse_rotate,
    rotation_quaternion_from_fl,
    scaled_radius_from_arch,
    tradelane_direction_quaternion,
)


def test_extract_arch_size_uses_suffix_or_default():
    assert extract_arch_size("planet_3000", 1000.0) == 3000.0
    assert extract_arch_size("planet", 1000.0) == 1000.0


def test_scaled_radius_from_arch_clamps_result():
    assert scaled_radius_from_arch("planet_4000", default_size=2000.0, base_size=2000.0, base_radius=10.0, min_r=5.0, max_r=20.0) > 10.0
    assert scaled_radius_from_arch("planet_1", default_size=2000.0, base_size=2000.0, base_radius=10.0, min_r=5.0, max_r=20.0) == 5.0


def test_parse_helpers_fall_back_to_zero():
    assert parse_pos("1,2") == (1.0, 2.0, 0.0)
    assert parse_rotate("bad,3,4") == (0.0, 3.0, 4.0)


def test_is_trade_lane_object_matches_name_or_arch():
    assert is_trade_lane_object(nickname="li01_trade_lane_ring_01", archetype="foo")
    assert is_trade_lane_object(nickname="foo", archetype="tradelane_ring")
    assert not is_trade_lane_object(nickname="planet", archetype="planet_3000")


def test_rotation_quaternion_from_fl_normalizes_yaw_only_pattern():
    q = rotation_quaternion_from_fl(-180.0, 90.0, -180.0)
    e = q.toEulerAngles()

    assert round(e.x(), 1) == 0.0
    assert round(e.y(), 1) == -90.0
    assert round(e.z(), 1) == 0.0


def test_tradelane_direction_quaternion_uses_neighbor_positions():
    q = tradelane_direction_quaternion(
        current_pos_raw="0,0,0",
        prev_pos_raw="-100,0,0",
        next_pos_raw="100,0,0",
    )

    assert q is not None
    e = q.toEulerAngles()
    assert round(e.y(), 1) == 90.0


def test_object_rotation_quaternion_prefers_tradelane_direction():
    q = object_rotation_quaternion(
        nickname="li01_trade_lane_ring_01",
        archetype="tradelane_ring",
        rotate_raw="0,45,0",
        current_pos_raw="0,0,0",
        prev_pos_raw=None,
        next_pos_raw="0,100,0",
    )

    e = q.toEulerAngles()
    assert round(e.x(), 1) == -90.0
