"""INI-Parser für Freelancer-Dateien (unterstützt doppelte Schlüssel)
sowie Hilfsfunktionen zum Auffinden von universe.ini und Systemen.
"""

from __future__ import annotations

from pathlib import Path

from .path_utils import ci_find, ci_resolve
from .bini import is_bini_bytes, decode_bini_to_ini_text


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

        raw_bytes = Path(filepath).read_bytes()
        if is_bini_bytes(raw_bytes):
            text = decode_bini_to_ini_text(raw_bytes)
        else:
            try:
                text = raw_bytes.decode("utf-8")
            except Exception:
                text = raw_bytes.decode("cp1252", errors="ignore")

        for raw in text.splitlines():
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
    def _collect_multiuniverse_positions(
        uni_dir: Path,
    ) -> tuple[dict[str, list[tuple[str, tuple[float, float]]]], dict[str, list[str]]]:
        result: dict[str, list[tuple[str, tuple[float, float]]]] = {}
        map_label_ids: dict[str, list[str]] = {}
        multi_ini = ci_resolve(uni_dir, "multiuniverse.ini")
        if not multi_ini:
            return result, map_label_ids
        try:
            sections = parser.parse(str(multi_ini))
        except Exception:
            return result, map_label_ids

        for sec_name, entries in sections:
            if sec_name.strip().lower() != "sector":
                continue
            sector_name = ""
            for k, v in entries:
                if k.strip().lower() == "mapping":
                    sector_name = str(v or "").split(",")[0].strip()
                    break
            if not sector_name:
                continue
            sector_key = sector_name.lower()
            label_ids: list[str] = map_label_ids.setdefault(sector_key, [])
            for k, v in entries:
                if k.strip().lower() != "label":
                    continue
                first = str(v or "").split(",")[0].strip()
                if first and first not in label_ids:
                    label_ids.append(first)
            for k, v in entries:
                if k.strip().lower() != "system":
                    continue
                parts = [p.strip() for p in str(v or "").split(",")]
                if len(parts) < 3:
                    continue
                nick = str(parts[0] or "").strip()
                if not nick:
                    continue
                try:
                    sx = float(parts[1]) if parts[1] else 0.0
                    sy = float(parts[2]) if parts[2] else 0.0
                except ValueError:
                    continue
                key = nick.upper()
                bucket = result.setdefault(key, [])
                exists = False
                for map_name, _pos in bucket:
                    if map_name.lower() == sector_name.lower():
                        exists = True
                        break
                if not exists:
                    bucket.append((sector_name, (sx, sy)))
        return result, map_label_ids

    def _pick_display_pos(
        base_pos: tuple[float, float],
        map_positions: list[tuple[str, tuple[float, float]]],
        pos_counts: dict[tuple[float, float], int],
    ) -> tuple[tuple[float, float], str]:
        if not map_positions:
            return base_pos, "universe"
        # Prefer the vanilla sector when present, otherwise the first map
        # entry from multiuniverse.ini.
        preferred_map_name, preferred_pos = map_positions[0]
        for map_name, map_pos in map_positions:
            if map_name.strip().lower() == "sector01":
                preferred_map_name, preferred_pos = map_name, map_pos
                break

        rounded = (round(float(base_pos[0]), 3), round(float(base_pos[1]), 3))
        stacked = int(pos_counts.get(rounded, 0)) >= 8
        if stacked:
            return preferred_pos, preferred_map_name
        return base_pos, "universe"

    def _collect_from_root(root: str, fb_root: str | None = None) -> list[dict]:
        uni_ini = find_universe_ini(root)
        if not uni_ini:
            return []

        uni_dir = uni_ini.parent      # …/DATA/UNIVERSE/
        data_dir = uni_dir.parent     # …/DATA/
        sections = parser.parse(str(uni_ini))
        multi_positions, multi_label_ids = _collect_multiuniverse_positions(uni_dir)
        out: list[dict] = []
        system_entries: list[dict[str, str]] = []
        pos_counts: dict[tuple[float, float], int] = {}

        for sec_name, entries in sections:
            if sec_name.lower() != "system":
                continue
            d: dict[str, str] = {}
            for k, v in entries:
                kl = k.lower()
                if kl not in d:
                    d[kl] = v
            if "file" not in d:
                continue
            pos = (0.0, 0.0)
            if "pos" in d:
                parts = [p.strip() for p in str(d["pos"]).split(",")]
                try:
                    x = float(parts[0]) if len(parts) >= 1 and parts[0] else 0.0
                    y = float(parts[1]) if len(parts) >= 2 and parts[1] else 0.0
                    pos = (x, y)
                except ValueError:
                    pass
            rp = (round(float(pos[0]), 3), round(float(pos[1]), 3))
            pos_counts[rp] = int(pos_counts.get(rp, 0)) + 1
            d["_base_pos"] = f"{pos[0]},{pos[1]}"
            system_entries.append(d)

        for d in system_entries:
            nickname = d.get("nickname", "???:?")
            file_rel = d["file"].strip()

            pos = (0.0, 0.0)
            base_parts = [p.strip() for p in str(d.get("_base_pos", "")).split(",")]
            try:
                if len(base_parts) >= 2:
                    pos = (float(base_parts[0]), float(base_parts[1]))
            except ValueError:
                pos = (0.0, 0.0)

            nick_key = str(nickname or "").upper()
            nick_maps = list(multi_positions.get(nick_key, []))
            display_pos, source_map = _pick_display_pos(pos, nick_maps, pos_counts)

            sys_path = None
            for search_base in (uni_dir, data_dir):
                resolved = ci_resolve(search_base, file_rel)
                if resolved:
                    sys_path = resolved
                    break
            if sys_path is None and fb_root:
                fb_uni = find_universe_ini(fb_root)
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
                out.append(
                    {
                        "nickname": nickname,
                        "path": str(sys_path),
                        "pos": display_pos,
                        "universe_pos": pos,
                        "pos_source_map": source_map,
                        "map_positions": [
                            {
                                "map": map_name,
                                "pos": map_pos,
                                "label_ids": list(multi_label_ids.get(str(map_name).lower(), [])),
                            }
                            for map_name, map_pos in nick_maps
                        ],
                        "ids_name": ids_name or strid_name,
                        "strid_name": strid_name,
                    }
                )
        return out

    systems = _collect_from_root(game_path, fb_root=fallback_root)
    if systems:
        return sorted(systems, key=lambda x: x["nickname"].lower())
    if fallback_root:
        fb = _collect_from_root(fallback_root, fb_root=None)
        if fb:
            return sorted(fb, key=lambda x: x["nickname"].lower())
    return []
