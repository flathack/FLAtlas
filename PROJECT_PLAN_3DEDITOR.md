# Projektplan: Ausbau des 3D-Editors mit nativer Anzeige von Freelancer-CMP-Objekten

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

- Freelancer-Modelle liegen typischerweise als `*.cmp` vor
- native Vorschaupfade für CMP sind bereits vorhanden
- die Haupt-3D-Ansicht nutzt diese nativen Daten aber noch nicht für das selektierte Objekt
- die Transform-Anwendung ist noch nicht robust genug, um die Darstellung als "spielnah korrekt" zu betrachten

## Ziel

Der 3D-Editor soll Freelancer-Objekte so anzeigen, wie sie im Spiel tatsächlich aussehen:

- native Unterstützung für `*.cmp`
- Vorbereitung für `*.3db` und verwandte Freelancer-Modellpfade
- Verwendung der echten Geometrie statt nur Sphären oder Würfeln
- Anzeige direkt in der bestehenden 3D-Systemansicht und in der Einzelmodell-Vorschau

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
- Phase 4 bis 6 sind noch offen:
  - Part- und Model-Transforms sind noch nicht vollständig belastbar im nativen Renderpfad integriert
  - Material- und Texturpfad ist weiterhin heuristisch und noch nicht materialtreu
  - die erste native Detail-Entity in `view_3d.py` für selektierte Objekte ist jetzt vorhanden
  - Bounds werden jetzt bereits für das Fokussieren selektierter nativer Detailmodelle genutzt
  - ein erster Render-Cache für wiederholt selektierte Detailmodelle ist jetzt vorhanden
  - ein erster Hintergrundladepfad für selektionsbezogene native Szenedaten ist jetzt vorhanden

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

## Phase 2: CMP-Dateien lesbar machen

Ziel:

- `*.cmp` strukturell einlesen und in ein internes Datenmodell überführen.

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
- klare Definition, wann ein Transform-Pfad als korrekt gilt
- Parent-Child-Zusammenhänge und kombinierte Model-Transforms sind über die aktuelle lokale Basis-Stabilisierung hinaus noch offen

Abnahmekriterien:

- mindestens ein einfacher Freelancer-CMP-Archetype kann intern als Mesh-Struktur geladen werden
- Transform-Daten lassen sich für bekannte Referenzmodelle konsistent reproduzieren

## Phase 3: Einzelmodell-Vorschau mit echten CMPs

Ziel:

- `MeshPreviewDialog` zeigt echte CMP-Geometrie statt Primitive-Fallback.

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

Abnahmekriterien:

- ausgewähltes Objekt im Editor zeigt in der 3D-Vorschau sein echtes Modell
- bekannte Referenzmodelle wirken in Position, Orientierung und Größe plausibel korrekt
- Ladefehler und unvollständige Materialzuordnung bleiben diagnostizierbar

## Phase 4: Integration in die System-3D-Ansicht

Ziel:

- nicht nur das Preview-Fenster, sondern auch die Haupt-3D-Ansicht soll echte Objekte verwenden.

Status:

- offen

Teilweise vorbereitet:

- `MainWindow` löst native Szenedaten für das selektierte Objekt jetzt bereits mit kleinem Modellpfad-Cache auf
- `System3DView` besitzt jetzt einen dedizierten Zustand für selektionsbezogene native Szenedaten
- eine erste native Detail-Entity wird für das selektierte Objekt bereits aufgebaut und ersetzt dort den Marker
- der Qt3D-Unterbau für native Geometrie und Materialien ist zwischen Preview und Systemansicht vereinheitlicht
- `center_on_item` nutzt bei nativen Detailmodellen jetzt Bounds-basierte Fokussierung
- wiederholte Auswahl desselben nativen Detailmodells kann jetzt die bereits aufgebaute Detail-Entity wiederverwenden
- pro-Geometrie-Texturauflösung wird jetzt bereits in den gemeinsamen Szenedaten vorbereitet und in Preview/Systemansicht genutzt

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

Messbare Zielwerte:

