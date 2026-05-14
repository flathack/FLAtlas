# FLAtlas Refactoring Plan

## Ziel

Dieser Plan beschreibt ein schrittweises Refactoring fuer FLAtlas V1. Das Ziel ist bessere Wartbarkeit, klarere Modulgrenzen und geringeres Risiko bei zukuenftigen Feature- und Bugfix-Arbeiten, ohne bestehende Nutzer-Workflows zu brechen.

Besonders wichtig:

- Mod-Pfade, aktive Mod-Kontexte und Vanilla-Fallback-Reads muessen erhalten bleiben.
- Writes duerfen nicht stillschweigend auf andere Ziele umgeleitet werden.
- Freelancer-Dateiformate, DLL-Ressourcen, BINI-Verarbeitung und INI-Serialisierung brauchen enge Regressionstests.
- UI-Refactors sollen bestehende DE/EN-Wording- und Bedienmuster respektieren.

## Aktueller Eindruck

Der Code ist bereits in viele Feature-Module unter `fl_editor/` aufgeteilt. Gleichzeitig gibt es einige klare Hotspots:

- `fl_editor/main_window.py` ist mit rund 41.000 Zeilen der zentrale Monolith und enthaelt UI-Koordination, Startup, Mod-Manager-Glue, INI-Editor-Hilfsklassen und viel Feature-Verkabelung.
- `fl_editor/dialogs.py` sammelt viele voneinander unabhaengige Dialoge in einer Datei.
- `fl_editor/view_3d.py` mischt Kamera, Qt3D-Scene-Management, Auswahl, Gizmo, native Preview und Entity-Erzeugung.
- `fl_editor/cmp_loader.py` enthaelt viele dichte Parser-, Decode- und Preview-Assembly-Funktionen.
- Write-nahe Module sind testkritisch und sollten nur sehr lokal veraendert werden.

## Leitprinzipien

1. Kleine, nachvollziehbare Schritte statt Big-Bang-Refactor.
2. Verhalten zuerst mit Tests absichern, dann Code bewegen.
3. Bestehende Muster fortfuehren: `*_logic.py`, `*_page.py`, `*_runtime.py`.
4. `MainWindow` langfristig als Koordinator behandeln, nicht als Speicherort fuer Feature-Logik.
5. Oeffentliche Importpfade bei Datei-Splits vorerst kompatibel halten.
6. Keine Refactors, die Save-/Write-Semantik nebenbei veraendern.

## Phase 1: Schutznetz und Baseline

### Aufgaben

- Vollstaendige Tests als Ausgangspunkt laufen lassen:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

- Compile-Sanity fuer schnelle Zwischenchecks verwenden:

```powershell
Get-ChildItem fl_atlas.py, fl_editor\*.py, tests\*.py | ForEach-Object { .\.venv\Scripts\python.exe -m py_compile $_.FullName }
```

- Fuer UI-lastige Schritte eine echte Startup-Smoke-Pruefung einplanen:

```powershell
python fl_atlas.py
```

### Ergebnis

- Bekannte Test-Baseline.
- Klare Liste, welche Tests nach welchem Refactor relevant sind.
- Keine Codebewegung ohne reproduzierbares Ausgangsverhalten.

## Phase 2: `main_window.py` entlasten

Status: gestartet. Schritte 2.1, 2.2 und 2.3 sind erledigt.

### Ziel

`fl_editor/main_window.py` soll schrittweise von Feature-Implementierung befreit werden und vor allem koordinieren.

### Empfohlene Schritte

1. INI-Code-Editor-Hilfsklassen auslagern:
   - `_IniLineNumberArea`
   - `_IniMiniMap`
   - `_TextOverviewMiniMap`
   - `_RevisionTimelineStrip`
   - `_IniCodeEditor`
   - `_IniSyntaxHighlighter`

   Zielmodul: `fl_editor/ini_code_editor.py`

   Status: erledigt. Die INI-Code-Editor-Widgets wurden nach `fl_editor/ini_code_editor.py` verschoben und in `main_window.py` weiterhin unter den bisherigen privaten Namen importiert, damit bestehende Tests und Call-Sites kompatibel bleiben.

2. Startup- und App-Konfig-Glue auslagern:
   - Startup-Progress
   - Update-Check-Scheduling
   - App-Config Import/Export
   - Window-title/version helpers

   Moegliche Zielmodule:
   - `fl_editor/startup_runtime.py`
   - `fl_editor/app_config_runtime.py`

