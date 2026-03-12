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
- native Vorschaupfade für CMP sind bereits vorhanden
- die Haupt-3D-Ansicht nutzt diese nativen Daten bisher nur teilweise für das selektierte Objekt
- reale Freelancer-Dateien zeigen, dass die aktuelle Parser- und Layout-Heuristik für echte Spielassets noch nicht belastbar genug ist
- die Transform-Anwendung ist noch nicht robust genug, um die Darstellung als "spielnah korrekt" zu betrachten

## Ziel

Der 3D-Viewer soll Freelancer-Objekte so anzeigen, wie sie im Spiel tatsächlich aussehen:

- native Unterstützung für `*.cmp`
- native Unterstützung für `*.3db`
- Verwendung der echten Geometrie statt nur Sphären oder Würfeln
- Anzeige direkt in der bestehenden 3D-Systemansicht und in der Einzelmodell-Vorschau
- Fokus explizit auf echte Freelancer-Dateistrukturen statt auf generische Mesh-Fallbacks

## Referenzbasis

Primäre Referenzbasis für Decoder-, Preview- und Viewer-Arbeit:

- Ein Programm, dass bereits diese formate lesen kann: `C:\Program Files\Freelancer Mod Studio`
- Verzeichnis: `C:\Users\STAdmin\FLAtlas\FL-Installationen\_FL Fresh Install-deutsch\DATA\SOLAR\DOCKABLE`
- erste Pflicht-Referenzen:
  - `jump_gatel.cmp`
  - `docking_ringx2_lod.cmp`
  - `space_police01.cmp`
  - `space_freeport01.cmp`

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
- Phase 4 bis 6 sind noch offen:
  - Part- und Model-Transforms sind noch nicht vollständig belastbar im nativen Renderpfad integriert
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

Die Analyse echter Dateien aus `DATA\\SOLAR\\DOCKABLE`, insbesondere `jump_gatel.cmp`, hat den technischen Schwerpunkt verschoben.

Aktueller Befund zu `jump_gatel.cmp`:

- UTF-Knotenstruktur, `parts`, `preview_nodes`, `preview_mesh_bindings` und `VMeshData`-Blöcke werden bereits erkannt
- trotzdem entstehen aktuell noch keine renderbaren `scene_geometries`
- `preview_geometry_sources` existieren, enden aber überwiegend in `unresolved` oder `no-fit`
- reale `VMeshRef`-Einträge dieses Dockable-CMPs passen nicht robust zu den bisherigen Annahmen aus synthetischen Testfällen
- `mesh_data_reference`, `vertex_count` und `index_count` werden für diesen realen Fall noch nicht belastbar genug interpretiert
- die Part-/Modell-Zuordnung war für reale `Cmpnd/Part_*`-Strukturen und verrauschte `*_lod...`-Modellnamen ebenfalls zu schwach
- der Loader meldet für solche Referenzen jetzt explizit Statuswerte wie `Resolved preview sources`, `Preview buffer slices` und `No-fit layouts`, sodass Blocker nicht mehr nur implizit im Fallback verschwinden
- echte Freelancer-UTF-Dateien nutzen bei Data-Nodes offenbar relative Offsets gegen `header.data_offset`; nach Korrektur dieses Punkts steigt `jump_gatel.cmp` bereits sichtbar von sehr wenigen auf mehrere korrekt aufgelöste Preview-Sources und Buffer-Slices
- reale `*.vms`-Dateinamen wie `lod0-112.vms` tragen offenbar verwertbare Layout-Hinweise; der Loader bevorzugt diese Strides jetzt bereits im Preview-Layout-Guess
- echte `VMeshData`-Bloecke in `jump_gatel.cmp` zeigen jetzt sichtbar gemischte Strukturmuster:
  - `lod4-212.vms` und `lod3-212.vms` wirken wie strukturierte Header-Bloecke
  - mehrere `*-112.vms`-Bloecke wirken wie reine Float-/Vertex-Streams
  - mindestens ein weiterer Block bleibt noch `unknown`
