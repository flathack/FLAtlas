# assets_db.py
from __future__ import annotations
from pathlib import Path
from typing import List
from flini import parse_blocks

def list_factions(initialworld_ini: Path) -> List[str]:
    text = initialworld_ini.read_text(encoding="utf-8", errors="ignore")
    _, blocks = parse_blocks(text)
    out = []
    for b in blocks:
        if b.name.lower() == "group":
            nick = b.get1("nickname")
            if nick:
                out.append(nick)
    return sorted(set(out))

def list_loadouts(loadouts_ini: Path) -> List[str]:
    text = loadouts_ini.read_text(encoding="utf-8", errors="ignore")
    _, blocks = parse_blocks(text)
    out = []
    for b in blocks:
        if b.name.lower() == "loadout":
            nick = b.get1("nickname")
            if nick:
                out.append(nick)
    return sorted(set(out))

def list_archetypes(solararch_ini: Path) -> List[str]:
    text = solararch_ini.read_text(encoding="utf-8", errors="ignore")
    _, blocks = parse_blocks(text)
    out = []
    for b in blocks:
        if b.name.lower() in ("solararch", "solar", "archetype"):  # mods variieren
            nick = b.get1("nickname") or b.get1("archetype")
            if nick:
                out.append(nick)
        # In Vanilla ist es oft [Solar] bzw. [SolarArch] je nach Template/Tooling.
    return sorted(set(out))
