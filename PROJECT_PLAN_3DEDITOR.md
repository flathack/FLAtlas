# Projektplan: Aufbau eines Freelancer-spezifischen 3D-Viewers fuer CMP- und 3DB-Dateien

## Kontext

FLAtlas besitzt bereits eine umfangreiche 3D-Systemansicht auf Basis von Qt3D:

- `fl_editor/view_3d.py`
- `fl_editor/view_3d_*` Hilfsmodule
- Integrationslogik in `fl_editor/main_window.py`
- `MeshPreviewDialog` in `fl_editor/dialogs.py`

Der aktuelle Editor kann bereits:

- Systeme, Zonen und Objekte in 3D visualisieren
- Kamera, Auswahl, Gizmo und Flight-Mode bedienen
- Archetypen auf `da_archetype` auflösen
- externe Mesh-Formate wie `obj`, `stl`, `ply`, `gltf`, `glb`, `dae`, `fbx`, `3ds` anzeigen
- bei nicht renderbaren Freelancer-Dateien auf Primitive-Fallbacks zurückfallen

Die zentrale Lücke ist inzwischen präziser:

- Freelancer-Modelle liegen typischerweise als `*.cmp` und `*.3db` vor
- native Vorschaupfade für CMP sind vorhanden und liefern für viele Referenzdateien korrekte Geometrie
- die Haupt-3D-Ansicht nutzt native Daten für das selektierte Objekt (Detail-Entity, Cache, Background-Load)
- viele Objekte werden geometrisch korrekt dargestellt
- **Hauptproblem aktuell**: die Ausrichtung (Orientierung) der nativen Modelle ist noch falsch – „unten ist nicht unten"
- die nötige Orientierungskorrektur muss aus den CMP-Daten kommen (kein generelles Hardcoded-Offset)
- `cmp_orientation_debug.py` berechnet bereits `suggested_up_correction_euler_deg` aus den CMP-`Fix`-Rotationsbasen, wendet diese aber noch nicht auf den Renderpfad an

## Ziel

Der 3D-Viewer soll Freelancer-Objekte so anzeigen, wie sie im Spiel tatsächlich aussehen:

- native Unterstützung für `*.cmp`
- native Unterstützung für `*.3db`
- Verwendung der echten Geometrie statt nur Sphären oder Würfeln
- Anzeige direkt in der bestehenden 3D-Systemansicht und in der Einzelmodell-Vorschau
- Fokus explizit auf echte Freelancer-Dateistrukturen statt auf generische Mesh-Fallbacks

## Erstes nutzbares Zielbild

Der erste belastbare Lieferstand ist bewusst enger als das Endziel. "Freelancer-Dateien in 3D ansehen" gilt fuer diesen Plan als erreicht, wenn folgende Kette funktioniert:

1. eine echte Freelancer-`CMP` oder `3DB` aus der Referenzbasis wird direkt geoeffnet
2. im `MeshPreviewDialog` erscheint sichtbare echte Geometrie statt `cube`-, `sphere`- oder Spezial-Fallback
3. Kamera-Fit, Bounds und Ausrichtung sind fuer die Referenzdatei plausibel
4. dieselbe Datei kann danach fuer ein selektiertes Objekt auch in der System-3D-Ansicht als echtes Detailmodell erscheinen

Der erste Pflichtfall dafuer ist:

- `jump_gatel.cmp` – Geometrie wird dargestellt, Orientierung noch falsch

Danach folgen als zweite Welle:
- `l_dreadnought` – wird noch nicht korrekt dargestellt
- `docking_ringx2_lod.cmp`
- `space_police01.cmp`
- `space_freeport01.cmp`

Wichtig:

- fuer den ersten sichtbaren Meilenstein ist untexturierte oder nur heuristisch texturierte Geometrie akzeptabel
- nicht akzeptabel ist weiterhin ein Primitive-Fallback statt echter Geometrie

## Nicht-Ziele fuer den ersten Meilenstein

Folgende Punkte sind wichtig, aber nicht Blocker fuer die erste echte 3D-Sichtbarkeit:

- vollstaendig spieltreue Materialien
- perfekte Mehrfachtextur- und Shader-Nachbildung
- alle Freelancer-Dateien sofort
- komplette Massendarstellung aller Modelle gleichzeitig in der Systemansicht
- finale Optimierung fuer sehr grosse Systeme

## Definition of Done fuer "Freelancer-Datei sichtbar"

Eine Freelancer-Datei gilt in diesem Projekt erst dann als wirklich "sichtbar", wenn alle folgenden Punkte fuer mindestens eine echte Referenzdatei erfuellt sind:

- `cmp_loader.py` erzeugt keine reine Diagnose mehr, sondern dekodierbare Geometrie fuer die Referenz
- `native_preview_geometry.py` baut daraus mindestens eine reale Rendergeometrie
- `MeshPreviewDialog` zeigt die Geometrie sichtbar und reproduzierbar
- der Dialog braucht dafuer keinen Primitive-Spezialfall fuer genau diese Datei
- dieselbe Datei kann ueber den nativen Szenedatenpfad in `view_3d.py` fuer das selektierte Objekt erscheinen
- der Erfolg ist durch Tests und einen dokumentierten Referenzfall abgesichert

## Referenzbasis

Primäre Referenzbasis für Decoder-, Preview- und Viewer-Arbeit:

- Ein Programm, dass bereits diese formate lesen kann: `C:\Program Files\Freelancer Mod Studio`
sowie C:\Program Files (x86)\HardCMP Editor. es können aus beiden programmen screenshots gezeigt werden zum gegenchecken.
- Verzeichnis: `C:\Users\STAdmin\FLAtlas\FL-Installationen\_FL Fresh Install-deutsch\DATA\SOLAR\DOCKABLE`
- erste Pflicht-Referenzen:
  - `jump_gatel.cmp`
  - `docking_ringx2_lod.cmp`
  - `space_police01.cmp`
  - `space_freeport01.cmp`
  -  space_port_dmg
  -  space_shipping02 - türen werden noch nicht korrekt positioniert.

Diese Dateien sind ab jetzt die maßgebliche Referenz. Ziel ist ein Viewer, der gezielt auf Freelancer-CMP- und 3DB-Dateien ausgerichtet ist, nicht nur ein allgemeiner 3D-Preview mit Spezial-Fallbacks.

## Aktueller Umsetzungsstand

Stand nach den letzten CMP-, Preview- und Material-Schritten:

- Phase 1 ist umgesetzt:
  - Modellauflösung ist in `freelancer_model_resolver.py` gekapselt
  - renderbare Standardformate, Freelancer-native Formate und Fallbacks sind getrennt
- Phase 2 ist weit fortgeschritten:
  - `cmp_loader.py` liest UTF-Struktur, Knotenpfade, Parts, `VMeshRef`, `VMeshData`, Modellknoten und Preview-Metadaten
  - `freelancer_mesh_data.py` enthält ein eigenes internes Datenmodell
  - Bounds, Hierarchie, Part-Metadaten, Geometriequellen, Layout-Heuristiken und Buffer-Slices werden erzeugt
  - `Cmpnd/Cons/Fix` wird als partbezogene Record-Metadaten erfasst und über `Part_*/Index` an Parts gekoppelt
  - `Cmpnd/Cons/Fix` wird in stabile Zeilen- und Blockstruktur zerlegt
  - aus `Cmpnd/Cons/Fix` werden bereits Transform-Hinweise wie Translation, Leitvektor und erste Rotationsbasen abgeleitet
  - Rotationsbasen werden inzwischen auch dann stabilisiert, wenn nur eine partielle Basis in `Fix` vorliegt und die dritte Achse rekonstruiert werden muss
  - lokale `Fix`-Transform-Hinweise werden jetzt pro Part auch als kombinierte Parent-Child-Hinweise (Translation/Rotation) vorbereitet
