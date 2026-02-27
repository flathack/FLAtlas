# FL Atlas – Changelog

---

## v0.5 — Sprache & Themes (27. Februar 2026)

### Neue Features

- **Sprachumschaltung DE ↔ EN**
  - Neuer Toggle-Button (DE/EN) in der Toolbar der Universum-Ansicht.
  - Alle UI-Texte (Buttons, Labels, Tooltips, Statusmeldungen, Dialoge, Fehlermeldungen) werden live umgeschaltet — kein Neustart nötig.
  - Übersetzungen liegen in `translations.json` (~280 Schlüssel-Wert-Paare).
  - Externe Konfiguration: Die Datei wird beim ersten Start nach `~/.config/fl_editor/translations.json` kopiert und kann dort frei angepasst werden.
  - Neues Modul `i18n.py` mit `tr()`, `set_language()`, `get_language()`, `reload_translations()`.

- **Theme-Switcher**
  - Dropdown-Menü (🎨 Theme) in der Toolbar neben dem „Über"-Menü.
  - Vier Themes:
    - **Founder Theme** — das bisherige dunkle Blau (#12122a).
    - **Dark** — neutrales Dunkelgrau (#1e1e1e).
    - **Light** — heller Modus (#f5f5f5).
    - **Custom** — eigene Akzentfarbe per `QColorDialog`; daraus wird automatisch eine vollständige Palette abgeleitet.
  - Theme-Auswahl wird in `~/.config/fl_editor/config.json` gespeichert.
  - Neues Modul `themes.py` mit Paletten-Definitionen (20 Farbschlüssel je Theme), `palette_from_accent()`, `get_stylesheet()`, `apply_theme()`.

### Änderungen

- `main_window.py`: Alle ~200+ hartcodierten deutschen Strings durch `tr()`-Aufrufe ersetzt.
- `dialogs.py`: Alle Dialog-Titel, Labels, Buttons, Tooltips und Legenden durch `tr()`-Aufrufe ersetzt.
- `_retranslate_ui()` aktualisiert sämtliche Widget-Texte bei Sprachwechsel.
- `_rebuild_legend()` baut die Legende bei Sprachwechsel komplett neu auf.
- `_make_tb_btn_style()` generiert Toolbar-Button-Styles passend zum aktiven Theme.
- Toolbar-Layout erweitert: `[Aktionen] [Checkboxen] [Buttons] [Modus-Label] [Spacer] [🎨 Theme ▾] [DE/EN] [ℹ️ Über ▾]`
- `_APP_STYLESHEET` entfernt; Stylesheet wird jetzt dynamisch aus der Theme-Palette erzeugt.
- `_LEGEND_ENTRIES` → `_LEGEND_KEYS` (Farbe + Übersetzungsschlüssel statt hartcodierter Texte).

### Bugfixes

- `themes.py`: `Config` wurde als Klasse statt als Instanz aufgerufen (`Config.get()` → `_cfg.get()`), was einen `AttributeError` auslöste.

### Neue Dateien

| Datei | Beschreibung |
|---|---|
| `fl_editor/i18n.py` | Übersetzungsmodul (`tr()`, Sprachverwaltung) |
| `fl_editor/themes.py` | Theme-Engine (4 Themes, Stylesheet-Generierung) |
| `fl_editor/translations.json` | ~280 DE/EN Übersetzungsschlüssel |

---

## v0.4 — FL Atlas (vorherige Sessions)

### Neue Features

- **Umbenennung** von „FLEditor" zu „FL Atlas".
- **Docking Ring erstellen** — Workflow: Planet anklicken → Dialog → Orbit-Platzierung.
- **Base erstellen** — Kompletter Workflow mit Room-Dateien, Base-INI, universe.ini-Eintrag.
- **Base bearbeiten** — Attribute, Equipment, Commodities und Schiffe über Tabbed-Dialog.
- **Base löschen** — Entfernt Objekte, universe.ini-Eintrag, Market-Einträge, Base-INI und Room-Dateien.
- **IDS-Scan** — Alle Systeme nach `ids_name=0` / `ids_info=0` durchsuchen → CSV-Export.
- **IDS-Import** — Ausgefüllte CSV-Einträge zurück in System-INI-Dateien schreiben.
- **Zone Population bearbeiten** — Encounters & Factions per Dialog editieren.
- **Tradelane erstellen / bearbeiten / löschen / repositionieren**.
- **Jump-Verbindungen erstellen** — Zwei-Klick-Modus über Systemgrenzen hinweg.
- **Neues System erstellen** — Auf der Universumskarte platzieren.
- **System-Einstellungen** — Musik, Farben, Hintergrund bearbeiten.
- **3D-Vorschau** — Archetype-Modelle als Qt3D-Preview anzeigen.
- **Hilfe-Datei** (`help.html`) mit umfassender Dokumentation.

### Architektur

- Monolithische Datei aufgeteilt in 12+ Module:
  - `main_window.py`, `dialogs.py`, `models.py`, `parser.py`, `browser.py`
  - `view_2d.py`, `view_3d.py`, `qt3d_compat.py`
  - `config.py`, `path_utils.py`, `pathgen.py`
  - `__init__.py`

### Bugfixes

- Room-Hotspot-Navigationsfehler behoben (`_patch_room_navigation`).
- Version auf 0.4 korrigiert.
