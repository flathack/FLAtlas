# FLAtlas Soll-/Ist-Abgleich

Stand: 2026-03-10

## Kurzfazit

FLAtlas ist produktseitig schon mehr als ein reiner System-Editor, aber die Codebasis bildet diese Produktbreite noch unzureichend modular ab. Der groesste Engpass ist die starke Zentralisierung in `fl_editor/main_window.py`.

## Anforderungen vs. Ist-Zustand

### Produktumfang

- Soll: Universe, System, Trade, Name/Info, Mod Manager, INI und Savegame-Flows sind als konsistentes Produkt erkennbar.
- Ist: Funktionsumfang ist vorhanden, aber README/Help liefen dem Produktstand teils hinterher.
- Massnahme: README aktualisiert, Help erweitert, Projektplan und Review-Dokument angelegt.

### Architektur

- Soll: UI-Logik, Workflow-Logik und Daten-/String-Helfer sind getrennt.
- Ist: `main_window.py` vereint Produktnavigation, UI-Bau, Produktlogik, Parser-Helfer und Doku-/Status-Helfer in einer Datei mit rund 30k Zeilen.
- Massnahme: Reine Hilfslogik nach `fl_editor/dev_status.py`, `fl_editor/help_content.py` und `fl_editor/infocard_utils.py` ausgelagert.

### UX

- Soll: Hauptpfade sind ohne versteckte Vorbedingungen nachvollziehbar.
- Ist: Produktfluss ist da, aber Dokumentation war unvollstaendig, besonders fuer INI Editor und Savegame-Anbindung.
- Massnahme: Help-Dateien und README an aktuelle Navigation angepasst.

### Tests

- Soll: Mindestens Smoke-Tests fuer Start, Navigation, Moduswechsel, Sprachwechsel und sichtbare Button-/Statuslogik.
- Ist: Vor dieser Aenderung keine belastbaren Tests im Repository.
- Massnahme: Neue Smoke- und Pure-Logic-Tests unter `tests/`.

### Dokumentation

- Soll: README, Help und Changelog spiegeln den realen Produktstand.
- Ist: README zeigte noch alte Release-Versionen und verwies auf nicht vorhandene QA-Datei.
- Massnahme: README berichtigt und QA-Sektion auf echte Checks umgestellt.

## Priorisierte naechste Refactorings

1. Mod-Manager-Service aus `main_window.py` extrahieren.
2. `retranslate_ui()` nach Seiten/Feature-Gruppen zerlegen.
3. Page-Builder fuer Trade/Name/INI/Mod Manager in eigene Module auslagern.
4. Dateisystem- und INI-Schreibpfade mit gezielten Integrationstests absichern.