- Phase 3 ist als nativer Preview-Pfad nutzbar:
  - `MeshPreviewDialog` rendert native Freelancer-Geometrie nicht mehr nur als Primitive- oder Text-Fallback
  - für `exact`- und `tight`-Fälle werden echte Vertex- und Index-Daten dekodiert und in Qt3D gerendert
  - mehrere native Geometrien pro Modell werden gemeinsam dargestellt
  - mehrere native Geometrien werden pro Part, Modell und Group-Range differenziert dargestellt
  - native Bounds werden für Kamera-Fit und Bounding-Visualisierung verwendet
  - `Reset Camera`, `Bounding Box`, `Wireframe` und `Part Names` sind im nativen Preview-Pfad verfügbar
  - erste Material- und Texturreferenzen werden extrahiert, auf Dateien aufgelöst und heuristisch auf native Geometriepfade gebunden
  - der Dialog nutzt jetzt einen separaten Szenedaten-Helfer für native Geometrien, Bounds, Part-Namen und globale Texturauflösung
  - der Dialog zeigt jetzt zusätzliche Referenzprüfungen pro nativer Geometrie, inklusive Bounds-Zentrum, Radius, Texturbindung und Translation-Hinweis
  - die Referenzprüfungen zeigen jetzt zusätzlich eine kompakte Delta-Zusammenfassung (Match/Mismatch gegen Translation-Hints, max. Delta, fehlende Texturen)
  - pro Geometrie werden jetzt explizite Delta- und Match-Werte zwischen Bounds-Zentrum und Translation-Hint ausgewiesen und im Dialog nach Abweichung priorisiert
  - Referenzzeilen unterscheiden jetzt lokales Bounds-Zentrum (`lc`) und Anzeigezentrum (`c`), damit lokale Geometrie und Translation-Hint klarer gegeneinander geprüft werden können
  - Referenz-Checks markieren Translation-Abweichungen jetzt zusätzlich mit Severity-Stufen (`ok`/`warn`/`high`) und zählen hohe Abweichungen separat
  - Referenz-Checks bewerten jetzt auch Rotationsqualität aus `Fix`-Basen (`det`, `ortho`, `rot=ok|warn|high`) und zählen Rotations-Risikofälle in der Summary
  - der native Geometriepfad nutzt jetzt bei Verfügbarkeit kombinierte Parent-Child-Transform-Hinweise (Translation/Rotation) statt nur lokaler Teil-Hinweise
  - Referenz-Checks nutzen jetzt ebenfalls bevorzugt kombinierte Parent-Child-Hinweise; Translation-/Rotationsquellen (`combined`/`local`) werden pro Zeile und in der Summary ausgewiesen
  - `jumpgate` besitzt jetzt einen Freelancer-spezifischen Preview-Fallback statt eines generischen `cube`
- Phase 4 bis 6 sind teilweise umgesetzt:
  - **Phase 4** (System-3D-Ansicht): selektionsbezogener Native-Detailpfad ist vorhanden und funktional
  - Part- und Model-Transforms sind für viele Referenzdateien nutzbar, aber die **Orientierung** ist noch falsch (siehe Orientierungsbug)
  - Material- und Texturpfad ist weiterhin heuristisch und noch nicht materialtreu
  - die erste native Detail-Entity in `view_3d.py` für selektierte Objekte ist jetzt vorhanden
  - Bounds werden jetzt bereits für das Fokussieren selektierter nativer Detailmodelle genutzt
  - ein erster Render-Cache für wiederholt selektierte Detailmodelle ist jetzt vorhanden
  - ein erster Hintergrundladepfad für selektionsbezogene native Szenedaten ist jetzt vorhanden
  - der Hintergrundladepfad priorisiert jetzt die aktuelle Selektion und verwirft veraltete, noch abbrechbare Pending-Loads
  - der native Szenedaten-Cache ist jetzt größenbegrenzt und wird per MRU-Reihenfolge bereinigt, um unbounded Wachstum bei langen Sessions zu vermeiden
  - die 3D-Synchronisierung nach Hintergrund-Loads läuft jetzt selektionsrelevant statt bei jedem abgeschlossenen Load
  - fehlgeschlagene Hintergrund-Loads blockieren einen Modellpfad nicht mehr dauerhaft; sie werden nach Cooldown erneut versucht
  - die Archetype-zu-Modell-Auflösung für selektionsbezogene Native-Details nutzt jetzt zusätzlich einen kleinen Cache, um wiederholte Resolve-Läufe zu reduzieren
  - der selektionsbezogene Detailpfad ist jetzt zusätzlich gegen Selektion/Deselektion, Objektbewegung, Rotation und `clear_scene()` gehärtet
  - `MainWindow` und Native-Scene-Runtime besitzen jetzt einen expliziten Diagnosepfad mit Event-/Status-Snapshots für Cache, Queue, Sync und verworfene Loads
  - alte Pending-Loads werden jetzt beim Verlust der Selektion oder deaktivierter 3D-Ansicht aktiv verworfen statt nur später ins Leere zu laufen
  - die `MainWindow`-Logik für Native-Scene-Runtime, Modellpfad-Cache und selektionsbezogenen Native-Sync ist jetzt in ein eigenes Runtime-Modul ausgelagert


## Neue Erkenntnisse aus echten Dockable-Dateien

Die Analyse echter Dateien aus `DATA\\SOLAR\\DOCKABLE`, insbesondere `jump_gatel.cmp`, hat den technischen Schwerpunkt mehrfach verschoben.

Wichtigste abgeschlossene Befunde:

- UTF-Knotenstruktur, Parts, VMeshRef/VMeshData-Blöcke werden korrekt gelesen
- `FlModelCrc`-Auflösung matcht `mesh_data_reference` deterministisch auf echte `*.vms`-Dateinamen
- VMeshData-Familien (Header-/Stream-Paarungen) werden erkannt und korrekt dekodiert
- strukturierte `MeshHeader`-Semantik ist bestätigt (`vertex_start + vertex_count`, `index_start + index_count`, `group_start + group_count`)
- für `jump_gatel.cmp` liefern sowohl `Level3` (family-split-header-stream) als auch `Level4` (structured-single-block) echte native Geometrie
- `decode_native_preview_geometries(...)` liefert für `jump_gatel.cmp` mehrere reale Geometrien
- der `MeshPreviewDialog` zeigt diese Geometrie nativ an (Render path: native geometry)
- die Geometrie ist visuell als Jumpgate erkennbar

Aktuelles Hauptproblem:

- **Orientierung ist falsch** – die Geometrie wird dargestellt, aber „unten ist nicht unten"
- Beispiel: `Li01_08` mit `rotate = 0, 40, 0` sollte tatsächlich `rotate = -90, -140, 0` benötigen, damit das Objekt korrekt ausgerichtet ist
- die -90°-X-Differenz ist kein allgemeines Hardcoded-Offset, sondern muss aus den CMP-`Fix`-Daten abgeleitet werden
- `cmp_orientation_debug.py` berechnet bereits `suggested_up_correction_euler_deg` aus dem Axis-Mapping der CMP-Rotationsbasen
- diese Korrektur wird aktuell **nicht** auf den Renderpfad angewendet (nur diagnostisch in der Referenzansicht sichtbar)
- der Fix muss in `view_3d_native_detail_state.py` → `native_detail_transform_state()` integriert werden

Folgerung:

- die Hauptarbeit liegt jetzt nicht mehr im Decoder oder Parser, sondern in der korrekten Orientierungsanwendung
- `jump_gatel.cmp` und weitere Referenzen werden zur Pflicht-Referenz für Orientierungsvalidierung
- die CMP-Orientierungsdaten sind bereits berechnet und müssen nur noch in den Renderpfad durchgereicht werden

## Arbeitsstand 2026-03-14

Der 3D-Viewer ist über das reine Decoder-Stadium hinaus. Geometrie wird für mehrere Referenzdateien korrekt dargestellt:

- nativer CMP-Datenpfad ist vorhanden und liefert echte Geometry für `jump_gatel.cmp` und weitere Dockables
- Preview und selektionsbezogene System-3D-Ansicht teilen sich denselben Szenedaten-Unterbau
- selektierte Objekte erscheinen als echtes Detailmodell (nicht mehr als Primitive)
- Background-Load, Cache und Retry-Grundlogik für den Detailpfad existieren
- `FlModelCrc`-Auflösung, VMeshData-Familien und strukturierte Decoder sind stabil