- daraus folgt: reale Freelancer-Dekodierung braucht wahrscheinlich kein simples `header + vertex-buffer + index-buffer`, sondern gepaarte Header-/Stream-Behandlung ueber mehrere `VMeshData`-Bloecke hinweg
- `mesh_data_reference` in realen `VMeshRef`-Eintraegen ist jetzt nicht mehr nur Vermutung:
  - ueber die aus `Freelancer Mod Studio` nachvollzogene `FlModelCrc`-Logik matchen diese Werte direkt auf echte `*.vms`-Dateinamen
  - damit lassen sich die realen `jump_gatel.cmp`-Referenzen jetzt deterministisch aufloesen statt nur ueber String-Heuristik
- `VMeshData`-Bloecke werden jetzt zusaetzlich in Familien zusammengefasst:
  - Dateinamen wie `jump_gatel.lod3-212.vms` und `jump_gatel.lod3-112.vms` werden zu einer gemeinsamen Familie `jump_gatel_lod3`
  - dadurch sind reale Multi-Block-Gruppen jetzt explizit im Datenmodell statt nur indirekt ueber Stringmuster sichtbar
- dieser Familienkontext wird jetzt bis in `preview_geometry_sources` und `preview_layout_guesses` durchgereicht
  - damit ist fuer jeden echten `VMeshRef` sichtbar, ob er auf einen Einzelblock oder auf eine Mehrblock-Familie zeigt
  - das ist die direkte Vorstufe fuer einen family-aware Decoder statt eines rein blocklokalen Heuristikpfads
- `preview_layout_guesses` unterscheiden jetzt auch explizit den Family-Layoutmodus:
  - `single-block`
  - `family-split-header-stream`
  - `family-multi-stream`
  - `family-multi-header`

Folgerung:

- die Hauptarbeit liegt jetzt nicht mehr im UI, sondern in einem Freelancer-spezifischen Importpfad für echte CMP-/3DB-Dateien
- synthetische Minimaltests bleiben wichtig, reichen aber nicht mehr als primäre Referenz
- `jump_gatel.cmp` wird zur Pflicht-Referenz für Decoder-, Layout- und Render-Validierung
- der Loader muss echte `Cmpnd`-Partpfade und reale Freelancer-LOD-Namensmuster robuster normalisieren, bevor Geometriezuordnung belastbar werden kann

## Arbeitsstand 2026-03-12

Der 3D-Viewer ist nicht mehr im Stadium "nur Primitive + Wunschliste". Die riskanten Grundlagen sind inzwischen vorhanden:

- nativer CMP-Datenpfad ist vorhanden
- Preview und selektionsbezogene System-3D-Ansicht teilen sich denselben Szenedaten-Unterbau
- selektierte Objekte können bereits als echtes Detailmodell erscheinen
- Background-Load, Cache und Retry-Grundlogik für diesen Detailpfad existieren

Der Engpass hat sich dadurch konkretisiert. Das Hauptproblem ist nicht mehr "ob" nativer 3D-Render möglich ist, sondern:

- wie korrekt Transform, Orientierung und Skalierung für echte Freelancer-Referenzobjekte sind
- wie reale `VMeshRef`-/`VMeshData`-Varianten aus Freelancer-CMPs korrekt interpretiert werden
- wie robust Material-/Texturzuordnung über unterschiedliche CMP-/3DB-Varianten hinweg bleibt
- wie stabil sich der Detailpfad unter echter Editor-Nutzung verhält
- wie gut sich problematische Modelle und Race-Pfade im laufenden Editor diagnostizieren lassen

Damit ist die nächste Iteration klarer als früher:

1. echte Freelancer-Referenzdateien als Primärquelle etablieren
2. `VMeshRef`-/`VMeshData`-Interpretation für reale CMPs stabilisieren
3. Diagnose und Sichtbarkeit für Abweichungen
4. Härtung des Detailpfads im laufenden Editor
5. danach erst breitere visuelle Qualität und Mehrfachmodell-Ausbau

Neuer Teilbefund aus der Referenz `jump_gatel.cmp`:

