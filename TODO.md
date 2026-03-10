# FLAtlas TODO

Stand: 2026-03-10

## Uebersicht

Ziel: Das Projekt bis zu einem produktseitig sauberen, wartbaren und belastbar getesteten Stand optimieren.

## Aktueller Fortschritt

- Fortschritt: 84%

## Prozentuebersicht

- Gesamt: 84%
- Architektur entkoppeln: 93%
- Grosse Dateien abbauen: 95%
- Produktfluss und UX absichern: 78%
- Tests ausbauen: 99%
- Daten- und Schreibpfade haerten: 92%
- Dokumentation angleichen: 72%
- Technische Qualitaet absichern: 91%
- Build- und Release-Qualitaet: 20%
- Abschlusskriterien: 34%

## Priorisierung der Restbloecke

- Hoch:
  - `view_3d.py` als verbleibende Render-Orchestrierung final bewerten und Restlogik weiter abbauen.
  - `flight_mode.py` als verbleibende Ablauf-Orchestrierung final bewerten und Restlogik weiter abbauen.
  - `dialogs.py` auf verbliebene Kopplung und Verantwortungen pruefen.
  - Wiederverwendbare UI-Helfer fuer Status, Navigation, Tabellen und Formulare weiter extrahieren.
  - Datei-/Pfadzugriffe weiter von UI-Code trennen.
  - Grosse produktkritische Methoden weiter in kleine testbare Funktionen zerlegen.
  - Harte Kopplungen zwischen MainWindow, Dialogen und Datenhelfern weiter reduzieren.

- Mittel:
  - Startfluss vom ersten App-Start bis zum aktiven Bearbeitungskontext komplett durchgehen.
  - Smoke-Tests weiter ausbauen.
  - Smoke-Tests fuer `Help`, `Welcome`, `DEV Status` und externen Savegame-Editor weiter ergaenzen.
  - README weiter an reale Features, Grenzen und Installationspfade anpassen.
  - Help-Dateien mit allen produktiv sichtbaren Hauptbereichen abgleichen.
  - Build-, Release- und QA-Doku vereinheitlichen.
  - Entwickler-Doku fuer Architektur, Hauptmodule und Teststrategie ergaenzen.

- Niedrig:
  - `main_window.py` weiter schrittweise zerlegen.
  - Mod-Manager-Logik weiter in Service-/Workflow-Module auslagern.
  - `retranslate_ui()` weiter nach Feature-Bloecken aufteilen.
  - `pytest` und Syntaxcheck noch verbindlicher als Standard-QA-Schritt verankern.

## Naechster Arbeitsblock
- [ ] Naechster sinnvoller Arbeitsblock: `view_3d.py` nach den ausgelagerten Kamera-/Camera-Effects-/Objekt-/Palette-/Material-/Gizmo-/Flight-Visual-/Flight-UI-/Flight-Overlay-/Flight-Apply-/Runtime-State-/Sky-/Interaktions-/Szenen-State-/Selection-State-/Event-Routing-Helfern als weitgehend Render-Orchestrierung final bewerten, danach `flight_mode.py` nach den Navigations-/HUD-/Kamera-/Orbit-/State-/Input-/Mouse-/Lifecycle-/Update-/Modepath-/Action-/Viewport-/Dispatch-/Target-/Snapshot-/Seed-/Constants-/Math-/Scene-Refs-/Editor-Context-/Editor-Seed-Helfern als weitgehend Ablauf-Orchestrierung final bewerten und anschliessend `dialogs.py` plus Doku-/Release-Luecken abschliessen.