Der Engpass hat sich konkretisiert:

- **Orientierung**: viele Objekte werden geometrisch korrekt gerendert, aber die Ausrichtung stimmt nicht – „unten ist nicht unten"
- Beispiel: `Li01_08` hat in den INI-Daten `rotate = 0, 40, 0`, braucht aber tatsächlich `rotate = -90, -140, 0`, damit es korrekt aussieht
- die -90°-Differenz auf der X-Achse ist **kein** pauschales Offset – sie muss aus dem CMP-Achsen-Mapping kommen
- `cmp_orientation_debug.py` berechnet `suggested_up_correction_euler_deg` bereits korrekt aus den CMP-`Fix`-Rotationsbasen
- diese Korrektur wird aktuell nur diagnostisch angezeigt, aber **nicht** im Renderpfad angewendet
- der Fix gehört in `view_3d_native_detail_state.py` → `native_detail_transform_state()`, wo die CMP-Orientierungskorrektur mit dem INI-Rotate kombiniert werden muss

Damit ist die nächste Iteration klar:

1. CMP-Orientierungskorrektur aus `cmp_orientation_debug.py` in den Renderpfad integrieren
2. Orientierung gegen echte Referenzobjekte validieren (Li01_08, weitere Gates, Stationen)
3. Transform-Kette: CMP-Up-Correction × INI-Rotate × Position
4. danach Material-/Texturtreue und breitere Modellabdeckung

## Orientierungsbug (Hauptblocker)

### Symptom

Viele 3D-Objekte werden geometrisch korrekt dargestellt, aber die Ausrichtung ist falsch – „unten ist nicht unten".

### Konkretes Beispiel

**Li01_08** (Jump Gate im New York-System):
- INI-Daten: `rotate = 0, 40, 0`
- Tatsächlich nötig für korrekte Darstellung: `rotate = -90, -140, 0`
- Differenz auf X-Achse: -90° (kommt aus dem CMP-Achsen-Mapping, nicht als pauschales Offset)

### Ursache

- `cmp_orientation_debug.py` berechnet bereits `suggested_up_correction_euler_deg` aus den CMP-`Fix`-Rotationsbasen
- Die Funktion `_up_correction_from_local_y()` mappt Achslabels (+X/-X/+Y/-Y/+Z/-Z) auf Euler-Korrekturwinkel
- Beispiel-Output: `axis_map: X=+X Y=-Z Z=+Y` → `suggested_up_correction: 90.0, 0.0, 0.0`
- Diese Korrektur wird **nur diagnostisch angezeigt** (im Referenz-Panel), aber **nicht** auf den Renderpfad angewendet

### Betroffene Module

- `fl_editor/view_3d_native_detail_state.py`: `native_detail_transform_state()` berechnet aktuell nur Trade-Lane-Rotation, ignoriert CMP-Orientierung
- `fl_editor/view_3d.py`: `_rebuild_selected_native_detail_entity()` wendet `rotate_euler_deg` aus `transform_state` an – dieses enthält nie die CMP-Korrektur
- `fl_editor/cmp_orientation_debug.py`: Berechnet die Korrektur korrekt, aber das Ergebnis wird nirgends im Renderpfad konsumiert

### Lösung

- `native_detail_transform_state()` muss `suggested_up_correction_euler_deg` aus den CMP-Orientierungsdaten lesen
- die CMP-Korrektur muss mit dem INI-Rotate kombiniert werden: **CMP-Up-Correction × INI-Rotate × Position**
- es darf **kein** generelles Hardcoded-Offset geben – die „wo ist unten"-Info muss aus dem CMP-File kommen
- jedes CMP hat sein eigenes Achsen-Mapping, die Korrektur ist modellspezifisch

### Validierung

- Li01_08: `rotate = 0, 40, 0` muss nach CMP-Korrektur korrekt ausgerichtet sein
- weitere Gates, Stationen und Dockables aus der Referenzbasis prüfen
- Test: `suggested_up_correction_euler_deg` wird für bekannte Referenz-CMPs korrekt berechnet und angewendet

Neuer Teilbefund (historisch, inzwischen abgeschlossen):

- `VMeshData`-Familienerkennung, `FlModelCrc`-Auflösung und `MeshHeader`-Semantik sind implementiert und stabil
- `Level3` (family-split-header-stream) und `Level4` (structured-single-block) liefern echte Geometrie
- der Decoder nutzt bestätigte `MeshHeader`-Semantik mit 16-Bit-Index-Fallback
- für die Referenzdatei `jump_gatel.cmp` existieren mehrere dekodierte native Geometrien

Bereits vorhandene Kernmodule:

- `fl_editor/freelancer_model_resolver.py`
- `fl_editor/cmp_loader.py`
- `fl_editor/freelancer_mesh_data.py`
- `fl_editor/native_preview_geometry.py`

Bereits vorhandene Testbasis:

- `tests/test_cmp_loader.py`
- `tests/test_mesh_preview_dialog.py`
- `tests/test_native_preview_geometry.py`

## Nutzerbedarf

### Für Mapper und System-Designer

- das echte 3D-Modell an der Objektposition sehen
- Größe, Rotation und Orientierung realistisch prüfen
- bessere Platzierung von Basen, Gates, Jumpholes, Planeten, Stationen und Solars
- visuelle Kollisionen und Überlappungen früher erkennen

### Für Modder

- sicher prüfen, ob ein Archetype auf die richtige CMP-Datei zeigt
- schnell erkennen, wenn ein Modell fehlt oder falsch aufgelöst wird
- neues Asset direkt im Editor testen
- visuell gegen bestehende Spielobjekte vergleichen

### Für die Editor-Qualität insgesamt

- weniger Ratespiel bei Archetypen
- weniger Fallback-Primitive
- höherer Nutzen des 3D-Modus
- bessere Glaubwürdigkeit des Editors als Modding-Werkzeug

## Technisch relevante Stellen

- `main_window.py`
  - `_build_archetype_model_index()`
  - `_resolve_model_for_archetype()`
  - `_find_preview_mesh_candidate()`
  - `_show_selected_3d_preview()`
- `dialogs.py`
  - `MeshPreviewDialog`
- `view_3d.py`
  - Qt3D-gestützte Systemdarstellung

## Ist-Zustand

Der Datenpfad ist funktional durchgängig:

- Modellauflösung und Formatklassifikation sind aus der UI-Logik herausgelöst
- die Einzelmodell-Vorschau besitzt einen nativen CMP-Renderpfad mit echter Geometrie
- die Haupt-3D-Ansicht besitzt einen selektionsbezogenen nativen Detailpfad mit Cache und Background-Load
- Preview und Systemansicht teilen sich denselben Szenedaten-Unterbau

Die größten aktuellen Einschränkungen sind:

- **Orientierung**: CMP-Modelle werden geometrisch korrekt dargestellt, aber die Ausrichtung stimmt nicht (siehe Orientierungsbug-Sektion)
- Material- und Texturzuordnung ist heuristisch, nicht vollständig
- nicht alle CMP-/3DB-Varianten werden bereits korrekt dekodiert

## Zielbild

Der 3D-Editor soll aus drei Schichten bestehen:

### 1. Modellauflösung

- Archetype -> `da_archetype` -> tatsächliche Modelldatei
- Unterstützung für Freelancer-Dateitypen und Standard-Meshes
- klare Ausgabe, welche Renderstrategie verwendet werden soll

### 2. Freelancer-Modellimport

- Loader für `CMP`-Inhalte
- Extraktion von Geometrie, Knoten, Parts, Transform und optional Material-Infos
- Umwandlung in interne, Qt3D-kompatible Mesh-Daten

### 3. Darstellung im Editor

- echtes Modell in der Einzelvorschau
- echtes Modell für das selektierte Objekt in der System-3D-Ansicht
- Fallback nur noch bei echten Fehlerfällen

## Technische Leitidee

Freelancer-`CMP` ist kein direkt von Qt3D lesbares Standard-Meshformat. FLAtlas braucht deshalb einen eigenen Importpfad.

