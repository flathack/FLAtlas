from __future__ import annotations

from fl_editor.flight_mode_constants import constants_ini_candidates, flight_constants_state, resolved_game_path


def test_resolved_game_path_prefers_browser_path_and_falls_back_to_config():
    assert resolved_game_path(browser_game_path="  /game/path  ", config_game_path="/cfg/path") == "/game/path"
    assert resolved_game_path(browser_game_path=" ", config_game_path="/cfg/path") == "/cfg/path"


def test_constants_ini_candidates_cover_supported_locations():
    candidates = constants_ini_candidates(game_path="/game")
    assert [str(path) for path in candidates] == [
        "/game/DATA/constants.ini",
        "/game/constants.ini",
        "/game/DATA/constants/constants.ini",
    ]


def test_flight_constants_state_parses_supported_keys_and_keeps_defaults():
    state = flight_constants_state(
        ini_text="""
            cruise_speed = 333
            cruise_charge_delay = 5.5
        """,
        default_cruise_speed=300.0,
        default_cruise_charge_time=4.0,
    )
    assert state == {
        "cruise_speed": 333.0,
        "cruise_charge_time": 5.5,
    }

    fallback = flight_constants_state(
        ini_text=None,
        default_cruise_speed=300.0,
        default_cruise_charge_time=4.0,
    )
    assert fallback == {
        "cruise_speed": 300.0,
        "cruise_charge_time": 4.0,
    }
