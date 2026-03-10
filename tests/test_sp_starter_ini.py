from __future__ import annotations

from fl_editor.sp_starter_ini import (
    sp_starter_current_from_lines,
    sp_starter_set_in_text,
)


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
