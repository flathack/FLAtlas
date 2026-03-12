from __future__ import annotations


def _find_ini_section_bounds(lines: list[str], section_name: str, nickname: str | None) -> tuple[int, int] | None:
    target_section = str(section_name or "").strip().lower()
    target_nick = str(nickname or "").strip().lower() if nickname is not None else None
    start = -1
    current_nick = ""
    for idx, raw in enumerate(lines):
        line = str(raw).strip()
        if not line.startswith("[") or not line.endswith("]"):
            continue
        if start >= 0:
            if target_nick is None or current_nick == target_nick:
                return start, idx
            start = -1
            current_nick = ""
        sec = line[1:-1].strip().lower()
        if sec == target_section:
            start = idx
            current_nick = ""
            continue
        if start >= 0 and "=" in line:
            key, value = line.split("=", 1)
            if key.strip().lower() == "nickname":
                current_nick = value.strip().lower()
    if start >= 0 and (target_nick is None or current_nick == target_nick):
        return start, len(lines)
    return None


def _set_single_key_line_in_section(section_lines: list[str], key_name: str, replacement_line: str) -> tuple[list[str], bool]:
    changed = False
    key_norm = str(key_name or "").strip().lower()
    found = False
    updated = list(section_lines)
    for idx in range(1, len(updated)):
        line = str(updated[idx]).strip()
        if "=" not in line:
            continue
        key, _value = line.split("=", 1)
        if key.strip().lower() != key_norm:
            continue
        found = True
        if updated[idx] != replacement_line:
            updated[idx] = replacement_line
            changed = True
        break
    if not found:
        updated.append(replacement_line)
        changed = True
    return updated, changed


def patch_perfoptions_resolution_text(raw: str, width: int, height: int, *, set_color_depth_32: bool = False) -> tuple[str, bool]:
    newline = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.splitlines()
    bounds = _find_ini_section_bounds(lines, "Display", None)
    size_line = f"size= {int(width)}, {int(height)}"
    depth_line = "color depth= 32"
    changed = False
    if bounds is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(["[Display]", size_line])
        if set_color_depth_32:
            lines.append(depth_line)
        changed = True
    else:
        start, end = bounds
        replaced = False
        replaced_depth = False
        for idx in range(start + 1, end):
            line = str(lines[idx]).strip()
            if "=" not in line:
                continue
            key, _value = line.split("=", 1)
            key = key.strip().lower()
            if key == "size":
                if lines[idx] != size_line:
                    lines[idx] = size_line
                    changed = True
                replaced = True
            elif set_color_depth_32 and key == "color depth":
                if lines[idx] != depth_line:
                    lines[idx] = depth_line
                    changed = True
                replaced_depth = True
            if replaced and (replaced_depth or not set_color_depth_32):
                break
        if not replaced:
            lines.insert(end, size_line)
            changed = True
            end += 1
        if set_color_depth_32 and not replaced_depth:
            lines.insert(end, depth_line)
            changed = True
    text = newline.join(lines)
    if lines:
        text += newline
    return text, changed


def patch_freelancer_display_text(raw: str, width: int, height: int, *, set_color_depth_32: bool = False) -> tuple[str, bool]:
    newline = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.splitlines()
    changed = False

    size_line = f"size = {int(width)},{int(height)}"
    color_line = "color_bpp = 32"
    depth_line = "depth_bpp = 32"

    def apply_display_section(section_name: str) -> tuple[bool, bool]:
        nonlocal lines
        bounds = _find_ini_section_bounds(lines, section_name, None)
        if bounds is None:
            return False, False
        start, end = bounds
        sec = list(lines[start:end])
        sec, c1 = _set_single_key_line_in_section(sec, "size", size_line)
        sec_changed = bool(c1)
        if set_color_depth_32:
            sec, c2 = _set_single_key_line_in_section(sec, "color_bpp", color_line)
            sec, c3 = _set_single_key_line_in_section(sec, "depth_bpp", depth_line)
            sec_changed = sec_changed or bool(c2) or bool(c3)
        if sec_changed:
            lines = lines[:start] + sec + lines[end:]
        return True, sec_changed

    found_section = False
    found, section_changed = apply_display_section(";Display")
    found_section = found_section or found
    changed = changed or section_changed
    found, section_changed = apply_display_section("Display")
    found_section = found_section or found
    changed = changed or section_changed

    if not found_section:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(["[Display]", size_line])
        if set_color_depth_32:
            lines.extend([color_line, depth_line])
        changed = True

    text = newline.join(lines)
    if lines:
        text += newline
    return text, changed
