from __future__ import annotations

import re


def _normalize_entry_pairs(entries: list[tuple[str, str]] | list[list[str]] | None) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for row in list(entries or []):
        if not isinstance(row, (list, tuple)) or len(row) < 2:
            continue
        out.append((str(row[0]), str(row[1])))
    return out


def find_base_builder_parent_nickname(
    entries: list[tuple[str, str]] | list[list[str]] | None,
) -> str:
    for key, value in _normalize_entry_pairs(entries):
        if str(key).strip().lower() == "parent":
            return str(value).strip()
    return ""


def is_base_builder_child_entries(
    entries: list[tuple[str, str]] | list[list[str]] | None,
    parent_base_nickname: str | None = None,
) -> bool:
    parent = find_base_builder_parent_nickname(entries)
    if not parent:
        return False
    target = str(parent_base_nickname or "").strip()
    if not target:
        return True
    return parent.lower() == target.lower()


def suggest_base_builder_part_nickname(
    base_nickname: str,
    existing_nicknames: list[str] | tuple[str, ...],
    *,
    width: int = 3,
) -> str:
    base = re.sub(r"[^A-Za-z0-9_]+", "_", str(base_nickname or "").strip()).strip("_") or "base"
    prefix = f"{base}_part_"
    used: list[int] = []
    pat = re.compile(rf"^{re.escape(prefix)}(\d+)$", re.IGNORECASE)
    for raw_name in existing_nicknames:
        match = pat.match(str(raw_name).strip())
        if not match:
            continue
        try:
            used.append(int(match.group(1)))
        except ValueError:
            pass
    nxt = (max(used) + 1) if used else 1
    return f"{prefix}{nxt:0{max(1, int(width))}d}"


def build_base_builder_part_entries(
    *,
    parent_nickname: str,
    part_nickname: str,
    archetype: str,
    pos_xyz: tuple[float, float, float],
    rotate_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0),
    reputation: str = "",
    loadout: str = "",
) -> list[tuple[str, str]]:
    px, py, pz = pos_xyz
    rx, ry, rz = rotate_xyz
    entries: list[tuple[str, str]] = [
        ("nickname", str(part_nickname).strip()),
        ("archetype", str(archetype).strip()),
        ("pos", f"{float(px):.2f}, {float(py):.2f}, {float(pz):.2f}"),
        ("rotate", f"{float(rx):.2f}, {float(ry):.2f}, {float(rz):.2f}"),
        ("parent", str(parent_nickname).strip()),
        ("visit", "0"),
    ]
    if str(loadout).strip():
        entries.append(("loadout", str(loadout).strip()))
    if str(reputation).strip():
        entries.append(("reputation", str(reputation).strip()))
    return entries