- `Structured VMeshData blocks = 2/7`
- `Vertex-stream VMeshData blocks = 4/7`
- der Loader kann diese Muster jetzt explizit unterscheiden und meldet gemischte Header-/Stream-Fälle als Warnung
- `Resolved preview sources` steigt mit `FlModelCrc`-Aufloesung jetzt von `5/26` auf `26/26`
- `jump_gate_*` und `door*_lod*`-Referenzen werden jetzt korrekt per `flcrc-source-match` an die passenden `VMeshData`-Bloecke gebunden
- `VMeshData families = 5`
- `Multi-block VMeshData families = 2`
- besonders wichtig:
  - `jump_gatel_lod3` zeigt bereits eine echte Header-/Stream-Paarung (`212` + `112`)
  - `jump_gatel_lod2` zeigt ebenfalls eine echte Multi-Block-Familie, aber aktuell noch ohne saubere Header-Erkennung
- `jump_gate_lod... Level3` zeigt jetzt explizit:
  - `matched_family_key = jump_gatel_lod3`
  - `matched_family_block_indices = (1, 2)`
  - `matched_family_structure_kinds = ('structured-header', 'vertex-stream')`
- zusaetzlich ist fuer die gleiche Referenz jetzt explizit sichtbar:
  - `layout_mode = family-split-header-stream`
  - `header_block_index = 1`
  - `stream_block_index = 2`
- `jump_gate_lod... Level2` wird aktuell als `family-multi-stream` erkannt
- daraus folgt:
  - der naechste Decoder-Schritt muss fuer solche Familien gezielt den Header-Block vom Stream-Block trennen
  - die bisherigen Einzelblock-Layoutwerte fuer `Level3` sind nur noch Uebergangsdiagnostik, nicht mehr das Zielmodell
- das nächste Decoder-Arbeitspaket muss deshalb die Paarung dieser Blocktypen angehen statt nur weitere Buffer-Fit-Heuristiken zu verfeinern

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

Der Datenpfad ist heute funktional in zwei Hälften geteilt:

- Modellauflösung und Formatklassifikation sind bereits aus der UI-Logik herausgelöst
- die Einzelmodell-Vorschau besitzt bereits einen nativen CMP-Renderpfad
- die Haupt-3D-Ansicht arbeitet weiterhin ohne selektionsbezogenen nativen Detailpfad

Die größten aktuellen Einschränkungen sind:

- Transform-Hinweise aus CMP-Daten sind noch nicht als vollständige, belastbare Part- und Model-Transforms umgesetzt
- Material- und Texturzuordnung ist heuristisch, nicht vollständig
- die Systemansicht kann das selektierte Objekt noch nicht als echtes CMP-Modell darstellen
- ohne Cache würde eine direkte Ausweitung auf viele echte Modelle die Performance gefährden
- der gemeinsame Szenedaten-Pfad wird jetzt sowohl von Preview als auch von der selektionsbezogenen Systemansicht genutzt
- `MainWindow` kann native Szenedaten für selektierte Freelancer-Modelle jetzt bereits auflösen und an `view_3d.py` weiterreichen
- der selektionsbezogene Detailpfad ersetzt aktuell den Marker nur für das ausgewählte Objekt und besitzt jetzt einen ersten Entity-Reuse-Cache
- die Kamera kann selektierte native Detailmodelle jetzt über deren Bounds fokussieren statt nur über generische Objektabstände
- Preview und `view_3d.py` nutzen jetzt denselben pro-Geometrie-Texturpfad aus `NativePreviewSceneData`
- `MainWindow` lädt selektionsbezogene native Szenedaten bei Cache-Miss jetzt asynchron im Hintergrund und synchronisiert die 3D-Ansicht nach Abschluss erneut
- `System3DView` besitzt jetzt einen kleinen Debug-Snapshot für den Zustand des selektierten Native-Detailpfads
- `MainWindow` besitzt jetzt einen Diagnose-Snapshot für Native-Scene-Runtime, Pending-Loads, Cache und Sync-Ereignisse
- veraltete Syncs werden jetzt verworfen, wenn sich die Auswahl während des Resolve-/Load-Pfads geändert hat
- `clear_scene()` räumt jetzt auch den kompletten selektionsbezogenen Native-Detail-Zustand mit ab

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

