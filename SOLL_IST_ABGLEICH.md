# FLAtlas Soll-/Ist-Abgleich

Stand: 2026-03-11

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
- Massnahme: Reine Hilfslogik, grobe Page-Builder, viele Schreibpfade und wesentliche Dialog-Datenlogik in eigene Module ausgelagert; `main_window.py` bleibt aber der groesste Restblock.

### UX

- Soll: Hauptpfade sind ohne versteckte Vorbedingungen nachvollziehbar.
- Ist: Produktfluss ist da, aber Dokumentation war unvollstaendig, besonders fuer INI Editor und Savegame-Anbindung.
- Massnahme: Help-Dateien und README an aktuelle Navigation angepasst.

### Tests

- Soll: Mindestens Smoke-Tests fuer Start, Navigation, Moduswechsel, Sprachwechsel und sichtbare Button-/Statuslogik.
- Ist: Breite Smoke- und Pure-Logic-Abdeckung ist im Repository vorhanden und lokal verifiziert; Stand 2026-03-11: `590 passed, 4 skipped`.
- Massnahme: `pytest` in die dokumentierten Build-/QA-Abhaengigkeiten aufgenommen, plattformabhaengige Pfad-Helper nachgeschaerft und der bisherige Headless-Abbruch im `MainWindow()`-/Qt3D-Testpfad fuer `offscreen`-/`minimal`-Umgebungen abgefangen.

### Dokumentation

- Soll: README, Help und Changelog spiegeln den realen Produktstand.
- Ist: README, BUILD_INFO und TODO sind auf den verifizierten QA-Stand angehoben; einzelne Review-Dokumente muessen noch weiter auf denselben Zahlenstand vereinheitlicht werden.
- Massnahme: README und BUILD_INFO auf reale Windows-QA-Befehle und die aktuelle grune Baseline nachgezogen; Review-Dokumente bleiben als verbleibender Doku-Feinschliff offen.

## Priorisierte naechste Refactorings

1. Mod-Manager-Service aus `main_window.py` extrahieren.
2. `retranslate_ui()` nach Seiten/Feature-Gruppen zerlegen.
3. Verbleibende direkte Dateisystem- und INI-Schreibpfade weiter zentralisieren.
4. Letzte UI-nahe Dialogreste nur noch dort weiter aufteilen, wo echter Logikgewinn entsteht.
5. Help-, Build- und Release-Doku auf den echten Produkt- und QA-Stand vervollstaendigen.
