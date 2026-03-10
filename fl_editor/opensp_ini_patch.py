from __future__ import annotations

from typing import Callable


Rule = tuple[str, str | None, str, str]


def apply_opensp_rules_to_text(
    raw_text: str,
    *,
    ini_name: str,
    rules: list[Rule],
    find_ini_section_bounds: Callable[[list[str], str, str | None], tuple[int, int] | None],
    replace_block_in_ini_section: Callable[[list[str], str, str], tuple[list[str], bool]],
    set_single_key_line_in_section: Callable[[list[str], str, str], tuple[list[str], bool]],
    comment_out_exact_line_in_section: Callable[[list[str], str], tuple[list[str], bool]],
) -> tuple[str, bool, list[str]]:
    newline = "\r\n" if "\r\n" in raw_text else "\n"
    lines = str(raw_text).splitlines()
    changed_any = False
    missing_rules: list[str] = []

    for idx, (sec_name, nick, dest_block, src_block) in enumerate(rules, start=1):
        bounds = find_ini_section_bounds(lines, sec_name, nick)
        if bounds is None:
            missing_rules.append(f"#{idx}: [{sec_name}]/{nick or '*'}")
            continue
        start, end = bounds
        new_sec, changed = replace_block_in_ini_section(lines[start:end], dest_block, src_block)
        if changed:
            lines = lines[:start] + new_sec + lines[end:]
            changed_any = True

    def set_for(section: str, nickname: str | None, key: str, line: str) -> None:
        nonlocal lines, changed_any
        bounds = find_ini_section_bounds(lines, section, nickname)
        if bounds is None:
            return
        start, end = bounds
        sec, changed = set_single_key_line_in_section(lines[start:end], key, line)
        if changed:
            lines = lines[:start] + sec + lines[end:]
            changed_any = True

    name = str(ini_name or "").strip().lower()
    if name == "m01a.ini":
        bounds = find_ini_section_bounds(lines, "Trigger", "tr_initialize_init")
        if bounds is not None:
            start, end = bounds
            sec = list(lines[start:end])
            sec2, changed = replace_block_in_ini_section(
                sec,
                "Act_ActTrig = tr_fp7_cam",
                "Act_ActTrig = tr_fp7_cam_end",
            )
            if changed:
                lines = lines[:start] + sec2 + lines[end:]
                changed_any = True
        set_for("Trigger", "tr_fp7_cam_end", "Cnd_Timer", "Cnd_Timer = 1")
        set_for("Trigger", "tr_fp7_cam_end", "Act_ForceLand", "Act_ForceLand = Li01_01_Base")
        set_for("Trigger", "tr_fp7_cam_end", "Act_SetShipAndLoadout", "Act_SetShipAndLoadout = ge_fighter, msn_playerloadout")
        set_for("Trigger", "tr_fp7_cam_end", "Act_SetRep", "Act_SetRep = Player, fc_lr_grp, REP_FRIEND_MAXIMUM")
        set_for("Trigger", "tr_fp7_cam_end", "Act_ChangeState", "Act_ChangeState = SUCCEED")
        set_for("Trigger", "mrp_accept", "Act_SetShipAndLoadout", "Act_SetShipAndLoadout = co_fighter, msn_playerloadout")
        set_for("Trigger", "mrp_accept", "Act_ChangeState", "Act_Changestate = SUCCEED")
    elif name == "m01b.ini":
        set_for("Mission", None, "Act_ChangeState", "Act_ChangeState = SUCCEED")
        set_for("Trigger", "space_enter", "Act_ChangeState", "Act_ChangeState = SUCCEED")
        bounds = find_ini_section_bounds(lines, "Trigger", "space_enter")
        if bounds is not None:
            start, end = bounds
            sec = list(lines[start:end])
            for raw in (
                "Act_ActTrig = start_init",
                "Act_ActTrig = launch_complete_RTC",
                "Act_PlayerCanDock = false",
                "Act_SetNNObj = nn_objsoon, OBJECTIVE_HISTORY",
                "Act_PlayMusic = music_li_space, music_li_danger, music_li_battle, music_li_space, 0, false",
            ):
                sec, changed = comment_out_exact_line_in_section(sec, raw)
                if changed:
                    changed_any = True
            if changed_any:
                lines = lines[:start] + sec + lines[end:]

    text = newline.join(lines)
    if lines:
        text += newline
    return text, changed_any, missing_rules
