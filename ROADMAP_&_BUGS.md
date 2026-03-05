# FLAtlas

## AKTUELLE BUGS:
- Änderungen in Datei schreiben wird markiert, obwohl nichts geändert wurde.
- Planeten Ringe - Optionen fehlen. 3D Ring Objekge im 3D Editor, die auch so ausgerichtet sind, wie im Spiel.


## v0.6.2.2 -> v0.6.2.3 - Changelog ########################################################################################

### Added
- Base-Creator deutlich erweitert:
  - Template-basierter Room-Setup verbessert
  - `ids_info`-Vorschau ergänzt
  - NPC-Customization integriert
- Objektgruppen-Dialog und Rumor-Workflow verbessert/ausgebaut.
- Auflösungs-Handling erweitert inkl. lokalisierter Anzeige (DE/EN).

### Changed
- Mod Manager umfassend überarbeitet:
  - Neue UI-Struktur
  - Pfad-Konfiguration konsolidiert
  - Launch-Resolution als optionales Opt-in
  - Besseres Aktivierungs-Feedback (Loading/Status)
- UI/Erstellungs-Workflows verbessert:
  - Planet/Wrack/Buoy-Erstellung überarbeitet
  - Bearbeitungszustände klarer und robuster
- Archetype-Handling robuster gemacht (Safe Fallbacks + Cleanup).

### Fixed
- Window-Startup/Launcher stabilisiert (u. a. Auflösung/Startverhalten).
- Widescreen-Ingame-Patches und Auflösungsauswahl korrigiert.
- Patrol/Exclusion-Zonen-Ausrichtung gefixt:
  - Exclusion-Cylinder-Rotation an Patrol-Orientierung angepasst
  - Patrol-Zonen-Rotation entspricht gezeichneter Achse
  - 3D-Patrol/Path-Cylinder jetzt konsistent zur 2D-Ansicht
- Linux- und Mod-Manager-spezifische Probleme behoben.

### Commits in diesem Bereich
- `07bb4f9` feat(base-creator): overhaul template-based room setup, ids_info preview and NPC customization
- `e5a06ab` Fix exclusion cylinder placement rotation to match patrol-zone orientation
- `4cc29a9` Fix patrol zone creation rotation to match drawn axis
- `272076e` Fix 3D patrol/path cylinder orientation to match 2D view exactly
- `00ce145` Improve editor UX: object groups dialog, rumor workflow, and Linux/mod-manager fixes
- `9ac1e73` feat(ui): improve editing-state actions and creation workflows (planet/wreck/buoy)
- `f542dc0` refactor(mod-manager): redesign UI + move path config + add launch resolution opt-in + activation loading feedback
- `4b2cbf8` fix(ui,launcher): harden window startup + add selectable launch resolution and widescreen ingame patches
- `e09d13e` feat(main_window, translations): update resolution handling and add localization for resolution label
- `7fcd9cf` feat(main_window): enhance archetype handling with safe fallbacks and cleanup

## v0.6.2.1 -> 0.6.2.2 Changelog ##############################################################################

### Changed
- Allgemeine Vorbereitung und Konsolidierung für `v0.6.2.2`.
- Editor-Workflows stabilisiert.
- IDS-Tooling robuster gemacht.
- Mod-Manager UX verbessert.
- Cross-Platform Launch-Flow (Windows/Linux) überarbeitet.

### Fixed
- Stabilitäts- und Kompatibilitätsfixes im Mod Manager, bei IDS und System-Workflows.
- Verbesserte Windows-Kompatibilität für die `0.6.2.2`-Abläufe.

### Internal
- Merge von `development` nach Release-Stand.

### Commits in diesem Bereich
- `759ead4` Vorbereitung auf 0.6.2.2 Update
- `bda8e73` stabilize editor workflows, IDS tooling, Mod Manager UX, and cross-platform launch flow
- `bca2213` fix(mod-manager, ids, systems): stabilize 0.6.2.2 workflows and Windows compatibility
- `2af4109` Merge branch 'development'


## ROADMAP - TODOs ##########################################################################################
- Pop Out 3D Editor mit Optionen zum Sync von 2d und 3d Ansicht
- Info Card creator für Systeme soll sich an aktuelle Standards halten
- aktualisiere die README.md und die Hilfe und die Übersetzungen
- Besserer Base Editor
- Spiele Übersetzer: FL von Englisch nach deutsch übersetzen
- Planetenringe
- Missions Editor
- commodity Creator / Modifier
- Equipment Creator / Modifier
- Ship (ini) Creator / Modifier
- Bearbeitung jeglicher ini files mit einem integriertem editor

## ToDOs für Später (erstmal nicht implementieren) #########################################################
- view 3d objects in editor
- use 3d objects in 3d editor for better visualizing