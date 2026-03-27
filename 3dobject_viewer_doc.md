# FL Atlas - 3D Object Viewer Developer Documentation

> Goal: describe the architecture, data flow, binary parsing, geometry decoding, and Qt3D rendering path of the FL Atlas 3D object viewer clearly enough that another developer could rebuild the system from scratch.

---

## Table of Contents

1. System Overview
2. Data Flow Pipeline
3. Freelancer CMP/3DB Container Format
   - 3.1 UTF Header
   - 3.2 UTF Node Tree
   - 3.3 Important UTF Nodes
4. CMP Loader (`cmp_loader.py`)
   - 4.1 Entry Point
   - 4.2 `VMeshRef` Parsing
   - 4.3 `VMeshData` Blocks
   - 4.4 `Cons/Fix` Records
   - 4.5 `Cons/Rev` Records
   - 4.6 Transform-Hint Extraction
   - 4.7 Hierarchical Transform Composition
   - 4.8 CRC-Based `VMesh` Resolution
5. Geometry Decoding (`native_preview_geometry.py`)
   - 5.1 Entry Points
   - 5.2 `VMeshData` Header Layout
   - 5.3 Mesh Header Array
   - 5.4 Flexible Vertex Format (`FVF`)
   - 5.5 Vertex Extraction
   - 5.6 Index Extraction
   - 5.7 Decode Strategies
   - 5.8 Transform Application
   - 5.9 General Rules for Non-Uniform Native Mesh Layouts
6. Scene Data and Render Integration
   - 6.1 Scene Data Container
   - 6.2 Qt3D Renderer Construction
   - 6.3 Material and Texture Resolution
   - 6.4 Camera and Interaction
   - 6.5 3D Model Manager
   - 6.6 System 3D Viewer vs. Standalone Preview
7. Coordinate System
8. Core Data Structures
9. File Map

---

## 1. System Overview

The FL Atlas 3D viewer is a Qt3D-based real-time renderer for Freelancer native model formats:

- `.cmp` for compound models with multiple parts
- `.3db` for single-part models
- `.sph`-adjacent handling is implemented separately for planets, but the native viewer is primarily focused on `.cmp` and `.3db`

The same core decode pipeline is reused in three places:

- object preview dialogs
- the embedded preview inside the `3D Model Manager`
- the 3D system viewer used inside the system editor

The important architectural principle is:

**one native decode path, multiple UI surfaces**

This keeps rendering behavior, geometry fixes, material handling, and decoder improvements consistent across the application.

### Main Modules

| Module | Responsibility |
|---|---|
| [`fl_editor/cmp_loader.py`](C:/Users/steve/Github/FLAtlas/fl_editor/cmp_loader.py) | UTF parsing, part hierarchy, transform extraction, `VMeshRef` and `VMeshData` analysis |
| [`fl_editor/native_preview_geometry.py`](C:/Users/steve/Github/FLAtlas/fl_editor/native_preview_geometry.py) | vertex/index decoding, geometry normalization, transform application |
| [`fl_editor/native_preview_scene_data.py`](C:/Users/steve/Github/FLAtlas/fl_editor/native_preview_scene_data.py) | scene-data packaging, geometry selection, texture lookup |
| [`fl_editor/native_preview_qt3d.py`](C:/Users/steve/Github/FLAtlas/fl_editor/native_preview_qt3d.py) | Qt3D geometry/material helpers |
| [`fl_editor/dialogs.py`](C:/Users/steve/Github/FLAtlas/fl_editor/dialogs.py) | standalone preview dialog |
| [`fl_editor/model_viewer_dialog.py`](C:/Users/steve/Github/FLAtlas/fl_editor/model_viewer_dialog.py) | `3D Model Manager` UI |
| [`fl_editor/view_3d.py`](C:/Users/steve/Github/FLAtlas/fl_editor/view_3d.py) | 3D system viewer |
| [`fl_editor/freelancer_mesh_data.py`](C:/Users/steve/Github/FLAtlas/fl_editor/freelancer_mesh_data.py) | immutable parse/result data classes |

---

## 2. Data Flow Pipeline

```text
User selects object or model entry
    |
    v
Resolve archetype -> model path
    |
    v
load_native_freelancer_model(path)
    |
    v
Parse UTF tree / parts / VMeshRef / VMeshData / materials / transform hints
    |
    v
decode_native_preview_geometries(mesh_data)
    |
    v
Apply structured decode rules, embedded decode rules, fallback slice decode
    |
    v
Normalize geometry where needed
    |
    v
build_native_preview_scene_data(...)
    |
    v
Convert scene data to Qt3D entities/materials
    |
    v
Display in:
    - MeshPreviewDialog
    - embedded 3D Model Manager preview
    - system 3D viewer
```

---

