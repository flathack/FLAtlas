# Projektplan: Integration und Ausbau des INI-Editors in FLAtlas

## Kontext

Der eigentliche FLAtlas-Code liegt unter `/home/steven/FLEditor`.

Der bestehende INI-Editor ist bereits vorhanden und aktuell über folgende Module angebunden:

- `fl_atlas.py` als Einstiegspunkt
- `fl_editor/main_window.py` als Integrationspunkt
- `fl_editor/ini_editor_page.py` für die UI
- `fl_editor/ini_editor_files.py` für Datei-/Kontextzugriff
- `fl_editor/ini_editor_logic.py` für Tree- und Section-Helfer
- `fl_editor/ini_section_writes.py` für einfache strukturierte Schreiboperationen
- Tests in `tests/test_ini_editor_logic.py`, `tests/test_ini_editor_files.py`, `tests/test_ini_section_writes.py`

## Ist-Zustand

Der aktuelle INI-Editor kann bereits:

- Mod-Kontextwurzel aus dem Mod-Manager ableiten
- den Projektbaum laden
- Dateien öffnen
- Dateiinhalt als Rohtext anzeigen und bearbeiten
- Sections im Text erkennen und anspringen
- Änderungen speichern
- den Editor als eigene FLAtlas-Seite öffnen

Technisch ist das aktuell ein schlanker Raw-Text-Editor mit Navigationshilfe.

## Aktuelle Schwächen

Für ernsthafte Freelancer-Modentwicklung reicht der jetzige Stand noch nicht aus:

- kein roundtrip-sicheres Dokumentmodell
- Speichern schreibt stumpf als UTF-8 zurück
- keine Backups im INI-Editor
- keine strukturierte Bearbeitung einzelner Keys/Values
- keine Referenzsuche über `nickname`, `base`, `system`, `archetype`, `loadout`, `faction`
- keine Validatoren
- keine tiefe Kopplung an Universe-/Base-/Zone-Workflows
- keine Refactor- oder Template-Funktionen

## Was Modder konkret brauchen

Für Freelancer-Modding sind vor allem diese Workflows relevant:

- schnelles Navigieren durch viele INI-Dateien
- sichere Bearbeitung ohne Zerstörung von Reihenfolge, Duplikaten und Layout
- Sprung von Atlas-Objekten zur zugrunde liegenden Section
- Referenzsuche über mehrere Dateien
- Validierung typischer Freelancer-Fehler
- Assistenten für wiederkehrende Datenstrukturen

Typische Ziele:

- Systeme und Universe-Einträge
- Basen und Rooms
- Zonen, Nebulae, Asteroid-Felder
- Schiffe, Loadouts, Goods, Markets
- Missionen, NPCs, News, Rumors
- `freelancer.ini` und andere zentrale Root-Dateien

## Zielbild

Der INI-Editor soll von einer reinen Textansicht zu einer produktiven, modding-spezifischen Arbeitsfläche ausgebaut werden:

- Raw-Text-Modus bleibt erhalten
- strukturierter Modus kommt hinzu
- Atlas und INI-Editor teilen sich Kontext, Selektion und Speicherlogik
- Änderungen werden sicher gespeichert
- Referenzen und Validierung werden projektweit nutzbar

## Architekturplan

## 1. Bestehende Module beibehalten, aber klar erweitern

Empfohlene Verantwortlichkeiten:

- `ini_editor_page.py`
  - UI erweitern
  - Split-Ansichten, Toolbars, Filter, Fehlerliste
- `ini_editor_files.py`
  - sicheres Laden/Speichern
  - Backup-Logik
  - Encoding-Erkennung
- `ini_editor_logic.py`
  - Dokumentmodell
  - Section-/Entry-Navigation
  - Referenzindex
  - Validatoren
- `ini_section_writes.py`
  - gezielte strukturierte Änderungen
  - später über Dokumentmodell statt einfacher Listenlogik
- `main_window.py`
  - Atlas-Integration
  - Selektion, Öffnen, Reload, Save-Pipeline

## 2. Dokumentmodell einführen

Der entscheidende nächste Schritt ist ein nicht-destruktives INI-Dokumentmodell.

Anforderungen:

- Reihenfolge von Sections erhalten
- Reihenfolge von Keys erhalten
- doppelte Keys erhalten
- Kommentare und Leerzeilen möglichst erhalten
- section-basierte Navigation ermöglichen
- spätere strukturierte Bearbeitung ermöglichen