Der sinnvolle Ausbau bleibt:

1. Loader und Decoder robust machen
2. interne Mesh- und Transform-Daten stabilisieren
3. denselben nativen Pfad in Preview und Systemansicht verwenden
4. erst danach Materialtreue, Caching-Ausbau und Mehrfachmodelle vertiefen

## Priorisierte Decoder-Reihenfolge

Die Decoder-Arbeit fuer die erste Referenzdatei ist abgeschlossen:

1. ✅ `jump_gatel.cmp` `Level4` als strukturierter Single-Block-Fall – dekodiert und sichtbar
2. ✅ `jump_gatel.cmp` `Level3` als strukturierter Header-/Stream-Familienfall – dekodiert und sichtbar
3. dieselben Decoderpfade fuer weitere `DOCKABLE`-Referenzen stabilisieren
4. erst danach breitere `CMP`-/`3DB`-Abdeckung und Materialtreue erweitern

**Aktueller Fokus**: Orientierungskorrektur (Decoder liefert korrekte Geometrie, aber die Ausrichtung stimmt nicht)

## Lieferstrecke bis zur ersten sichtbaren Freelancer-Datei

Die naechsten Arbeitspakete muessen jetzt direkt auf ein sichtbares Renderergebnis einzahlen. Die Reihenfolge ist absichtlich eng:

### Paket A: `jump_gatel.cmp` `Level4` sichtbar machen

Ziel:

- erster echter nativer Geometriepfad ohne Primitive-Fallback

Betroffene Module:

- `fl_editor/cmp_loader.py`
- `fl_editor/freelancer_mesh_data.py`
- `fl_editor/native_preview_geometry.py`
- `tests/test_cmp_loader.py`
- `tests/test_native_preview_geometry.py`

Erwartetes Ergebnis:

- `structured_decode_plan` fuer `Level4` wird in echte Vertex-/Index-Geometrie umgesetzt
- `decode_native_preview_geometries(...)` liefert fuer `jump_gatel.cmp` mindestens eine reale Geometrie
- der Preview-Dialog kann diese Geometrie sichtbar rendern

Aktueller Stand:

- erreicht ✅ – Decode und Render funktionieren
- `decode_native_preview_geometries(...)` liefert fuer `jump_gatel.cmp` reale `Level4`-Geometrie mit `confidence = structured-single-block`
- der `MeshPreviewDialog` zeigt den nativen Renderpfad (`Render path: native geometry`)
- Geometrie ist visuell als Jumpgate erkennbar
- **offener Restpunkt**: Orientierung noch falsch (siehe Orientierungsbug)

### Paket B: `jump_gatel.cmp` `Level3` Family-Decode sichtbar machen

Ziel:

- erster echter Header-/Stream-Paar-Decoder fuer reale Freelancer-Familien

Betroffene Module:

- `fl_editor/cmp_loader.py`
- `fl_editor/freelancer_mesh_data.py`
- `fl_editor/native_preview_geometry.py`
- `tests/test_cmp_loader.py`
- `tests/test_native_preview_geometry.py`

Erwartetes Ergebnis:

- `family-split-header-stream` wird nicht mehr nur diagnostiziert, sondern dekodiert
- `jump_gatel_lod3` liefert sichtbare Geometrie statt `no-fit`

Aktueller Stand:

- erreicht ✅ – Decode und Render funktionieren
- `decode_native_preview_geometries(...)` liefert fuer `jump_gatel.cmp` reale `Level3`-Geometrie mit `confidence = structured-family-split`
- Family-Decoder nutzt Header-/Stream-Paarung korrekt
- **offener Restpunkt**: Orientierung noch falsch (siehe Orientierungsbug)

### Paket C: Preview-Abnahme gegen Referenzdateien

Ziel:

- sichtbarer Decoderpfad nicht nur fuer eine, sondern fuer mehrere echte Freelancer-Dateien

Referenzen:

- `jump_gatel.cmp`
- `docking_ringx2_lod.cmp`
- `space_police01.cmp`
- `space_freeport01.cmp`

Erwartetes Ergebnis:

- fuer jede Referenz ist dokumentiert:
  - native Geometrie sichtbar ja/nein
  - welche LODs dekodieren
  - ob Fallback noch noetig ist
  - welche sichtbaren Probleme offen bleiben

### Paket D: Uebernahme in die System-3D-Ansicht

Ziel:

- derselbe erfolgreiche Preview-Pfad erscheint auch fuer selektierte Objekte in `view_3d.py`

Betroffene Module:

- `fl_editor/native_scene_main_window_runtime.py`
- `fl_editor/view_3d.py`
- `fl_editor/main_window.py`
- `tests/test_main_window_smoke.py`
- `tests/test_view_3d_widget_smoke.py`

Erwartetes Ergebnis:

- ein Objekt mit `jump_gatel.cmp` oder anderer erfolgreicher Referenz erscheint auch in der Systemansicht als echte Geometrie
- der Detailpfad faellt nur noch bei echten Decoder-Fehlern auf Marker/Fallback zurueck

Aktueller Stand:

- der selektionsbezogene `view_3d.py`-Pfad verarbeitet bereits mehrere native Geometrien aus einer Szene
- die Debug-Sicht meldet jetzt dafuer explizit:
  - `geometry_count`
  - `geometry_confidences`
- `MainWindow` uebernimmt diese Detailsicht jetzt ebenfalls in den Native-Scene-Debug-Snapshot
  - damit ist aus dem normalen Objekt-Workflow direkt sichtbar, was `view3d` fuer das selektierte Objekt gerade wirklich rendert
- damit ist die Uebernahme des nativen Preview-Erfolgs in den System-Detailpfad nicht mehr nur implizit, sondern gezielt pruef- und testbar

## Testmatrix fuer echte Referenzdateien

Die Teststrategie darf sich nicht mehr nur auf synthetische Fixtures stuetzen. Fuer jede Referenzdatei wird ab jetzt dieselbe Matrix angewendet:

1. `cmp_loader.py`
   - Datei wird gelesen
   - `preview_geometry_sources` werden erzeugt
   - `structured_decode_plans` oder family-aware Decoderpfade sind vorhanden
2. `native_preview_geometry.py`
   - mindestens eine reale Geometrie wird erzeugt
   - Geometrie hat plausible Bounds
3. `MeshPreviewDialog`
   - sichtbare Geometrie statt Primitive-Fallback
   - Kamera-Fit funktioniert
4. `view_3d.py`
   - selektiertes Objekt kann dieselbe Geometrie als Detailmodell anzeigen

Die erste verpflichtende gruen-zu-pruefende Matrix ist:

- `jump_gatel.cmp`

Danach:

- `docking_ringx2_lod.cmp`
- `space_police01.cmp`
- `space_freeport01.cmp`

## Referenz-Abnahmeliste

Diese Liste ist die operative Sicht auf den Plan. Jede Datei bekommt einen klaren Status statt nur allgemeiner Aussagen.

### `jump_gatel.cmp`

Zielstatus fuer die erste echte Lieferung:

- `Level4` sichtbar im Preview
- `Level3` sichtbar im Preview
- kein Primitive- oder Spezial-Fallback mehr fuer den erfolgreichen LOD-Fall
- selektiertes Objekt kann denselben Pfad in der Systemansicht nutzen

Offene Kernfragen:

- Positionsoffset im Vertexrecord
- reales Indexformat und Indexbereich
- exakte Auswertung der `MeshHeader`-Semantik gegen Stream-Daten

### `docking_ringx2_lod.cmp`

Zielstatus fuer die zweite Welle:

- mindestens ein sichtbarer nativer LOD-Fall im Preview
- Vergleich, ob derselbe Decoderpfad wie bei `jump_gatel.cmp` wiederverwendbar ist

Offene Kernfragen:

- nutzt die Datei denselben Family-Aufbau oder einen anderen realen Variantenfall
- ob die bereits benannten Header-Endsemantiken hier ebenfalls tragen

### `space_police01.cmp`

Zielstatus fuer die zweite Welle:

