"""Shared DEV status metadata and normalization helpers."""

from __future__ import annotations

from typing import Any

DEFAULT_DEV_STATUS_STATES: list[dict[str, str]] = [
    {"id": "pre_alpha", "label": "Pre Alpha", "description": "Very buggy, major changes expected."},
    {"id": "alpha", "label": "Alpha", "description": "Core exists, still unstable and incomplete."},
    {"id": "beta", "label": "Beta", "description": "Feature complete enough, testing and polish ongoing."},
    {"id": "release_candidate", "label": "Release Candidate", "description": "Near release, only critical fixes expected."},
    {"id": "gold", "label": "Gold", "description": "Release quality and considered stable."},
]

DEFAULT_DEV_STATUS_BY_NAV: dict[str, str] = {
    "universe": "beta",
    "viewer_3d": "beta",
    "trade_routes": "beta",
    "name_editor": "beta",
    "mod_manager": "alpha",
    "npc_editor": "alpha",
    "rumor_editor": "alpha",
    "news_editor": "alpha",
    "savegame_editor": "alpha",
    "settings": "beta",
}

DEFAULT_DEV_STATUS_FEATURES_BY_NAV: dict[str, dict[str, list[str]]] = {
    "universe": {
        "implemented": [
            "2D Universe-Map mit Systemknoten und Verbindungen",
            "System-Positionen laden/speichern (universe.ini)",
            "Direktes Springen in den System-Editor",
        ],
        "missing": [
            "Erweiterte Validierung aller Universe-Referenzen",
            "Mehrstufige Konfliktanalyse für große Total-Conversion-Mods",
        ],
    },
    "trade_routes": {
        "implemented": [
            "Trade-Route-Liste mit Filtern und Profitberechnung",
            "Bearbeitung von MarketGood-Einträgen",
            "Persistenz benutzerdefinierter Routen",
        ],
        "missing": [
            "Interaktive Routen-Visualisierung auf der Universe-Map",
            "Szenario-/Balancing-Assistent für Ökonomie-Änderungen",
        ],
    },
    "viewer_3d": {
        "implemented": [
            "Universe / System Map: 3D Ansicht von echten Freelancer Models",
            "3D Objektvorschau für unterstützte Asset-Typen",
            "Native Scene-/Mesh-Ladepfade mit Fallback-Logik",
        ],
        "missing": [
            "Vollständige Abdeckung aller exotischen Freelancer-Asset-Varianten",
            "Erweiterte Diagnoseoberfläche für problematische Modellketten",
        ],
    },
    "name_editor": {
        "implemented": [
            "IDS Name/Info Anzeige mit DLL-Auflösung",
            "Suche/Filter in Name- und Info-Ansicht",
            "Schreiben neuer IDS-Einträge in Resource-DLL",
        ],
        "missing": [
            "Bulk-Workflow mit Konfliktvorschau vor dem Schreiben",
            "Kompletter Diff-Workflow zwischen Mod und Vanilla-IDS",
        ],
    },
    "mod_manager": {
        "implemented": [
            "Repo- und Direct-Profile verwalten",
            "Aktivieren/Deaktivieren mit Backup/Restore",
            "Bearbeitungskontext und Zielinstallation setzen",
        ],
        "missing": [
            "Komplette FLMM-Script-Abdeckung aller Spezialmethoden",
            "Erweiterte Diagnoseansicht für Aktivierungsfehler (guided fixes)",
        ],
    },
    "npc_editor": {
        "implemented": [
            "NPC-Listen laden und bearbeiten",
            "Änderungen in INI-Sektionen zurückschreiben",
        ],
        "missing": [
            "Komfort-Workflows für Batch-Änderungen über mehrere Dateien",
            "Tiefe Validierung von NPC-Referenzen",
        ],
    },
    "rumor_editor": {
        "implemented": [
            "Gerüchteeinträge anzeigen/bearbeiten",
            "IDS-Textauflösung für zugehörige Text-IDs",
        ],
        "missing": [
            "Strukturierte Vorlagen und Qualitätschecks für neue Rumors",
            "Cross-File Konsistenzprüfung (MBase/News/Rumor Links)",
        ],
    },
    "news_editor": {
        "implemented": [
            "News-Einträge laden/bearbeiten",
            "Speichern inkl. ids_name/ids_info-Verknüpfungen",
        ],
        "missing": [
            "Workflow für Serien-/Kampagnen-News",
            "Kontextabhängige Validierung gegen Fraktionen/Orte",
        ],
    },
    "settings": {
        "implemented": [
            "Theme- und Sprachumschaltung",
            "Mod-Manager, XML-Editor und BINI-Einstellungen",
            "DLL-Fallback-Debug-Ansicht",
        ],
        "missing": [
            "Import/Export kompletter FLAtlas-Profile",
            "Erweiterte Validierungsassistenten für Pfadkonfigurationen",
        ],
    },
}

