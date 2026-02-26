"""Generator für systems_shortest_path.ini, shortest_legal_path.ini
und shortest_illegal_path.ini.

Baut den Verbindungsgraphen aus allen System-INI-Dateien und berechnet
per BFS die kürzesten Pfade.
"""

from __future__ import annotations

import re
from collections import deque
from pathlib import Path

from .parser import FLParser, find_all_systems, find_universe_ini
from .path_utils import ci_resolve


# ------------------------------------------------------------------
#  Graph aufbauen
# ------------------------------------------------------------------

def _build_connection_graph(game_path: str, parser: FLParser
                            ) -> tuple[dict[str, set[str]],
                                       dict[str, set[str]],
                                       dict[str, set[str]]]:
    """Liest alle Systeme und gibt drei Adjazenzlisten zurück:

    - ``graph_all``   – Jump Gates + Jump Holes  (→ systems_shortest_path)
    - ``graph_legal`` – nur Jump Gates            (→ shortest_legal_path)
    - ``graph_illegal`` – nur Jump Holes          (→ shortest_illegal_path)

    Schlüssel/Werte sind uppercase System-Nicknames.
    """
    systems = find_all_systems(game_path, parser)

    graph_all: dict[str, set[str]] = {}
    graph_legal: dict[str, set[str]] = {}
    graph_illegal: dict[str, set[str]] = {}

    # Alle Systeme als Knoten anlegen (auch isolierte)
    for s in systems:
        nick = s["nickname"].upper()
        graph_all.setdefault(nick, set())
        graph_legal.setdefault(nick, set())
        graph_illegal.setdefault(nick, set())

    for s in systems:
        src = s["nickname"].upper()
        try:
            secs = parser.parse(s["path"])
        except Exception:
            continue
        for obj in parser.get_objects(secs):
            arch = obj.get("archetype", "").lower()
            is_gate = "jumpgate" in arch or "nomad_gate" in arch
            is_hole = arch.startswith("jumphole")
            if not is_gate and not is_hole:
                continue

            # Ziel ermitteln
            dest = None
            goto = obj.get("goto", "")
            if goto:
                dest = goto.split(",")[0].strip().upper()
            if not dest:
                m = re.search(r"to_([A-Za-z0-9]+)", obj.get("nickname", ""), re.I)
                if m:
                    dest = m.group(1).upper()
            if not dest or dest == src:
                continue

            # Kanten eintragen (bidirektional)
            graph_all.setdefault(src, set()).add(dest)
            graph_all.setdefault(dest, set()).add(src)

            if is_gate:
                graph_legal.setdefault(src, set()).add(dest)
                graph_legal.setdefault(dest, set()).add(src)
            else:
                graph_illegal.setdefault(src, set()).add(dest)
                graph_illegal.setdefault(dest, set()).add(src)

    return graph_all, graph_legal, graph_illegal


# ------------------------------------------------------------------
#  BFS  – kürzeste Pfade von einem Quellknoten zu allen anderen
# ------------------------------------------------------------------

def _bfs_all(graph: dict[str, set[str]], source: str
             ) -> dict[str, list[str]]:
    """Gibt ``{ziel: [source, hop1, hop2, …, ziel]}`` zurück.

    Nicht erreichbare Ziele sind nicht im Ergebnis enthalten.
    """
    paths: dict[str, list[str]] = {source: [source]}
    visited: set[str] = {source}
    queue: deque[str] = deque([source])

    while queue:
        node = queue.popleft()
        for neighbour in sorted(graph.get(node, [])):
            if neighbour not in visited:
                visited.add(neighbour)
                paths[neighbour] = paths[node] + [neighbour]
                queue.append(neighbour)

    return paths


# ------------------------------------------------------------------
#  INI-Datei schreiben
# ------------------------------------------------------------------

def _write_path_file(filepath: Path,
                     graph: dict[str, set[str]],
                     all_systems: list[str]):
    """Schreibt eine shortest-path-INI-Datei.

    Pro Quellsystem wird eine ``[SystemConnections]``-Sektion erzeugt mit
    je einer ``Path``-Zeile für jedes erreichbare Zielsystem.
    """
    lines: list[str] = []

    # Nur Systeme, die im Graphen Nachbarn haben ODER im Graphen vorkommen
    # und von mindestens einem anderen System erreichbar sind.
    for source in all_systems:
        if source not in graph:
            continue
        paths = _bfs_all(graph, source)
        if not paths:
            continue

        # Alle erreichbaren Ziele (ausgehend von jeweiligem Graphen)
        reachable = sorted(paths.keys(), key=str.upper)
        if not reachable:
            continue

        lines.append("[SystemConnections]")
        for dest in reachable:
            route = paths[dest]
            lines.append(f"Path = {source}, {dest}, {', '.join(route)}")
        lines.append("")

    # Schreiben (kein Backup)
    filepath.write_text("\n".join(lines), encoding="utf-8")


# ------------------------------------------------------------------
#  Öffentliche API
# ------------------------------------------------------------------

def regenerate_shortest_paths(game_path: str, parser: FLParser) -> str:
    """Berechnet alle drei shortest-path-Dateien neu.

    Gibt eine Statusmeldung zurück.
    """
    uni_ini = find_universe_ini(game_path)
    if not uni_ini:
        return "Fehler: universe.ini nicht gefunden"

    uni_dir = uni_ini.parent  # …/DATA/UNIVERSE/

    graph_all, graph_legal, graph_illegal = _build_connection_graph(
        game_path, parser
    )

    # Quellsysteme: die aus dem jeweiligen Graphen, die Verbindungen haben
    # systems_shortest_path: alle Systeme die im kombinierten Graphen erreichbar sind
    all_systems_all = sorted(graph_all.keys())
    all_systems_legal = sorted(
        s for s in graph_legal if graph_legal[s]  # nur mit Nachbarn
    )
    all_systems_illegal = sorted(
        s for s in graph_illegal if graph_illegal[s]
    )

    # Dateipfade (case-insensitive auflösen, falls vorhanden)
    def _resolve_or_create(name: str) -> Path:
        resolved = ci_resolve(uni_dir, name)
        return resolved if resolved else uni_dir / name

    f_all = _resolve_or_create("systems_shortest_path.ini")
    f_legal = _resolve_or_create("shortest_legal_path.ini")
    f_illegal = _resolve_or_create("shortest_illegal_path.ini")

    _write_path_file(f_all, graph_all, all_systems_all)
    _write_path_file(f_legal, graph_legal, all_systems_legal)
    _write_path_file(f_illegal, graph_illegal, all_systems_illegal)

    return (
        f"✔  Shortest-Path-Dateien aktualisiert: "
        f"{len(all_systems_all)} Systeme (all), "
        f"{len(all_systems_legal)} (legal), "
        f"{len(all_systems_illegal)} (illegal)"
    )
