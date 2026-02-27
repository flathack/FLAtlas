"""Hilfsfunktionen für Exclusion-Zonen (Freelancer System-INI)."""

from __future__ import annotations

import re


def normalize_name(value: str) -> str:
    """Normalisiert Namen für Nickname-Bausteine."""
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", (value or "").strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "zone"


def generate_exclusion_nickname(
    system_nickname: str,
    field_zone_nickname: str,
    existing_zone_nicknames: list[str],
) -> str:
    """Erzeugt einen eindeutigen Exclusion-Zonen-Nickname.

    Schema: Zone_<System>_<Field>_exclusion_<n>
    """
    sys_part = normalize_name(system_nickname)
    field_raw = normalize_name(field_zone_nickname)
    field_l = field_raw.lower()

    if field_l.startswith("zone_"):
        field_raw = field_raw[5:]
        field_l = field_raw.lower()

    sys_prefix = f"{sys_part.lower()}_"
    if field_l.startswith(sys_prefix):
        field_raw = field_raw[len(sys_prefix):]

    field_part = normalize_name(field_raw)
    base = f"Zone_{sys_part}_{field_part}_exclusion"
    existing_lower = {n.lower() for n in existing_zone_nicknames}
    n = 1
    while True:
        candidate = f"{base}_{n}"
        if candidate.lower() not in existing_lower:
            return candidate
        n += 1


def build_exclusion_zone_entries(
    nickname: str,
    shape: str,
    pos: tuple[float, float, float],
    size: float | tuple[float, float, float],
    rotate: tuple[float, float, float] | None = None,
    comment: str | None = None,
    sort: int | None = None,
) -> list[tuple[str, str]]:
    """Baut den [Zone]-Eintragstext für eine Exclusion-Zone."""
    shape_up = (shape or "SPHERE").upper()
    if shape_up not in ("SPHERE", "ELLIPSOID", "BOX"):
        shape_up = "SPHERE"

    px, py, pz = pos
    if isinstance(size, tuple):
        sx, sy, sz = size
        size_str = f"{sx:.0f}, {sy:.0f}, {sz:.0f}"
    else:
        size_str = f"{float(size):.0f}"

    entries: list[tuple[str, str]] = [("nickname", nickname)]
    if comment:
        entries.append(("comment", comment.strip()))
    entries.append(("pos", f"{px:.0f}, {py:.0f}, {pz:.0f}"))
    if rotate is not None:
        rx, ry, rz = rotate
        entries.append(("rotate", f"{rx:.0f}, {ry:.0f}, {rz:.0f}"))
    entries.append(("shape", shape_up))
    entries.append(("size", size_str))
    entries.append(("property_flags", "131072"))
    if sort is not None:
        entries.append(("sort", str(int(sort))))
    return entries


def is_field_zone_nickname(
    sections: list[tuple[str, list[tuple[str, str]]]],
    zone_nickname: str,
) -> bool:
    """Prüft, ob Nickname in [Nebula]/[Asteroids] als zone referenziert wird."""
    target = (zone_nickname or "").strip().lower()
    if not target:
        return False
    for sec_name, entries in sections:
        if sec_name.lower() not in ("nebula", "asteroids"):
            continue
        for k, v in entries:
            if k.lower() == "zone" and v.strip().lower() == target:
                return True
    return False


def add_exclusion_entry(
    zone_entries: list[tuple[str, str]],
    exclusion_zone_nickname: str,
) -> tuple[list[tuple[str, str]], bool]:
    """Fügt `exclusion = ...` an den Zone-Eintrag an (ohne Duplikat)."""
    target = exclusion_zone_nickname.strip().lower()
    if not target:
        return list(zone_entries), False

    has_already = any(
        k.lower() == "exclusion" and v.strip().lower() == target
        for k, v in zone_entries
    )
    if has_already:
        return list(zone_entries), False

    out = list(zone_entries)
    last_excl_idx = -1
    for idx, (k, _v) in enumerate(out):
        if k.lower() == "exclusion":
            last_excl_idx = idx

    if last_excl_idx >= 0:
        out.insert(last_excl_idx + 1, ("exclusion", exclusion_zone_nickname))
    else:
        out.append(("exclusion", exclusion_zone_nickname))
    return out, True


def _find_zone_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """Gibt [Zone]-Blockbereiche als (start, end) in Zeilenindizes zurück."""
    headers: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        s = line.strip()
        if s.startswith("[") and s.endswith("]") and len(s) > 2:
            headers.append((idx, s[1:-1].strip().lower()))

    if not headers:
        return []

    blocks: list[tuple[int, int]] = []
    for i, (start, name) in enumerate(headers):
        end = headers[i + 1][0] if i + 1 < len(headers) else len(lines)
        if name == "zone":
            blocks.append((start, end))
    return blocks


