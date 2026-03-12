from __future__ import annotations

from pathlib import Path

from fl_editor.flight_mode_constants import (
    constants_ini_candidates,
    editor_game_path_inputs,
    flight_constants_state,
    loaded_flight_constants_state,
    resolved_game_path,
)


def test_resolved_game_path_prefers_browser_path_and_falls_back_to_config():
    assert resolved_game_path(browser_game_path="  /game/path  ", config_game_path="/cfg/path") == "/game/path"
    assert resolved_game_path(browser_game_path=" ", config_game_path="/cfg/path") == "/cfg/path"


def test_editor_game_path_inputs_reads_browser_and_config_paths_when_available():
    class PathEdit:
        def text(self):
            return "  /browser/path  "

    class Browser:
        path_edit = PathEdit()

    class Editor:
        browser = Browser()
        _cfg = {"game_path": "  /cfg/path  "}

    assert editor_game_path_inputs(Editor()) == {
        "browser_game_path": "/browser/path",
        "config_game_path": "/cfg/path",
    }


def test_editor_game_path_inputs_handles_missing_editor_attributes():
    class Editor:
        pass

    assert editor_game_path_inputs(None) == {
        "browser_game_path": "",
        "config_game_path": "",
    }
    assert editor_game_path_inputs(Editor()) == {
        "browser_game_path": "",
        "config_game_path": "",
    }


def test_constants_ini_candidates_cover_supported_locations():
    candidates = constants_ini_candidates(game_path="/game")
    assert candidates == [
        Path("/game/DATA/constants.ini"),
        Path("/game/constants.ini"),
        Path("/game/DATA/constants/constants.ini"),
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


def test_loaded_flight_constants_state_uses_first_existing_candidate_and_falls_back_on_errors():
    existing = {Path("/game/DATA/constants.ini")}

    state = loaded_flight_constants_state(
        browser_game_path="/game",
        config_game_path="",
        default_cruise_speed=300.0,
        default_cruise_charge_time=4.0,
        path_exists=lambda path: path in existing,
        read_text=lambda _path: "cruising_speed = 444\ncruise_charge_time = 6",
    )
    assert state == {
        "cruise_speed": 444.0,
        "cruise_charge_time": 6.0,
    }

    fallback = loaded_flight_constants_state(
        browser_game_path="/game",
        config_game_path="",
        default_cruise_speed=300.0,
        default_cruise_charge_time=4.0,
        path_exists=lambda _path: True,
        read_text=lambda _path: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert fallback == {
        "cruise_speed": 300.0,
        "cruise_charge_time": 4.0,
    }
