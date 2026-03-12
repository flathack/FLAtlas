from __future__ import annotations

from fl_editor.sp_starter_ini import (
    sp_starter_current_from_lines,
    sp_starter_set_custom_loadout_in_text,
    sp_starter_set_in_text,
    sp_starter_write_custom_loadout_ini,
    sp_starter_write_trigger_ini,
)
from pathlib import Path


def _find_trigger_bounds(lines: list[str], section_name: str, nickname: str | None):
    start = None
    for idx, line in enumerate(lines):
        if str(line).strip().lower() == "[trigger]":
            start = idx
            continue
        if start is not None and nickname and str(line).strip().lower() == f"nickname = {nickname.lower()}":
            end = len(lines)
            for j in range(idx + 1, len(lines)):
                stripped = str(lines[j]).strip()
                if stripped.startswith("[") and stripped.endswith("]"):
                    end = j
                    break
            return start, end
    return None


def _find_section_bounds(lines: list[str], section_name: str, nickname: str | None):
    start = None
    target_header = f"[{str(section_name).strip().lower()}]"
    for idx, line in enumerate(lines):
        if str(line).strip().lower() == target_header:
            start = idx
            continue
        if start is not None and nickname and str(line).strip().lower() == f"nickname = {nickname.lower()}":
            end = len(lines)
            for j in range(idx + 1, len(lines)):
                stripped = str(lines[j]).strip()
                if stripped.startswith("[") and stripped.endswith("]"):
                    end = j
                    break
            return start, end
    return None


def test_sp_starter_current_from_lines_reads_ship_and_loadout():
    lines = [
        "[Trigger]",
        "nickname = tr_fp7_cam_end",
        "Act_SetShipAndLoadout = ge_fighter, ge_fighter_loadout",
    ]

    result = sp_starter_current_from_lines(lines, _find_trigger_bounds)

    assert result == ("ge_fighter", "ge_fighter_loadout")


def test_sp_starter_set_in_text_replaces_existing_line():
    raw = "[Trigger]\nnickname = tr_fp7_cam_end\nAct_SetShipAndLoadout = old_ship, old_loadout\n"

    ok, patched, error_code = sp_starter_set_in_text(
        raw,
        ship="new_ship",
        loadout="new_loadout",
        find_ini_section_bounds=_find_trigger_bounds,
    )

    assert ok
    assert error_code == ""
    assert "Act_SetShipAndLoadout = new_ship, new_loadout" in patched


def test_sp_starter_set_in_text_inserts_line_when_missing():
    raw = "[Trigger]\nnickname = tr_fp7_cam_end\nAct_PlayMusic = intro\n"

    ok, patched, error_code = sp_starter_set_in_text(
        raw,
        ship="new_ship",
        loadout="new_loadout",
        find_ini_section_bounds=_find_trigger_bounds,
    )

    assert ok
    assert error_code == ""
    assert patched.endswith("Act_SetShipAndLoadout = new_ship, new_loadout\n")


def test_sp_starter_set_custom_loadout_in_text_replaces_existing_section():
    raw = (
        "[Loadout]\n"
        "nickname = first\n"
        "archetype = ge_fighter\n"
        "\n"
        "[Loadout]\n"
        "nickname = custom_loadout\n"
        "archetype = old_ship\n"
        "equip = old_gun\n"
        "\n"
    )

    patched = sp_starter_set_custom_loadout_in_text(
        raw,
        nickname="custom_loadout",
        archetype="new_ship",
        equip_lines=["gun01", "gun02"],
        cargo_lines=["commodity, 5"],
        find_ini_section_bounds=_find_section_bounds,
    )

    assert "nickname = custom_loadout\narchetype = new_ship\nequip = gun01\nequip = gun02\ncargo = commodity, 5\n" in patched
    assert "old_ship" not in patched


def test_sp_starter_set_custom_loadout_in_text_appends_when_missing():
    raw = "[Loadout]\nnickname = existing\narchetype = ge_fighter\n"

    patched = sp_starter_set_custom_loadout_in_text(
        raw,
        nickname="new_loadout",
        archetype="li_fighter",
        equip_lines=["gun01"],
        cargo_lines=[],
        find_ini_section_bounds=_find_section_bounds,
    )

    assert patched.endswith("\n[Loadout]\nnickname = new_loadout\narchetype = li_fighter\nequip = gun01\n")


def test_sp_starter_write_trigger_ini_persists_patched_text(tmp_path: Path):
    ini_path = tmp_path / "m01a.ini"
    raw = "[Trigger]\nnickname = tr_fp7_cam_end\nAct_PlayMusic = intro\n"

    ok, patched, error_code = sp_starter_write_trigger_ini(
        ini_path,
        raw_text=raw,
        ship="new_ship",
        loadout="new_loadout",
        find_ini_section_bounds=_find_trigger_bounds,
    )

    assert ok
    assert error_code == ""
    assert ini_path.read_text(encoding="utf-8") == patched


def test_sp_starter_write_custom_loadout_ini_persists_patched_text(tmp_path: Path):
    ini_path = tmp_path / "loadouts.ini"
    raw = "[Loadout]\nnickname = existing\narchetype = ge_fighter\n"

    patched = sp_starter_write_custom_loadout_ini(
        ini_path,
        raw_text=raw,
        nickname="new_loadout",
        archetype="li_fighter",
        equip_lines=["gun01"],
        cargo_lines=["commodity, 5"],
        find_ini_section_bounds=_find_section_bounds,
    )

    assert ini_path.read_text(encoding="utf-8") == patched
    assert "nickname = new_loadout" in patched