- sichtbare native Geometrie im Preview
- Plausibilitaetscheck fuer Bounds, Orientierung und Fokus

Offene Kernfragen:

- andere Part- oder Materialstruktur als Dockables
- moegliche Unterschiede bei LOD- und Group-Aufteilung

### `space_freeport01.cmp`

Zielstatus fuer die zweite Welle:

- sichtbare native Geometrie im Preview
- stabile Nutzung im selektionsbezogenen System-Detailpfad

Offene Kernfragen:

- groessere Part-Zahl
- groessere Material- und Texturvielfalt
- Performance unter realer Preview- und Detaildarstellung

## Blocker-Katalog fuer die ersten sichtbaren Modelle

Folgende Punkte sind ab jetzt echte Lieferblocker und nicht nur "spaeter noch verbessern":

- **Orientierung falsch**: CMP-Modelle werden geometrisch dargestellt, aber „unten ist nicht unten" – die CMP-Orientierungskorrektur (`suggested_up_correction_euler_deg`) wird berechnet, aber nicht im Renderpfad angewendet
- sichtbare Geometrie mit offensichtlich falscher Bounds- oder Fokuslage
- Preview und Systemansicht verwenden unterschiedliche native Datenpfade und driften auseinander

Bereits behoben (kein Blocker mehr):

- ~~`decode_ready`, aber weiterhin `0` reale Geometrien fuer die Referenzdatei~~ → Geometrie wird jetzt erzeugt
- ~~sichtbare Geometrie nur ueber Primitive- oder Spezial-Fallback statt ueber nativen Decode~~ → nativer Decode funktioniert
- ~~Header-/Stream-Familie wird nur diagnostiziert, aber nicht bis zu Renderdaten aufgeloest~~ → Family-Decode funktioniert

Nicht als Blocker fuer den ersten Meilenstein zaehlen:

- noch unvollstaendige Texturtreue
- einfache Qt3D-Materialien
- fehlende Mehrfachmodell-Darstellung
- noch nicht abgedeckte Fremddateien ausserhalb der Referenzbasis

## Risiko- und Entscheidungsregister

### Risiko 1: weitere Heuristik statt echter Semantik

Gefahr:

- der Loader produziert neue `weak`- oder Diagnosepfade, aber weiterhin keine sichtbare Geometrie

Entscheidung:

- keine weitere breite Layout-Heuristik ohne direkten Bezug auf `jump_gatel.cmp` `Level4` oder `Level3`

### Risiko 2: Preview-Erfolg ohne Wiederverwendung in `view_3d.py`

Gefahr:

- sichtbare Geometrie erscheint nur im Dialog, nicht im eigentlichen Editor-Nutzfall

Entscheidung:

- jeder erfolgreiche Preview-Decoder muss anschliessend explizit gegen den selektionsbezogenen Native-Detailpfad eingeplant werden

### Risiko 3: Materialtreue zieht den Scope auseinander

Gefahr:

- Geometrie wird zugunsten von Materialdetails wieder nach hinten geschoben

Entscheidung:

- Materialtreue bleibt nachrangig, bis `jump_gatel.cmp` sichtbar ohne Fallback laeuft

## Ausbauplan

## Phase 1: Modellauflösung und Datenpfad

Ziel:

- Die bestehende Modellauflösung von der eigentlichen Darstellung trennen.

Status:

- umgesetzt

Ergebnis:

- Archetype- und Preview-Modellauflösung ist aus `main_window.py` in `freelancer_model_resolver.py` gezogen
- direkte UI-Fallback-Entscheidungen sind von der Auflösung getrennt
- der Pfad unterscheidet sauber zwischen:
  - direkt renderbaren Formaten
  - Freelancer-nativen Formaten wie `cmp` und `3db`
  - Fallback- und Fehlerfällen

## Phase 2: CMP- und 3DB-Dateien lesbar machen

Ziel:

- `*.cmp` und `*.3db` strukturell einlesen und in ein internes Datenmodell überführen.

Status:

- weit fortgeschritten

Bereits erreicht:

- UTF-Header und UTF-Knotenstruktur werden gelesen
- Parent- und Path-Hierarchie der Knoten wird rekonstruiert
- Parts inklusive `File name` und `Object name` werden extrahiert
- Part-Indizes aus `Index`-Nodes werden extrahiert
- `VMeshRef` wird inklusive Bounds gelesen
- `VMeshData`-Blöcke werden gelesen und mit Metadaten versehen
- `Cmpnd/Cons/Fix` wird als partbezogene Record-Liste gelesen
- diese Records werden über `Part_*/Index` stabil an Parts gekoppelt
- `Cmpnd/Part_*`-Kinder werden jetzt beim Part-Aufbau bevorzugt pfadbasiert ausgewertet statt nur per linearem Folgescan
- reale Freelancer-`*_lod...`-Modellnamen mit langem Ziffernsuffix werden jetzt näher an ihre eigentliche LOD-Form normalisiert, damit Part-Matching für Referenzdateien wie `jump_gatel.cmp` früher greift
- der Loader erzeugt jetzt explizite Warnungen für `unresolved`-Referenzen, `no-fit`-Layouts und den Fall "resolved but no buffer slices"
- UTF-Data-Offsets werden jetzt sowohl für synthetische absolute Fixtures als auch für reale relative Freelancer-Dateien aufgelöst
- `VMeshData`-Layout-Heuristiken bevorzugen jetzt reale Freelancer-Stride-Hinweise aus `*.vms`-Dateinamen wie `-112` oder `-212`
- Records tragen bereits strukturierte Row-Darstellung mit `row_count`, `row_width` und `rows`
- daraus werden bereits aufgebaut:
  - `model_nodes`
  - `preview_nodes`
  - `preview_mesh_bindings`
  - `preview_geometry_candidates`
  - `preview_submeshes`
  - `preview_geometry_sources`
  - `preview_layout_guesses`
  - `preview_buffer_slices`
  - `cmp_fix_records`
  - `cmp_transform_hints`

Noch offen:

- belastbare vollständige Dekodierung von Part- und Model-Transforms aus nativen CMP-Daten (Geometrie funktioniert, **Orientierung noch falsch**)
- **CMP-Orientierungskorrektur in den Renderpfad integrieren** (Daten werden in `cmp_orientation_debug.py` bereits berechnet, aber nicht angewendet)
- klare Definition, wann ein Transform-Pfad als korrekt gilt
- kombinierte Parent-Child-Hinweise werden jetzt im nativen Geometriepfad bevorzugt verwendet; offen bleibt die vollständige Validierung gegen größere Referenz-CMPs

Abnahmekriterien:

- mindestens ein einfacher Freelancer-CMP-Archetype kann intern als Mesh-Struktur geladen werden
- Transform-Daten lassen sich für bekannte Referenzmodelle konsistent reproduzieren

## Phase 3: Einzelmodell-Vorschau mit echten CMPs und 3DBs

Ziel:

- `MeshPreviewDialog` zeigt echte Freelancer-Geometrie statt Primitive-Fallback.

Status:

- nutzbar, aber noch nicht fertig

Bereits erreicht:

- `MeshPreviewDialog` zeigt native Modellinformationen in einer strukturierten Seitenleiste
- Part-Einträge und Fix-Records zeigen den zugehörigen CMP-Index an
- Fix-Records zeigen ihre Blockstruktur, z. B. `rows=4x11`
- erste Transform-Hinweise aus `Fix` werden im Preview-Panel sichtbar gemacht
- Translation, Leitvektor-Rotation und erste 3x3-Rotationsbasen werden auf native Preview-Geometrien angewendet
- partielle 3x3-Basen aus `Fix` können jetzt zu stabilen Vorschau-Rotationen ergänzt werden, solange mindestens zwei belastbare Achsen vorliegen
- für `exact`- und `tight`-Layout-Fälle werden echte Vertex- und Index-Daten dekodiert
- diese Daten werden in Qt3D als nativer Vorschaupfad gerendert
- mehrere native Geometrien können gleichzeitig angezeigt werden
- mehrere native Geometrien werden farblich pro Part, Modell und Group-Range unterschieden
- der Kamera-Fit nutzt native Bounds statt pauschalem Primitive-Fallback
- erste Preview-Bedienelemente sind umgesetzt:
  - `Reset Camera`
  - `Bounding Box`
  - `Wireframe`
  - `Part Names`