3. Center-TabBar-Widget auslagern:
   - `CenterTabBar`

   Zielmodul: `fl_editor/center_tab_bar.py`

   Status: erledigt. Das Drag/Reorder-State-Widget liegt jetzt in einem eigenen Modul und wird von `main_window.py` nur noch importiert.

4. Mod-Manager-Restlogik aus `MainWindow` weiter in bestehende `mod_manager_*` Module verschieben.

5. Numerischen Table-Item-Helfer auslagern:
   - `_NumericTableWidgetItem`

   Zielmodul: `fl_editor/numeric_table_item.py`

   Status: erledigt. Der Sortierhelfer liegt jetzt in einem eigenen Modul und bleibt in `main_window.py` unter dem bisherigen privaten Namen importiert.

6. Feature-spezifische Menue-/Toolbar-Actions ueber kleine Builder oder Runtime-Module kapseln.

### Validierung

- `tests/test_main_window_smoke.py`
- `tests/test_ini_editor_*`
- `tests/test_mod_manager_*`
- Manueller Startup-Smoke

Ausgefuehrt fuer Schritt 2.1:

- `.\.venv\Scripts\python.exe -m py_compile fl_editor\main_window.py fl_editor\ini_code_editor.py`
- `.\.venv\Scripts\python.exe -m pytest -q tests\test_ini_editor_logic.py`
- `.\.venv\Scripts\python.exe -m pytest -q tests\test_ini_editor_files.py`
- `.\.venv\Scripts\python.exe -m pytest -q tests\test_main_window_smoke.py::test_ini_editor_can_open_context_tree_and_sections tests\test_main_window_smoke.py::test_ini_editor_build_time_machine_dialog_shows_revision_slider`

Bekannte Einschraenkung:

- Ein breiterer Lauf von `tests\test_main_window_smoke.py` wurde nicht als Commit-Gate verwendet. Der gezielte Lauf mit `test_main_window_starts_with_core_navigation` zeigt aktuell einen nicht durch diesen Refactor verursachten Fehler: `MainWindow` hat kein Attribut `nav_savegame_btn`.

Ausgefuehrt fuer Schritt 2.2:

- `.\.venv\Scripts\python.exe -m py_compile fl_editor\main_window.py fl_editor\center_tab_bar.py`
- `.\.venv\Scripts\python.exe -m pytest -q tests\test_main_window_smoke.py::test_center_tab_bar_disables_change_current_on_drag_when_supported tests\test_main_window_smoke.py::test_on_center_tab_changed_ignores_changes_while_tab_reorder_drag_is_active`

Ausgefuehrt fuer Schritt 2.3:

- `.\.venv\Scripts\python.exe -m py_compile fl_editor\main_window.py fl_editor\numeric_table_item.py`
- `.\.venv\Scripts\python.exe -c "from fl_editor.numeric_table_item import _NumericTableWidgetItem; a=_NumericTableWidgetItem(2); b=_NumericTableWidgetItem(10); assert a < b; assert _NumericTableWidgetItem(1.25).text() == '1.25'; print('numeric item ok')"`

### Risiko

Mittel. Die Auslagerung ist strukturell einfach, aber `MainWindow` verbindet viele Features. Importzyklen und gebrochene Signal/Slot-Verbindungen sind die wahrscheinlichsten Fehler.

## Phase 3: Dialog-Monolith splitten

Status: gestartet. Schritt 3.1 ist erledigt.

### Ziel

`fl_editor/dialogs.py` soll in fachliche Dialogmodule aufgeteilt werden, ohne alle Call-Sites auf einmal umzubauen.

### Vorgeschlagene Module

- `fl_editor/zone_dialogs.py`
- `fl_editor/object_dialogs.py`
- `fl_editor/base_dialogs.py`
- `fl_editor/system_dialogs.py`
- `fl_editor/preview_dialogs.py`

### Vorgehen

1. Klassen gruppenweise verschieben.
2. `dialogs.py` vorerst als Kompatibilitaets-Fassade behalten und Klassen re-exportieren.
3. Tests pro Gruppe laufen lassen.
4. Erst spaeter direkte Imports auf neue Module umstellen.

Erledigt in Schritt 3.1:

