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

## Aktueller Umsetzungsstand

Stand nach den letzten CMP-/Preview-Arbeitsschritten:

- Phase 1 ist praktisch umgesetzt:
  - Modellauflösung ist in `freelancer_model_resolver.py` gekapselt
  - renderbare Standardformate, Freelancer-native Formate und Fallbacks sind getrennt
- Phase 2 ist weit fortgeschritten:
  - `cmp_loader.py` liest UTF-Struktur, Knotenpfade, Parts, `VMeshRef`, `VMeshData`, Modellknoten und erste Preview-Metadaten
  - `freelancer_mesh_data.py` enthält dafür ein eigenes internes Datenmodell
  - Bounds, Hierarchie, Part-Metadaten, Geometriequellen, Layout-Heuristiken und Buffer-Slices werden bereits erzeugt
  - `Cmpnd/Cons/Fix` wird bereits als partbezogene Record-Metadaten erfasst und über `Part_*/Index` an Parts gekoppelt
  - `Cmpnd/Cons/Fix` wird zusätzlich schon in stabile Zeilen-/Blockstruktur zerlegt
  - aus `Cmpnd/Cons/Fix` werden bereits erste Transform-Hinweise wie Translation und Leitvektor abgeleitet
- Phase 3 ist als erster nativer Prototyp erreicht:
  - `MeshPreviewDialog` zeigt native Freelancer-Modelle nicht mehr nur als Primitive-/Text-Fallback
  - für `exact`/`tight`-Fälle werden bereits echte Vertex-/Index-Daten dekodiert und in Qt3D gerendert
- mehrere native Geometrien pro Modell werden bereits gemeinsam in der Vorschau dargestellt
- erste `CMP Transform Hints` fließen bereits als Translation und grobe Leitvektor-Rotation in den nativen Preview-Pfad ein
- native Mehrfachgeometrien werden im Preview bereits pro Part/Modell farblich differenziert dargestellt
- Phase 4 bis 6 sind noch offen:
  - Part-/Model-Transforms sind noch nicht sauber in den nativen Renderpfad integriert
  - Material-/Texturpfad fehlt
  - Integration in die eigentliche `view_3d.py`-Systemansicht steht noch aus

Bereits hinzugekommene Kernmodule:

- `fl_editor/freelancer_model_resolver.py`
- `fl_editor/cmp_loader.py`
- `fl_editor/freelancer_mesh_data.py`
- `fl_editor/native_preview_geometry.py`

Bereits ergänzte Testbasis:

- `tests/test_cmp_loader.py`
- `tests/test_mesh_preview_dialog.py`
- `tests/test_native_preview_geometry.py`

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

Bereits erledigt:

- Archetype- und Preview-Modellauflösung ist aus `main_window.py` in `freelancer_model_resolver.py` gezogen
- direkte UI-Fallback-Entscheidungen sind von der Auflösung getrennt
- der Pfad unterscheidet jetzt sauber zwischen:
  - direkt renderbaren Formaten
  - Freelancer-nativen Formaten (`cmp`, `3db`)
  - Fallback-/Fehlerfällen

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

Bereits erledigt:

- UTF-Header und UTF-Knotenstruktur werden gelesen
- Parent-/Path-Hierarchie der Knoten wird rekonstruiert
- Parts inklusive `File name`/`Object name` werden extrahiert
- Part-Indizes aus `Index`-Nodes werden extrahiert
- `VMeshRef` wird inklusive Bounds gelesen
- `VMeshData`-Blöcke werden gelesen und mit Metadaten versehen:
  - `sha1`
  - Header-Hex
  - erste Header-Wörter
- `Cmpnd/Cons/Fix` wird bereits als partbezogene Record-Liste gelesen
- diese Records werden über `Part_*/Index` stabil an Parts gekoppelt
- die Records tragen bereits eine erste strukturierte Row-Darstellung (`row_count`, `row_width`, `rows`)
- aus diesen Rows werden bereits erste Transform-Hinweise (`translation_xyz`, `leading_vector_xyz`) abgeleitet
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

Noch offen in Phase 2:

- belastbare vollständige Dekodierung von Part-/Model-Transforms aus nativen CMP-Daten, z. B. `\/Cmpnd/Cons/Fix`
- stabilere Ableitung echter Geometriestrukturen aus `VMeshData` jenseits des aktuellen Minimal-Decoders

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

Bereits erledigt:

- `MeshPreviewDialog` zeigt native Modellinformationen in einer strukturierten Seitenleiste:
  - UTF Nodes
  - Parts
  - Model Nodes
  - Geometry Candidates
  - Submeshes
  - Geometry Sources
  - Layout Guesses
  - Buffer Slices
  - CMP Fix Records
  - VMesh Data Blocks
- Part-Einträge und Fix-Records zeigen dabei bereits den zugehörigen CMP-Index an
- Fix-Records zeigen außerdem bereits ihre Blockstruktur, z. B. `rows=4x11`
- erste Transform-Hinweise aus `Fix` werden bereits im Preview-Panel sichtbar gemacht
- Translation und grobe Leitvektor-Rotation aus diesen Transform-Hinweisen werden bereits auf native Preview-Geometrien angewendet
- für `exact`/`tight`-Layout-Fälle werden echte Vertex-/Index-Daten dekodiert
- diese Daten werden bereits in Qt3D als nativer Vorschaupfad gerendert
- mehrere native Geometrien können bereits gleichzeitig angezeigt werden
- mehrere native Geometrien werden dabei bereits farblich pro Part/Modell und Group-Range unterschieden
- der Kamera-Fit nutzt native Bounds statt pauschalem Primitive-Fallback
- erste Preview-Bedienelemente sind umgesetzt:
  - `Reset Camera`
  - `Bounding Box` an/aus
- `Part Names` können in der nativen Vorschau jetzt als schaltbare Render-Info eingeblendet werden
- `Wireframe` ist in der nativen Vorschau jetzt als schaltbares Overlay verfügbar
- erste native Material-/Texturreferenzen werden bereits aus CMP/3DB extrahiert und im Preview-Panel angezeigt

Noch offen in Phase 3:

- vollständige Part-/Model-Transforms und belastbare Rotationsdekodierung auf den nativen Preview-Pfad anwenden
- Submesh-/Materialgruppen weiter ausbauen, über die aktuelle Part-/Modell-/Group-Farbkodierung hinaus
- Material-/Texturpfad von bloßer Referenzanzeige zu echter Materialanwendung erweitern

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

Noch offen:

- den nativen Preview-Pfad aus `MeshPreviewDialog` gezielt in `view_3d.py` überführen
- zunächst nur für das selektierte Objekt
- erst nach stabiler Transform-Anwendung und belastbarer Geometriezuordnung

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

Teilweise vorbereitet:

- die nativen Schritte sind bereits in kleine Hilfsmodule getrennt, was spätere Caches erleichtert
- ein echter Modell-/Geometrie-Cache ist aber noch nicht eingebaut

## Phase 6: Materialien, Texturen und visuelle Qualität

Ziel:

- nach Geometrie auch die visuelle Glaubwürdigkeit verbessern.

Mögliche Features:

- diffuse Texturen lesen und anwenden

Noch offen:

- Material- und Texture-Pfade aus nativen Freelancer-Modellen auflösen
- visuelle Qualität über reine Positions-/Index-Geometrie hinaus anheben
- Drahtgitter-/Bounding-Box-/Part-Overlay gezielt für den nativen Pfad ergänzen
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