## erledigt

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
- [x] Weitere manuelle INI-Rewrite-Pfade fuer System-/Jump-Objekt-Loeschlogik aus `main_window.py` auf gemeinsame INI-Schreibhelfer umgestellt.
- [x] SP-Starter-Custom-Loadout-Patchlogik aus `main_window.py` in das bestehende `sp_starter_ini`-Modul ausgelagert.
- [x] System-Editor-Persistenzfluss fuer Objekt-/Zonen-Section-Merge aus `main_window.py` in testbaren Helper ausgelagert.
- [x] Weitere `universe.ini`- und `market_commodities.ini`-Schreibpfade aus `main_window.py` auf gemeinsame INI-Schreibhelfer umgestellt.
- [x] Zone-Link-Dateipersistenz aus `main_window.py` in testbaren Helper ausgelagert.
- [x] Welcome-Page-Builder aus `main_window.py` in eigenes UI-Modul ausgelagert.
- [x] Global-Settings-Page-Builder aus `main_window.py` in eigenes UI-Modul ausgelagert.
- [x] Trade-Routes-Page-Builder aus `main_window.py` in eigenes UI-Modul ausgelagert.
- [x] Name-&-Info-Editor-Page-Builder aus `main_window.py` in eigenes UI-Modul ausgelagert.
- [x] INI-Editor-Page-Builder aus `main_window.py` in eigenes UI-Modul ausgelagert.
- [x] Mod-Manager-Page-Builder aus `main_window.py` in eigenes UI-Modul ausgelagert.
- [x] CSV-Import-/Rewrite-Pfad fuer fehlende `ids_name`/`ids_info` aus `main_window.py` in testbaren Schreibhelper ausgelagert.
- [x] System-Erstellungs-Schreibpfad fuer System-INI und `universe.ini` aus `main_window.py` in testbaren Helper ausgelagert.
- [x] Wiederholte Base-INI-Dateiausgabe aus `main_window.py` in den bestehenden `base_scaffolding`-Helper zentralisiert.
- [x] Aufloesungs-/Display-INI-Patchlogik fuer `perfoptions.ini` und `freelancer.ini` aus `main_window.py` in testbare Pure-Logic-Helfer ausgelagert.
- [x] Resource-RC-/XML-Bundle-Erzeugung fuer DLL-Stringwrites aus `main_window.py` in testbaren Helper ausgelagert.
- [x] README, Projektplan und Soll-/Ist-Abgleich auf den aktuellen Refactor-, QA- und Produktstand nachgezogen.
- [x] OpenSP-Starter-Dateischreibpfade fuer `m01a.ini` und `loadouts.ini` aus `main_window.py` in das bestehende `sp_starter_ini`-Modul gezogen.
- [x] OpenSP-INI-Patch-/Harden-Logik aus `main_window.py` in testbare Pure-Logic-Helfer ausgelagert.
- [x] Room-INI-Generierung und Hotspot-Navigationsnormalisierung aus `main_window.py` in den gemeinsamen `base_scaffolding`-Helper ausgelagert.
- [x] Base-Loeschpfad fuer Nickname-Aufloesung, Universe-Bereinigung und Room-Datei-Lookup aus `main_window.py` in testbare Datenhelfer ausgelagert.
- [x] `mbases.ini`-Blockbereinigung im Base-Loeschpfad aus `main_window.py` in testbare Pure-Logic-Helfer ausgelagert.
- [x] Base-Erstellungsfluss fuer Object-Entries und Universe-Base-Entries aus `main_window.py` in testbare Datenhelfer ausgelagert.
- [x] Room-Dateierzeugung im Base-Erstellungsfluss aus `main_window.py` in den gemeinsamen `base_scaffolding`-Workflow-Helfer ausgelagert.
- [x] Room-Dateisynchronisierung im Base-Bearbeitungsfluss aus `main_window.py` in den gemeinsamen `base_scaffolding`-Workflow-Helfer ausgelagert.
- [x] Universe-Base-Entry-Aktualisierung im Base-Bearbeitungsfluss aus `main_window.py` in testbare Datenhelfer ausgelagert.
- [x] NPC-/Room-Customization-Nachhaertung im Base-Bearbeitungsfluss aus `main_window.py` in testbare Pure-Logic-Helfer ausgelagert.
- [x] News-Editor-Datenpfad fuer Row-Parsing, Rank-Split und Save-Row-Aufbereitung aus `main_window.py` in testbare Editorlogik ausgelagert.
- [x] Rumor-Editor-Datenpfad fuer Scope-Sammlung, CSV-Normalisierung, Zeilenaufbereitung und Form-Parsing aus `main_window.py` in testbare Editorlogik ausgelagert.
- [x] NPC-Editor-Logik fuer Mission-/Rumor-Zeilen, Listenaufbereitung und Form-Helfer aus `main_window.py` in testbare Editorlogik ausgelagert.
- [x] Base-Room-Template- und Scene-Helfer fuer Hotspot-/Scene-Anpassung aus `main_window.py` in testbare Domainlogik ausgelagert.
- [x] Base-Template-Ladepfad fuer Room-Dateien, Room-Details und Virtual-Room-Ziele aus `main_window.py` in testbare Domainlogik ausgelagert.
- [x] NPC-`mbases.ini`-Operationen fuer Attach/Insert/Detach/Lookup/Collect aus `main_window.py` in testbare Domainlogik ausgelagert.
- [x] NPC-Room-Persistenz fuer Room-Key-/Role-Normalisierung und `MRoom`-Upsert aus `main_window.py` in testbare Domainlogik ausgelagert.
- [x] `dialogs.py` als groessten verbliebenen Restkopplungsblock ausserhalb von `main_window.py` bestaetigt und Room-/NPC-Regellogik aus `BaseCreationDialog` in `base_dialog_logic.py` ausgelagert.
- [x] Payload-/State-Logik aus `BaseCreationDialog` fuer Start-Room-Auswahl, Costume-String und Payload-Aufbau in `base_dialog_logic.py` ausgelagert.
- [x] Template-/Room-State-Planung aus `BaseCreationDialog` fuer Raumanwendung, Locked-Rooms, Info-Text und bevorzugten Start-Raum in `base_dialog_logic.py` ausgelagert.
- [x] Datenaufbereitung aus `BaseEditDialog` fuer Object-Properties, Costume-Split sowie Equipment-/Commodity-/Ship-Market-Ergebnisse in `base_edit_logic.py` ausgelagert.
- [x] Properties-Initialzustand aus `BaseEditDialog` fuer Entry-Normalisierung, Pilot-Optionen und Infocard-Jump-Pruefung in `base_edit_logic.py` ausgelagert.
- [x] Market-/Tab-Logik aus `BaseEditDialog` fuer Assigned-Nicknames, Default-Zeilen, Preiszellen und Ship-Slot-Werte in `base_edit_logic.py` ausgelagert.
- [x] Equipment-Gruppenauflösung und verfügbare Group-Filterung aus `BaseEditDialog` in `base_edit_logic.py` ausgelagert.
- [x] Nickname-Sammellogik aus `BaseEditDialog` fuer Equipment-, Commodity- und Ship-Auswahl in `base_edit_logic.py` zentralisiert.
- [x] UI-Tab-Builder aus `BaseEditDialog` fuer Properties, Equipment, Commodities und Ships in `base_edit_page.py` ausgelagert.
- [x] Kamera- und Pan-/Zoom-Mathematik aus `view_3d.py` in `view_3d_camera.py` ausgelagert und separat getestet.
- [x] Kamera-Side-Effect-Helfer aus `view_3d.py` fuer Camera-Pos, Label-Skalierung und Sky-Sync in `view_3d_camera_effects.py` ausgelagert.
- [x] Objekt-/Transformations-Helfer aus `view_3d.py` fuer Pos/Rotate/Trade-Lane-Ausrichtung und Archetype-Groessen in `view_3d_object_logic.py` ausgelagert.
- [x] Farb-/Palette-Helfer aus `view_3d.py` fuer Objekte, Sonnen, Planeten und Zonen in `view_3d_palette.py` ausgelagert.
- [x] Objektklassifikation aus `view_3d.py` fuer Objektarten wie Gate, Planet, Station, Hazard und Transport in `view_3d_object_kinds.py` ausgelagert.
- [x] Material-/Mesh-Helfer aus `view_3d.py` fuer Torus, Phong/Alpha-Material und Always-on-top-Renderstates in `view_3d_materials.py` ausgelagert.
- [x] Gizmo-Helfer aus `view_3d.py` fuer Transform-Berechnung, Farbzustand, Lock-Toggle und Klick-State in `view_3d_gizmo.py` ausgelagert.
- [x] Flight-Visual-Helfer aus `view_3d.py` fuer Ship-Render-Pose, Dust-Seeding und Dust-Update in `view_3d_flight_visuals.py` ausgelagert.
- [x] Flight-UI-Helfer aus `view_3d.py` fuer Flight-Toggle- und Visual-Enable-State in `view_3d_flight_ui.py` ausgelagert.
- [x] Flight-Overlay-Helfer aus `view_3d.py` fuer Overlay-Layout, Overlay-Text und Charge-Bar-State in `view_3d_flight_overlay.py` ausgelagert.
- [x] Flight-Apply-Helfer aus `view_3d.py` fuer Kamera-Kontext und Dust-Enable-Anwendung in `view_3d_flight_apply.py` ausgelagert.
- [x] Laufzeit-State-Helfer aus `view_3d.py` fuer Orbit-State, Label-Scale und Flight-Overlay-Layout in `view_3d_runtime_state.py` ausgelagert.
- [x] Sky-Texture-Darken-Helper aus `view_3d.py` in `view_3d_sky.py` ausgelagert und separat getestet.
- [x] Interaktions-Helfer aus `view_3d.py` fuer Orbit/Pan/Wheel/Axis-Scroll in `view_3d_interaction.py` ausgelagert.
- [x] Szenen-State-Helfer aus `view_3d.py` fuer Nickname-Index und Kamera-/System-Startzustand in `view_3d_scene_state.py` ausgelagert.
- [x] Auswahl-/Move-State-Helfer aus `view_3d.py` fuer Selection-, Visibility-, Label- und Gizmo-Entscheidungen in `view_3d_selection_state.py` ausgelagert.
- [x] Objekt-Update-Helfer aus `view_3d.py` fuer Positions- und Label-Translation in `view_3d_object_updates.py` ausgelagert.
- [x] Reset-State-Helfer aus `view_3d.py` fuer Scene-/Gizmo-Clear-Zustand in `view_3d_reset_state.py` ausgelagert.
- [x] Event-Routing-Helfer aus `view_3d.py` fuer Flight-Weiterleitung, Locked-Axis-Wheel-Capture und Qt3D-Target-Pruefung in `view_3d_event_routing.py` ausgelagert.
- [x] Trade-Lane-Navigations- und Positionshilfen aus `flight_mode.py` in `flight_mode_navigation.py` ausgelagert.
- [x] HUD-/Overlay-Helfer aus `flight_mode.py` fuer Snapshot- und Textaufbereitung in `flight_mode_hud.py` ausgelagert.
- [x] Orbit-/Kamerazustands-Helfer aus `flight_mode.py` fuer Seeding, Mouse-Offset, Turn-State und Camera-Pose in `flight_mode_camera.py` ausgelagert.
- [x] Mode-/Cruise-State-Helfer aus `flight_mode.py` fuer Modewechsel, Cruise-Abbruch und Chase-Distance-Normalisierung in `flight_mode_state.py` ausgelagert.
- [x] Input-/Key-Decision-Helfer aus `flight_mode.py` fuer Cruise-Toggle, Sonderaktionen und Tradelane-Keyhandling in `flight_mode_input.py` ausgelagert.
- [x] Maus-/Orbit-Input-Helfer aus `flight_mode.py` fuer Press/Release/Move/Wheel-State in `flight_mode_mouse.py` ausgelagert.
- [x] Lifecycle-/Reset-Helfer aus `flight_mode.py` fuer Start-/Stop-Zustand in `flight_mode_lifecycle.py` ausgelagert.
- [x] Update-/Speed-State-Helfer aus `flight_mode.py` fuer LMB-Aktivierung, Drive-Key-State, Cruise-Phase und Geschwindigkeitsfortschreibung in `flight_mode_update.py` ausgelagert.
- [x] Autopilot-/Tradelane-Modepfade aus `flight_mode.py` fuer Zielanflug, Dockingstart, Docking-Update und Lane-Travel in `flight_mode_mode_paths.py` ausgelagert.
- [x] Action-Helfer aus `flight_mode.py` fuer Free-Flight-, Autopilot- und Aktivierungsentscheidungen in `flight_mode_actions.py` ausgelagert.
- [x] Viewport-Kamera-Helfer aus `flight_mode.py` fuer Chase-/Orbit-Pose und Viewport-Sync in `flight_mode_viewport.py` ausgelagert.
- [x] Dispatch-Helfer aus `flight_mode.py` fuer Overlay- und HUD-Weitergabe in `flight_mode_dispatch.py` ausgelagert.
- [x] Target-Helfer aus `flight_mode.py` fuer Selection- und Autopilot-Zielkontext in `flight_mode_targets.py` ausgelagert.
- [x] Snapshot-Helfer aus `flight_mode.py` fuer gemeinsamen Selection-/Autopilot-Zielkontext in `flight_mode_snapshot.py` ausgelagert.
- [x] Seed-Helfer aus `flight_mode.py` fuer Auswahl-Startposition und Blickrichtung in `flight_mode_seed.py` ausgelagert.
- [x] Constants-Helfer aus `flight_mode.py` fuer Game-Path-Aufloesung, Dateisuche und Konstanten-Parsing in `flight_mode_constants.py` ausgelagert.
- [x] Math-Helfer aus `flight_mode.py` fuer lineare und Winkel-Annäherung in `flight_mode_math.py` ausgelagert.
- [x] Scene-Ref-Helfer aus `flight_mode.py` fuer Weltposition, Trade-Lane-Erkennung und Lane-Path-Aufbereitung in `flight_mode_scene_refs.py` ausgelagert.
- [x] Editor-Context-Helfer aus `flight_mode.py` fuer Selection- und Autopilot-Distanzkontext in `flight_mode_editor_context.py` ausgelagert.
- [x] Editor-Seed-Helfer aus `flight_mode.py` fuer den Startzustand aus aktueller Selection in `flight_mode_editor_seed.py` ausgelagert.
- [x] README, Projektplan, Soll-/Ist-Abgleich und Roadmap/Changelog-Hinweise auf aktuellen Refactor-, QA- und Doku-Stand nachgezogen.