## 3. Freelancer CMP/3DB Container Format

Freelancer native models are UTF containers. A `.cmp` or `.3db` file is not a simple raw mesh blob; it is a hierarchical binary container with named nodes, binary data nodes, and embedded geometry/material metadata.

### 3.1 UTF Header

The UTF file begins with a fixed-size header.

Typical interpretation:

| Offset | Size | Type | Meaning |
|---|---:|---|---|
| `0x00` | 4 | char[4] | magic, usually `"UTF "` |
| `0x04` | 4 | `u32` | version |
| `0x08` | 4 | `u32` | node block offset |
| `0x0C` | 4 | `u32` | node block size |
| `0x14` | 4 | `u32` | node entry size, usually `44` |
| `0x18` | 4 | `u32` | string table offset |
| `0x24` | 4 | `u32` | data block offset |

Node count is derived from:

```python
node_count = node_block_size // node_entry_size
```

### 3.2 UTF Node Tree

After the header, the file stores a flat list of node entries. These entries form a tree through child and peer pointers.

Important behavior:

- a node can be a container or a data node
- container nodes point to the first child
- sibling traversal is done through `peer_offset`
- data nodes point into the binary payload block

### 3.3 Important UTF Nodes

Typical model files expose nodes such as:

- `Cmpnd`
- `Part_*`
- `VMeshLibrary`
- `VMeshData`
- `VMeshRef`
- material and texture nodes
- `Cons/Fix`
- `Cons/Rev`

The exact subtree varies by asset.

---

## 4. CMP Loader (`cmp_loader.py`)

### 4.1 Entry Point

```python
load_native_freelancer_model(path: str | Path) -> FreelancerMeshData
```

This is the main parse step. It reads the file, reconstructs the UTF tree, extracts model parts, `VMeshRef` records, `VMeshData` blocks, transform hints, material bindings, and returns an immutable [`FreelancerMeshData`](C:/Users/steve/Github/FLAtlas/fl_editor/freelancer_mesh_data.py) instance.

### 4.2 `VMeshRef` Parsing

`VMeshRef` records connect logical model nodes to geometry data.

Relevant fields:

- `mesh_data_reference`
- `vertex_start`
- `vertex_count`
- `index_start`
- `index_count`
- `group_start`
- `group_count`
- bounds metadata

The parser treats these values as hints, not absolute truth. Some assets store them conventionally, others store them in reorganized or unusual layouts.

### 4.3 `VMeshData` Blocks

Each `VMeshData` block is classified heuristically.

Stored metadata includes:

- source node name
- byte size
- family key
- stride hints derived from source naming
- decoded header hints

The loader builds:

- raw block list
- grouped block families
- preview source candidates
- structured decode plans
- fallback buffer slices

### 4.4 `Cons/Fix` Records

`Cons/Fix` records represent fixed relationships between parts.

They are used to extract:

- local translation
- local rotation rows
- combined hierarchical translation
- combined hierarchical rotation rows

These hints are later applied to decoded geometry so compound model parts appear in the correct spatial relationship.

### 4.5 `Cons/Rev` Records

`Cons/Rev` records describe revolute or animated relationships. They are parsed for completeness and diagnostics, but the static preview pipeline mainly relies on fixed transform hints for geometry placement.

### 4.6 Transform-Hint Extraction

The loader resolves transform information into [`FreelancerCmpTransformHint`](C:/Users/steve/Github/FLAtlas/fl_editor/freelancer_mesh_data.py) records.

Each hint may contain:

- local translation
- combined translation
- local normalized rotation rows
- combined rotation rows

### 4.7 Hierarchical Transform Composition

Part transforms are composed recursively along the parent chain:

```python
combined_translation = parent_translation + rotate(parent_rotation, local_translation)
combined_rotation = parent_rotation @ local_rotation
```

This is important for compound models where child pieces are positioned relative to parent parts.

### 4.8 CRC-Based `VMesh` Resolution

When direct block lookup is ambiguous or unstable, the loader can resolve geometry through Freelancer-style CRC matching of model/source names.

Resolution order is approximately:

1. direct block match
2. family-aware structured match
3. CRC-based name resolution
4. fallback heuristics

---

## 5. Geometry Decoding (`native_preview_geometry.py`)

### 5.1 Entry Points

```python
decode_native_preview_geometries(mesh_data, normalize_to_center=True)
decode_native_preview_geometry(mesh_data)
```

`decode_native_preview_geometries(...)` returns all decoded geometry chunks.

`decode_native_preview_geometry(...)` returns the first decoded geometry for legacy/simpler call sites.

### 5.2 `VMeshData` Header Layout

The structured single-block path treats the start of a block as:

```python
<II4H
```

Conceptually:

