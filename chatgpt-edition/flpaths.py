# flpaths.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass
class FLPaths:
    install: Path
    data: Path
    universe: Path
    initialworld: Path
    loadouts: Path
    solararch: Path

def make_paths(install: Path) -> FLPaths:
    data = install / "DATA"
    return FLPaths(
        install=install,
        data=data,
        universe=data / "UNIVERSE",
        initialworld=data / "initialworld.ini",   # Schreibweise ist oft genau so
        loadouts=data / "EQUIPMENT" / "loadouts.ini",
        solararch=data / "SOLAR" / "solararch.ini",
    )

def _resolve_child_case_insensitive(parent: Path, child_name: str) -> Path:
    """Findet child_name unter parent unabhängig von Groß/Kleinschreibung.
    Fällt zurück auf parent/child_name, wenn parent nicht existiert oder nichts passt.
    """
    if not parent.exists() or not parent.is_dir():
        return parent / child_name

    target = child_name.casefold()
    for entry in parent.iterdir():
        if entry.name.casefold() == target:
            return entry
    return parent / child_name


def resolve_path_case_insensitive(base: Path, rel: str) -> Path:
    """Resolve a relative path like 'systems\\li01\\li01.ini' on case-sensitive FS."""
    rel = rel.replace("\\", "/").strip("/")

    p = base
    for part in rel.split("/"):
        if part in ("", "."):
            continue
        p = _resolve_child_case_insensitive(p, part)
    return p