- belastbare vollständige Dekodierung von Part- und Model-Transforms aus nativen CMP-Daten
- stabilere Ableitung echter Geometriestrukturen aus `VMeshData` jenseits des aktuellen Minimal-Decoders
- belastbare Interpretation realer `VMeshRef`-Varianten aus Dockable-CMPs wie `jump_gatel.cmp`
- robuste Auflösung von `mesh_data_reference` gegen reale `VMeshLibrary`-Blöcke statt nur gegen einfache Testfall-Annahmen
- Layout-Guess nicht nur gegen synthetische Exact-Fits, sondern gegen echte `VMeshData`-Blöcke aus der Freelancer-Installation absichern
- die neue Part-/LOD-Normalisierung verbessert zwar das Matching für reale Referenzdateien, löst aber die eigentliche `VMeshRef`-/Geometrie-Dekodierung noch nicht
- die neuen Diagnosezeilen zeigen den Engpass jetzt sichtbar an, beheben ihn aber noch nicht
- trotz korrekterer Offset-Auflösung liefern die aktuell gefundenen `weak`-Layouts fuer `jump_gatel.cmp` noch keine dekodierbare Geometrie; der nächste Engpass liegt jetzt im realen Vertex-/Index-Layout
- für `jump_gatel.cmp` kippen die `rings_lod...`-Layouts inzwischen zwar sinnvoll auf `stride=112`, aber die Indexlage bzw. Positionsoffsets innerhalb des Vertexrecords sind noch nicht korrekt dekodiert
- klare Definition, wann ein Transform-Pfad als korrekt gilt
- Parent-Child-Zusammenhänge und kombinierte Model-Transforms sind im Loader jetzt vorbereitet, aber im Renderpfad noch nicht vollständig durchgängig genutzt
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

- vollständige Part- und Model-Transforms über den aktuellen Translation- und Rotationsbasis-Stand hinaus anwenden
- Submesh- und Materialgruppen über den aktuellen heuristischen Stand hinaus robust machen
- Material- und Texturpfad zu echter Mehrfachtextur-Anwendung und höherer Materialtreue ausbauen
- für Referenzdateien aus `DATA\\SOLAR\\DOCKABLE` echte Geometrie statt spezieller Fallback-Primitive liefern

Abnahmekriterien:

- ausgewähltes Objekt im Editor zeigt in der 3D-Vorschau sein echtes Modell
- bekannte Referenzmodelle wirken in Position, Orientierung und Größe plausibel korrekt
- Ladefehler und unvollständige Materialzuordnung bleiben diagnostizierbar

## Phase 4: Integration in die System-3D-Ansicht

Ziel:

- nicht nur das Preview-Fenster, sondern auch die Haupt-3D-Ansicht soll echte Objekte verwenden.

Status:

- begonnen, aber noch nicht abgenommen

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

## Empfohlener nächster Schritt

Der nächste konkrete Umsetzungsschritt ist jetzt die Stabilisierung des nativen Freelancer-Importpfads gegen echte Referenzdateien aus `DATA\\SOLAR\\DOCKABLE`, beginnend mit `jump_gatel.cmp`. Danach sollte der Material-/Texturpfad weiter von heuristisch auf robustere Zuordnung ausgebaut werden.

## Empfohlene nächste Lieferung

Die nächste in sich sinnvolle Lieferung für den 3D-Editor sollte nicht "noch mehr Decoder" sein, sondern ein klar abnehmbares Stabilitätspaket:

- Referenz-CMPs definieren und dokumentieren
- Referenzdateien aus `DATA\\SOLAR\\DOCKABLE` als Pflichtbasis festhalten
- Native Detaildarstellung für selektierte Objekte gegen diese Referenzen prüfen
- Decoder-/Layout-Probleme echter Dockable-CMPs vor weiterer UI-Arbeit beheben
- auffällige Transform-Abweichungen mit vorhandener Referenzdiagnostik reduzieren
- Background-Load/Cache-Verhalten für schnelle Selektion härten
- dafür gezielte Tests für Cache, Retry, veraltete Loads und Fallback ergänzen
- den jetzt vorhandenen Diagnosepfad gezielt für diese Referenzprüfung nutzen

Erst wenn diese Lieferung stabil ist, sollte die nächste Ausbaustufe folgen:

- Material-/Texturtreue sichtbar verbessern
- mehr als nur das selektierte Objekt nativ darstellen
- optional Asset-Inspektor / Hardpoint-/Part-Inspektion ausbauen
