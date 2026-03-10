# Projektplan: Ausbau des 3D-Editors mit nativer Anzeige von Freelancer-CMP-Objekten

## Kontext

FLAtlas besitzt bereits eine umfangreiche 3D-Systemansicht auf Basis von Qt3D:

- `fl_editor/view_3d.py`
- `fl_editor/view_3d_*` Hilfsmodule
- Integrationslogik in `fl_editor/main_window.py`
- `MeshPreviewDialog` in `fl_editor/dialogs.py`

Der aktuelle Stand kann:

- Systeme, Zonen und Objekte in 3D visualisieren
- Kamera, Auswahl, Gizmo und Flight-Mode bedienen
- Archetypen auf `da_archetype` auflösen
- externe Mesh-Formate wie `obj`, `stl`, `ply`, `gltf`, `glb`, `dae`, `fbx`, `3ds` anzeigen
- bei nicht renderbaren Freelancer-Dateien auf Primitive-Fallbacks zurückfallen

Die zentrale Lücke ist klar:

- Freelancer-Modelle liegen typischerweise als `*.cmp` vor
- diese werden aktuell nicht nativ gelesen und gerendert
- dadurch sieht der Nutzer im Editor nicht das echte Spielobjekt

## Ziel

Der 3D-Editor soll Freelancer-Objekte so anzeigen, wie sie im Spiel tatsächlich aussehen:

- native Unterstützung für `*.cmp`
- möglichst auch Vorbereitung für `*.3db` und verwandte Freelancer-Modellpfade
- Verwendung der echten Geometrie statt nur Sphären/Würfeln
- Anzeige direkt in der bestehenden 3D-Systemansicht und in der Einzelmodell-Vorschau

## Welche Features Nutzer wirklich brauchen

## 1. Für Mapper und System-Designer

- das echte 3D-Modell an der Objektposition sehen
- Größe, Rotation und Orientierung realistisch prüfen
- bessere Platzierung von Basen, Gates, Jumpholes, Planeten, Stationen und Solars
- visuelle Kollisionen und Überlappungen früher erkennen

## 2. Für Modder

- sicher prüfen, ob ein Archetype auf die richtige CMP-Datei zeigt
- schnell erkennen, wenn ein Modell fehlt oder falsch aufgelöst wird
- neues Asset direkt im Editor testen
- visuell gegen bestehende Spielobjekte vergleichen

## 3. Für allgemeine Editor-Qualität

- weniger Ratespiel bei Archetypen
- weniger Fallback-Primitive
- höherer Nutzen des 3D-Modus
- bessere Glaubwürdigkeit des Editors als Modding-Werkzeug

## Ist-Zustand

Technisch relevante Stellen im aktuellen Code:

- `main_window.py`
  - `_build_archetype_model_index()`
  - `_resolve_model_for_archetype()`
  - `_find_preview_mesh_candidate()`
  - `_show_selected_3d_preview()`
- `dialogs.py`
  - `MeshPreviewDialog`
- `view_3d.py`
  - Qt3D-gestützte Systemdarstellung

Aktuelle Einschränkung:

- `_find_preview_mesh_candidate()` sucht nur nach Standard-Meshformaten
- `*.cmp` wird zwar als Dateityp akzeptiert, aber nicht gerendert
- bei fehlendem konvertierbaren Mesh wird nur ein Primitive gezeigt

## Zielbild

Der 3D-Editor soll aus drei Schichten bestehen:

## 1. Modellauflösung

- Archetype -> `da_archetype` -> tatsächliche Modelldatei
- Unterstützung für Freelancer-Dateitypen

## 2. Freelancer-Modellimport

- Loader für `CMP`-Inhalte
- Extraktion von Geometrie, Knoten/Parts, Transform und optional Material-Infos
- Umwandlung in Qt3D-kompatible Mesh-Daten

## 3. Darstellung im Editor

- echtes Modell in der Einzelvorschau
- echtes Modell optional in der System-3D-Ansicht
- Fallback nur noch bei echten Fehlerfällen

## Technische Leitidee

Der wichtigste Unterschied zu gewöhnlichen 3D-Dateien:

- Freelancer-`CMP` ist kein direkt von Qt3D lesbares Standard-Meshformat
- deshalb braucht FLAtlas einen eigenen Importpfad

