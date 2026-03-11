from fl_editor.path_utils import parse_position


def test_parse_position_standard_csv_triplet():
    assert parse_position("1, 2, 3") == (1.0, 2.0, 3.0)


def test_parse_position_two_components_third_falls_back_to_second():
    assert parse_position("5, 7") == (5.0, 7.0, 7.0)


def test_parse_position_whitespace_separated_values():
    assert parse_position("-32 154") == (-32.0, 154.0, 154.0)


def test_parse_position_invalid_value_returns_origin():
    assert parse_position("not_a_position") == (0.0, 0.0, 0.0)