- Auswahlwechsel in typischen Systemen bleibt subjektiv flüssig
- wiederholte Anzeige desselben Modells nutzt Cache statt Neudekodierung
- das Öffnen oder Wechseln der Selektion blockiert die UI nicht spürbar

Abnahmekriterien:

- Editor bleibt bei typischen Systemen responsiv
- wiederholte Selektionen desselben Archetyps führen zu Cache-Hits

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
- als Nächstes Referenz-CMPs auswählen, an denen Position und Orientierung gegen bekannte Spielobjekte verifiziert werden
- danach Parent-Child- und kombinierte Model-Transforms reproduzierbar machen
- klare Diagnosepfade für unvollständige oder widersprüchliche Transform-Daten behalten

### Schritt 2

Wiederverwendbaren nativen Renderpfad extrahieren:

- gemeinsamer Szenedaten-Helfer für native Geometrie, Bounds, Part-Namen und globale Texturauflösung ist aus `MeshPreviewDialog` herausgelöst
- als Nächstes denselben Datenpfad in `view_3d.py` für das selektierte Objekt verwenden
- danach Material-Bindings und Debug-Daten weiter in wiederverwendbare Bausteine ziehen

### Schritt 3

`view_3d.py` um Detailmodell-Entity ergänzen:

- Daten-Brücke von `MainWindow` nach `view_3d.py` für selektionsbezogene native Szenedaten ist vorhanden
- selektiertes Objekt wird jetzt bereits als native Detail-Entity aufgebaut
- Marker wird bei Selektion ersetzt und bei Deselektion wiederhergestellt
- Bounds-basierte Fokussierung für native Detailmodelle ist jetzt vorhanden
- ein erster Render-Cache für wiederholte Selektion desselben Modells ist jetzt vorhanden
- pro-Geometrie-Texturpfade werden jetzt bereits sowohl im Preview als auch in `view_3d.py` genutzt
- als Nächstes diesen Detailpfad gegen bekannte Referenz-CMPs prüfen und Materialtreue weiter schärfen
- Fallback bei Ladefehlern oder unvollständigen Daten bleibt aktiv

### Schritt 4

Minimalen Cache ergänzen:

- geladene native Modelldaten nach Pfad cachen
- wiederholte Dekodierung desselben Modells vermeiden

### Schritt 5

Asynchrones Laden und Materialpfad ausbauen:

- selektionsbezogene Native-Szenedaten werden jetzt bereits im Hintergrund geladen und nach Abschluss in die 3D-Ansicht übernommen
- als Nächstes den Hintergrundpfad gegen größere Referenzmodelle prüfen und bei Bedarf Debouncing oder Priorisierung ergänzen
- Material- und Texturpfad schrittweise verbessern

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

## Risiken

- CMP-Parsing und Transform-Dekodierung sind der technisch schwierigste Teil
- Qt3D akzeptiert Freelancer-Dateien nicht direkt
- vollständige Material- und Texturunterstützung kann deutlich aufwendiger werden
- ungecachtes Laden kann die Systemansicht stark verlangsamen
- doppelte Logik in Preview und Systemansicht würde Wartung und Fehlersuche unnötig erschweren

## Erfolgskriterien

Das Vorhaben ist erfolgreich, wenn:

- ein selektiertes Freelancer-Objekt im Editor als echtes CMP-Modell angezeigt wird
- die Einzelvorschau kein Primitive mehr für normale CMP-Archetypen braucht
- Position, Rotation und grobe Größe für bekannte Referenzmodelle sichtbar korrekt wirken
- Ladefehler klar diagnostiziert werden
- die 3D-Ansicht trotz echter Modelle flüssig bleibt

## Empfohlener nächster Schritt

Der nächste konkrete Umsetzungsschritt ist jetzt die Prüfung des nativen Detailpfads gegen bekannte Referenz-CMPs, insbesondere für Transform-Korrektheit, Materialzuordnung und das Verhalten des neuen Hintergrundladepfads bei größeren Modellen. Danach lohnt sich weiterer Ausbau von Materialtreue und Ladepriorisierung.