## 1. Architektur entkoppeln

- Fortschritt: 93%

- [~] `fl_editor/main_window.py` weiter zerlegen.
- [~] Mod-Manager-Logik in eigene Service-/Workflow-Module auslagern.
- [x] Page-Builder fuer `Trade Routes`, `Name & Info`, `INI Editor`, `Mod Manager`, `Welcome` in eigene Module verschieben.
- [~] `retranslate_ui()` nach Feature-Bloecken aufteilen.
- [x] Eigenstaendigen Savegame-Editor aus dem Code entfernen; nur noch Verweis/Start des externen Editors bleibt.
- [x] Savegame-Helfer aus `main_window.py` im Zuge der Entfernung entfallen lassen.
- [ ] Wiederverwendbare UI-Helfer fuer Status, Navigation, Tabellen und Formulare extrahieren.
- [~] Datei-/Pfadzugriffe von UI-Code trennen.
- Schreiboperationen fuer INI/DLL/Mod-Aktivierung zentralisieren.
- Naechste Arbeitsbloecke:
  - `view_3d.py` nach den Kamera-/Camera-Effects-/Objekt-/Palette-/Material-/Gizmo-/Flight-Visual-/Flight-UI-/Flight-Overlay-/Flight-Apply-/Runtime-State-/Sky-/Interaktions-/Szenen-State-/Selection-State-/Event-Routing-Refactors als weitgehend Render-Orchestrierung final bewerten.
  - `flight_mode.py` nach den Navigations-/HUD-/Orbit-/State-/Input-/Mouse-/Lifecycle-/Update-/Modepath-/Action-/Viewport-/Dispatch-/Target-/Snapshot-/Seed-/Constants-/Math-/Scene-Refs-/Editor-Context-/Editor-Seed-Refactors als weitgehend Orchestrierung final bewerten.
  - danach `dialogs.py` nach `BaseCreationDialog`-/`BaseEditDialog`-Auslagerungen als vorwiegend UI-Orchestrierung final bewerten.
  - anschliessend die verbleibenden Doku-, QA- und Release-Luecken schliessen.