DEV_STATUS_NAV_ITEMS: list[tuple[str, str]] = [
    ("universe", "dev_status.nav.universe"),
    ("viewer_3d", "dev_status.nav.viewer_3d"),
    ("trade_routes", "dev_status.nav.trade_routes"),
    ("name_editor", "dev_status.nav.name_editor"),
    ("mod_manager", "dev_status.nav.mod_manager"),
    ("npc_editor", "dev_status.nav.npc_editor"),
    ("rumor_editor", "dev_status.nav.rumor_editor"),
    ("news_editor", "dev_status.nav.news_editor"),
    ("settings", "dev_status.nav.settings"),
]


def default_dev_status_states() -> list[dict[str, str]]:
    return [dict(row) for row in DEFAULT_DEV_STATUS_STATES]


def dev_status_nav_items() -> list[tuple[str, str]]:
    return list(DEV_STATUS_NAV_ITEMS)


def default_dev_status_by_nav() -> dict[str, str]:
    return dict(DEFAULT_DEV_STATUS_BY_NAV)


def default_dev_status_features_by_nav() -> dict[str, dict[str, list[str]]]:
    out: dict[str, dict[str, list[str]]] = {}
    for nav_key, payload in DEFAULT_DEV_STATUS_FEATURES_BY_NAV.items():
        out[str(nav_key)] = {
            "implemented": [str(x) for x in payload.get("implemented", []) if str(x).strip()],
            "missing": [str(x) for x in payload.get("missing", []) if str(x).strip()],
        }
    return out


def normalize_dev_status_config(app: Any) -> tuple[list[dict[str, str]], dict[str, str]]:
    states = default_dev_status_states()
    status_by_nav: dict[str, str] = {}
    if app is None:
        return states, status_by_nav

    raw_states = app.property("dev_status_states")
    raw_map = app.property("dev_status_by_nav")

    if isinstance(raw_states, list):
        parsed_states: list[dict[str, str]] = []
        for state in raw_states:
            if not isinstance(state, dict):
                continue
            state_id = str(state.get("id", "") or "").strip()
            if not state_id:
                continue
            parsed_states.append(
                {
                    "id": state_id,
                    "label": str(state.get("label", state_id) or state_id).strip(),
                    "description": str(state.get("description", "") or "").strip(),
                }
            )
        if parsed_states:
            states = parsed_states

    if isinstance(raw_map, dict):
        status_by_nav = {
            str(key or "").strip().lower(): str(value or "").strip().lower()
            for key, value in raw_map.items()
            if str(key or "").strip()
        }

    return states, status_by_nav


def normalize_dev_status_features_config(app: Any) -> dict[str, dict[str, list[str]]]:
    features = default_dev_status_features_by_nav()
    if app is None:
        return features
    raw = app.property("dev_status_features_by_nav")
    if not isinstance(raw, dict):
        return features
    for nav_key, payload in raw.items():
        key = str(nav_key or "").strip().lower()
        if not key or not isinstance(payload, dict):
            continue
        impl_raw = payload.get("implemented", [])
        miss_raw = payload.get("missing", [])
        implemented = [str(x).strip() for x in impl_raw] if isinstance(impl_raw, list) else []
        missing = [str(x).strip() for x in miss_raw] if isinstance(miss_raw, list) else []
        features[key] = {
            "implemented": [x for x in implemented if x],
            "missing": [x for x in missing if x],
        }
    return features


def build_dev_status_legend_lines(states: list[dict[str, str]]) -> list[str]:
    legend_lines: list[str] = []
    for state in states:
        label = str(state.get("label", "") or "").strip()
        description = str(state.get("description", "") or "").strip()
        if label:
            legend_lines.append(f"- {label}: {description}" if description else f"- {label}")
    return legend_lines


def build_dev_status_rows(
    states: list[dict[str, str]],
    status_by_nav: dict[str, str],
    nav_items: list[tuple[str, str]],
    tr_func,
) -> list[tuple[str, str, str]]:
    state_map = {str(state.get("id", "")).strip().lower(): state for state in states}
    rows: list[tuple[str, str, str]] = []
    for nav_key, nav_label in nav_items:
        state_id = str(status_by_nav.get(nav_key, "") or "").strip().lower()
        state = state_map.get(state_id)
        state_label = str(state.get("label", tr_func("dev_status.unknown")) if state else tr_func("dev_status.unknown"))
        state_desc = str(state.get("description", "") if state else "")
        rows.append((str(tr_func(nav_label)), state_label, state_desc))
    return rows
