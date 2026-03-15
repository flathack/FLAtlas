# FL Atlas — 3D Object Viewer: Entwickler-Dokumentation

> **Ziel:** Diese Dokumentation beschreibt die Architektur, Datenformate und Algorithmen des 3D-Object-Viewers
> in FL Atlas so detailliert, dass ein Entwickler den Editor von Grund auf nachbauen könnte.

---

## Inhaltsverzeichnis

1. [Systemübersicht](#1-systemübersicht)
2. [Datenfluss-Pipeline](#2-datenfluss-pipeline)
3. [Freelancer CMP/3DB-Dateiformat (UTF)](#3-freelancer-cmp3db-dateiformat-utf)
   - 3.1 [UTF-Header](#31-utf-header)
   - 3.2 [UTF-Node-Baum](#32-utf-node-baum)
   - 3.3 [Wichtige UTF-Knoten in CMP-Dateien](#33-wichtige-utf-knoten-in-cmp-dateien)
4. [CMP-Loader (`cmp_loader.py`)](#4-cmp-loader)
   - 4.1 [Einstiegspunkt](#41-einstiegspunkt)
   - 4.2 [VMeshRef-Parsing](#42-vmeshref-parsing)
   - 4.3 [VMeshData-Blöcke](#43-vmeshdata-blöcke)
   - 4.4 [Cons/Fix-Records (Transformationen)](#44-consfix-records-transformationen)
   - 4.5 [Cons/Rev-Records](#45-consrev-records)
   - 4.6 [Transform-Hint-Extraktion](#46-transform-hint-extraktion)
   - 4.7 [Hierarchische Transform-Kombination](#47-hierarchische-transform-kombination)
   - 4.8 [CRC-basierte VMesh-Auflösung](#48-crc-basierte-vmesh-auflösung)
5. [Geometrie-Dekodierung (`native_preview_geometry.py`)](#5-geometrie-dekodierung)
   - 5.1 [Einstiegspunkte](#51-einstiegspunkte)
   - 5.2 [VMeshData-Header-Format](#52-vmeshdata-header-format)
   - 5.3 [Mesh-Header-Array](#53-mesh-header-array)
   - 5.4 [FVF (Flexible Vertex Format)](#54-fvf-flexible-vertex-format)
   - 5.5 [Vertex-Extraktion](#55-vertex-extraktion)
   - 5.6 [Index-Extraktion](#56-index-extraktion)
   - 5.7 [Dekodierungs-Strategien](#57-dekodierungs-strategien)
   - 5.8 [Transform-Anwendung auf Geometrie](#58-transform-anwendung-auf-geometrie)
6. [Qt3D-Rendering (`view_3d.py`, `native_preview_qt3d.py`)](#6-qt3d-rendering)
   - 6.1 [Szenen-Aufbau](#61-szenen-aufbau)
   - 6.2 [Mesh-Entity-Erstellung](#62-mesh-entity-erstellung)
   - 6.3 [Material-System](#63-material-system)
   - 6.4 [Kamera & Interaktion](#64-kamera--interaktion)
   - 6.5 [Beleuchtung](#65-beleuchtung)
7. [Koordinatensystem](#7-koordinatensystem)
8. [Datenstrukturen-Referenz](#8-datenstrukturen-referenz)
9. [Datei-Übersicht](#9-datei-übersicht)

---

## 1. Systemübersicht

Der 3D Object Viewer ist ein Qt3D-basierter Echtzeit-Renderer, der Freelancer-Modelle im `.cmp`-
(Compound Model) und `.3db`-Format (Single-Part Model) laden und anzeigen kann. Er ist Teil des
FL Atlas System-Editors und wird aktiviert, wenn der Benutzer ein Solar-Objekt (Station, Planet,
Tradelane, etc.) im System-Browser auswählt.

**Technologie-Stack:**
- Python 3.13+
- PySide6 / Qt 6.10+ (Qt3D-Modul für Hardware-beschleunigtes 3D-Rendering)
- Struct-basiertes Binary-Parsing (kein externer Abhängigkeiten für das Dateiformat)

**Kernkomponenten:**

| Modul | Aufgabe |
|-------|---------|
| `cmp_loader.py` | UTF-Binary-Parsing, Part-Hierarchie, Transform-Extraktion |
| `native_preview_geometry.py` | Vertex- und Index-Dekodierung aus VMeshData |
| `native_preview_scene_data.py` | Szenen-Container mit Geometrien, Bounds, Texturen |
| `native_preview_qt3d.py` | Qt3D-Entity/Mesh/Material-Erstellung |
| `view_3d.py` | Haupt-Widget, Kamera, Interaktion, Rendering-Loop |
| `freelancer_mesh_data.py` | Datenklassen für alle Parse-Ergebnisse |

---

## 2. Datenfluss-Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│ 1. Benutzer wählt Solar-Objekt im System-Browser             │
│    → Archetype-Lookup: solar_arch → model_file               │
│    → z.B. "SOLAR\MISC\weapons_platform_lod.cmp"             │
└─────────────────────────┬────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. load_native_freelancer_model(pfad)           [cmp_loader] │
│    ├─ Datei als Bytes lesen                                  │
│    ├─ UTF-Header parsen (56 Bytes)                           │
│    ├─ UTF-Node-Baum rekonstruieren                           │
│    ├─ VMeshRef-Einträge extrahieren (Geometrie-Referenzen)   │
│    ├─ VMeshData-Blöcke klassifizieren (Vertex/Index-Daten)   │
│    ├─ Cons/Fix + Cons/Rev Records parsen (Transformationen)  │
│    ├─ Transform-Hints berechnen (lokal + kombiniert)         │
│    └─ → FreelancerMeshData (immutable Datencontainer)        │
└─────────────────────────┬────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. build_native_preview_scene_data(mesh_data)    [scene_data]│
│    ├─ decode_native_preview_geometries(mesh_data)            │
│    │   ├─ VMeshData-Header entschlüsseln                     │
│    │   ├─ FVF → Vertex-Stride berechnen                      │
│    │   ├─ Positionen extrahieren (x, y, z)                   │
│    │   ├─ Indices extrahieren (Triangle-Liste)                │
│    │   ├─ Rotation anwenden (3×3 Matrix × Vertex)            │
│    │   └─ Translation anwenden (Offset addieren)             │
│    ├─ Bounds aggregieren                                     │
│    ├─ Texturen auflösen                                      │
│    └─ → NativePreviewSceneData                               │
└─────────────────────────┬────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ 4. System3DView._update_native_detail()          [view_3d]   │
│    ├─ Für jede Geometrie:                                    │
│    │   ├─ build_native_geometry_renderer() → QGeometryRend.  │
│    │   │   ├─ Vertex Buffer (Position-Daten als <3f)         │
│    │   │   ├─ Index Buffer (u16 oder u32)                    │
│    │   │   └─ QAttribute3D → QGeometry3D → QGeomRenderer3D   │
│    │   ├─ Material erstellen (Textur oder Phong-Fallback)    │
│    │   └─ QEntity3D(root) + addComponent(renderer, material) │
│    ├─ Kamera auf Modell-Bounds zentrieren                    │
│    └─ → Rendering durch Qt3D Render-Loop                     │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Freelancer CMP/3DB-Dateiformat (UTF)

Freelancer verwendet ein proprietäres Binärformat namens **UTF** (Universal Tree Format).
Jede `.cmp`- und `.3db`-Datei ist ein UTF-Container.

### 3.1 UTF-Header

**Größe:** 56 Bytes  
**Struct-Format:** `<4s13I` (Little-Endian, 4-Byte-Magic + 13 × uint32)

```
Offset  Größe  Typ     Feld
──────  ─────  ──────  ──────────────────────────
0x00    4      char[]  magic = "UTF " (mit Leerzeichen)
0x04    4      u32     version
0x08    4      u32     node_block_offset
0x0C    4      u32     node_block_size
0x10    4      u32     unknown0
0x14    4      u32     node_entry_size (Standard: 44)
0x18    4      u32     names_offset
0x1C    4      u32     names_allocated_size
0x20    4      u32     names_used_size
0x24    4      u32     data_offset
0x28    4      u32     unknown1
0x2C    4      u32     unknown2
0x30    4      u32     timestamp_low
0x34    4      u32     timestamp_high
```

**Berechnung der Node-Anzahl:**
```
node_count = node_block_size / node_entry_size
```

### 3.2 UTF-Node-Baum

Nach dem Header folgt der Node-Block: ein flaches Array von 44-Byte-Einträgen, die einen
Baum bilden.

**Größe pro Node:** 44 Bytes  
**Struct-Format:** `<11I` (11 × uint32)

```
Offset  Größe  Typ   Feld
──────  ─────  ────  ──────────────────────────
0x00    4      u32   peer_offset (Offset zum nächsten Geschwister-Node)
0x04    4      u32   name_offset (Offset in die Namenstabelle)
0x08    4      u32   flags (Bit 0x80 = Daten-Node)
0x0C    4      u32   reserved
0x10    4      u32   child_or_data_offset
0x14    4      u32   allocated_size (nur bei Daten-Nodes)
0x18    4      u32   used_size (nur bei Daten-Nodes)
0x1C    4      u32   timestamp
0x20    12     u32×3 (reserviert, ignoriert)
```

**Semantik:**
- Wenn `flags & 0x80 != 0`: Der Node enthält Binärdaten. `child_or_data_offset` zeigt
  auf den Beginn der Daten im Datenblock, `used_size` gibt die Byte-Länge an.
- Wenn `flags & 0x80 == 0`: Der Node ist ein Container. `child_or_data_offset` zeigt auf
  den ersten Kind-Node.
- `peer_offset` verbindet Geschwister-Nodes (Linked-List). Wenn kein weiterer
  Geschwister existiert, ist der Wert 0.

**Namenstabelle:** Ab `names_offset` folgt ein Block null-terminierter ASCII-Strings.
`name_offset` im Node-Eintrag zeigt relativ zum Anfang der Namenstabelle.

**Baumtraversierung:** Rekursiv mit Zykluserkennung (visited-Set auf Offsets):
1. Lies den Node am aktuellen Offset
2. Wenn Container-Node: Steige in `child_offset` ab (rekursiv)
3. Wenn `peer_offset > 0`: Gehe zum Geschwister (iterativ)

### 3.3 Wichtige UTF-Knoten in CMP-Dateien

```
Root/
├── Cmpnd/                          ← Compound-Definition
│   ├── Part count                  ← u32 Daten-Node: Anzahl Parts
│   ├── Root/                       ← Root-Part-Definition
│   │   ├── Object name             ← String: "Root" o.Ä.
│   │   ├── File name               ← String: "Part_ROOT.3db"
│   │   └── Index                   ← u32: cmp_index
│   ├── Part_1/                     ← Weiterer Part
│   │   ├── Object name
│   │   ├── File name
│   │   └── Index
│   ├── ...
│   ├── Cons/
│   │   ├── Fix/                    ← Feste Verbindungen (Cons/Fix)
│   │   │   └── (Binary Data)       ← Fix-Records (Transform-Daten)
│   │   └── Rev/                    ← Drehbare Verbindungen (Cons/Rev)
│   │       └── (Binary Data)       ← Rev-Records
│   └── ...
├── Part_ROOT.3db/                  ← Embedded 3DB für Root-Part
│   ├── VMeshRef/                   ← Geometrie-Referenz
│   │   └── (Binary Data)           ← 60 Bytes
│   └── ...
├── Part_1.3db/                     ← Weitere Part-3DBs
│   └── VMeshRef/
├── VMeshLibrary/                   ← Vertex/Index-Datenansammlung
│   ├── some_name.vms/              ← VMesh-Stream
│   │   └── VMeshData               ← Header + Vertices + Indices
│   └── ...
├── Texture Library/                ← Texturen (optional)
│   └── ...
└── Material Library/               ← Materialien (optional)
```

---

## 4. CMP-Loader

### 4.1 Einstiegspunkt

```python
def load_native_freelancer_model(path: str | Path) -> FreelancerMeshData
```

Liest die gesamte Datei als `bytes`, parst den UTF-Header und -Baum, extrahiert alle
relevanten Daten (Parts, VMeshRefs, VMeshData-Blöcke, Fix/Rev-Records, Material-Referenzen)
und gibt ein immutablees `FreelancerMeshData`-Objekt zurück.

### 4.2 VMeshRef-Parsing

VMeshRef-Nodes verbinden Parts mit ihren Geometriedaten im VMeshData-Block.

**Struct-Format:** `<IIHHHHHH10f` (60 Bytes)

```
Offset  Größe  Typ    Feld
──────  ─────  ─────  ──────────────────────
0x00    4      u32    header_size (Referenz-Index)
0x04    4      u32    mesh_data_reference
0x08    2      u16    vertex_start
0x0A    2      u16    vertex_count
0x0C    2      u16    index_start
0x0E    2      u16    index_count
0x10    2      u16    group_start
0x12    2      u16    group_count
0x14    40     f32×10 Bounds: max_x, min_x, max_y, min_y, max_z, min_z,
                              center_x, center_y, center_z, radius
```

### 4.3 VMeshData-Blöcke

VMeshData enthält die eigentlichen Vertex- und Index-Daten. Die Klassifizierung erfolgt
heuristisch über den 16-Byte-Header (siehe Abschnitt 5.2).

Für jedes `VMeshData`-Node wird ein `FreelancerVMeshDataBlock` erstellt mit:
- `source_name`: Name des Parent-Nodes (z.B. `"some_name.vms"`)
- `stride_hint`: Vertex-Stride, extrahiert aus dem VMS-Dateinamen (falls vorhanden)
- `header_hint`: Heuristisch erkannte Struktur aus den ersten 16 Bytes

**Struktur-Erkennung (`_looks_like_structured_vmesh_header`):**
- `mesh_count` muss im Bereich 1..4096 liegen
- `flexible_vertex_format > 0`
- `vertex_count` im Bereich 1..65535
- Gesamtgröße muss für Header + Mesh-Headers + Vertices + Indices ausreichen

### 4.4 Cons/Fix-Records (Transformationen)

Cons/Fix beschreibt **feste** Verbindungen zwischen Parts. Zwei Formate existieren:

#### Format A: 176-Byte-Records (mit Namen)

**Erkennung:** Datengröße ist Vielfaches von 176; erstes Byte ist druckbares ASCII;
beide 64-Byte-Namensfelder enthalten Null-Terminatoren.

```
Offset  Größe  Typ      Feld
──────  ─────  ───────  ──────────────────────
0x00    64     char[64] parent_object_name (null-padded ASCII)
0x40    64     char[64] child_object_name (null-padded ASCII)
0x80    12     f32×3    origin: tx, ty, tz (Translation)
0x8C    36     f32×9    rotation: 3×3 Matrix (Row-Major)
                         r00, r01, r02,
                         r10, r11, r12,
                         r20, r21, r22
```

**Gesamtgröße pro Record:** 176 Bytes (64 + 64 + 12 + 36)

Die Part-Zuordnung erfolgt über den `child_object_name`, der mit den Part-`object_name`-Einträgen
aus den Cmpnd-Nodes abgeglichen wird.

#### Format B: Legacy-Records (ohne Namen)

Wenn die 176-Byte-Erkennung fehlschlägt:
1. `record_size = used_size / part_count`
2. `float_count = record_size / 4`
3. Row-Width-Erkennung: Versuche Kandidaten 11, 16, 12, 8, 4 — der erste Kandidat,
   durch den `float_count` glatt teilbar ist, wird gewählt.

**Standard 12-Float-Layout pro Row:**
```
Index  Feld
─────  ──────────────────
0-2    r00, r01, r02  (Rotationszeile 1)
3-5    r10, r11, r12  (Rotationszeile 2)
6-8    r20, r21, r22  (Rotationszeile 3)
9-11   tx, ty, tz     (Translation)
```

### 4.5 Cons/Rev-Records

Cons/Rev beschreibt **drehbare** Verbindungen (z.B. rotierende Turm-Elemente).

**Record-Größe:** 208 Bytes

```
Offset  Größe  Typ      Feld
──────  ─────  ───────  ──────────────────────
0x00    64     char[64] parent_object_name
0x40    64     char[64] child_object_name
0x80    12     f32×3    origin (tx, ty, tz)
0x8C    12     f32×3    offset
0x98    12     f32×3    axis_rotation
0xA4    36     f32×9    rotation (3×3 Matrix)
0xC8    8      -        padding
```

### 4.6 Transform-Hint-Extraktion

Aus den geparseten Fix/Rev-Records werden `FreelancerCmpTransformHint`-Objekte erstellt:

**Translation-Extraktion (`_cmp_fix_translation_hint`):**
```
176-Byte-Format:  row[0], row[1], row[2]   (Indices 0-2 = Origin)
12-Float-Legacy:  row[9], row[10], row[11]  (Indices 9-11)
11-Float-Legacy:  row[7], row[8], row[9]    (Indices 7-9)
```

**Rotation-Extraktion (`_cmp_fix_rotation_rows_hint`):**
```
176-Byte-Format:  [[row[3],row[4],row[5]], [row[6],row[7],row[8]], [row[9],row[10],row[11]]]
12-Float-Legacy:  [[row[0],row[1],row[2]], [row[3],row[4],row[5]], [row[6],row[7],row[8]]]
Multi-Row:        [[r0[0],r0[1],r0[2]], [r1[0],r1[1],r1[2]], [r2[0],r2[1],r2[2]]]
```

**Validierung der Rotationsmatrix:**
1. Jede Zeile wird normalisiert (Einheitsvektor)
2. Orthogonalitätscheck: `|dot(row_i, row_j)| < 0.8` für alle Paare
3. Determinantencheck: `|det(M)| > 1e-5` (nicht-singulär)
4. Bei nur 2 gültigen Zeilen: Dritte wird per Kreuzprodukt ergänzt, dann
   Gram-Schmidt-Orthogonalisierung

### 4.7 Hierarchische Transform-Kombination

CMP-Modelle haben eine Parent-Child-Hierarchie. Die lokale Transformation jedes Parts
wird mit der seines Parents kombiniert (rekursiv bis zum Root).

**Algorithmus (`_combined_cmp_transform_for_part`):**

```
combined_transform(part):
    local_T = translation(part)
    local_R = rotation(part)
    parent = parent_of(part)

    if parent == None:
        return (local_T, local_R)

    (parent_T, parent_R) = combined_transform(parent)

    # Translation: Parent-Rotation auf lokale Translation anwenden, dann addieren
    rotated_local_T = parent_R × local_T
    combined_T = parent_T + rotated_local_T

    # Rotation: Matrixmultiplikation parent_R × local_R
    combined_R = parent_R × local_R

    return (combined_T, combined_R)
```

**Rotation × Vektor:**
```
apply_rotation(R, v):
    x, y, z = v
    return (
        R[0][0]*x + R[0][1]*y + R[0][2]*z,
        R[1][0]*x + R[1][1]*y + R[1][2]*z,
        R[2][0]*x + R[2][1]*y + R[2][2]*z
    )
```

**Rotation × Rotation (Matrixmultiplikation):**
```
combined_R[i] = apply_rotation(parent_R, local_R[i])    für jede Zeile i
```

### 4.8 CRC-basierte VMesh-Auflösung

VMeshRef-Einträge referenzieren VMeshData-Blöcke über einen Index. Wenn die direkte
Zuordnung fehlschlägt (z.B. bei reorgaisierten Daten), wird ein CRC32-Lookup verwendet:

**CRC32-Berechnung:**
```python
def _freelancer_model_crc(name: str) -> int:
    # Freelancer-spezifische CRC32 mit vorgegebener Lookup-Tabelle
    # Verarbeitet den lowercase ASCII-Namen zeichenweise
    crc = 0xFFFFFFFF
    for char in name.lower():
        crc = CRC_TABLE[(crc ^ ord(char)) & 0xFF] ^ (crc >> 8)
    return crc ^ 0xFFFFFFFF
```

**Auflösungs-Reihenfolge:**
1. Direkter Index in VMeshData-Block-Array
2. CRC-Match: CRC des VMeshRef-Source-Namens ↔ CRC der VMeshData-Block-Source-Namen
3. Source-Name-String-Match (case-insensitive)
4. Fallback: Einzelner Block (wenn nur einer existiert)
5. Unresolved (Warnung)

---

## 5. Geometrie-Dekodierung

### 5.1 Einstiegspunkte

```python
def decode_native_preview_geometries(
    mesh_data: FreelancerMeshData,
) -> tuple[NativePreviewGeometry, ...]

def decode_native_preview_geometry(
    mesh_data: FreelancerMeshData,
) -> NativePreviewGeometry | None
```

`decode_native_preview_geometries` gibt alle dekodierten Part-Geometrien zurück.
`decode_native_preview_geometry` gibt nur die erste (primäre) zurück.

### 5.2 VMeshData-Header-Format

Der VMeshData-Block beginnt mit einem 16-Byte-Header:

**Struct-Format:** `<II4H` (2 × uint32 + 4 × uint16)

```
Offset  Größe  Typ   Feld
──────  ─────  ────  ──────────────────────
0x00    4      u32   mesh_type (ignoriert)
0x04    4      u32   surface_type (ignoriert)
0x08    2      u16   mesh_count
0x0A    2      u16   num_ref_vertices (= Index-Anzahl)
0x0C    2      u16   flexible_vertex_format (FVF)
0x0E    2      u16   vertex_count
```

**Daten nach dem Header:**
```
[16 .. 16 + mesh_count×12]        Mesh-Header-Array
[.. + num_ref_vertices×2]         Index-Buffer (uint16-Tripel)
[.. + vertex_count×stride]        Vertex-Buffer
```

### 5.3 Mesh-Header-Array

Jeder Mesh-Header ist 12 Bytes groß:

```
Offset  Größe  Typ   Feld
──────  ─────  ────  ──────────────────────
0x00    4      u32   material_id (ignoriert für Preview)
0x04    2      u16   start_vertex
0x06    2      u16   end_vertex
0x08    2      u16   num_ref_indices
0x0A    2      u16   padding
```

Die Mesh-Headers definieren Submeshes innerhalb des Vertex-Buffers: welcher Bereich
von Vertices und wie viele Indices zu einem bestimmten Material gehören.

### 5.4 FVF (Flexible Vertex Format)

Die FVF-Bits bestimmen, welche Daten pro Vertex gespeichert sind und damit den Vertex-Stride:

```
Bit-Maske  Komponente             Größe
─────────  ─────────────────────  ─────
0x002      Position (XYZ)         12 Bytes (immer vorhanden)
0x010      Normal (NX, NY, NZ)    12 Bytes
0x040      Diffuse Color (RGBA)    4 Bytes
0x100      1 Tex-Coord (U, V)      8 Bytes
0x200      2 Tex-Coords           16 Bytes
0x400      4 Tex-Coords           32 Bytes
0x500      5 Tex-Coords           40 Bytes
```

**Stride-Berechnung:**
```python
stride = 12                          # Basis: 3×f32 für (x, y, z)
if fvf & 0x10:  stride += 12        # Normal
if fvf & 0x40:  stride += 4         # Diffuse Color
tex = fvf & 0x700
if   tex == 0x500: stride += 40     # 5 Tex-Coords
elif tex == 0x400: stride += 32     # 4 Tex-Coords
elif tex == 0x200: stride += 16     # 2 Tex-Coords
elif tex == 0x100: stride += 8      # 1 Tex-Coord
```

**Typisches Beispiel:** FVF = `0x0112` (D3DFVF_XYZ | D3DFVF_NORMAL | D3DFVF_TEX1)
→ Stride = 12 + 12 + 8 = **32 Bytes**

### 5.5 Vertex-Extraktion

Positionen werden aus dem Vertex-Buffer extrahiert. Pro Vertex werden nur die ersten
12 Bytes gelesen (Position); der Rest (Normal, Textur-Koordinaten) wird übersprungen:

```python
for i in range(vertex_count):
    offset = i * stride
    x, y, z = struct.unpack_from("<3f", raw, offset)  # 3 × float32 LE
    positions.append((x, y, z))
```

**Validierung pro Vertex:**
- Alle Werte müssen `finite` sein (kein NaN/Inf)
- `max(|x|, |y|, |z|) ≤ 1.000.000` (Plausibilitätscheck)

**Koordinatensystem:** Y-up (kein Achsentausch). Die Rohdaten aus der CMP-Datei
werden direkt als `(x, y, z)` übernommen.

### 5.6 Index-Extraktion

Indices folgen direkt nach den Mesh-Headers. Sie sind als uint16-Tripel gespeichert:

```python
for i in range(num_ref_vertices // 3):
    offset = index_base + i * 6
    v1, v3, v2 = struct.unpack_from("<3H", raw, offset)  # 3 × uint16 LE
    triangles.append((v1, v2, v3))
```

**Wichtig:** Die Datei speichert die Reihenfolge `(v1, v3, v2)`. Beim Lesen wird zu
`(v1, v2, v3)` umgeordnet — dies korrigiert die Winding Order für korrekte
Face-Normals (Counter-Clockwise).

### 5.7 Dekodierungs-Strategien

Die Dekodierung versucht mehrere Strategien in absteigender Priorität:

| Priorität | Strategie | Confidence-Label | Beschreibung |
|-----------|-----------|-------------------|-------------|
| 1 | Structured Decode Plan | `structured-*` | VMeshData-Header erkannt, FVF-basierter Stride, Mesh-Header für Ranges |
| 2 | Embedded VMeshData | `structured-single-block` | Eingebetteter VMeshData-Block direkt im Part-Node |
| 3 | Exact-Fit Slice | `exact` | Vertex-Count × Stride = exakte Buffer-Größe |
| 4 | Tight-Fit Slice | `tight` | Buffer-Größe passt nach Abzug eines kleinen Headers |
| 5 | Loose-Fit Slice | `loose` | Heuristik mit mehreren Stride-Kandidaten |

**Structured Decode Plan (bevorzugt):**
1. VMeshData-Header entschlüsseln (16 Bytes)
2. FVF → Stride berechnen
3. Mesh-Header-Array lesen
4. Indices aus dem Block extrahieren
5. Vertices aus dem Block extrahieren
6. Part-spezifischen Bereich über `group_start`/`group_count` selektieren

### 5.8 Transform-Anwendung auf Geometrie

Nach der Vertex-Extraktion werden CMP-Transformationen angewandt (in `_build_raw_geometry`):

**Schritt 1 — Rotation (zuerst):**
```python
if rotation_rows is not None:
    for (x, y, z) in positions:
        new_x = R[0][0]*x + R[0][1]*y + R[0][2]*z
        new_y = R[1][0]*x + R[1][1]*y + R[1][2]*z
        new_z = R[2][0]*x + R[2][1]*y + R[2][2]*z
```

**Schritt 2 — Translation (danach):**
```python
if translation is not None:
    for (x, y, z) in positions:
        new_pos = (x + tx, y + ty, z + tz)
```

**Reihenfolge ist entscheidend:** Zuerst rotieren, dann translatieren. Andernfalls würde
die Rotation um den verschobenen Ursprung erfolgen.

**Transform-Matching:** Die Zuordnung Transform → Geometrie erfolgt über den `part_name`:
1. Finde den Part-Namen für den aktuellen `model_name`
2. Suche in `cmp_transform_hints` nach einem Eintrag mit gleichem `part_name`
3. Verwende bevorzugt `combined_translation_xyz` und `combined_rotation_rows_xyz`
   (hierarchisch aufgelöst)
4. Fallback auf `translation_xyz` und `normalized_rotation_rows_xyz` (lokal)

---

## 6. Qt3D-Rendering

### 6.1 Szenen-Aufbau

```python
# Qt3D-Fenster und Root-Entity
self._window = Qt3DWindow()
self._root = QEntity()
self._window.setRootEntity(self._root)

# In Qt-Widget-Hierarchie einbetten
self._container = QWidget.createWindowContainer(self._window)
```

### 6.2 Mesh-Entity-Erstellung

Für jede `NativePreviewGeometry` wird eine Qt3D-Entity aufgebaut
(in `build_native_geometry_renderer()`):

**Vertex-Buffer:**
```python
vertex_blob = QByteArray()
for x, y, z in geometry.positions:
    vertex_blob.append(struct.pack("<3f", x, y, z))  # 12 Bytes pro Vertex

vertex_buffer = QBuffer()
vertex_buffer.setData(vertex_blob)
```

**Position-Attribut:**
```python
position_attr = QAttribute()
position_attr.setName(QAttribute.defaultPositionAttributeName())
position_attr.setVertexBaseType(QAttribute.Float)
position_attr.setVertexSize(3)        # 3 Komponenten (x, y, z)
position_attr.setByteStride(12)       # 3 × 4 Bytes
position_attr.setCount(len(geometry.positions))
position_attr.setBuffer(vertex_buffer)
```

**Index-Buffer:**
```python
index_blob = QByteArray()
if geometry.index_size == 2:
    for idx in geometry.indices:
        index_blob.append(struct.pack("<H", idx))    # uint16
    index_type = QAttribute.UnsignedShort
else:
    for idx in geometry.indices:
        index_blob.append(struct.pack("<I", idx))    # uint32
    index_type = QAttribute.UnsignedInt
```

**Geometry-Renderer:**
```python
renderer = QGeometryRenderer()
renderer.setGeometry(geometry_object)
renderer.setPrimitiveType(QGeometryRenderer.Triangles)
renderer.setVertexCount(len(geometry.indices))
```

**Entity-Zusammenbau:**
```python
entity = QEntity(root_entity)
entity.addComponent(renderer)    # Mesh-Geometrie
entity.addComponent(material)    # Material/Textur
entity.addComponent(QTransform())  # Identity-Transform (bereits in Vertices eingebacken)
```

**Hinweis:** Die Transformationen sind bereits in die Vertex-Positionen eingerechnet
(Abschnitt 5.8). Der `QTransform` auf der Entity bleibt die Identity-Matrix. Es findet
**keine** doppelte Transform-Anwendung statt.

### 6.3 Material-System

**Prioritäts-Reihenfolge:**

1. **Textur-Material:** Wenn eine Textur-Datei für den Part gefunden wird:
   ```python
   texture = QTextureLoader()
   texture.setSource(QUrl.fromLocalFile(texture_path))
   material = QTextureMaterial()
   material.setTexture(texture)
   ```

2. **Diffuse-Map-Fallback:** Wenn `QTextureMaterial` nicht verfügbar:
   ```python
   material = QDiffuseMapMaterial()
   material.setDiffuse(texture)
   ```

3. **Phong-Material-Fallback:** Ohne Textur:
   ```python
   material = QPhongMaterial()
   material.setShininess(8.0)
   material.setAmbient(QColor(r-48, g-48, b-48))  # Abgedunkelter Ambient
   material.setDiffuse(QColor(r, g, b))
   ```

**Farb-Generierung:** Die Phong-Farben werden deterministisch aus dem Modell-/Part-Namen
generiert (`native_preview_rgb()`), so dass jeder Part eine konsistente, unterscheidbare
Farbe erhält.

### 6.4 Kamera & Interaktion

**Kamera-Typ:** Perspektivische Orbit-Kamera

**Initialwerte:**
```python
field_of_view = 45.0°
aspect_ratio  = 16:9
near_plane    = 0.1
far_plane     = 50000.0

cam_target    = (0, 0, 0)      # Orbit-Zentrum
cam_distance  = 450.0          # Abstand zum Zentrum
cam_yaw       = 0.0°           # Horizontale Rotation
cam_pitch     = ~81.4°         # Vertikale Rotation (1.42 rad, nahe Draufsicht)
```

**Kamera-Position-Berechnung (sphärische Koordinaten):**
```
x = target.x + distance × sin(pitch) × sin(yaw)
y = target.y + distance × cos(pitch)
z = target.z + distance × sin(pitch) × cos(yaw)
```

**Maus-Interaktion:**

| Aktion | Taste | Verhalten |
|--------|-------|-----------|
| Orbit | LMB + Drag | `yaw += delta_x × 0.5°`, `pitch += delta_y × 0.5°` |
| Pan | RMB + Drag | Target in der Bildschirmebene verschieben |
| Zoom | Mausrad | `distance *= 1.1^(wheel_delta)` (logarithmisch) |

**Auto-Framing:** Beim Laden eines neuen Modells wird die Kamera automatisch so positioniert,
dass das gesamte Modell (basierend auf den aggregierten Bounds) sichtbar ist.

### 6.5 Beleuchtung

Zwei gerichtete Lichter (DirectionalLight) für Tiefen-Wahrnehmung:

```python
# Licht 1: Von oben-hinten (Hauptlicht)
light1.direction = (-0.6, -1.0, -0.4)

# Licht 2: Von oben-vorne (Fülllicht, asymmetrisch)
light2.direction = (0.2, -0.8, 0.7)
```

Die asymmetrische Anordnung verhindert flache Beleuchtung und sorgt für erkennbare
3D-Konturen auch bei einfachen Phong-Materialien.

---

## 7. Koordinatensystem

**Alle Daten im Viewer verwenden Y-up:**

```
        +Y (oben)
         |
         |
         |_______ +X (rechts)
        /
       /
      +Z (zum Betrachter)
```

**Wichtig:**
- CMP-Vertex-Daten sind nativ Y-up (DirectX-Konvention)
- CMP-Transform-Daten (Fix/Rev) sind ebenfalls Y-up
- Es findet **kein** Y↔Z-Achsentausch statt
- Die Daten werden direkt aus der Datei gelesen: `(x, y, z)` → `(x, y, z)`

**VMeshRef-Bounds:** Bei den Bounds in VMeshRef-Nodes wird ein Y↔Z-Swap durchgeführt,
da die Bounds in einem anderen Koordinatensystem (Z-up) gespeichert sind als die
Vertex-Daten (Y-up). Dies betrifft nur die Bounding-Box-Metadaten, nicht die
eigentlichen Vertices.

---

## 8. Datenstrukturen-Referenz

### FreelancerMeshData (Hauptcontainer)

```python
@dataclass(frozen=True)
class FreelancerMeshData:
    source_path: Path                    # Originaler Dateipfad
    format: str                          # "cmp" oder "3db"
    node_count: int                      # Anzahl UTF-Nodes
    node_entry_size: int                 # 44

    # UTF-Baum
    nodes: tuple[FreelancerUtfNode, ...]
    node_names: tuple[str, ...]

    # Part-Hierarchie
    parts: tuple[FreelancerMeshPart, ...]

    # Geometrie-Referenzen
    vmesh_references: tuple[str, ...]
    vmesh_refs: tuple[FreelancerVMeshRef, ...]
    vmesh_data_blocks: tuple[FreelancerVMeshDataBlock, ...]
    vmesh_data_families: tuple[FreelancerVMeshDataFamily, ...]

    # Dekodierungs-Pläne
    structured_mesh_header_records: tuple[FreelancerStructuredMeshHeaderRecord, ...]
    structured_decode_plans: tuple[FreelancerStructuredDecodePlan, ...]

    # Preview-Matching
    model_nodes: tuple[FreelancerModelNode, ...]
    preview_nodes: tuple[FreelancerPreviewMeshNode, ...]
    preview_geometry_sources: tuple[FreelancerPreviewGeometrySource, ...]
    preview_layout_guesses: tuple[FreelancerPreviewLayoutGuess, ...]
    preview_buffer_slices: tuple[FreelancerPreviewBufferSlice, ...]
    preview_family_decode_hints: tuple[FreelancerPreviewFamilyDecodeHint, ...]

    # CMP-Transformationen
    cmp_fix_records: tuple[FreelancerCmpFixRecord, ...]
    cmp_transform_hints: tuple[FreelancerCmpTransformHint, ...]

    # Materialien
    material_references: tuple[FreelancerMaterialReference, ...]
    preview_material_bindings: tuple[FreelancerPreviewMaterialBinding, ...]

    # Meta
    bounds: FreelancerBounds | None
    warnings: tuple[str, ...]
```

### FreelancerCmpFixRecord

```python
@dataclass(frozen=True)
class FreelancerCmpFixRecord:
    part_name: str                       # Zugeordneter Part-Name
    part_index: int | None               # CMP-Index des Parts
    record_index: int                    # Position im Record-Array
    record_size: int                     # Bytes pro Record (176 oder variabel)
    float_count: int                     # Anzahl Floats im Record
    row_width: int                       # Floats pro Zeile
    row_count: int                       # Anzahl Zeilen
    rows: tuple[tuple[float, ...], ...]  # Float-Daten als Zeilen
    first_f32: tuple[float, ...]         # Debug: erste 8 Floats
    first_u32: tuple[int, ...]           # Debug: erste 8 uint32s
    parent_name: str | None = None       # Parent-Part-Name (bei 176-Byte-Format)
    cons_fix_format: bool = False        # True für 176-Byte-Format
```

### FreelancerCmpTransformHint

```python
@dataclass(frozen=True)
class FreelancerCmpTransformHint:
    part_name: str
    part_index: int | None
    record_index: int
    row_width: int
    row_count: int
    translation_xyz: tuple[float, float, float] | None             # Lokale Translation
    combined_translation_xyz: tuple[float, float, float] | None    # Welt-Translation
    leading_vector_xyz: tuple[float, float, float] | None
    normalized_forward_xyz: tuple[float, float, float] | None
    normalized_rotation_rows_xyz: tuple[tuple[float, float, float], ...] | None  # Lokale 3×3 Matrix
    combined_rotation_rows_xyz: tuple[tuple[float, float, float], ...] | None   # Welt-3×3 Matrix
    translation_magnitude: float | None
```

### NativePreviewGeometry

```python
@dataclass(frozen=True)
class NativePreviewGeometry:
    model_name: str                                  # z.B. "twr_top"
    level_name: str | None                           # z.B. "Level0"
    part_name: str | None                            # CMP-Part-Name
    group_start: int                                 # Mesh-Gruppen-Start
    group_count: int                                 # Mesh-Gruppen-Anzahl
    positions: tuple[tuple[float, float, float], ...]  # Transformierte Vertices
    indices: tuple[int, ...]                         # Triangle-Index-Liste
    vertex_stride: int                               # Original-Stride in Bytes
    index_size: int                                  # 2 (uint16) oder 4 (uint32)
    confidence: str                                  # Dekodierungs-Qualität
    bounds: FreelancerBounds                         # AABB nach Transform
```

### NativePreviewSceneData

```python
@dataclass(frozen=True)
class NativePreviewSceneData:
    geometries: tuple[NativePreviewGeometry, ...]    # Alle Geometrien
    primary_geometry: NativePreviewGeometry | None   # Erste Geometrie
    bounds: FreelancerBounds | None                  # Aggregierte AABB
    part_names: tuple[str, ...]                      # Alle Part-Namen
    texture_path: Path | None                        # Haupt-Textur
    geometry_texture_paths: tuple[Path | None, ...]  # Textur pro Geometrie
    cmp_orientation_debug_rows: tuple[...]           # Debug-Infos
    cmp_up_correction_euler_deg: tuple[float, float, float]
    cmp_transform_hints: tuple[FreelancerCmpTransformHint, ...]
```

---

## 9. Datei-Übersicht

| Datei | Zeilen | Hauptverantwortung |
|-------|--------|-------------------|
| `fl_editor/cmp_loader.py` | ~1800 | UTF-Parsing, Part-Hierarchie, Cons/Fix, Cons/Rev, CRC, VMesh-Auflösung |
| `fl_editor/native_preview_geometry.py` | ~1300 | VMeshData-Dekodierung, FVF, Vertex/Index-Extraktion, Transform-Anwendung |
| `fl_editor/native_preview_scene_data.py` | ~200 | Szenen-Container, Bounds-Aggregation, Textur-Auflösung |
| `fl_editor/native_preview_qt3d.py` | ~300 | Qt3D-Entity-/Mesh-/Material-Erstellung |
| `fl_editor/view_3d.py` | ~800 | Haupt-Widget, Kamera, Maus-Interaktion, Rendering-Setup |
| `fl_editor/freelancer_mesh_data.py` | ~500 | Alle Datenklassen (frozen dataclasses) |
| `fl_editor/native_preview_materials.py` | ~150 | Textur-Pfad-Auflösung, Farb-Zuweisung |
| `fl_editor/cmp_orientation_debug.py` | ~100 | CMP-Orientierungs-Analyse, Up-Korrektur |