Pragmatischer Ansatz:

1. zuerst ein Loader/Decoder für Freelancer-CMP bauen
2. daraus interne Mesh-Daten erzeugen
3. diese Daten in Qt3D renderbar machen
4. erst danach tief in die Systemansicht integrieren

## Ausbauplan

## Phase 1: Analyse und Datenpfad sauber definieren

Ziel:

- Die bestehende Modellauflösung von der eigentlichen Darstellung trennen.

Arbeitspakete:

- neues Modul für Freelancer-Modellauflösung, z. B.:
  - `freelancer_model_resolver.py`
- neues Modul für CMP-Laden, z. B.:
  - `cmp_loader.py`
- neues Modul für Renderdaten, z. B.:
  - `freelancer_mesh_data.py`

Aufgaben:

- aktuelle Archetype-Auflösung aus `main_window.py` sauber kapseln
- unterscheiden zwischen:
  - Modell gefunden
  - Modellformat direkt renderbar
  - Modellformat Freelancer-spezifisch
  - Modell unlesbar

Abnahmekriterien:

- Modellauflösung ist nicht mehr direkt mit UI-Fallbacks vermischt

## Phase 2: CMP-Dateien lesbar machen

Ziel:

- `*.cmp` strukturell einlesen und in ein internes Datenmodell überführen.

Benötigte Fähigkeiten:

- CMP-Datei öffnen
- relevante Knoten/Parts lesen
- Geometriequellen identifizieren
- Transform-Hierarchie auslesen
- Bounding-Box / Bounding-Radius bestimmen

Wichtige Ausgabe eines ersten internen Modells:

- Part-Liste
- Vertex-Daten
- Index-Daten
- Part-Transforms
- optional Material-/Texturpfade

Wichtig für den Scope:

- zuerst Geometrie und Transform priorisieren
- Materialtreue ist erst zweitrangig

Abnahmekriterien:

- mindestens ein einfacher Freelancer-CMP-Archetype kann intern als Mesh-Struktur geladen werden

## Phase 3: Einzelmodell-Vorschau mit echten CMPs

Ziel:

- `MeshPreviewDialog` zeigt echte CMP-Geometrie statt Primitive-Fallback.

Arbeitspakete:

- `MeshPreviewDialog` erweitern oder neuen Dialog ergänzen
- Qt3D-Entity-Aufbau aus internem Mesh-Modell
- Kamera auf Bounding-Box/Bouding-Radius automatisch fitten
- Debug-Overlay mit:
  - Datei
  - Archetype
  - Parts
  - Vertex-/Triangle-Anzahl

UI-Features:

- Drahtgitter an/aus
- Bounding Box an/aus
- Part-Namen anzeigen
- Reset Camera

Abnahmekriterien:

- ausgewähltes Objekt im Editor zeigt in der 3D-Vorschau sein echtes Modell

## Phase 4: Integration in die System-3D-Ansicht

Ziel:

- nicht nur Preview-Fenster, sondern auch die Haupt-3D-Ansicht soll echte Objekte verwenden.

Strategie:

- zunächst nur ausgewähltes Objekt als echtes CMP laden
- alle anderen Objekte bleiben performant als vereinfachte Marker
- später optional LOD-System für mehrere echte Modelle

Warum so:

- volle CMP-Darstellung für hunderte Objekte in einem System wäre zu teuer
- ein selektionsbasierter Ansatz bringt sofort Nutzwert ohne Performance-Kollaps

Arbeitspakete:

- `view_3d.py` um "selected object detailed mesh" erweitern
- Objektwechsel triggert Modell-Reload
- Rotation/Position des echten Modells an Objekt-Daten koppeln

Abnahmekriterien:

- selektiertes Objekt erscheint in der 3D-Systemansicht als echtes Modell

## Phase 5: Performance und Caching

Ziel:

- echtes Modellrendering alltagstauglich machen.

Benötigt:

- Modellcache nach Pfad
- Render-Mesh-Cache nach Archetype
- optional vereinfachte Proxy-Meshes
- asynchrones Laden, damit UI nicht einfriert

Sinnvolle Optimierungen:

- lazy loading
- shared geometry für gleiche Archetypen
- nur sichtbare oder selektierte Detailmodelle laden