- erste native Material- und Texturreferenzen werden aus CMP und 3DB extrahiert und im Preview-Panel angezeigt
- erste Texturreferenzen werden auf reale Dateien aufgelöst und bei Verfügbarkeit im Vorschaupfad verwendet
- modell-, level- und group-bezogene Material-Bindings werden heuristisch aufgebaut
- zusätzliche Referenz-Checks zeigen jetzt pro nativer Geometrie kompakte Vergleichswerte für Mittelpunkt, Radius, Texturstatus und Translation-Hinweise

Noch offen:

- **Orientierung der dargestellten Geometrie korrigieren** – Geometrie ist erkennbar, aber „unten ist nicht unten"
- vollständige Part- und Model-Transforms über den aktuellen Translation- und Rotationsbasis-Stand hinaus anwenden
- Submesh- und Materialgruppen über den aktuellen heuristischen Stand hinaus robust machen
- Material- und Texturpfad zu echter Mehrfachtextur-Anwendung und höherer Materialtreue ausbauen
- für weitere Referenzdateien aus `DATA\\SOLAR\\DOCKABLE` echte Geometrie statt spezieller Fallback-Primitive liefern

Abnahmekriterien:

- `jump_gatel.cmp` zeigt im Preview mindestens fuer einen echten LOD-Fall sichtbare native Geometrie
- der Preview-Pfad benoetigt fuer `jump_gatel.cmp` keinen Spezial-Fallback mehr
- ausgewähltes Objekt im Editor zeigt in der 3D-Vorschau sein echtes Modell
- bekannte Referenzmodelle wirken in Position, Orientierung und Größe plausibel korrekt
- Ladefehler und unvollständige Materialzuordnung bleiben diagnostizierbar

## Phase 4: Integration in die System-3D-Ansicht

Ziel:

- nicht nur das Preview-Fenster, sondern auch die Haupt-3D-Ansicht soll echte Objekte verwenden.

Status:

- funktional vorhanden, **Orientierung noch nicht korrekt**

Teilweise vorbereitet:

- `MainWindow` löst native Szenedaten für das selektierte Objekt jetzt bereits mit kleinem Modellpfad-Cache auf
- `System3DView` besitzt jetzt einen dedizierten Zustand für selektionsbezogene native Szenedaten
- eine erste native Detail-Entity wird für das selektierte Objekt bereits aufgebaut und ersetzt dort den Marker
- der Qt3D-Unterbau für native Geometrie und Materialien ist zwischen Preview und Systemansicht vereinheitlicht
- `center_on_item` nutzt bei nativen Detailmodellen jetzt Bounds-basierte Fokussierung
- wiederholte Auswahl desselben nativen Detailmodells kann jetzt die bereits aufgebaute Detail-Entity wiederverwenden
- pro-Geometrie-Texturauflösung wird jetzt bereits in den gemeinsamen Szenedaten vorbereitet und in Preview/Systemansicht genutzt
- Selektion/Deselektion, Objektbewegung, Rotation und `clear_scene()` sind jetzt für den selektionsbezogenen Native-Detailpfad bereits per Widget-Smoketests abgesichert
- der `MainWindow`-Syncpfad verwirft jetzt stale Native-Syncs bei zwischenzeitlich geänderter Auswahl

Strategie:

- zunächst nur das selektierte Objekt als echtes CMP laden
- alle anderen Objekte bleiben performant als vereinfachte Marker
- später optional LOD-System oder mehrere echte Modelle

Warum so:

- volle CMP-Darstellung für hunderte Objekte in einem System wäre zu teuer
- ein selektionsbasierter Ansatz bringt sofort Nutzwert ohne Performance-Kollaps

Arbeitspakete:

- `view_3d.py` um eine `selected object detailed mesh`-Entity erweitern
- Objektwechsel triggert Modell-Reload oder Cache-Hit
- Position, Rotation und Skalierung des echten Modells an Objekt-Daten koppeln
- nativen Preview-Pfad in wiederverwendbare Bausteine zerlegen, statt Logik zu duplizieren

Abnahmekriterien:

- selektiertes Objekt erscheint in der 3D-Systemansicht als echtes Modell
- Objektwechsel ersetzt die Detail-Entity stabil ohne Leaks oder alte Rest-Entities
- Position und Orientierung sind für bekannte Referenzobjekte sichtbar korrekt
- Fallback bleibt erhalten, wenn ein Modell nicht nativ geladen werden kann

Restarbeiten bis "Phase 4 nutzbar":

- Referenzliste für echte Ingame-Objekte definieren:
  - Station
  - Planet
  - Gate/Jumphole
  - Battleship/Transport
  - kleiner Solar/Fighter-naher Archetype
- pro Referenz prüfen:
  - sitzt das Modell auf dem Objektzentrum plausibel
  - zeigt die Längsachse plausibel in die erwartete Richtung
  - wird Bounds-basierter Fokus reproduzierbar korrekt gesetzt
- Fehlerbilder explizit unterscheiden:
  - falsche Rotation
  - falsche Translation
  - lokale Geometrie korrekt, aber globale Part-Kombination falsch
  - Material korrekt/inkorrekt bei ansonsten richtiger Geometrie
- selektionsbezogenen Native-Detailpfad noch explizit gegen echte System-Reload-/Dokumentwechselpfade im laufenden Editor validieren

## Phase 5: Performance und Caching

Ziel:

- echtes Modellrendering alltagstauglich machen.

Status:

- begonnen

Benötigt:

- Modellcache nach Pfad
- Render-Mesh-Cache nach Archetype oder Modellpfad
- optional vereinfachte Proxy-Meshes
- robusteres asynchrones Laden, damit UI auch bei größeren Modellen nicht einfriert

Sinnvolle Optimierungen:

- lazy loading
- shared geometry für gleiche Archetypen
- nur sichtbare oder selektierte Detailmodelle laden
- Hintergrundladen mit Ergebnis-Übernahme auf dem UI-Thread ist für selektierte Native-Details jetzt im Minimalpfad vorhanden
- Hintergrundladen verwirft jetzt veraltete, noch nicht gestartete Selektions-Requests zugunsten des aktuell ausgewählten Modells
- native Szenedaten werden jetzt in einem begrenzten Cache gehalten (MRU-Touch + Prune), damit alte Modelle aus langen Selektionen kontrolliert auslaufen
- die Archetype-zu-Modell-Auflösung wird jetzt ebenfalls gecacht, damit häufige Auswahlwechsel weniger Auflösungskosten verursachen
- offene Pending-Loads werden jetzt bei `keine Auswahl` und `3D deaktiviert` aktiv verworfen
- Runtime-Diagnostik liefert jetzt bereits Debug-Metriken und Event-Spuren für Queue, Cache, Sync und verworfene Pending-Loads

Messbare Zielwerte:

- Auswahlwechsel in typischen Systemen bleibt subjektiv flüssig
- wiederholte Anzeige desselben Modells nutzt Cache statt Neudekodierung
- das Öffnen oder Wechseln der Selektion blockiert die UI nicht spürbar

Abnahmekriterien:

- Editor bleibt bei typischen Systemen responsiv
- wiederholte Selektionen desselben Archetyps führen zu Cache-Hits

Restarbeiten bis "Phase 5 belastbar":

- Cache-Größe gegen reale große Systeme kalibrieren
- die vorhandenen Metriken für Cache-Hit/Miss, Queue, Sync und Pending-Discard im echten Editorfluss auswertbar machen
- prüfen, ob lange Detail-Loads die Selektion noch sichtbar "nachziehen" und ggf. härter preempten
- prüfen, ob Entity-Reuse auch bei schnellem Wechsel zwischen verschiedenen Archetypen sauber bleibt

## Phase 6: Materialien, Texturen und visuelle Qualität

Ziel:

- nach Geometrie auch die visuelle Glaubwürdigkeit verbessern.

Status:

