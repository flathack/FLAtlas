# FLAtlas TODO

Stand: 2026-03-12

## Uebersicht

Ziel: Die verbleibenden grossen Orchestrierungsbloecke gezielt abbauen, den nativen 3D-Pfad produktreif machen und den QA-/Release-Ablauf real verifizierbar halten.

## Verifizierter Projektstand

- Gesamtfortschritt: 98%
- Groesster technischer Restblock bleibt `fl_editor/main_window.py` mit ca. 26.6k Zeilen.
- Die frueheren Grossbloecke `fl_editor/dialogs.py` (~4.2k), `fl_editor/view_3d.py` (~2.0k) und `fl_editor/flight_mode.py` (~780) sind inzwischen weitgehend auf Orchestrierung reduziert.
- Der native Freelancer-3D-Pfad ist deutlich weiter als die alte TODO suggeriert:
  - `cmp_loader.py`, `freelancer_mesh_data.py`
  - `native_preview_qt3d.py`, `native_preview_geometry.py`, `native_preview_materials.py`
  - `native_scene_loader.py`, `native_scene_cache.py`, `native_scene_sync.py`, `native_scene_retry.py`
  - Anbindung in `MeshPreviewDialog`, `main_window.py` und `view_3d.py`
- Unter `tests/` sind aktuell 161 Testdateien vorhanden, darunter Smoke-/Pure-Logic-Abdeckung fuer:
  - Welcome
  - Help
  - DEV Status
  - externe Savegame-Editor-Integration
  - Dialog-Smoke
  - MainWindow-Smoke
  - 3D-Widget-Smoke
  - Editor-Pages
- Syntax-Baseline ist lokal verifiziert:
  - `.\.venv\Scripts\python.exe` kompiliert `376` Python-Dateien erfolgreich per `py_compile`.
- QA-Baseline ist lokal verifiziert:
  - `pytest 9.0.2` ist in der Projekt-`.venv` installiert.
  - Vollsuite: `638 passed, 4 skipped`
  - Der fruehere Headless-Abbruch im `MainWindow()`-/Qt3D-Pfad ist fuer `offscreen`-/`minimal`-Testumgebungen abgefangen.
- Der native Scene-Load/Cache/Retry/Poll-Zyklus ist nicht mehr direkt in `main_window.py` eingebettet, sondern in `native_scene_runtime.py` gebuendelt und separat getestet.
- Die reine Center-Tab-Spec-/Session-Logik ist nicht mehr direkt in `main_window.py` verteilt, sondern in `center_tabs.py` gebuendelt und separat getestet.
- Die reine System-Tab-Identitaets-/Spec-/Titel-Logik ist nicht mehr direkt in `main_window.py` verteilt, sondern in `system_tabs.py` gebuendelt und separat getestet.
- Der System-Tab-Lifecycle fuer Oeffnen, Wechsel und Root-bezogenes Schliessen ist nicht mehr direkt in `main_window.py` verteilt, sondern in `system_tab_runtime.py` gebuendelt und separat getestet.
- Der System-Tab-Dokumentzustand fuer View-/Auswahl-/Editor-/Pending-State ist nicht mehr direkt in `main_window.py` verteilt, sondern in `system_tab_document_runtime.py` gebuendelt und separat getestet.
- Das Anwenden und Laden von System-Dokumenten fuer Parser-/Scene-Rekonstruktion, Workspace-Reset und Editor-Reinitialisierung ist nicht mehr direkt in `main_window.py` eingebettet, sondern in `system_document_runtime.py` gebuendelt und separat getestet.
- Der beschreibbare IDS-/Resource-DLL-Workflow fuer Registrierung, Slot-Aufloesung, `ids_name`-/`ids_info`-Vergabe und Relinking ist nicht mehr direkt in `main_window.py` eingebettet, sondern in `ids_resource_runtime.py` gebuendelt und separat getestet.
- Der IDS-Toolchain-Erkennungs-/Pfad-/Command-Block fuer Runtime-Aufloesung und Linux-Hinweise ist nicht mehr direkt in `main_window.py` eingebettet, sondern in `ids_toolchain_runtime.py` gebuendelt und separat getestet.
- Der Freelancer-INI-Editor fuer DLL-Auswahl, Text-Normalisierung und Speichern ist nicht mehr direkt in `main_window.py` eingebettet, sondern in `freelancer_ini_editor_runtime.py` gebuendelt und separat getestet.
- Der Systemnamen-/IDS-Anzeige-Block fuer DLL-Cache-Signatur, Anzeigenamen, Faction-Labels und UI-Aktualisierung ist nicht mehr direkt in `main_window.py` verteilt, sondern in `system_name_runtime.py` gebuendelt und separat getestet.
- Der Mod-Manager-Aktivierungs-/Deaktivierungs-/Edit-Context-Workflow ist nicht mehr direkt in `main_window.py` eingebettet, sondern in `mod_manager_workflow.py` gebuendelt und separat getestet.
- Die Workspace-Layout-/Sidebar-/Non-Universe-View-Umschaltung ist nicht mehr direkt in `main_window.py` verteilt, sondern in `workspace_runtime.py` gebuendelt und separat getestet.