- `SimpleZoneDialog`, `PatrolZoneDialog` und `ExclusionZoneDialog` wurden nach `fl_editor/zone_dialogs.py` verschoben.
- `fl_editor/dialogs.py` bleibt als Kompatibilitaets-Fassade erhalten und re-exportiert die drei Dialogklassen.
- `ZoneCreationDialog` und `ZonePopulationDialog` bleiben vorerst in `dialogs.py`, damit der Schritt klein und risikoarm bleibt.

### Validierung

- `tests/test_dialog_smoke.py`
- `tests/test_base_*`
- `tests/test_system_*`
- `tests/test_docking_ring_*`
- `tests/test_exclusion_zones.py`

Ausgefuehrt fuer Schritt 3.1:

- `.\.venv\Scripts\python.exe -m py_compile fl_editor\dialogs.py fl_editor\zone_dialogs.py`
- Direkter Qt-Smoke fuer `SimpleZoneDialog`, `PatrolZoneDialog` und `ExclusionZoneDialog`
- Fassaden-Smoke: `from fl_editor import dialogs; assert dialogs.SimpleZoneDialog; assert dialogs.PatrolZoneDialog; assert dialogs.ExclusionZoneDialog`

Bekannte Einschraenkung:

- `tests\test_dialog_smoke.py` kann aktuell nicht gesammelt werden, weil der Test `ConnectionDialog` und `GateInfoDialog` aus `fl_editor.dialogs` importiert, diese Namen dort aber nicht vorhanden sind. Das wurde nicht in Schritt 3.1 behoben, um den Dialog-Split nicht mit einem separaten Test-/Fassadenproblem zu vermischen.

### Risiko

Niedrig bis mittel. Hauptgefahr sind fehlende Imports, Qt-Signal-Verbindungen und versehentlich veraenderte Dialog-Payloads.

## Phase 4: 3D-View modularisieren

### Ziel

`fl_editor/view_3d.py` soll in klarere Verantwortlichkeiten getrennt werden.

### Kandidaten fuer Auslagerung

- Kamera/Orbit/Free-Camera:
  - `fl_editor/view_3d_camera_runtime.py`

- Native Preview Scheduling, Cache und Progress:
  - `fl_editor/view_3d_native_preview_runtime.py`

- Entity-Erzeugung fuer Objekte, Zonen, Planeten, Labels und Gizmo:
  - `fl_editor/view_3d_entities.py`

- Auswahl- und Detail-State koennen weiter mit bestehenden Modulen wie `view_3d_selection_state.py`, `view_3d_native_detail_state.py` und `view_3d_object_logic.py` abgestimmt werden.

### Vorgehen

1. Pure Hilfsfunktionen zuerst bewegen.
2. Danach kleine Runtime-Objekte einfuehren, falls dadurch State sauberer wird.
3. Keine grossen Qt3D-Lebenszyklus-Aenderungen im selben Schritt wie Datei-Splits.
4. Nach jedem Schritt Scene-Smoke und relevante Tests laufen lassen.

### Validierung

- `tests/test_view_3d_*`
- `tests/test_native_scene_*`
- `tests/test_native_preview_*`
- Manueller Smoke mit Systemansicht und nativer Preview

### Risiko

Hoch. Qt3D-Lebenszyklen, Entity-Ownership, Kamera-State und verzögerte Preview-Builds koennen subtil brechen.

## Phase 5: CMP-/Native-Model-Loader strukturieren

### Ziel

`fl_editor/cmp_loader.py` soll besser lesbar und testbarer werden, ohne Decode-Verhalten zu veraendern.

### Kandidaten fuer Module

- `fl_editor/cmp_utf.py`
  - UTF header parsing
  - node parsing
  - string table handling

- `fl_editor/cmp_transforms.py`
  - CMP fix records
  - rotation/translation helpers
  - transform hints

- `fl_editor/cmp_vmesh.py`
  - VMESH layout detection
  - stride/header inference
  - block matching

- `fl_editor/cmp_preview_assembly.py`
  - preview nodes
  - preview geometry candidates
  - material/reference bindings

### Vorgehen

1. Dataclasses und public API stabil halten.
2. Private Funktionsgruppen mit Tests bewegen.
3. Erst nach Stabilisierung neue Abstraktionen einfuehren.
4. Keine heuristischen Parser-Aenderungen mit Struktur-Refactor mischen.

### Validierung