Abnahmekriterien:

- Editor bleibt bei typischen Systemen responsiv

## Phase 6: Materialien, Texturen und visuelle Qualität

Ziel:

- nach Geometrie auch die visuelle Glaubwürdigkeit verbessern.

Mögliche Features:

- diffuse Texturen lesen und anwenden
- einfache Materialkonvertierung in Qt3D-Materialien
- Beleuchtung an Freelancer-Look annähern
- Emissive/Glow später optional

Wichtig:

- Materialtreue ist ein Ausbauziel, nicht Voraussetzung für die erste nutzbare Version

Abnahmekriterien:

- wichtige Modelle sind nicht nur als graue Geometrie, sondern visuell besser unterscheidbar

## Priorisierte Nutzerfeatures

## Muss zuerst kommen

- echte CMP-Geometrie in der Einzelvorschau
- verlässliche Archetype-zu-Modell-Auflösung
- Debug-Information bei Ladefehlern
- selektiertes Objekt im 3D-Editor als echtes Modell

## Danach

- Modellcache
- Bounding Box / Drahtgitter / Part-Overlay
- Unterstützung weiterer Freelancer-Modelldateien
- asynchrones Laden

## Später

- Materialien und Texturen
- mehrere echte Modelle gleichzeitig im System
- LOD-Strategien
- Asset-Inspektor für Parts/Hardpoints

## Konkrete technische Schritte im Code

## Schritt 1

Neue Resolver-/Loader-Module anlegen:

- `freelancer_model_resolver.py`
- `cmp_loader.py`
- optional `freelancer_mesh_qt3d.py`

## Schritt 2

`main_window.py` entkoppeln:

- `_resolve_model_for_archetype()` beibehalten oder delegieren
- `_find_preview_mesh_candidate()` erweitern um:
  - Standard-Mesh
  - Freelancer-CMP-Pfad
  - Renderstrategie

## Schritt 3

`MeshPreviewDialog` erweitern:

- Standard-Mesh-Pfad weiter unterstützen
- zusätzlich internen CMP-Renderpfad einbauen

## Schritt 4

`view_3d.py` um Detailmodell-Entity ergänzen:

- selektiertes Objekt bekommt echtes Modell
- Entity wird bei Selektion ersetzt

## Schritt 5

Caches und Async-Lader ergänzen.

## Schritt 6

Debug- und Diagnoseoberfläche für Modellprobleme ergänzen.

## Benötigte Tests

Automatisierte Tests sollten mindestens abdecken:

- Archetype-Auflösung zu `da_archetype`
- CMP-Lader mit Minimal- und Fehlerfällen
- Mesh-Daten-Erzeugung aus geladenem Modell
- Fallback, wenn CMP unlesbar ist
- Cache-Hits bei wiederholter Modellnutzung
- UI-Logik für Preview-Pfadentscheidung

Zusätzlich sinnvoll:

- kleine Fixtures mit bekannten CMP-Testdateien
- Golden-Tests für Bounding-Daten und Part-Anzahl

## Risiken

- CMP-Parsing ist der technisch schwierigste Teil
- Qt3D akzeptiert Freelancer-Dateien nicht direkt
- vollständige Material-/Texturunterstützung kann deutlich aufwendiger werden
- ungecachtes Laden kann die Systemansicht stark verlangsamen

## Erfolgskriterien

Das Vorhaben ist erfolgreich, wenn:

- ein selektiertes Freelancer-Objekt im Editor als echtes CMP-Modell angezeigt wird
- die Einzelvorschau kein Primitive mehr für normale CMP-Archetypen braucht
- Position, Rotation und grobe Größe sichtbar korrekt wirken
- Ladefehler klar diagnostiziert werden
- die 3D-Ansicht trotz echter Modelle flüssig bleibt

## Empfohlener nächster Schritt

Der erste konkrete Umsetzungsschritt sollte ein isolierter CMP-Loader-Prototyp sein, der für ein einzelnes Archetype-Modell Geometrie und Bounds extrahiert und in der `MeshPreviewDialog`-Vorschau rendert. Erst wenn dieser Pfad stabil ist, sollte die tiefe Integration in `view_3d.py` folgen.