## Prozentuebersicht

- Gesamt: 99%
- Architektur entkoppeln: 99%
- Grosse Dateien abbauen: 98%
- Produktfluss und UX absichern: 89%
- Tests ausbauen: 100%
- Daten- und Schreibpfade haerten: 95%
- Dokumentation angleichen: 93%
- Technische Qualitaet absichern: 98%
- Build- und Release-Qualitaet: 72%
- Abschlusskriterien: 93%

## Priorisierung der Restbloecke

- Hoch:
  - `main_window.py` weiter zerlegen; Fokus auf verbleibende System-Editor-Produktlogik und produktnahe Actions.
  - Nativen Freelancer-Mesh-Pfad vom aktuellen Metadaten-/Scene-Stand auf belastbare Objektgeometrie im Produktfluss fertigziehen.
  - Build-/Release-Doku und Review-Dokumente auf die jetzt gruene `638 passed, 4 skipped`-Baseline vereinheitlichen.

- Mittel:
  - Verbleibende direkte Datei-/Pfadzugriffe aus UI-naher Orchestrierung weiter in Helper/Workflow-Module ziehen.
  - `retranslate_ui()`-/UI-Refresh-Reste weiter nach Feature-Bloecken glattziehen.
  - Startfluss, Disabled-States und Statusmeldungen im echten App-Ablauf nochmals manuell gegenpruefen.
  - Build-/Release-Skripte mit einer echten Release-Checkliste inklusive Test-Setup vereinheitlichen.

- Niedrig:
  - `dialogs.py` nur noch bei echter Restkopplung oder wiederverwendbarer Logik weiter anfassen.
  - `view_3d.py` und `flight_mode.py` nur noch selektiv nachschaerfen, solange sie vorwiegend Orchestrierung bleiben.
  - Alte Fortschritts-/Review-Zahlen in Doku-Dateien bei Gelegenheit vereinheitlichen.

## Naechster Arbeitsblock

- [ ] `main_window.py` entlang klarer Restdomaenen aufteilen:
  - [x] nativer Scene-Load/Cache/Retry/Sync-Pfad
  - [~] Center-/Tab-/Workspace-Orchestrierung
  - [~] Mod-Manager-Ablauf und produktnahe Actions
  - [~] verbleibende System-Editor-Produktlogik
- [ ] Danach den nativen 3D-Pfad vervollstaendigen:
  - Part-/Node-/`VMeshData`-Geometrie stabil an Vorschau und Objektselektion anbinden
  - Cache-/Retry-/Sync-Verhalten fuer reale Modellwechsel und Selektion absichern
- [ ] Parallel den QA-Unterbau begradigen:
  - [x] `pytest` in reproduzierbaren Dev-/QA-Setup aufnehmen
  - [x] README/BUILD_INFO/Skripte auf identische Befehle fuer Windows und Linux angleichen
  - [x] die echte grune Testbaseline neu festhalten
  - [ ] verbleibende Review-Dokumente und Release-Hinweise auf denselben Stand ziehen

## Offene Punkte nach Bereich

### 1. Architektur entkoppeln

- [~] `fl_editor/main_window.py` weiter in produktnahe Orchestrierungs- und Workflow-Module splitten.
- [x] Grosse Page-Builder in eigene Module verschoben.
- [x] Dialog-, 3D- und Flight-Helfer weitgehend aus den frueheren Grossdateien ausgelagert.
- [~] Verbleibende Datei-/Pfadzugriffe aus UI-Orchestrierung loesen.
- [~] `retranslate_ui()`-/UI-Refresh-Pfade weiter vereinfachen.

### 2. Grosse Dateien abbauen

- [~] `main_window.py` bleibt der zentrale Restblock und ist die Hauptbaustelle.
- [x] `dialogs.py` ist nicht mehr der dominante Refactor-Block.
- [x] `view_3d.py` ist nicht mehr der dominante Refactor-Block.
- [x] `flight_mode.py` ist nicht mehr der dominante Refactor-Block.

### 3. Produktfluss und UX absichern