- begonnen, aber klar nachrangig gegenüber Transform-Korrektheit und Systemintegration

Bereits vorbereitet:

- erste Material- und Texturreferenzen werden aus nativen Freelancer-Modellen extrahiert
- erste Texturdateien werden aufgelöst und im Vorschaupfad verwendet
- erste Materialgruppen und Kandidatenlisten sind sichtbar

Noch offen:

- Material- und Texturpfade aus nativen Freelancer-Modellen robuster auflösen
- visuelle Qualität über reine Positions- und Index-Geometrie hinaus anheben
- einfache Materialkonvertierung in Qt3D-Materialien stabilisieren
- Beleuchtung an den Freelancer-Look annähern
- Emissive- und Glow-Pfade später optional ergänzen

Wichtig:

- Materialtreue ist ein Ausbauziel, nicht Voraussetzung für die erste nutzbare Version

Abnahmekriterien:

- wichtige Modelle sind nicht nur als graue Geometrie, sondern visuell besser unterscheidbar

Restarbeiten bis "Phase 6 sinnvoll nutzbar":

- Materialkandidaten nicht nur heuristisch matchen, sondern für häufige Referenzfälle reproduzierbar priorisieren
- fehlende Texturen und nicht auflösbare Materialgruppen im UI klar markieren
- testen, ob einfache Qt3D-Materialien für Freelancer-Assets ausreichend sind oder ein eigener Materialpfad nötig wird

## Priorisierte Nutzerfeatures

### Muss zuerst kommen

- echte CMP-Geometrie in der Einzelvorschau
- verlässliche Archetype-zu-Modell-Auflösung
- belastbare Transform-Anwendung für bekannte Referenzmodelle
- selektiertes Objekt im 3D-Editor als echtes Modell
- Debug-Information bei Ladefehlern

### Danach

- Modellcache
- Bounding Box, Drahtgitter und Part-Overlay im wiederverwendbaren nativen Pfad
- Unterstützung weiterer Freelancer-Modelldateien
- asynchrones Laden

### Später

- Materialien und Texturen mit höherer Treue
- mehrere echte Modelle gleichzeitig im System
- LOD-Strategien
- Asset-Inspektor für Parts und Hardpoints

## Konkrete nächste technische Schritte

## Naechste zwei technischen Lieferungen

### Lieferung 1

`jump_gatel.cmp` `Level4` muss von "decode-ready" auf "sichtbar" gebracht werden.

Konkrete Prueffragen:

- welcher Buffer-Slice wird fuer `Level4` tatsaechlich verwendet
- wo liegen Positionsdaten im betreffenden Record
- ist das Indexformat bereits korrekt oder noch falsch interpretiert
- welche minimale Geometrie entsteht daraus im Preview wirklich

Abnahme:

- sichtbare Geometrie im Preview
- kein `cube`-, `sphere`- oder `jumpgate`-Spezial-Fallback fuer diesen Fall

Aktueller Stand:

- Decode-Ebene erreicht ✅
- sichtbare Render-Summary im Preview vorhanden ✅
- Geometrie ist visuell als Jumpgate erkennbar ✅
- **Orientierung noch falsch** – das Modell ist geometrisch korrekt, aber nicht richtig ausgerichtet

### Lieferung 2

`jump_gatel.cmp` `Level3` muss als echter Header-/Stream-Fall dekodieren.

Konkrete Prueffragen:

- wie mappt der strukturierte Header auf den `112`-Stream
- welche Headerfelder bestimmen Vertex-/Index- und Group-Ranges konkret
- ob `Freelancer Mod Studio`-Semantik und unsere Records voll deckungsgleich sind

Abnahme:

- sichtbare Geometrie fuer `Level3`
- Family-Decoder ersetzt `header-stream-capacity-mismatch` als Endzustand

Aktueller Stand:

- Decode-Ebene erreicht ✅
- sichtbare Render-Summary im Preview vorhanden ✅
- Geometrie wird dargestellt ✅
- **Orientierung noch falsch** – gleiches Problem wie bei Level4

### Schritt 1

Transform-Pfad stabilisieren:

- lokale Rotationsbasis aus `Cmpnd/Cons/Fix` ist für vollständige und partielle Basen robuster gemacht
- als Nächstes Referenz-CMPs aus `DATA\\SOLAR\\DOCKABLE` auswählen, an denen Position und Orientierung gegen bekannte Spielobjekte verifiziert werden
- die Referenz-Ansicht liefert dafür jetzt bereits kompakte Match/Mismatch-Kennzahlen und max.-Delta zwischen Bounds-Zentrum und Translation-Hint
- pro Referenzzeile sind Delta und Match-Status jetzt direkt sichtbar; große Abweichungen stehen im Dialog zuerst
- pro Referenzzeile werden jetzt auch lokales Zentrum (`lc`) und Anzeigezentrum (`c`) getrennt ausgewiesen
- pro Referenzzeile wird jetzt zusätzlich eine Rotationsqualitätsdiagnostik (`det`, `ortho`, `rot`) aus vorhandenen `Fix`-Rotationsbasen angezeigt
- kombinierte Parent-Child-Hinweise werden jetzt im nativen Geometrie- und Referenzpfad bevorzugt verwendet; die Referenz-Summary zeigt dafür `t/r-combined` gegen `t/r-local`
- als Nächstes Referenz-CMP-Abdeckung mit `jump_gatel.cmp`, `docking_ringx2_lod.cmp`, `space_police01.cmp` und `space_freeport01.cmp` verbreitern und auffällige `local`-Fallbacks/hohe Deltas gezielt nacharbeiten
- klare Diagnosepfade für unvollständige oder widersprüchliche Transform-Daten behalten

Konkrete Deliverables:

- kleine feste Referenzliste aus `DATA\\SOLAR\\DOCKABLE` in Dokumentation/Testdaten festhalten
- für jede Referenz einen erwarteten Plausibilitätsstatus erfassen:
  - ok
  - warn
  - high
- bestehende Referenzausgabe so nutzen, dass auffällige Modelle gezielt nach Loader- oder Render-Ursache getrennt werden können

### Schritt 2

Wiederverwendbaren nativen Renderpfad extrahieren:

- gemeinsamer Szenedaten-Helfer für native Geometrie, Bounds, Part-Namen und globale Texturauflösung ist aus `MeshPreviewDialog` herausgelöst
- als Nächstes denselben Datenpfad in `view_3d.py` für das selektierte Objekt verwenden
- danach Material-Bindings und Debug-Daten weiter in wiederverwendbare Bausteine ziehen
- der `MainWindow`-seitige Native-Scene-Block ist jetzt bereits in ein eigenes Runtime-Modul ausgelagert; als Nächstes können weitere 3D-bezogene `main_window.py`-Blöcke entlang desselben Musters folgen

### Schritt 3

`view_3d.py` um Detailmodell-Entity ergänzen:

- Daten-Brücke von `MainWindow` nach `view_3d.py` für selektionsbezogene native Szenedaten ist vorhanden
- selektiertes Objekt wird jetzt bereits als native Detail-Entity aufgebaut
- Marker wird bei Selektion ersetzt und bei Deselektion wiederhergestellt
- Bounds-basierte Fokussierung für native Detailmodelle ist jetzt vorhanden
- ein erster Render-Cache für wiederholte Selektion desselben Modells ist jetzt vorhanden
- pro-Geometrie-Texturpfade werden jetzt bereits sowohl im Preview als auch in `view_3d.py` genutzt
- als Nächstes diesen Detailpfad gegen echte Referenz-CMPs aus `DATA\\SOLAR\\DOCKABLE` prüfen und Materialtreue weiter schärfen
- Fallback bei Ladefehlern oder unvollständigen Daten bleibt aktiv

Konkrete Deliverables:

- prüfen, ob der Markerersatz bei Selektion/Deselektion in allen Pfaden stabil ist:
  - normale Selektion
  - schneller Objektwechsel
  - Tabwechsel
  - Reload des Systems
