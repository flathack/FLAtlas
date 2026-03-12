from fl_editor.opensp_ini_patch import apply_opensp_rules_to_text


def _find_bounds(lines: list[str], section_name: str, nickname: str | None):
    current_start = None
    current_section = None
    current_nick = None
    for idx, raw in enumerate(lines):
        line = str(raw).strip()
        if line.startswith("[") and line.endswith("]"):
            if current_start is not None and current_section == section_name.lower():
                if nickname is None or current_nick == nickname.lower():
                    return current_start, idx
            current_start = idx
            current_section = line[1:-1].strip().lower()
            current_nick = None
            continue
        if current_start is not None and "=" in line:
            key, value = line.split("=", 1)
            if key.strip().lower() == "nickname":
                current_nick = value.strip().lower()
    if current_start is not None and current_section == section_name.lower():
        if nickname is None or current_nick == nickname.lower():
            return current_start, len(lines)
    return None


def _replace_block(section_lines: list[str], dest_block: str, src_block: str):
    changed = False
    updated = []
    for raw in section_lines:
        if str(raw).strip() == dest_block:
            updated.append(src_block)
            changed = True
        else:
            updated.append(raw)
    return updated, changed


def _set_single(section_lines: list[str], key: str, line: str):
    updated = list(section_lines)
    key = key.lower()
    for idx in range(1, len(updated)):
        raw = str(updated[idx]).strip()
        if "=" not in raw:
            continue
        left, _right = raw.split("=", 1)
        if left.strip().lower() == key:
            if updated[idx] != line:
                updated[idx] = line
                return updated, True
            return updated, False
    updated.append(line)
    return updated, True


def _comment_out(section_lines: list[str], exact_line: str):
    changed = False
    updated = []
    for raw in section_lines:
        if str(raw).strip() == exact_line:
            updated.append(";" + raw)
            changed = True
        else:
            updated.append(raw)
    return updated, changed


def test_apply_opensp_rules_to_text_patches_m01a_and_reports_missing():
    raw = (
        "[Trigger]\n"
        "nickname = tr_initialize_init\n"
        "Act_ActTrig = tr_fp7_cam\n"
        "[Trigger]\n"
        "nickname = tr_fp7_cam_end\n"
        "Act_SetRep = old\n"
    )

    patched, changed, missing = apply_opensp_rules_to_text(
        raw,
        ini_name="m01a.ini",
        rules=[("Trigger", "missing_nick", "foo", "bar")],
        find_ini_section_bounds=_find_bounds,
        replace_block_in_ini_section=_replace_block,
        set_single_key_line_in_section=_set_single,
        comment_out_exact_line_in_section=_comment_out,
    )

    assert changed is True
    assert missing == ["#1: [Trigger]/missing_nick"]
    assert "Act_ActTrig = tr_fp7_cam_end" in patched
    assert "Cnd_Timer = 1" in patched
    assert "Act_SetRep = Player, fc_lr_grp, REP_FRIEND_MAXIMUM" in patched


def test_apply_opensp_rules_to_text_patches_m01b_commentouts():
    raw = (
        "[Trigger]\n"
        "nickname = space_enter\n"
        "Act_ActTrig = start_init\n"
        "Act_PlayerCanDock = false\n"
    )

    patched, changed, missing = apply_opensp_rules_to_text(
        raw,
        ini_name="m01b.ini",
        rules=[],
        find_ini_section_bounds=_find_bounds,
        replace_block_in_ini_section=_replace_block,
        set_single_key_line_in_section=_set_single,
        comment_out_exact_line_in_section=_comment_out,
    )

    assert changed is True
    assert missing == []
    assert ";Act_ActTrig = start_init" in patched
    assert ";Act_PlayerCanDock = false" in patched