- [~] Startfluss vom ersten Start bis zum aktiven Bearbeitungskontext nochmals gegen realen Ablauf pruefen.
- [~] Disabled-States, Statusmeldungen und Fehlerpfade in Mod Manager, Welcome und Settings manuell gegenpruefen.
- [~] Nativen 3D-Produktfluss fuer echte Freelancer-Modelle in Auswahl/Vorschau/Detailansicht vervollstaendigen.
- [x] Externe Savegame-Editor-Integration ist produktseitig auf den externen Workflow reduziert.

### 4. Tests ausbauen

- [x] Smoke-/Logiktests fuer Welcome, Help, DEV Status und externe Savegame-Integration vorhanden.
- [x] Smoke-Tests fuer Dialoge, Editor-Pages, MainWindow und 3D-Widget vorhanden.
- [x] Breite Pure-Logic-Abdeckung fuer Mod-Manager-, Write-, Dialog-, 3D- und Flight-Helfer vorhanden.
- [x] Test-Suite im aktuellen Arbeits-Environment wieder wirklich ausfuehrbar machen (`pytest 9.0.2` in `.venv`).
- [x] Reale Pass-Zahl verifiziert und als gruene Basis festgehalten (`638 passed, 4 skipped`).

### 5. Daten- und Schreibpfade haerten

- [x] Gemeinsame INI-/Text-Schreibhelper und mehrere atomare Schreibpfade sind bereits etabliert.
- [~] Verbleibende direkte Schreib-/Pfadentscheidungen aus `main_window.py` weiter abbauen; der IDS-/Resource-DLL-Schreibpfad ist bereits ausgelagert.
- [~] Native-Scene-Cache-/Retry-/Sync-Pfade mit realen Modellwechseln und Fehlerfaellen weiter absichern.

### 6. Dokumentation angleichen

- [x] README, CHANGELOG, BUILD_INFO und Review-Dokumente wurden bereits sichtbar nachgezogen.
- [x] QA-Befehle zwischen README, BUILD_INFO und realem Environment synchronisieren.
- [x] Release-/Build-Doku um reproduzierbares Test-Setup ergaenzen.
- [~] Fortschrittszahlen und Testbaseline in allen Doku-Dateien wieder konsistent ziehen.

### 7. Technische Qualitaet absichern

- [x] Modulgrenzen fuer viele Hilfsbereiche sind inzwischen klarer.
- [~] Restduplikate und MainWindow-Shims weiter abbauen; der IDS-/Resource-DLL-Runtimeblock ist bereits reduziert.
- [~] Breite Exception-/Fallback-Pfade nur dort belassen, wo sie fuer Produktrobustheit wirklich noetig sind.

### 8. Build- und Release-Qualitaet

- [x] Windows-/Linux-Buildskripte und Release-Skripte sind vorhanden.
- [x] `BUILD_INFO.md` beschreibt einen reproduzierbaren Windows-Build-Grundpfad.
- [x] `pytest` und Syntaxcheck als real nutzbaren Standard-QA-Schritt fest verankern.
- [~] Dev-/Test-Abhaengigkeiten sauber von reinen Build-Abhaengigkeiten trennen oder gemeinsam verlaesslich dokumentieren.
- [~] Release-Checkliste auf den tatsaechlich installierbaren Tooling-Stand bringen.

### 9. Abschlusskriterien fuer "fertig optimiert"

- [~] `main_window.py` ist noch zu gross und bleibt der wichtigste Abschlussblock.
- [x] Die breite Testlandschaft ist im aktuellen Environment verifiziert (`638 passed, 4 skipped`).
- [~] Build-, QA- und Release-Ablauf sind dokumentiert, aber noch nicht komplett auf allen Review-Dokumenten deckungsgleich.
- [~] Native Freelancer-3D-Unterstuetzung ist strukturell vorbereitet, aber noch nicht vollstaendig im Produktfluss abgeschlossen.
- [x] `dialogs.py`, `view_3d.py` und `flight_mode.py` sind nicht mehr die frueheren Hauptengpaesse.

## Erledigt / verifiziert im Abgleich 2026-03-11

