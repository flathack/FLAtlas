"""Case-insensitive Pfadauflösung (Komponente für Komponente).

Erforderlich weil Freelancer-Dateien unter Windows geschrieben wurden,
aber auf Linux/Wine betrieben werden, wo Gross-/Kleinschreibung relevant ist.
"""

from __future__ import annotations

from pathlib import Path
import re


def _ci_name_key(value: str) -> str:
    return re.sub(r"[_\-\s]+", "", str(value or "").strip().lower())


def ci_find(base: Path, name: str) -> Path | None:
    """Findet einen Verzeichnis-/Dateieintrag in *base* case-insensitiv."""
    try:
        target_raw = str(name)
        target = target_raw.lower()
        target_key = _ci_name_key(target_raw)
        fallback: Path | None = None
        normalized_fallback: Path | None = None
        for entry in base.iterdir():
            # Bei kollidierenden Namen (z.B. ASTEROIDS + asteroids) zuerst
            # exakte Schreibweise bevorzugen.
            if entry.name == target_raw:
                return entry
            if fallback is None and entry.name.lower() == target:
                fallback = entry
            if normalized_fallback is None and _ci_name_key(entry.name) == target_key:
                normalized_fallback = entry
        if fallback is not None:
            return fallback
        if normalized_fallback is not None:
            return normalized_fallback
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
    parts = [p.strip() for p in str(pos_str).split(",")]
    try:
        fx = float(parts[0]) if len(parts) > 0 and parts[0] else 0.0
        fy = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
        fz = (
            float(parts[2])
            if len(parts) > 2 and parts[2]
            else (float(parts[1]) if len(parts) > 1 and parts[1] else 0.0)
        )
        return fx, fy, fz
    except (TypeError, ValueError):
        # Fallback für inkonsistente Daten wie "-32 154" (whitespace-getrennt)
        # oder Strings mit sonstigen Trennzeichen.
        nums = re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", str(pos_str))
        if not nums:
            return 0.0, 0.0, 0.0
        fx = float(nums[0])
        fy = float(nums[1]) if len(nums) > 1 else 0.0
        fz = float(nums[2]) if len(nums) > 2 else fy
        return fx, fy, fz


def format_position(fx: float, fy: float, fz: float) -> str:
    """Formatiert ein Float-Tripel als Freelancer-Positionsangabe."""
    return f"{fx:.2f}, {fy:.2f}, {fz:.2f}"


def is_offmap_helper_object_data(data: dict[str, object] | None) -> bool:
    """Return True for helper objects that should not affect map framing.

    Some mods place self-referencing beam targets far outside the playable
    system (for example at ``z = 1000000``). They are runtime helpers rather
    than real system anchors and would otherwise blow up the 2D/3D map scale.
    """
    if not isinstance(data, dict):
        return False

    nickname = str(data.get("nickname", "") or "").strip()
    nickname_lower = nickname.lower()
    archetype = str(data.get("archetype", "") or "").strip().lower()

    if "beam_target" in nickname_lower:
        return True
    if not any(token in archetype for token in ("jumphole", "jump_hole")):
        return False

    base_value = str(data.get("base", "") or "").strip()
    dock_with = str(data.get("dock_with", "") or "").strip()
    if not nickname:
        return False
    self_linked = nickname.lower() == base_value.lower() or nickname.lower() == dock_with.lower()
    if not self_linked:
        return False

    fx, _fy, fz = parse_position(str(data.get("pos", "0,0,0") or "0,0,0"))
    return max(abs(float(fx)), abs(float(fz))) >= 900000.0
