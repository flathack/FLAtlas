# FLAtlas TODO

Stand: 2026-03-10
Fortschritt gesamt: 83%

## Fortschrittslogik

- Berechnung ueber gewichtete Hauptbereiche statt freier Schaetzung.
- Aktueller Gesamtwert ist die gewichtete Summe der unten aufgefuehrten Bereichswerte.
- Gewichtung:
  - Architektur entkoppeln:                   20%
  - Grosse Dateien abbauen:                   15%
  - Produktfluss und UX absichern:            10%
  - Tests ausbauen:                           20%
  - Daten- und Schreibpfade haerten:          10%
  - Dokumentation angleichen:                 10%
  - Technische Qualitaet absichern:           5%
  - Build- und Release-Qualitaet:             5%
  - Abschlusskriterien:                       5%
- Aktueller Bewertungsstand: ------------------------------------------
  - Architektur entkoppeln:                   100% |----------- 100% ------------|
  - Grosse Dateien abbauen:                   100% |----------- 100% ------------|
  - Produktfluss und UX absichern:             76% |-------- 76% -------------   |
  - Tests ausbauen:                           100% |----------- 100% ------------|
  - Daten- und Schreibpfade haerten:           76% |-------- 76% ------------    |
  - Dokumentation angleichen:                  40% |----- 40% ----               |
  - Technische Qualitaet absichern:           100% |----------- 100% ------------|
  - Build- und Release-Qualitaet:              10% |- 10%                        |
  - Abschlusskriterien:                         0% | 0%                          |

Ziel: Das Projekt bis zu einem produktseitig sauberen, wartbaren und belastbar getesteten Stand optimieren.

## Aktueller Fortschritt