- ignored/unknown fields
- `mesh_count`
- `num_ref_vertices`
- `flexible_vertex_format`
- `vertex_count`

### 5.3 Mesh Header Array

After the 16-byte header, structured decode expects a mesh-header array. Each header describes:

- material or group identifier
- `start_vertex`
- `end_vertex`
- `num_ref_indices`

This allows the decoder to map `group_start` / `group_count` from `VMeshRef` into the correct sub-range of the block.

### 5.4 Flexible Vertex Format (`FVF`)

`FVF` determines the per-vertex payload layout.

General rule used by the current decoder:

```python
stride = 12  # XYZ
if fvf & 0x10:
    stride += 12  # normal
if fvf & 0x40:
    stride += 4   # diffuse color
tex_coord_set_count = (fvf & 0x700) >> 8
stride += tex_coord_set_count * 8
```

Important implication:

- the decoder no longer hardcodes only a few special UV masks
- the number of UV sets is derived generically from the `0x700` bits

This is required for assets that use layouts such as:

- `0x112` -> position + normal + 1 UV set
- `0x212` -> position + normal + 2 UV sets
- `0x312` -> position + normal + 3 UV sets

### 5.5 Vertex Extraction

Vertices are decoded from the raw block according to the derived stride.

The preview pipeline always extracts:

- position
- first UV set when available

Additional UV sets are skipped for rendering unless specifically needed elsewhere.

Validation checks include:

- finite float values
- reasonable absolute coordinate limits

### 5.6 Index Extraction

Indices are decoded as `u16` or `u32` depending on the active decode plan or fallback slice.

The native preview pipeline normalizes the triangle winding consistently so the rendered geometry behaves correctly under Qt3D.

### 5.7 Decode Strategies

The decoder tries several strategies, in priority order:

1. structured decode plan
2. embedded structured `VMeshData`
3. exact/tight fallback slice
4. broader heuristic fallback

Confidence strings include values such as:

- `structured-single-block`
- `structured-family-split`
- `exact`
- `tight`

### 5.8 Transform Application

After decoding vertices and indices, part transforms are applied.

The important order is:

1. rotate
2. translate

Conceptually:

```python
rotated = R @ position
final = rotated + T
```

Transforms are matched to decoded geometry through part/model names and the previously extracted CMP transform hints.

### 5.9 General Rules for Non-Uniform Native Mesh Layouts

Not all native model files organize geometry the same way. The decoder must therefore rely on structural rules, not assumptions tied to one exact asset family.

The current general rules are:

#### Rule 1: derive UV-set count generically from FVF

Do not hardcode a tiny whitelist of texture-coordinate layouts.

Use:

```python
tex_coord_set_count = (fvf & 0x700) >> 8
```

This avoids misreading valid vertex streams whose layout is wider than the simplest common cases.

#### Rule 2: treat `VMeshRef` counts as hints when necessary

Some native assets store geometry counts in ways that are not perfectly conventional. The decoder should compare:

- header semantics
- slice fit
- family structure
- index range plausibility

rather than trusting one count field blindly in every case.

#### Rule 3: normalize exploded triangle-soup geometry

Some native meshes are stored as effectively exploded triangle soup:

- `index_count == vertex_count`
- triangles reference mostly sequential vertex triplets
- many vertices are duplicates or near-duplicates

For those cases the decoder now performs a generic reindexing pass:

- build a merge key from `(position, uv)`
- use a small tolerance when forming that key
- remap indices onto reused vertices

This is not tied to one specific model. It is a structural cleanup step for any geometry that matches the pattern.

#### Rule 4: keep normalization narrow

The tolerance-based merge is intentionally limited to geometry that already looks like exploded triangle soup.

It is **not** a global vertex snapping pass for all meshes.

This keeps normal assets stable while still repairing over-expanded geometry layouts.

#### Rule 5: preserve origin where world placement matters

The decoder supports two meaningful output modes:

- centered preview mode
- origin-preserving world-placement mode

Centered mode is useful for standalone preview dialogs and the model manager.

Origin-preserving mode is required in the 3D system viewer, where station parts and compound assets must remain spatially aligned in world space.

---

## 6. Scene Data and Render Integration

### 6.1 Scene Data Container

[`build_native_preview_scene_data(...)`](C:/Users/steve/Github/FLAtlas/fl_editor/native_preview_scene_data.py) wraps decoded geometry into a render-oriented scene object.

It contains:

- selected display geometries
- aggregate bounds
- texture paths
- part-name list
- transform/orientation debug data

### 6.2 Qt3D Renderer Construction

For each geometry:

- build a Qt3D geometry renderer
- create vertex and index buffers
- attach material
- create optional wireframe entity

The native preview path bakes transforms into vertex positions. Qt3D `QTransform` components are therefore usually identity transforms for the model geometry itself.

