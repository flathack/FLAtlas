"""Case-insensitive Pfadauflösung (Komponente für Komponente).

Erforderlich weil Freelancer-Dateien unter Windows geschrieben wurden,
aber auf Linux/Wine betrieben werden, wo Gross-/Kleinschreibung relevant ist.
"""

from __future__ import annotations

from pathlib import Path


def ci_find(base: Path, name: str) -> Path | None:
    """Findet einen Verzeichnis-/Dateieintrag in *base* case-insensitiv."""
    try:
        target = name.lower()
        for entry in base.iterdir():
            if entry.name.lower() == target:
                return entry
    except Exception:
        pass
    return None


def ci_resolve(base: Path, rel: str) -> Path | None:
    """Löst einen relativen Pfad (Backslash ODER Slash) von *base* aus
    vollständig case-insensitiv auf – Komponente für Komponente.

    Beispiel::

        base = /DATA/UNIVERSE/
        rel  = systems\\\\ST04\\\\ST04.ini
        →     /DATA/UNIVERSE/SYSTEMS/ST04/ST04.ini   (echter Pfad auf Disk)
    """
    parts = rel.replace("\\", "/").split("/")
    current = base
    for part in parts:
        if not part:
            continue
        found = ci_find(current, part)
        if found is None:
            return None
        current = found
    return current if current.is_file() else None


def parse_position(pos_str: str) -> tuple[float, float, float]:
    """Parst eine Freelancer-Positionsangabe ``'x, y, z'`` in ein Float-Tripel.

    Fehlende Komponenten werden mit 0.0 ergänzt; die dritte Komponente
    fällt auf die zweite zurück wenn sie fehlt (FL-Konvention).
    """
    parts = [p.strip() for p in pos_str.split(",")]
    fx = float(parts[0]) if len(parts) > 0 and parts[0] else 0.0
    fy = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
    fz = (
        float(parts[2])
        if len(parts) > 2 and parts[2]
        else (float(parts[1]) if len(parts) > 1 and parts[1] else 0.0)
    )
    return fx, fy, fz


def format_position(fx: float, fy: float, fz: float) -> str:
    """Formatiert ein Float-Tripel als Freelancer-Positionsangabe."""
    return f"{fx:.2f}, {fy:.2f}, {fz:.2f}"
