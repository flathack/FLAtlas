# FLAtlas Project Plan

Stand: 2026-03-10

## Zielbild

- Produktfluss klarer machen: Start, Mod-Kontext, Navigation, Editor-Wechsel.
- `main_window.py` schrittweise entkoppeln, beginnend mit reiner Hilfslogik.
- Kritische Smoke-Tests fuer UI-Start und Hauptnavigation absichern.
- README und Help auf den tatsaechlichen Produktstand bringen.

## Priorisierte Arbeitspakete

1. Reine UI-/Produktlogik aus `fl_editor/main_window.py` auslagern.
   - DEV-Status-Metadaten
   - Help-XML-Laden
   - Infocard-Helfer
2. Smoke-Tests fuer die wichtigsten Produktpfade ergaenzen.
   - Fensterstart
   - Navigation: Mod Manager, Trade Routes, Name Editor, Settings
   - Moduswechsel im Name/Info-Editor
   - Sprachwechsel
3. Doku an den Ist-Stand anpassen.
   - README-Version und Feature-Liste
   - Help fuer INI Editor und Savegame-Integration
4. Naechster Refactor-Schritt nach diesem Stand:
   - Mod-Manager-Logik aus `main_window.py` in eigene Services zerlegen
   - `retranslate_ui()` in kleinere Feature-Module aufteilen
   - Savegame-/Name-/Trade-View-Builder in eigene Presenter oder Page-Module verschieben

## Verifikation

- `pytest`
- `python -m py_compile fl_atlas.py fl_editor/*.py`
- Offscreen-Smoke-Test durch `tests/test_main_window_smoke.py`