## 2. Grosse Dateien abbauen

- Fortschritt: 95%

- [~] `main_window.py` schrittweise in mehrere Module splitten.
- [~] `dialogs.py` auf Groesse und Verantwortungen pruefen und schrittweise aufteilen.
- [x] `savegame_editor.py` entfernt; externer Editor-Verweis bleibt in MainWindow/Settings.
- [~] Grosse, produktkritische Methoden identifizieren und in kleine testbare Funktionen zerlegen.
- [~] Harte Kopplungen zwischen MainWindow, Dialogen und Datenhelfern reduzieren.
- Naechste Arbeitsbloecke:
  - `view_3d.py` Rest nach den Kamera-/Camera-Effects-/Objekt-/Palette-/Material-/Gizmo-/Flight-Visual-/Flight-UI-/Flight-Overlay-/Flight-Apply-/Runtime-State-/Sky-/Interaktions-/Szenen-State-/Selection-State-/Event-Routing-Refactors auf verbleibende Render-Orchestrierung reduzieren.
  - `flight_mode.py` Rest nach den Navigations-/HUD-/Orbit-/State-/Input-/Mouse-/Lifecycle-/Update-/Modepath-/Action-/Viewport-/Dispatch-/Target-/Snapshot-/Seed-/Constants-/Math-/Scene-Refs-/Editor-Context-/Editor-Seed-Refactors als verbleibende Orchestrierung bewerten.
  - anschliessend `dialogs.py` Rest nach dem `BaseEditDialog`-Page-Builder als vorwiegend UI-Orchestrierung final bewerten.

