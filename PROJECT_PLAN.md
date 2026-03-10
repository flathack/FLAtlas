# FLAtlas Project Plan

Stand: 2026-03-10

## Zielbild

- Produktfluss klarer machen: Start, Mod-Kontext, Navigation, Editor-Wechsel.
- `main_window.py` schrittweise entkoppeln, beginnend mit reiner Hilfslogik.
- Kritische Smoke-Tests fuer UI-Start und Hauptnavigation absichern.
- README und Help auf den tatsaechlichen Produktstand bringen.

## Priorisierte Arbeitspakete

1. Verbleibende Workflow-Logik aus `fl_editor/main_window.py` weiter zerlegen.
   - Mod-Manager-Aktivierung/Deaktivierung
   - OpenSP-Patchpfade
   - verbleibende Universe-/System-Mutationspfade
2. Produktfluss und UX weiter absichern.
   - Default- und Leerzustaende pruefen
   - Disabled-States und Fehlermeldungen vereinheitlichen
   - Sprachwechsel auf verbleibende Views/Dialogs pruefen
3. Doku und Release-Artefakte weiter an den Ist-Stand anpassen.
   - README, Help und Review-Dokumente nach laufendem Refactor nachziehen
   - Build-/Release-Doku vereinheitlichen
4. Naechster Refactor-Schritt nach diesem Stand:
   - `retranslate_ui()` weiter in kleinere Feature-Module aufteilen
   - verbleibende direkte Dateischreibpfade aus `main_window.py` reduzieren
   - `dialogs.py` auf weitere Aufteilung pruefen

## Verifikation

- `pytest`
- `python -m py_compile fl_atlas.py fl_editor/*.py tests/*.py`
- Offscreen-Smoke-Test durch `tests/test_main_window_smoke.py`