- [x] TODO-Liste als laufend pflegbare Arbeitsliste etabliert.
- [x] INI-Editor-Logik fuer Dateibaum und Section-Erkennung aus `main_window.py` herausgezogen.
- [x] Zusätzliche Smoke-Tests fuer INI Editor, Help und DEV Status ergänzt.
- [x] Settings-Navigation aus `main_window.py` entkoppelt und separat testbar gemacht.
- [x] Welcome-/Settings-Teil aus `retranslate_ui()` in eigenes Modul ausgelagert.
- [x] Mod-Manager-Teil aus `retranslate_ui()` in eigenes UI-Modul ausgelagert.
- [x] Trade-/Name-/INI-Teil aus `retranslate_ui()` in eigenes UI-Modul ausgelagert.
- [x] Mod-Manager-Aufloesungs-/Seitenverhaeltnis-Logik aus `main_window.py` in eigenes Modul ausgelagert.
- [x] Mod-Manager-Dateisystem-/Pfad-Helfer aus `main_window.py` in eigenes Modul ausgelagert.
- [x] Interne Savegame-Editor-Logik aus `main_window.py` entfernt; externer Launcher bleibt.
- [x] Verbliebene Savegame-Editor-Datei, Tests und Doku auf externen Editor-only Stand bereinigt.
- [x] Mod-Manager-Profil-/ID-/Pfad-Normalisierung und Statushilfen aus `main_window.py` ausgelagert.
- [x] Mod-Manager-Savegame-Policy-Helfer aus `main_window.py` ausgelagert.
- [x] Mod-Manager-Konflikt-/Overlap-Logik aus `main_window.py` in testbares Hilfsmodul ausgelagert.
- [x] Pure-Logic-Tests fuer Mod-Manager-Konflikt-/Touch-Signatur ergaenzt.
- [x] Mod-Manager-Status-/Darstellungslogik aus Tabellen-Refresh in testbare Hilfsfunktionen ausgelagert.
- [x] Mod-Manager-Launch-/Profilwahl- und EXE-Aufloesungslogik aus `main_window.py` ausgelagert.
- [x] Mod-Manager-Action-State-Berechnung aus `main_window.py` in testbare Hilfslogik ausgelagert.
- [x] Freelancer-INI-Pfadaufloesung aus `main_window.py` in eigenes Hilfsmodul ausgelagert.
- [x] Trade-Route-Schreiblogik fuer `market_commodities.ini` in testbares Hilfsmodul ausgelagert.
- [x] OpenSP-Starter-INI-Lese-/Schreiblogik in testbares Hilfsmodul ausgelagert.
- [x] INI-Editor-Kontext- und Datei-Open/Save-Logik in testbares Hilfsmodul ausgelagert.
- [x] Generischen Editor-Page-Builder aus `main_window.py` in wiederverwendbares UI-Hilfsmodul ausgelagert.
- [x] Wiederverwendbare Browse-Pfadzeile und Trade-Route-Tabellen-/Filter-Initialisierung aus grossen Page-Buildern ausgelagert.
- [x] Wiederverwendbare Readonly-Tabellenkonfiguration aus dem Name-Editor/Page-Builder ausgelagert.
- [x] Welcome-/Erststart-Produktfluss fuer Continue- und Toolchain-Hinweislogik in testbare Helfer ausgelagert.
- [x] Weitere Readonly-Tabellenkonfigurationen aus Global Settings, Info-Editor und Mod-Manager auf gemeinsame UI-Helfer umgestellt.
- [x] BINI-Ordnerkonvertierung aus `main_window.py` in testbares Schreibpfad-Hilfsmodul ausgelagert.
- [x] BINI-Erkennung unter `DATA` sowie Kopieren/Decodieren in Mod-Ordner aus `main_window.py` in testbare Hilfslogik ausgelagert.
- [x] Global-Settings-Tab-Auswahl und Name-Editor-Subview-/Sidebar-Zustaende in testbare UI-State-Helfer ausgelagert.
- [x] BINI-Settings-Workflow fuer Zielordner-Pruefung und Ergebnisaufbereitung in testbare Hilfslogik ausgelagert.
- [x] DEV-Status-Zeilenaufbereitung fuer die Settings-Tabelle in das bestehende `dev_status`-Modul ausgelagert.
- [x] Linke Sidebar-/Splitter-Zustandslogik fuer Compact-Width in testbare Workspace-Helfer ausgelagert.
- [x] Wiederkehrende Workspace-Presets fuer Global Settings, Mod Manager, INI Editor, Name Editor und Trade Routes zentralisiert.
- [x] Global-Settings-Form-Synchronisierung in testbare Hilfslogik fuer Defaults, Mehrfachpfade und Sichtbarkeiten ausgelagert.
- [x] DLL-Debug-Aufbereitung fuer die Global Settings in testbare Hilfslogik fuer Quelle und Zeilenformat ausgelagert.
- [x] Wiederkehrende Toolbar-/Mode-Resets fuer nicht-Universe-Views in testbare View-Actions ausgelagert.
- [x] Name-Editor-Filter- und kleine Darstellungslogik in testbares Hilfsmodul ausgelagert.
- [x] Custom-Trade-Route-Speicher aus `main_window.py` in testbares Config-Hilfsmodul ausgelagert.
- [x] Externe Savegame-Editor-Pfadauflosung und Statustexte aus `main_window.py` in testbares Integrationsmodul ausgelagert.
- [x] Game-Path-abhaengige Aktionsfreigaben aus `main_window.py` in testbare UI-State-Logik ausgelagert.
- [x] Infocard-XML-Builder aus `main_window.py` in das bestehende `infocard_utils`-Modul ausgelagert.
- [x] Universe-Positionsspeicherung und Snapshot-Serialisierung aus `main_window.py` in testbare Schreibpfad-Helfer ausgelagert.
- [x] System-Editor-Aktionsfreigaben und Tradelane-Erkennung aus `main_window.py` in testbare UI-State-Helfer ausgelagert.
- [x] Objekt-/Zonen-Combo-Aufbau und Auswahl-Sync aus `main_window.py` in testbare UI-Helfer ausgelagert.
- [x] Objekt-Rotationsnormalisierung und Rotate-Entry-Update aus `main_window.py` in testbare Datenhelfer ausgelagert.
- [x] Infocard-Editor-Navigation und ID-Normalisierung aus `main_window.py` in testbare Helfer ausgelagert.
- [x] Linked-System-Navigation aus Szenenobjekten aus `main_window.py` in testbare Navigationshelfer ausgelagert.
- [x] Default-Infocard-XML fuer Szenenobjekte und Zonen aus `main_window.py` in `infocard_utils` ausgelagert.
- [x] Universe-Edit-Cache und System-Section-Lookup aus `main_window.py` in testbare State-Helfer ausgelagert.
- [x] `ids_info`-Zuweisung fuer Szenenobjekte und Zonen aus `main_window.py` in testbare Assignment-Helfer ausgelagert.
- [x] Universe-Section-Schreibpfad aus `main_window.py` in testbare Persistence-Helfer ausgelagert.
- [x] Infocard-Dialog-XML-Validierung aus `main_window.py` in testbare Dialoglogik ausgelagert.
- [x] Universe-System-`ids_info`-Lookup fuer den Infocard-Produktfluss aus `main_window.py` in testbare Helfer ausgelagert.
- [x] System-Infocard-Generator auf gemeinsame testbare XML-Validierungslogik umgestellt.
- [x] System-Infocard-Draft-Basisdaten und RDL-Textaufbau aus `main_window.py` in testbare Draft-Helfer ausgelagert.
- [x] Universe-System-`ids_info`-Persistierung fuer den System-Infocard-Generator aus `main_window.py` in testbare Assignment-Helfer ausgelagert.
- [x] Universe-Infocard-Persistenz-Refreshbedingung aus `main_window.py` in testbare Persistence-Helfer ausgelagert.
- [x] INI-Section-Update- und Serialisierungspfad fuer fehlende `ids_name`/`ids_info` aus `main_window.py` in testbare Schreibhelfer ausgelagert.
- [x] Systemdokument-Schreibpfad aus `main_window.py` auf den gemeinsamen INI-Serializer umgestellt.
- [x] `universe.ini`-Append- und Rewrite-Pfade fuer neue Base-/System-Eintraege auf gemeinsame INI-Schreibhelfer umgestellt.
- [x] Mehrfach verwendete `cp1252`-mit-UTF-8-Fallback-Schreiblogik aus `main_window.py` in gemeinsamen Text-Schreibhelper zentralisiert.
- [x] Weitere Mod-Manager- und BINI-Schreibpfade aus `main_window.py` auf den gemeinsamen Text-Schreibhelper umgestellt.
- [x] Atomare Tempfile-Schreibpfade fuer Systemdokumente, Universe-Snapshots und Trade-Route-Market-Writes in gemeinsamen Helper ausgelagert.
- [x] Wiederholte Room-/Base-Scaffolding-Dateiausgabe aus `main_window.py` in gemeinsamen Domain-Helper ausgelagert.
- [ ] Naechster sinnvoller Arbeitsblock: verbleibende grosse Seitenaufbauten und weitere zentrale Schreibpfade aus `main_window.py` weiter zerlegen.

