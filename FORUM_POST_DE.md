FL Atlas - Freelancer Modding Suite
===================================

FL Atlas ist ein Desktop-Tool fuer Freelancer, das mehrere typische Modding-Workflows in einer Anwendung zusammenfuehrt. Das Ziel ist nicht nur das Bearbeiten einzelner Dateien, sondern zusammenhaengende Workflows direkt in einem zentralen Editor anzubieten.

Download-Links:
- GitHub: https://github.com/flathack/FLAtlas
- ModDB: https://www.moddb.com/games/freelancer/downloads/fl-atlas-visual-freelancer-editor-for-systems-modding-and-ids-workflows

Begleitprojekte:
- FL Lingo: https://www.moddb.com/games/freelancer/downloads/fl-lingo-a-freelancer-translator
- Savegame Editor: https://www.moddb.com/games/freelancer/downloads/flatlas-savegame-editor
- FL Atlas Launcher: https://github.com/flathack/FL-Atlas-Launcher

Projektfokus
============

FL Atlas richtet sich an Freelancer-Modder, die:

- Systeme und Universe-Daten visuell bearbeiten wollen
- Bases, Zonen, Objekte und Verbindungen schneller erstellen oder aendern wollen
- DLL-Texte, Infocards und Datei-Referenzen zentral verwalten wollen
- fuer grosse INI-Dateien nicht mehr nur auf einen simplen Texteditor angewiesen sein moechten
- 3D-Modelle, Charaktere und Base-Kompositionen direkt im Tool ansehen wollen

Im aktuellen Entwicklungsbereich von `v0.6.9 -> v0.7.0` wurden grosse Teile von FL Atlas weiter ausgebaut, vereinheitlicht und stabilisiert.

Version Changelog
=================

## v0.6.9 -> v0.7.0

### Highlights
- `File Explorer` und `IDS Editor` wurden weiter als zentrale Workflows geschliffen.
- Die `Time Machine` zeigt jetzt echte Diffs mit Side-by-side, Inline-Modus, Minimap-Markierungen, Timeline und kompakter Sektionsdarstellung.
- Der neue `Clipboard Collector` sammelt kopierten Text und Dateipfade, bleibt als eigenes Tool-Fenster offen und kann Snippets direkt wieder in den Editor einfuegen.
- Erstellungsdialoge fuer Objekte, Weapon Platforms, Wrecks, Depots und Bases haben jetzt deutlich brauchbarere 3D-Vorschauen.
- Das Base-Editing nutzt jetzt einen echten Edit-Modus mit klarerer Trennung von allgemeinen Daten und Base-Loadout.
- Die Tool-Verwaltung in Menueleiste und Settings wurde mit `Pinned Tools` und `FL Atlas Suite Apps` neu organisiert.

### Behobene GitHub-Issues (24)
- `#4` Patrol-Zone-Defaults fuer path-basierte Encounters
- `#6` Neue Starspheres fehlten in der Hintergrund-Auswahl
- `#10` Time-Machine-Diff-Ansicht deutlich ausgebaut
- `#11` Clipboard Collector fuer den File Editor
- `#12` Falsche `dock_with`-Verknuepfungen bei planetaren Base-Edits
- `#13` Base Builder auf Planeten / Docking Rings nicht zulassen
- `#16` Neu erzeugte Systeme als eigener Tab
- `#17` Planet-Deathzone und Atmosphaere aus Planetengroesse vorbelegen
- `#19` Mehrere Probleme im Docking-Ring-Base-Create-Workflow
- `#20` `[Zone]` / `[Object]`-Header im 2D-Objekt-Editor anzeigen
- `#23` 3D-Previews in Erstellungsdialogen
- `#25` Hover-Artefakte in 2D-System- und Universe-View
- `#26` Creation-Buttons im 2D-System-View bei kleinen Fenstern zusammengedrueckt
- `#27` `ids_info` direkt im Planet-Erstellungsdialog anlegen
- `#28` Tabs lassen sich nur Nachbar-weise verschieben
- `#32` Linux: falsche Orientierung einzelner Child-Parts in 3D
- `#35` 2D-Objekt-Editing soll auch `ids_info` bearbeiten
- `#36` Alte User-Configs uebernehmen alte Tab-Namen
- `#37` Base-Edit-Dialog grundlegend ueberarbeitet
- `#40` Zoom/Kamera beim System-Tab-Wechsel bleiben erhalten
- `#46` Komplette Sektionen im File Editor selektieren und kopieren
- `#50` Main-Tab-Management und Suite-Tool-Verwaltung in den Settings
- `#52` Free-Cam-`A`/`D` vertauscht
- `#54` Tradelane-Ringanzahl bei geaenderten Endpunkten falsch

### Ausgewaehlte Funktionsaenderungen
- `Time Machine`:
  - Side-by-side- und Inline-Diff
  - Wort-Level-Highlights
  - Diff-Minimaps mit klaren Markierungen
  - Timeline mit Segmenten und Datum
  - nur geaenderte Sektionen offen, unveraenderte Bereiche kompakt
- `Clipboard Collector`:
  - sammelt normales `Copy` aus dem Editor automatisch ein
  - kann Dateipfade aus dem Explorer mit aufnehmen
  - `Paste`, `Remove`, `Clear all`, `Close`
  - nicht-modal, always-on-top, halbtransparent ohne Fokus
- 2D-System-View:
  - kompaktere rechte Sidebar
  - stabilere Hover-Darstellung
  - bessere Objekt-/Sektionsbearbeitung
  - Zoom- und Kamera-Zustaende bleiben pro Tab erhalten
- Creation/Edit-Dialoge:
  - groessere 3D-Vorschauen
  - Base-Dialog mit rechter Preview-Sidebar
  - `ids_info`-Workflow fuer Planeten und Objekte erweitert
- Settings / Menus:
  - `IDS Editor` statt `Name & Info Editor`
  - `Pinned Tools`
  - `FL Atlas Suite Apps`
  - Web-Apps in einer Zeile mit Internet-Markierung

### Kurzfazit
Der Schritt von `v0.6.9` zu `v0.7.0` war vor allem ein grosser Ausbau der taeglichen Editor-Workflows: bessere Diffs, bessere Vorschauen, weniger UI-Reibung, stabilere System-Tabs und deutlich mehr Direktfunktionen fuer den Datei-Editor.