Wichtig:

- `configparser` ist dafür ungeeignet
- das Modell sollte Raw-Lines und strukturierte Einträge parallel halten

## 3. Save-Pipeline härten

`ini_editor_save_file()` ist aktuell zu einfach. Daraus sollte eine sichere Save-Pipeline werden:

- Encoding bestmöglich erkennen
- Datei vor Schreiben sichern
- optional atomisch über temporäre Datei schreiben
- Dirty-State sauber zurücksetzen
- nach Save optional Section-/Referenz-Refresh auslösen
- Fehler mit Dateipfad und Ursache melden

## Ausbauplan in Phasen

## Phase 1: Technische Basis härten

Ziel:

- Den bestehenden Raw-Editor verlässlich machen, ohne die Bedienung zu verkomplizieren.

Arbeitspakete:

- `ini_editor_files.py`
  - Backup-Funktion ergänzen
  - sicheres Speichern mit Temp-Datei ergänzen
  - Encoding-Fallbacks sauber kapseln
- `ini_editor_logic.py`
  - einfaches Dokumentmodell statt nur `parse_ini_sections`
  - Section-Metadaten mit Start-/End-Zeilen
- `main_window.py`
  - Schutz gegen Datenverlust beim Dateiwechsel
  - Warnung bei ungespeicherten Änderungen
- Tests erweitern:
  - Save mit Backup
  - Dirty-State-Verhalten
  - unveränderte Datei bleibt textgleich

Abnahmekriterien:

- Editor verliert keine Änderungen stillschweigend
- Speichern ist robuster
- Sections bleiben korrekt navigierbar

## Phase 2: Strukturierte Bearbeitung ergänzen

Ziel:

- Neben dem Raw-Text einen echten Freelancer-INI-Arbeitsmodus anbieten.

Arbeitspakete:

- `ini_editor_page.py`
  - zusätzliche Detailansicht für aktuelle Section
  - Liste aller Keys in der Section
  - Add/Edit/Delete für Entries
- `ini_editor_logic.py`
  - Parser für Section-Entries
  - Mehrfach-Keys korrekt behandeln
- `ini_section_writes.py`
  - Write-Operationen auf Dokumentmodell umstellen

Wichtige Feldtypen:

- `nickname`
- `ids_name`
- `ids_info`
- `pos`
- `rotate`
- `base`
- `system`
- `archetype`
- `loadout`
- `faction`

Abnahmekriterien:

- einzelne Einträge können bearbeitet werden, ohne das Dateiformat unnötig umzuschreiben
- doppelte Keys bleiben erhalten

## Phase 3: Freelancer-spezifische Produktivität

Ziel:

- Der Editor soll projektweit nutzbares Freelancer-Wissen enthalten.

Arbeitspakete:

- projektweite Suche nach:
  - `nickname`
  - `ids_name`
  - `ids_info`
  - `base`
  - `system`
  - `archetype`
  - `loadout`
- Referenzindex einführen
- "Gehe zu Definition"
- "Wo verwendet?"
- Validatoren für:
  - doppelte Nicknames
  - fehlende Referenzen
  - fehlende Dateien
  - offensichtliche IDS-Probleme

Betroffene Module:

- primär `ini_editor_logic.py`
- UI-Anbindung in `ini_editor_page.py`
- Event-Anbindung in `main_window.py`

Abnahmekriterien:

- ein Modder kann von einem Wert direkt zur Zieldefinition springen
- häufige Referenzfehler werden vor dem Spielstart sichtbar

## Phase 4: Tiefe FLAtlas-Integration

Ziel:

- Der INI-Editor wird Teil des Atlas-Workflows statt ein separater Textbereich zu bleiben.

Arbeitspakete:

- in `main_window.py` neue Öffnungsroutinen:
  - Datei und Section gezielt öffnen
  - von selektiertem System/Objekt/Zone aus direkt springen
- Universe-/Base-/Zone-Editoren geben Quellpfad und Section-Nickname mit
- nach Atlas-Schreiboperationen gezielten Reload im INI-Editor auslösen
- gemeinsame Save-/Dirty-Strategie abstimmen

Konkrete Integrationen:

