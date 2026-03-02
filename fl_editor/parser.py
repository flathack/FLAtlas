"""INI-Parser für Freelancer-Dateien (unterstützt doppelte Schlüssel)
sowie Hilfsfunktionen zum Auffinden von universe.ini und Systemen.
"""

from __future__ import annotations

from pathlib import Path

from .path_utils import ci_find, ci_resolve


class FLParser:
    """Parst Freelancer-INI-Dateien, die (abweichend vom Standard)
    doppelte Schlüssel innerhalb einer Sektion verwenden können.

    Rückgabe von :meth:`parse` ist eine Liste von
    ``(section_name, [(key, value), …])``-Tupeln.
    """

    # ------------------------------------------------------------------
    #  Kernparser
    # ------------------------------------------------------------------
    def parse(self, filepath: str) -> list[tuple[str, list[tuple[str, str]]]]:
        sections: list[tuple[str, list[tuple[str, str]]]] = []
        cur_name: str | None = None
        cur_entries: list[tuple[str, str]] = []

        with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith(";") or line.startswith("//"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    if cur_name is not None:
                        sections.append((cur_name, cur_entries))
                    cur_name = line[1:-1].strip()
                    cur_entries = []
                elif "=" in line and cur_name is not None:
                    sem = line.find(";")
                    if sem > 0:
                        line = line[:sem].strip()
                    k, _, v = line.partition("=")
                    cur_entries.append((k.strip(), v.strip()))

        if cur_name is not None:
            sections.append((cur_name, cur_entries))
        return sections

    # ------------------------------------------------------------------
    #  Hilfsfunktionen
    # ------------------------------------------------------------------
    @staticmethod
    def _build(entries: list[tuple[str, str]]) -> dict:
        d: dict = {"_entries": list(entries)}
        for k, v in entries:
            if k.lower() not in d:
                d[k.lower()] = v
        return d

    def get_objects(self, sections: list[tuple[str, list[tuple[str, str]]]]) -> list[dict]:
        return [self._build(e) for n, e in sections if n.lower() == "object"]

    def get_zones(self, sections: list[tuple[str, list[tuple[str, str]]]]) -> list[dict]:
        return [self._build(e) for n, e in sections if n.lower() == "zone"]


# ------------------------------------------------------------------
#  System-Finder  (universe.ini → alle System-INI-Dateien)
# ------------------------------------------------------------------

def find_universe_ini(game_path: str) -> Path | None:
    """Sucht ``universe.ini`` ab *game_path* – vollständig case-insensitiv.

    Unterstützte Strukturen::

        <path>/DATA/UNIVERSE/universe.ini   ← Standard
        <path>/UNIVERSE/universe.ini
        <path>/universe.ini
    """
    base = Path(game_path)
    if not base.exists():
        return None
    for components in [
        ["DATA", "UNIVERSE", "universe.ini"],
        ["UNIVERSE", "universe.ini"],
        ["universe.ini"],
    ]:
        result = ci_resolve(base, "/".join(components))
        if result:
            return result
    return None


def find_all_systems(game_path: str, parser: FLParser, fallback_root: str | None = None) -> list[dict]:
    """Liest ``universe.ini`` und gibt alle ``[system]``-Einträge mit
    aufgelöstem absolutem Dateipfad zurück.

    Jeder Eintrag enthält ``nickname``, ``path`` und ``pos`` (Navmap-Tupel).
    """
    uni_ini = find_universe_ini(game_path)
    if not uni_ini:
        return []

    uni_dir = uni_ini.parent      # …/DATA/UNIVERSE/
    data_dir = uni_dir.parent     # …/DATA/

    sections = parser.parse(str(uni_ini))
    systems: list[dict] = []

    for sec_name, entries in sections:
        if sec_name.lower() != "system":
            continue
        d: dict = {}
        for k, v in entries:
            if k.lower() not in d:
                d[k.lower()] = v
        if "file" not in d:
            continue

        nickname = d.get("nickname", "???:?")
        file_rel = d["file"].strip()

        # Navmap-Positionen aus universe.ini (x, y)
        pos = (0.0, 0.0)
        if "pos" in d:
            parts = [p.strip() for p in d["pos"].split(",")]
            try:
                x = float(parts[0]) if len(parts) >= 1 and parts[0] else 0.0
                y = float(parts[1]) if len(parts) >= 2 and parts[1] else 0.0
                pos = (x, y)
            except ValueError:
                pass

        sys_path = None
        for search_base in (uni_dir, data_dir):
            resolved = ci_resolve(search_base, file_rel)
            if resolved:
                sys_path = resolved
                break
        if sys_path is None and fallback_root:
            fb_uni = find_universe_ini(fallback_root)
            if fb_uni:
                fb_uni_dir = fb_uni.parent
                fb_data_dir = fb_uni_dir.parent
                for search_base in (fb_uni_dir, fb_data_dir):
                    resolved = ci_resolve(search_base, file_rel)
                    if resolved:
                        sys_path = resolved
                        break

        strid_name = d.get("strid_name", "").strip()
        ids_name = d.get("ids_name", "").strip()
        if sys_path:
            systems.append(
                {
                    "nickname": nickname,
                    "path": str(sys_path),
                    "pos": pos,
                    "ids_name": ids_name or strid_name,
                    "strid_name": strid_name,
                }
            )

    return sorted(systems, key=lambda x: x["nickname"].lower())