- prüfen, ob selektionsbezogene Native-Details bei Undo/Redo oder Objektbewegung korrekt nachgeführt werden
- aktuelle Lage:
  - Selektion/Deselektion ist per Test abgesichert
  - Objektbewegung ist per Test abgesichert
  - Rotationsänderung ist per Test abgesichert
  - `clear_scene()` / Reload-Grundpfad ist per Test abgesichert
  - offen bleiben echte Dokumentwechsel-/Undo-Redo-Pfade über `MainWindow`

### Schritt 4

Minimalen Cache ergänzen:

- geladene native Modelldaten werden jetzt nach Pfad gecacht
- wiederholte Dekodierung desselben Modells wird bei Cache-Hit vermieden
- der Cache ist jetzt mit Max-Größe und MRU-Prune abgesichert; als Nächstes Größe gegen größere Referenzsysteme kalibrieren

### Schritt 5

Asynchrones Laden und Materialpfad ausbauen:

- selektionsbezogene Native-Szenedaten werden jetzt bereits im Hintergrund geladen und nach Abschluss in die 3D-Ansicht übernommen
- Debouncing/Priorisierung für selektionsbezogene Requests ist jetzt im Pending-Load-Pfad ergänzt (veraltete, cancelbare Requests werden verworfen)
- selektionsbezogene 3D-Synchronisierung wird jetzt nur ausgelöst, wenn abgeschlossene Background-Loads den aktuell selektierten Modellpfad betreffen
- fehlgeschlagene Background-Loads werden jetzt zeitgesteuert wiederholt statt als permanenter `None`-Cache behandelt
- als Nächstes den Hintergrundpfad gegen größere Referenzmodelle prüfen und bei Bedarf weitere Priorisierung (z. B. harte Preemption bei langen Loads) ergänzen
- Material- und Texturpfad schrittweise verbessern

Konkrete Deliverables:

- sichtbare Debug-Ausgabe für:
  - Cache-Hit
  - Cache-Miss
  - Background-Load-Start
  - Background-Load-Abbruch/verworfen
  - Retry nach Fehler
- prüfen, ob die aktuelle Selektion nach Abschluss eines alten Loads garantiert nicht überschrieben wird
- aktuelle Lage:
  - Runtime sammelt diese Ereignisse jetzt bereits intern als Diagnose-Events
  - `MainWindow` besitzt dafür jetzt einen Snapshot über Runtime- und Sync-Zustand
  - stale Syncs bei Auswahlwechsel werden jetzt verworfen
  - Pending-Loads werden jetzt bei `keine Auswahl` und `3D aus` aktiv abgeräumt

### Schritt 6

Debug- und Diagnoseoberfläche für Modellprobleme ergänzen:

- klare Hinweise bei Transform-Problemen
- klare Hinweise bei Material- oder Textur-Lücken
- technische Details nur dann zeigen, wenn sie bei der Fehlersuche helfen

## Benötigte Tests

Automatisierte Tests sollten mindestens abdecken:

- Archetype-Auflösung zu `da_archetype`
- CMP-Lader mit Minimal- und Fehlerfällen
- Mesh-Daten-Erzeugung aus geladenem Modell
- Transform-Ableitung für bekannte Referenzdaten
- Fallback, wenn CMP unlesbar ist
- Cache-Hits bei wiederholter Modellnutzung
- UI-Logik für Preview- und Systempfadentscheidung

Zusätzlich sinnvoll:

- kleine Fixtures mit bekannten CMP-Testdateien
- Golden-Tests für Bounds, Part-Anzahl und Transform-Ergebnisse

Nächste Testpriorität:

- Tests und Dokumentation für reale Referenzdateien aus `DATA\\SOLAR\\DOCKABLE`, beginnend mit `jump_gatel.cmp`
- Tests für Decoder-/Layout-Status pro Referenzdatei:
  - `resolved`
  - `no-fit`
  - `unresolved`
- Tests für belastbare `scene_geometries` bei mindestens einer echten Dockable-Referenz
- Tests für selektionsbezogenen Native-Detail-Cache
- Tests für Verwerfen veralteter Background-Loads
- Tests für Cooldown-/Retry-Verhalten bei fehlgeschlagenen Native-Loads
- Tests für Bounds-basiertes Fokussieren des selektierten nativen Detailmodells
- Tests für Fallback-Rückkehr auf Marker, wenn native Detaildaten fehlen
- Tests für `clear_scene()` / Reload-Rücksetzung des Native-Detail-Zustands
- Tests für `MainWindow`-seitige stale Sync-Abbrüche und Pending-Discard bei `keine Auswahl` / `3D aus`

## Risiken

- CMP-Parsing und Transform-Dekodierung sind der technisch schwierigste Teil
- reale Freelancer-CMPs können von synthetischen Testfällen deutlich abweichende `VMeshRef`-/`VMeshData`-Strukturen besitzen
- Qt3D akzeptiert Freelancer-Dateien nicht direkt
- vollständige Material- und Texturunterstützung kann deutlich aufwendiger werden
- ungecachtes Laden kann die Systemansicht stark verlangsamen
- doppelte Logik in Preview und Systemansicht würde Wartung und Fehlersuche unnötig erschweren

## Erfolgskriterien

Das Vorhaben ist erfolgreich, wenn:

- ein selektiertes Freelancer-Objekt im Editor als echtes CMP-Modell angezeigt wird
- die Einzelvorschau für normale Freelancer-CMP-Archetypen in der Regel keine Primitive mehr braucht
- Position, Rotation und grobe Größe für bekannte Referenzmodelle sichtbar korrekt wirken
- Ladefehler klar diagnostiziert werden
- die 3D-Ansicht trotz echter Modelle flüssig bleibt

## Aktueller UI-Stand

- der `MeshPreviewDialog` zeigt standardmäßig zuerst nur die 3D-Vorschau
- textlastige Modell- und Diagnoseinformationen sind in einen zweiten Tab `Details` verschoben
- damit ist die erste sichtbare Freelancer-Vorschau nicht mehr durch Debug-Text überlagert
- der `Details`-Tab ist scrollbar, damit sein Inhalt die Fenstergroesse nicht mehr unnoetig auf Bildschirmhoehe aufblaeht
- die Dialoghoehe wird jetzt an die verfuegbare Bildschirmhoehe geklemmt; die 3D-Vorschau skaliert mit dem Fenster

## Empfohlener nächster Schritt

Der nächste konkrete Umsetzungsschritt ist die **Korrektur der Modell-Orientierung**:

1. `suggested_up_correction_euler_deg` aus `cmp_orientation_debug.py` in den Renderpfad integrieren
2. `native_detail_transform_state()` in `view_3d_native_detail_state.py` muss die CMP-Orientierungskorrektur auf das Rotate anwenden
3. Die Korrektur muss aus dem CMP-Achsen-Mapping kommen (kein generelles Hardcoded-Offset)
4. Validierung gegen Referenzobjekte: Li01_08 (`rotate = 0, 40, 0` → soll mit CMP-Korrektur korrekt aussehen)

Danach:
- Material-/Texturpfad weiter von heuristisch auf robustere Zuordnung ausbauen
- breitere Modellabdeckung (weitere Dockables, Schiffe, Stationen)

## Empfohlene nächste Lieferung

Die nächste in sich sinnvolle Lieferung für den 3D-Editor ist ein **Orientierungs-Korrekturpaket**:

- CMP-Orientierungskorrektur (`suggested_up_correction_euler_deg`) aus `cmp_orientation_debug.py` in `native_detail_transform_state()` integrieren
- Transform-Kette im Renderpfad: CMP-Up-Correction × INI-Rotate × Position
- Validierung gegen Li01_08 und weitere Referenzobjekte
- die Korrektur darf kein generelles Hardcoded-Offset sein – sie muss aus dem CMP-`Fix`-Achsen-Mapping kommen
- Tests für korrekte Orientierung gegen bekannte Referenz-Rotationen ergänzen

Erst wenn diese Lieferung stabil ist, sollte die nächste Ausbaustufe folgen:

- Material-/Texturtreue sichtbar verbessern
- mehr als nur das selektierte Objekt nativ darstellen
- optional Asset-Inspektor / Hardpoint-/Part-Inspektion ausbauen