- System in Universe-Ansicht selektieren -> passende Section in `universe.ini` oder Systemdatei öffnen
- Base selektieren -> passende `[Base]`-Section öffnen
- Zone selektieren -> passende `[zone]`-/`[Zone]`-Section öffnen
- Objekt selektieren -> passende `[Object]`-Section öffnen

Abnahmekriterien:

- Atlas-Selektion und INI-Editor-Selektion sind miteinander verknüpfbar
- der Nutzer muss relevante Dateien nicht mehr manuell suchen

## Phase 5: Wizards und Refactoring

Ziel:

- Wiederkehrende Modding-Aufgaben beschleunigen.

Arbeitspakete:

- Assistent für neues System
- Assistent für neue Base
- Assistent für Zone/Nebula/Asteroid-Feld
- Section duplizieren
- Nickname umbenennen mit Referenzupdate
- Vorlagen für wiederkehrende Einträge

Naheliegende Wiederverwendung:

- bestehende System-/Base-Module wie
  - `system_creation_writes.py`
  - `base_creation.py`
  - `base_scaffolding.py`
  - `zone_link_persistence.py`

Abnahmekriterien:

- Standardobjekte lassen sich schneller erzeugen als per manuellem Raw-Text-Edit

## Priorisierte Featureliste für Freelancer-Modder

## Muss zuerst kommen

- sicheres Speichern mit Backup
- Warnung bei Dateiwechsel mit ungespeicherten Änderungen
- Dokumentmodell für sections und entries
- strukturierter Section-Editor
- Referenzsuche nach `nickname`
- Jump-to-Section aus Atlas

## Danach

- Validatoren
- Go-to-definition
- Cross-file Suche
- Vorlagen/Wizards
- Refactor für Nicknames

## Später

- Schema-Hinweise und Tooltips pro Dateityp
- Bulk-Edit für große Umstellungen
- Presets für typische Freelancer-Datenblöcke

## Konkrete technische Schritte im Code

## Schritt 1

Neue Kernklasse in `ini_editor_logic.py` einführen, z. B.:

- `IniDocument`
- `IniSection`
- `IniEntry`

## Schritt 2

`main_window.py` von reinem `parse_ini_sections()` auf Dokumentmodell umstellen, zunächst nur lesend.

## Schritt 3

`ini_editor_save_file()` erweitern und Tests in `tests/test_ini_editor_files.py` ergänzen.

## Schritt 4

In `ini_editor_page.py` neben `ini_sections_list` eine Entry-Ansicht hinzufügen.

## Schritt 5

`ini_section_writes.py` schrittweise von Listen-Tupeln auf Dokumentobjekte migrieren.

## Schritt 6

Gezielte Deep-Link-Funktion in `main_window.py` ergänzen:

- `open_ini_file(path)`
- `open_ini_file_and_section(path, section_name, nickname=None)`

## Schritt 7

Referenzindex und Validatoren ergänzen, zunächst auf `nickname`-basierte Workflows fokussiert.

## Teststrategie

Bestehende Tests sind eine gute Basis, decken aktuell aber nur Minimalfälle ab.

Zusätzliche Tests:

- Dateiwechsel mit Dirty-State
- Backup-Erzeugung
- atomisches Speichern
- Section mit Duplicate Keys
- Kommentare bleiben erhalten
- gezieltes Öffnen einer Datei und Section
- Refactor einer `nickname`-Referenz
- Cross-file Lookup über zwei oder mehr INI-Dateien

Zusätzlich sinnvoll:

- Testdaten aus echten Freelancer-INI-Strukturen
- Golden-file-Tests für roundtrip-sicheres Schreiben

## Risiken

- zu frühes Umbauen von `main_window.py` ohne stabile Dokument-API
- strukturierte Writes könnten bestehende Formatierung verändern
- Referenzindex kann bei großen Mods träge werden, wenn er synchron läuft
- unterschiedliche INI-Stile im Freelancer-Ökosystem erschweren starre Schemata

## Empfehlung für den nächsten konkreten Schritt

Der sinnvollste nächste Schritt ist nicht sofort ein großer UI-Umbau, sondern:

1. `ini_editor_logic.py` um ein kleines, roundtrip-fähiges Dokumentmodell erweitern
2. `ini_editor_files.py` mit Backup- und sicherer Save-Logik härten
3. erst danach die strukturierte Section-/Entry-UI ergänzen

Damit wird der bestehende INI-Editor stabil erweitert, statt durch neue Features auf einer zu schwachen Basis komplexer zu werden.