## 3. Produktfluss und UX absichern

- Fortschritt: 78%

- [~] Startfluss vom ersten App-Start bis zum aktiven Bearbeitungskontext durchgehen.
- Welcome-Screen gegen echten Produktfluss pruefen und vereinfachen.
- Standardzustaende fuer Navigation, leere Datenlagen und fehlende Pfade vereinheitlichen.
- Fehlermeldungen, Disabled-States und Statusmeldungen auf Konsistenz pruefen.
- Mod-Manager-Workflow auf Klarheit und sichere Defaults ueberarbeiten.
- Sprachwechsel in allen relevanten Views auf Vollstaendigkeit pruefen.
- Editor-Wechsel und Tab-Wechsel auf Verlust von Zustand und versteckte Nebenwirkungen testen.
- [x] Savegame-Editor-Integration auf externen Editor reduziert und UX-Texte angepasst.

## 4. Tests ausbauen

- Fortschritt: 99%

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

- Fortschritt: 92%

- INI-Schreibpfade auf sichere Roundtrip-Erhaltung pruefen.
- Mod-Aktivierung/Deaktivierung mit Testdaten absichern.
- Savegame-Schreibpfade mit Regressionstests absichern.
- BINI-Konvertierung und Fallback-Lesen gezielt testen.
- DLL-String-Handling gegen kaputte oder unvollstaendige Dateien absichern.
- Fehlerfaelle fuer fehlende, schreibgeschuetzte oder inkonsistente Pfade systematisch behandeln.