- `tests/test_cmp_loader.py`
- `tests/test_native_preview_*`
- `tests/test_mat_texture_loader.py`
- Falls vorhanden, manuelle Probe mit bekannten CMP-/3DB-Modellen.

### Risiko

Hoch. Byte-Offsets, Header-Heuristiken und Transform-Matrizen sind fehleranfaellig und oft nur durch visuelles Verhalten bemerkbar.

## Phase 6: Write-Pfade absichern und vereinheitlichen

### Ziel

Write-nahe Logik soll besser dokumentiert und an den Modulgrenzen klarer werden, ohne bestehende Semantik zu aendern.

### Kritische Module

- `fl_editor/text_write_utils.py`
- `fl_editor/ini_section_writes.py`
- `fl_editor/universe_writes.py`
- `fl_editor/universe_edit_state.py`
- `fl_editor/system_editor_persistence.py`
- `fl_editor/system_creation_writes.py`
- `fl_editor/bini_data_copy.py`
- `fl_editor/bini_conversion.py`

### Vorgehen

1. Contract-Tests fuer Read-Fallback und Write-Ziel pruefen.
2. Gemeinsame Helper nur dann extrahieren, wenn Duplikate wirklich dieselbe Semantik haben.
3. Keine Schreibpfad-Aenderung ohne passende Regressionstests.
4. Atomic-write-Verhalten und Encoding bewusst beibehalten.

### Validierung

- `tests/test_ini_section_writes.py`
- `tests/test_universe_writes.py`
- `tests/test_system_creation_writes.py`
- `tests/test_system_editor_persistence.py`
- `tests/test_bini_*`
- Mod-Manager-Tests, wenn aktive Mod-Kontexte betroffen sind.

### Risiko

Hoch. Kleine Aenderungen koennen viele Editorfeatures betreffen und Nutzerdaten veraendern.

## Phase 7: Import- und Modulgrenzen bereinigen

### Ziel

Feature-Bereiche sollen klarer voneinander abhaengen. `MainWindow` soll weniger direkte Low-Level-Imports brauchen.

### Aufgaben

- Feature-Fassaden fuer groessere Bereiche pruefen:
  - Mod Manager
  - System Editor
  - INI Editor
  - IDS/Infocard
  - Trade Routes

- Zirkulaere Abhaengigkeiten aktiv vermeiden.
- UI-nahe Module duerfen Runtime koordinieren, Runtime-Module sollten UI moeglichst nicht kennen.
- Gemeinsame Datentypen in kleine neutrale Module legen, wenn mehrere Features sie brauchen.

### Validierung

- Compile-Sanity.
- Vollstaendige Tests nach jedem groesseren Import-Schnitt.

### Risiko

Mittel. Importzyklen sind wahrscheinlich, aber meist schnell sichtbar.

## Empfohlene Reihenfolge

1. `ini_code_editor.py` aus `main_window.py` extrahieren.
2. `dialogs.py` in kompatible Submodule splitten.
3. Mod-Manager-Restlogik aus `main_window.py` verschieben.
4. Startup/App-Config-Glue aus `main_window.py` verschieben.
5. `view_3d.py` in kleinen, testbaren Schritten modularisieren.
6. `cmp_loader.py` nach Parser-/Preview-Verantwortlichkeiten strukturieren.
7. Write-Pfade nur gezielt und testgetrieben bereinigen.

## Definition of Done pro Refactor-Schritt

- Verhalten ist durch vorhandene oder neue Tests abgedeckt.
- Kein bewusstes Aendern von Save-/Write-Semantik ohne explizite Entscheidung.
- Imports bleiben nachvollziehbar und ohne neue Zyklen.
- UI-Text und DE/EN-Verhalten bleiben konsistent.
- Relevante Tests wurden ausgefuehrt und dokumentiert.
- Bei UI-lastigen Aenderungen wurde ein manueller Smoke-Pfad empfohlen oder ausgefuehrt.

## Offene Entscheidungen

- Soll `dialogs.py` dauerhaft als Kompatibilitaets-Fassade bleiben oder spaeter entfernt werden?
- Soll `MainWindow` langfristig in mehrere Controller-Klassen zerlegt werden oder nur Feature-Glue auslagern?
- Wie streng soll eine interne public/private Modulgrenze fuer `fl_editor/` werden?
- Soll vor den grossen Refactors ein statisches Tooling wie Ruff oder MyPy schrittweise eingefuehrt werden?