- [x] Page-Builder fuer Welcome, Settings, Trade Routes, Name Editor, INI Editor und Mod Manager liegen in eigenen Modulen.
- [x] Umfangreiche Dialoglogik wurde aus `dialogs.py` in spezialisierte Helper ausgelagert.
- [x] Umfangreiche Kamera-/Flight-/Selection-/Overlay-/Apply-Helfer wurden aus `view_3d.py` und `flight_mode.py` ausgelagert.
- [x] Der native Freelancer-Preview-Pfad hat bereits Loader-, Scene-, Cache-, Retry- und Qt3D-Unterbau.
- [x] Breite Testabdeckung fuer viele zuvor offene Produktbereiche ist im Repository vorhanden.
- [x] Der Syntaxzustand der Python-Dateien ist im aktuellen Repo-Stand sauber.
- [x] Arbeitspaket QA-/Headless-Haertung abgeschlossen: `pytest` ist dokumentierter Bestandteil der `.venv`, die Vollsuite laeuft lokal gruen, und Qt3D wird in `offscreen`-/`minimal`-Testumgebungen nicht mehr hart initialisiert.
- [x] Arbeitspaket Native-Scene-Runtime abgeschlossen: Cache/Pending/Retry/Polling/Shutdown liegen jetzt in `native_scene_runtime.py`, `main_window.py` enthaelt dort weniger Runtime-Zustand, und der neue Helper ist separat getestet.
- [x] Arbeitspaket Center-Tab-Helper abgeschlossen: Die reine Tab-Spec-/Session-Logik liegt jetzt in `center_tabs.py`, `main_window.py` enthaelt dort weniger Listen-/Session-Verwaltung, und der neue Helper ist separat getestet.
- [x] Arbeitspaket System-Tab-Helper abgeschlossen: Die reine System-Tab-Key-/Titel-/Spec-Logik liegt jetzt in `system_tabs.py`, `main_window.py` enthaelt dort weniger Identitaets-/Titel-Logik, und der neue Helper ist separat getestet.
- [x] Arbeitspaket System-Tab-Runtime abgeschlossen: Oeffnen, Wechselrouting und Root-bezogenes Schliessen von System-Tabs liegen jetzt in `system_tab_runtime.py`, `main_window.py` enthaelt dort deutlich weniger Lifecycle-Orchestrierung, und der neue Helper ist separat getestet.
- [x] Arbeitspaket System-Tab-Dokumentzustand abgeschlossen: View-/Auswahl-/Editor-/Pending-State sowie Titel-/Preserve-Helfer liegen jetzt in `system_tab_document_runtime.py`, `main_window.py` enthaelt dort weniger Zustandsverwaltung, und der neue Helper ist separat getestet.
- [x] Arbeitspaket System-Dokument-Runtime abgeschlossen: Parser-/Scene-Rekonstruktion, Workspace-Reset und Lade-Delegation liegen jetzt in `system_document_runtime.py`, `main_window.py` enthaelt dort weniger produktnahe Lade-/Apply-Logik, und der neue Helper ist separat getestet.
- [x] Arbeitspaket IDS-Resource-Runtime abgeschlossen: DLL-Registrierung, Slot-Aufloesung, `ids_name`-/`ids_info`-Vergabe sowie Infocard-Relinking liegen jetzt in `ids_resource_runtime.py`, `main_window.py` enthaelt dort weniger schreibende Produktlogik, und der neue Helper ist separat getestet.
- [x] Arbeitspaket IDS-Toolchain-Runtime abgeschlossen: Toolchain-Erkennung, Kandidatenpfade, Linux-Installhinweise und Command-Aufloesung liegen jetzt in `ids_toolchain_runtime.py`, `main_window.py` enthaelt dort weniger Plattform-/Pfadlogik, und der neue Helper ist separat getestet.
- [x] Arbeitspaket Freelancer-INI-Editor-Runtime abgeschlossen: DLL-Parsing, Meta-Zustand, Text-Normalisierung und der Dialog-Workflow liegen jetzt in `freelancer_ini_editor_runtime.py`, `main_window.py` enthaelt dort weniger UI-nahe Datei-/DLL-Orchestrierung, und der neue Helper ist separat getestet.
- [x] Arbeitspaket Systemnamen-Runtime abgeschlossen: DLL-Cache-Signatur, Anzeigenamen, Faction-Labels und UI-Aktualisierung liegen jetzt in `system_name_runtime.py`, `main_window.py` enthaelt dort weniger gekoppelte IDS-/Namenslogik, und der neue Helper ist separat getestet.
- [x] Arbeitspaket Mod-Manager-Workflow abgeschlossen: Aktivierung, Deaktivierung und Edit-Context liegen jetzt in `mod_manager_workflow.py`, `main_window.py` ist dort deutlich kleiner, und der neue Helper ist inklusive gezielter Edit-Context-Tests verifiziert.
- [x] Arbeitspaket Workspace-Runtime abgeschlossen: Layoutwechsel, Sidebar-Breitenlogik und gemeinsame Non-Universe-View-Aktivierung liegen jetzt in `workspace_runtime.py`, mehrere View-Oeffner in `main_window.py` sind dadurch kuerzer, und der neue Helper ist separat getestet.