## 1. Architektur entkoppeln

- [~] `fl_editor/main_window.py` weiter zerlegen.
- [~] Mod-Manager-Logik in eigene Service-/Workflow-Module auslagern.
- [ ] Page-Builder fuer `Trade Routes`, `Name & Info`, `INI Editor`, `Mod Manager`, `Welcome` in eigene Module verschieben.
- [~] `retranslate_ui()` nach Feature-Bloecken aufteilen.
- [x] Eigenstaendigen Savegame-Editor aus dem Code entfernen; nur noch Verweis/Start des externen Editors bleibt.
- [x] Savegame-Helfer aus `main_window.py` im Zuge der Entfernung entfallen lassen.
- [ ] Wiederverwendbare UI-Helfer fuer Status, Navigation, Tabellen und Formulare extrahieren.
- [~] Datei-/Pfadzugriffe von UI-Code trennen.
- Schreiboperationen fuer INI/DLL/Mod-Aktivierung zentralisieren.

## 2. Grosse Dateien abbauen

- [~] `main_window.py` schrittweise in mehrere Module splitten.
- `dialogs.py` auf Groesse und Verantwortungen pruefen und bei Bedarf aufteilen.
- [x] `savegame_editor.py` entfernt; externer Editor-Verweis bleibt in MainWindow/Settings.
- [~] Grosse, produktkritische Methoden identifizieren und in kleine testbare Funktionen zerlegen.
- Harte Kopplungen zwischen MainWindow, Dialogen und Datenhelfern reduzieren.

## 3. Produktfluss und UX absichern

- Startfluss vom ersten App-Start bis zum aktiven Bearbeitungskontext durchgehen.
- Welcome-Screen gegen echten Produktfluss pruefen und vereinfachen.
- Standardzustaende fuer Navigation, leere Datenlagen und fehlende Pfade vereinheitlichen.
- Fehlermeldungen, Disabled-States und Statusmeldungen auf Konsistenz pruefen.
- Mod-Manager-Workflow auf Klarheit und sichere Defaults ueberarbeiten.
- Sprachwechsel in allen relevanten Views auf Vollstaendigkeit pruefen.
- Editor-Wechsel und Tab-Wechsel auf Verlust von Zustand und versteckte Nebenwirkungen testen.
- [x] Savegame-Editor-Integration auf externen Editor reduziert und UX-Texte angepasst.

