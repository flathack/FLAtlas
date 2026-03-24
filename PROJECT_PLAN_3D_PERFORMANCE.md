# FLAtlas 3D Performance Plan

## Goal

The 3D system editor and 3D model workflows should feel responsive even in large systems with many native `CMP/3DB` objects.

The main user-facing targets are:

- opening a system must not freeze the UI
- switching from `2D` to `3D` should feel immediate
- large systems such as `Li03`, `Ku01` and Crossfire-heavy scenes must continue loading progressively
- the progress indicator must keep moving and must not get stuck on values such as `4 / 16` or `10 / 113`
- placeholders should be replaced gradually without visible stutter

## Current Reality

The current architecture is already better than the initial version:

- 3D preview loading is incremental at object level
- large native models are now also built incrementally across multiple ticks
- placeholder primitives stay visible while real models load
- refresh storms during `2D -> 3D` switching were reduced
- some queue-reset bugs were fixed

Even with these fixes, the remaining bottlenecks are still mostly in:

- native model decode cost
- texture/material resolution cost
- Qt3D entity/component creation on the UI thread
- repeated work for identical archetypes
- too much work starting at once during system open or `2D -> 3D`

## Core Constraint

Not all work can be parallelized safely.

Good candidates for background workers:

- reading `CMP/3DB` files
- decoding `UTF` / `VMeshData`
- resolving materials and textures
- computing bounds and transform metadata
- preparing cached preview data

Poor candidates for background workers:

- creating `Qt3D` scene entities directly
- mutating visible Qt widgets from worker threads
- building large batches of `QEntity`, `QMaterial`, `QTransform`, `QMesh` objects outside the main thread

This means the right architecture is:

1. decode and prepare in background
2. hand over small prepared chunks
3. attach Qt3D objects in tiny UI-thread batches

## Performance Strategy

### Phase 1: Stabilize the Existing Path

Status: partly done, should continue immediately

Tasks:

- keep native preview building incremental both per object and per geometry chunk
- ensure refresh requests cannot restart an active build pipeline repeatedly
- delay heavy 3D rebuilds until after the 2D system view has painted
- cap per-tick UI work so one bad model cannot freeze the window
- improve progress reporting so the current object/archetype can be diagnosed quickly

Success criteria:

- no hard freeze on `Li03`
- progress values continue moving
- closing or switching tabs during load does not leak half-built entities

### Phase 2: Archetype-Level Shared Cache

Status: not fully implemented

Problem:

If a system contains many objects with the same archetype, FLAtlas still repeats too much preparation and scene setup work.

Tasks:

- cache decoded native geometry by archetype/model path
- cache texture/material resolution results separately
- cache transform-ready preview metadata that can be reused for multiple instances
- reuse the same prepared geometry package for all identical archetypes in the system

Expected benefit:

- much faster repeated loads
- less CPU work per system
- less disk access and texture churn

### Phase 3: Background Decode Workers

Status: recommended next medium-term step

Tasks:

- move native decode work into worker threads or worker processes
- keep the worker result format UI-agnostic
- return prepared scene payloads to the main thread via a queue
- prioritize visible/near/selected objects first
- support cancellation when the user closes the system tab or switches systems

Important note:

The worker should never create Qt3D entities. It should only produce prepared data such as:

- decoded geometry blocks
- bounds
- part names
- material/texture references
- transform metadata

Expected benefit:

- faster system opening on multi-core CPUs
- much less UI hitching during large decode bursts

### Phase 4: Persistent Native Preview Cache

Status: not yet implemented

Problem:

Currently much of the expensive work is repeated after app restart.

Tasks:

- add a disk cache for decoded preview data
- key the cache by:
  - model file path
  - file size
  - file timestamp
  - optional content hash for stricter validation
- store:
  - decoded geometry metadata
  - bounds
  - material references
  - texture resolution results

Expected benefit:

- huge improvement after first load
- better startup behavior for large mods
- less repeated Crossfire decode cost

### Phase 5: Smarter Loading Policy

Status: partially implemented, needs refinement

Tasks:

- prioritize visible objects before off-screen objects
- prioritize selected object and large gameplay-relevant objects
- add a maximum number of new native previews started per frame
- support quality profiles such as:
  - `Near`
  - `Balanced`
  - `All`
  - `Selection Only`
- allow delayed loading of low-value objects such as tiny debris or distant clutter

Expected benefit:

- better perceived performance without removing detail entirely
- faster time-to-first-useful-3D-view

### Phase 6: Reuse and Instancing

Status: longer-term improvement

Tasks:

- investigate whether identical simple preview geometry can be reused more directly
- avoid rebuilding equivalent Qt3D material setups repeatedly
- keep lightweight per-instance transforms separate from heavy shared data

Note:

Qt3D does not make high-performance instancing as simple as modern game engines, so this needs careful feasibility checking. Still, reducing duplication at the preparation layer should already help a lot.

## GPU Considerations

The GPU can help with rendering, but it does not solve the whole problem.

GPU helps with:

- drawing already-created geometry
- textured materials
- keeping the camera responsive once the scene exists

GPU does not automatically help with:

- decoding Freelancer formats
- creating thousands of Qt3D objects
- Python-side loops and object orchestration
- file and texture resolution

Conclusion:

More GPU power helps after scene creation, but the biggest FLAtlas gains come from reducing main-thread setup work and moving decode/preparation work off the UI thread.

## Recommended Roadmap

### Short Term

Implement next:

1. active-object debug info in the `Loading 3D objects...` progress path
2. stricter cancellation when switching systems/tabs during load
3. archetype-level in-memory cache for decoded preview payloads
4. start only a limited number of new heavy native loads per update cycle

### Medium Term

Implement next:

1. worker-thread or process-based decode pipeline
2. persistent preview cache on disk
3. smarter prioritization by visibility and relevance
4. user-facing quality presets

### Long Term

Implement only if still needed:

1. deeper shared-geometry reuse
2. optional native extension in `C++` or `Rust` for hot decode paths
3. more advanced render backend or preview path if Qt3D becomes the limiting factor

## Suggested Metrics

To know whether each step helps, FLAtlas should measure:

- time to open a system in `2D`
- time to first visible `3D` frame
- time to first 10 native models
- total time until preview queue is complete
- average and worst UI-frame hitch during load
- number of queued / active / failed native loads
- cache hit rate for native preview data

## Immediate Next Implementation

If work starts right away, the best next technical task is:

1. build an archetype-level decoded preview cache in memory
2. add active-object progress/debug reporting
3. then move decode into background workers

That sequence should give the best payoff without a risky full rewrite.

## Summary

The best performance path for FLAtlas is not "use more CPU cores everywhere" or "let the GPU do it". The winning strategy is:

- decode in background
- cache aggressively
- build Qt3D in tiny main-thread chunks
- avoid redoing work for identical archetypes
- prioritize what the user actually needs first

This gives the highest chance of keeping the 3D editor smooth in both Vanilla Freelancer and large mods such as Crossfire.
