from __future__ import annotations

from pathlib import Path
from typing import Callable


def resolved_game_path(*, browser_game_path: str, config_game_path: str) -> str:
    game_path = str(browser_game_path or "").strip()
    if game_path:
        return game_path
    return str(config_game_path or "").strip()


def constants_ini_candidates(*, game_path: str) -> list[Path]:
    base = Path(game_path)
    return [
        base / "DATA" / "constants.ini",
        base / "constants.ini",
        base / "DATA" / "constants" / "constants.ini",
    ]


def flight_constants_state(
    *,
    ini_text: str | None,
    default_cruise_speed: float,
    default_cruise_charge_time: float,
) -> dict[str, float]:
    state = {
        "cruise_speed": float(default_cruise_speed),
        "cruise_charge_time": float(default_cruise_charge_time),
    }
    if not ini_text:
        return state
    for line in str(ini_text).splitlines():
        raw = line.strip()
        if "=" not in raw:
            continue
        key_raw, _, value_raw = raw.partition("=")
        key = key_raw.strip().lower()
        value = value_raw.strip()
        if key in ("cruise_speed", "cruising_speed"):
            state["cruise_speed"] = float(value)
        elif key in ("cruise_charge_time", "cruise_charge_delay"):
            state["cruise_charge_time"] = float(value)
    return state


def loaded_flight_constants_state(
    *,
    browser_game_path: str,
    config_game_path: str,
    default_cruise_speed: float,
    default_cruise_charge_time: float,
    path_exists: Callable[[Path], bool],
    read_text: Callable[[Path], str],
) -> dict[str, float]:
    defaults = flight_constants_state(
        ini_text=None,
        default_cruise_speed=default_cruise_speed,
        default_cruise_charge_time=default_cruise_charge_time,
    )
    game_path = resolved_game_path(
        browser_game_path=browser_game_path,
        config_game_path=config_game_path,
    )
    if not game_path:
        return defaults
    ini_path = None
    for candidate in constants_ini_candidates(game_path=game_path):
        if path_exists(candidate):
            ini_path = candidate
            break
    if ini_path is None:
        return defaults
    try:
        return flight_constants_state(
            ini_text=read_text(ini_path),
            default_cruise_speed=defaults["cruise_speed"],
            default_cruise_charge_time=defaults["cruise_charge_time"],
        )
    except Exception:
        return defaults