## 4. Tests ausbauen

- [~] Bestehende Smoke-Tests erweitern.
- [x] Smoke-Tests fuer `INI Editor` ergaenzen.
- [~] Smoke-Tests fuer `Help`, `Welcome`, `DEV Status` und externen Savegame-Editor ergaenzen.
- [x] Pure-Logic-Tests fuer Mod-Manager-Konfliktlogik ergaenzen.
- Tests fuer Button-States und Statusmeldungen in zentralen Produktpfaden ergaenzen.
- Sprachwechsel-Tests fuer mehr als nur die Hauptnavigation ergaenzen.
- Tests fuer Moduswechsel zwischen Universe/System/Trade/Name/Settings ergaenzen.
- Tests fuer Konfigurationsmigration und Default-Werte ergaenzen.
- Tests fuer Infocard-Parsing und Help-Fallbacks weiter vertiefen.
- [x] Tests fuer die reduzierte externe Savegame-Editor-Integration ergaenzen.
- Mindestens einen End-to-End-Smoke-Test fuer App-Start und Kernnavigation stabilisieren.

## 5. Daten- und Schreibpfade haerten

- INI-Schreibpfade auf sichere Roundtrip-Erhaltung pruefen.
- Mod-Aktivierung/Deaktivierung mit Testdaten absichern.
- Savegame-Schreibpfade mit Regressionstests absichern.
- BINI-Konvertierung und Fallback-Lesen gezielt testen.
- DLL-String-Handling gegen kaputte oder unvollstaendige Dateien absichern.
- Fehlerfaelle fuer fehlende, schreibgeschuetzte oder inkonsistente Pfade systematisch behandeln.

## 6. Dokumentation angleichen

- [~] README weiter an reale Features, bekannte Grenzen und Installationspfade anpassen.
- [~] Help-Dateien mit allen produktiv sichtbaren Hauptbereichen abgleichen.
- Changelog auf reale Commits und tatsaechliche Produktaenderungen bereinigen.
- Produktgrenzen und bekannte Risiken explizit dokumentieren.
- Build-, Release- und QA-Doku vereinheitlichen.
- [x] Doku auf externen Savegame-Editor-Verweis ohne eingebauten Savegame-Workflow angepasst.
- Entwickler-Doku fuer Architektur, Hauptmodule und Teststrategie ergaenzen.

## 7. Technische Qualitaet absichern

- Einheitliche Modulgrenzen und Benennungen festlegen.
- Ueberfluessige Duplikate und Legacy-Shims identifizieren und schrittweise abbauen.
- Tote UI-Pfade, ungenutzte Helfer und alte Fallbacks bereinigen.
- Logging/Status-Ausgaben vereinheitlichen.
- Kritische Exceptions enger fassen statt breite `except Exception`-Pfadnutzung beizubehalten, wo realistisch moeglich.
- Konfigurations- und Persistenzzugriffe robuster machen.

## 8. Build- und Release-Qualitaet

- Python-Abhaengigkeiten fuer Dev/Test/Build klar dokumentieren.
- [~] `pytest` und Syntaxcheck als Standard-QA-Schritt fest verankern.
- Build-Skripte fuer Windows/Linux auf Vollstaendigkeit und Konsistenz pruefen.
- Release-Artefakte, Versionsnummern und Changelog-Abgleich standardisieren.
- Optional: CI fuer Syntaxcheck und Test-Suite vorbereiten.

## 9. Abschlusskriterien fuer "fertig optimiert"

- `main_window.py` ist deutlich kleiner und nicht mehr zentraler Sammelort fuer Produkt-, UI- und Datenlogik.
- Kritische Produktpfade sind per Smoke-Tests abgesichert.
- Schreibpfade fuer INI, Mod-Manager und Savegame sind regressionstestbar.
- README, Help und Changelog spiegeln den echten Produktstand.
- Start-, Navigation-, Sprach- und Moduswechsel verhalten sich stabil und nachvollziehbar.
- Build- und QA-Ablauf sind reproduzierbar dokumentiert.