def _block_nickname(lines: list[str], start: int, end: int) -> str:
    for i in range(start + 1, end):
        raw = lines[i].strip()
        if not raw or raw.startswith(";") or raw.startswith("//"):
            continue
        if "=" not in raw:
            continue
        k, _, v = raw.partition("=")
        if k.strip().lower() == "nickname":
            return v.strip()
    return ""


def patch_system_ini_for_exclusion(
    ini_text: str,
    field_zone_nickname: str,
    exclusion_zone_nickname: str,
    exclusion_zone_entries: list[tuple[str, str]],
    link_to_field_zone: bool = True,
) -> str:
    """Patcht System-INI minimal: Field-Zone um exclusion ergänzen + neuen [Zone]-Block anhängen."""
    lines = ini_text.splitlines()
    zone_blocks = _find_zone_blocks(lines)
    field_target = field_zone_nickname.strip().lower()

    if link_to_field_zone:
        field_block = None
        for start, end in zone_blocks:
            nick = _block_nickname(lines, start, end).lower()
            if nick == field_target:
                field_block = (start, end)
                break
        if field_block is None:
            raise ValueError(f"Field zone not found: {field_zone_nickname}")

        start, end = field_block
        has_link = False
        last_exclusion_line = None
        for i in range(start + 1, end):
            raw = lines[i].strip()
            if "=" not in raw:
                continue
            k, _, v = raw.partition("=")
            if k.strip().lower() == "exclusion":
                last_exclusion_line = i
                if v.strip().lower() == exclusion_zone_nickname.strip().lower():
                    has_link = True

        if not has_link:
            if last_exclusion_line is not None:
                insert_at = last_exclusion_line + 1
            else:
                last_kv_line = None
                for i in range(start + 1, end):
                    raw = lines[i].strip()
                    if raw and not raw.startswith(";") and not raw.startswith("//") and "=" in raw:
                        last_kv_line = i
                insert_at = (last_kv_line + 1) if last_kv_line is not None else end
            lines.insert(insert_at, f"exclusion = {exclusion_zone_nickname}")

    if lines and lines[-1].strip() != "":
        lines.append("")
    lines.append("[Zone]")
    for k, v in exclusion_zone_entries:
        lines.append(f"{k} = {v}")

    out = "\n".join(lines)
    if ini_text.endswith("\n"):
        out += "\n"
    return out


def patch_field_ini_exclusion_section(
    ini_text: str,
    exclusion_zone_nickname: str,
) -> tuple[str, bool]:
    """Ergänzt `[Exclusion Zones]` in der Feld-INI um `exclusion = ...`.

    Gibt `(patched_text, changed)` zurück.
    """
    target = exclusion_zone_nickname.strip()
    if not target:
        return ini_text, False

    lines = ini_text.splitlines()
    headers: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        s = line.strip()
        if s.startswith("[") and s.endswith("]") and len(s) > 2:
            headers.append((idx, s[1:-1].strip().lower()))

    excl_start = None
    excl_end = None
    for i, (start, name) in enumerate(headers):
        if name == "exclusion zones":
            excl_start = start
            excl_end = headers[i + 1][0] if i + 1 < len(headers) else len(lines)
            break

    changed = False

    if excl_start is None:
        prop_start = None
        prop_end = None
        for i, (start, name) in enumerate(headers):
            if name == "properties":
                prop_start = start
                prop_end = headers[i + 1][0] if i + 1 < len(headers) else len(lines)
                break

        if prop_start is not None and prop_end is not None:
            insert_at = prop_end
            block_lines: list[str] = []
            if insert_at > 0 and lines[insert_at - 1].strip() != "":
                block_lines.append("")
            block_lines.append("[Exclusion Zones]")
            block_lines.append(f"exclusion = {target}")
            if insert_at < len(lines) and lines[insert_at].strip() != "":
                block_lines.append("")
            lines[insert_at:insert_at] = block_lines
        else:
            if lines and lines[-1].strip() != "":
                lines.append("")
            lines.append("[Exclusion Zones]")
            lines.append(f"exclusion = {target}")
        changed = True
    else:
        has_entry = False
        last_excl_line = None
        for i in range(excl_start + 1, excl_end):
            raw = lines[i].strip()
            if not raw or raw.startswith(";") or raw.startswith("//") or "=" not in raw:
                continue
            k, _, v = raw.partition("=")
            if k.strip().lower() == "exclusion":
                last_excl_line = i
                if v.strip().lower() == target.lower():
                    has_entry = True
                    break
        if not has_entry:
            insert_at = (last_excl_line + 1) if last_excl_line is not None else excl_end
            lines.insert(insert_at, f"exclusion = {target}")
            changed = True

    out = "\n".join(lines)
    if ini_text.endswith("\n"):
        out += "\n"
    return out, changed
