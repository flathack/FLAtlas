from __future__ import annotations

from fl_editor.object_rotation import apply_object_rotate_entries, normalize_angle_180, parse_object_rotate


def test_normalize_angle_180_wraps_values_into_expected_range():
    assert normalize_angle_180(190) == -170
    assert normalize_angle_180(-190) == 170
    assert normalize_angle_180(-180) == 180.0


def test_parse_object_rotate_handles_missing_and_invalid_parts():
    assert parse_object_rotate("10, 20, 30") == (10.0, 20.0, 30.0)
    assert parse_object_rotate("10, nope") == (10.0, 0.0, 0.0)
    assert parse_object_rotate("") == (0.0, 0.0, 0.0)


def test_apply_object_rotate_entries_replaces_or_appends_rotate():
    updated, rotate_str = apply_object_rotate_entries([("nickname", "obj"), ("rotate", "1, 2, 3")], (190, 20, -190))

    assert rotate_str == "-170, 20, 170"
    assert updated == [("nickname", "obj"), ("rotate", "-170, 20, 170")]

    appended, rotate_str = apply_object_rotate_entries([("nickname", "obj")], (0, -180, 45))

    assert rotate_str == "0, 180, 45"
    assert appended == [("nickname", "obj"), ("rotate", "0, 180, 45")]