### 6.3 Material and Texture Resolution

Material resolution follows a layered fallback approach:

1. native texture path resolved from material bindings
2. `.mat` / texture-library fallback
3. plain colored Phong-style material

This keeps models visible even when texture resolution is incomplete.

### 6.4 Camera and Interaction

The preview camera is orbit-style.

The camera is framed from aggregate bounds:

- center from AABB midpoint
- distance derived from radius

The preview dialog also exposes a preview zoom factor used by:

- standalone object preview
- embedded preview in the 3D Model Manager

### 6.5 3D Model Manager

The `3D Model Manager` is a tool tab that reuses the same native preview pipeline.

Its layout is:

- left: categorized model tree
- right:
  - `Preview` tab with large embedded live preview
  - `Details` tab with metadata and preview hints

The embedded preview is a `MeshPreviewDialog` running in widget mode rather than modal-dialog mode.

The manager exposes:

- live preview
- dedicated zoom slider
- open separate preview
- open source INI
- open model file

### 6.6 System 3D Viewer vs. Standalone Preview

The system 3D viewer and standalone preview intentionally use slightly different scene-data output behavior.

#### Standalone preview / 3D Model Manager

Default:

```python
normalize_to_center=True
```

This is ideal for inspection because the camera can always frame the object around the local center.

#### System 3D viewer

Uses:

```python
normalize_to_center=False
```

This preserves the original model origin so world placement stays correct for:

- compound stations
- multi-part bases
- other assembled world objects

Without this distinction, parts that belong together can appear spatially separated inside the system view.

---

## 7. Coordinate System

The preview pipeline uses the model-space coordinates as decoded from the native data.

Conceptually:

- `X` = horizontal
- `Y` = vertical
- `Z` = depth

The important practical rule is:

**do not add ad-hoc axis swaps unless a proven data interpretation requires it**

Most preview failures in the current codebase came from:

- wrong vertex stride
- wrong submesh/header interpretation
- wrong transform selection

and not from the global coordinate system itself.

---

## 8. Core Data Structures

### `FreelancerMeshData`

High-level immutable parse result containing:

- UTF nodes
- parts
- `VMeshRef` records
- `VMeshData` blocks and families
- preview source candidates
- fallback slices
- structured decode plans
- CMP transform hints
- material bindings

Defined in:

- [`freelancer_mesh_data.py`](C:/Users/steve/Github/FLAtlas/fl_editor/freelancer_mesh_data.py)

### `NativePreviewGeometry`

Represents one decoded renderable geometry chunk.

Important fields:

- `model_name`
- `level_name`
- `part_name`
- `positions`
- `indices`
- `vertex_stride`
- `index_size`
- `confidence`
- `bounds`
- `tex_coords`

### `NativePreviewSceneData`

Represents the render-facing bundle used by UI components.

Includes:

- geometry tuple
- primary geometry
- aggregate bounds
- part names
- texture paths
- CMP debug rows

---

## 9. File Map

| File | Responsibility |
|---|---|
| [`fl_editor/cmp_loader.py`](C:/Users/steve/Github/FLAtlas/fl_editor/cmp_loader.py) | UTF parsing, `VMeshRef` and `VMeshData` analysis, transform extraction |
| [`fl_editor/native_preview_geometry.py`](C:/Users/steve/Github/FLAtlas/fl_editor/native_preview_geometry.py) | geometry decoding, FVF handling, normalization, transform application |
| [`fl_editor/native_preview_scene_data.py`](C:/Users/steve/Github/FLAtlas/fl_editor/native_preview_scene_data.py) | preview-scene packaging, geometry selection |
| [`fl_editor/native_preview_qt3d.py`](C:/Users/steve/Github/FLAtlas/fl_editor/native_preview_qt3d.py) | Qt3D helpers |
| [`fl_editor/dialogs.py`](C:/Users/steve/Github/FLAtlas/fl_editor/dialogs.py) | standalone mesh preview dialog |
| [`fl_editor/model_viewer_dialog.py`](C:/Users/steve/Github/FLAtlas/fl_editor/model_viewer_dialog.py) | model manager UI |
| [`fl_editor/view_3d.py`](C:/Users/steve/Github/FLAtlas/fl_editor/view_3d.py) | system 3D viewer |
| [`tests/test_native_preview_geometry.py`](C:/Users/steve/Github/FLAtlas/tests/test_native_preview_geometry.py) | decoder regression coverage |

---

## Current Practical Summary

The current native viewer is built around these principles:

- decode structurally, not by filename special-casing
- derive vertex layout from actual `FVF` bits
- normalize exploded triangle soup generically
- preserve origin in world-placement contexts
- reuse the same core preview path across all UI surfaces

That combination has proven much more robust than trying to patch individual models one by one.