## 6. Dokumentation angleichen

- Fortschritt: 72%

- [~] README weiter an reale Features, bekannte Grenzen und Installationspfade anpassen.
- [~] Help-Dateien mit allen produktiv sichtbaren Hauptbereichen abgleichen.
- Changelog auf reale Commits und tatsaechliche Produktaenderungen bereinigen.
- Produktgrenzen und bekannte Risiken explizit dokumentieren.
- [~] Build-, Release- und QA-Doku vereinheitlichen.
- [x] Doku auf externen Savegame-Editor-Verweis ohne eingebauten Savegame-Workflow angepasst.
- [~] Entwickler-Doku fuer Architektur, Hauptmodule und Teststrategie ergaenzen.

## 7. Technische Qualitaet absichern

- Fortschritt: 91%

- Einheitliche Modulgrenzen und Benennungen festlegen.
- Ueberfluessige Duplikate und Legacy-Shims identifizieren und schrittweise abbauen.
- Tote UI-Pfade, ungenutzte Helfer und alte Fallbacks bereinigen.
- Logging/Status-Ausgaben vereinheitlichen.
- Kritische Exceptions enger fassen statt breite `except Exception`-Pfadnutzung beizubehalten, wo realistisch moeglich.
- Konfigurations- und Persistenzzugriffe robuster machen.

## 8. Build- und Release-Qualitaet

- Fortschritt: 20%

- Python-Abhaengigkeiten fuer Dev/Test/Build klar dokumentieren.
- [~] `pytest` und Syntaxcheck als Standard-QA-Schritt fest verankern.
- Build-Skripte fuer Windows/Linux auf Vollstaendigkeit und Konsistenz pruefen.
- Release-Artefakte, Versionsnummern und Changelog-Abgleich standardisieren.
- Optional: CI fuer Syntaxcheck und Test-Suite vorbereiten.

## 9. Abschlusskriterien fuer "fertig optimiert"

- Fortschritt: 34%

- `main_window.py` ist deutlich kleiner und nicht mehr zentraler Sammelort fuer Produkt-, UI- und Datenlogik.
- Kritische Produktpfade sind per Smoke-Tests abgesichert.
- Schreibpfade fuer INI, Mod-Manager und Savegame sind regressionstestbar.
- README, Help und Changelog spiegeln den echten Produktstand.
- Start-, Navigation-, Sprach- und Moduswechsel verhalten sich stabil und nachvollziehbar.
- Build- und QA-Ablauf sind reproduzierbar dokumentiert.
