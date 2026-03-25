# FLAtlas 3D Background Streaming Plan

## Goal

The 3D system viewer should load native objects as unobtrusively as possible while the user keeps navigating the scene.

The target user experience is:

- opening a system should remain responsive
- camera orbit, pan, zoom, and free-cam movement should not stutter because of 3D object loading
- real 3D models should appear progressively in the background
- placeholders should remain stable until a real model is ready
- large scenes should avoid visible "load spikes"

## Honest Constraint

This can be improved a lot, but not fully eliminated.

Some work is good for background execution:

- reading `CMP/3DB` files
- UTF parsing
- `VMeshData` decode
- LOD selection
- bounds computation
- placeholder / preview decision making
- cache key generation

Some work is still expensive on the main thread:

- creating Qt3D entities
- attaching Qt3D components
- inserting many scene nodes at once
- replacing placeholders with real entities

So the correct strategy is:

1. move as much preparation as possible off the UI thread
2. keep the main thread work very small and predictable
3. reduce the number of objects that need a full native build at all

## Current Problems

Based on the current FLAtlas behavior, the remaining sources of stutter are:

- object decode and scene-data preparation still happen too close to interactive camera movement
- too many native preview candidates can become eligible at once
- repeated archetypes still cost too much when many instances exist in a system
- Qt3D entity creation happens in chunks that are still too heavy
- object replacement sometimes competes with camera navigation

## Proposed Architecture

### Stage 1: Smooth Scheduling

Goal: reduce visible hitches without large architectural risk.

Changes:

- introduce a strict camera-idle gate before any new native load work begins
- pause new native preview work completely while the camera is actively moving
- allow only a very small number of new object replacements per UI tick
- prioritize only objects that are:
  - in view
  - near the camera
  - stable in view for a short time
- keep placeholders visible until the replacement entity is fully ready
- never remove an already valid native preview just because a later refresh briefly misses it

Expected result:

- much smoother orbit / pan / free-cam
- less "camera fights loader"
- fewer visible load spikes

Implementation notes:

- extend the existing camera-idle refresh logic in `view_3d.py`
- cap the per-tick replacement budget
- add a "stable for N ms" eligibility window before starting native work

### Stage 2: Background Scene-Data Preparation

Goal: move expensive non-Qt preparation off the main thread.

Changes:

- create worker tasks for:
  - file read
  - UTF parse
  - geometry decode
  - LOD extraction
  - bounds calculation
  - simple color-only preview material metadata
- the worker output should be plain Python data, not Qt3D objects
- the main thread should only:
  - receive prepared scene-data
  - build entities in very small batches
  - attach them when complete

Expected result:

- the biggest decode cost no longer blocks the UI directly
- camera movement remains responsive while model data is prepared

Implementation notes:

- do not create Qt widgets or Qt3D entities in workers
- use worker-safe immutable payloads
- include cancellation tokens so stale jobs are dropped when the camera moves away

### Stage 3: Archetype-Level Reuse

Goal: stop rebuilding the same model repeatedly for many objects.

Changes:

- maintain a prepared-scene cache per resolved model path / archetype / LOD mode
- when many objects share the same model, decode once and reuse the prepared result
- separate:
  - prepared geometry cache
  - live entity instance state
- allow cheap per-instance transforms on top of shared prepared scene-data

Expected result:

- major improvement in systems with many repeated tradelane rings, platforms, depots, buoys, and similar objects

Implementation notes:

- the cache key must include:
  - model path
  - decode mode
  - simplified system-view flags
  - LOD selection mode
- cache eviction should be bounded to prevent memory growth

### Stage 4: Tiered System-View Rendering

Goal: avoid full native builds for objects that do not benefit from them.

Changes:

- define clear tiers for system-view rendering:
  - Tier A: placeholder only
  - Tier B: cheap native preview
  - Tier C: full native preview
- suggested policy:
  - near + visible + stable: Tier C
  - mid distance or lower priority: Tier B
  - far or unstable view: Tier A
- "cheap native preview" can mean:
  - coarsest LOD only
  - only major parts
  - color-only material path
  - no texture resolution

Expected result:

- much less scene complexity in large systems
- better perceptual quality near the camera
- lower overall Qt3D load

## Priority Order

Recommended implementation order:

1. Stage 1: Smooth Scheduling
2. Stage 2: Background Scene-Data Preparation
3. Stage 3: Archetype-Level Reuse
4. Stage 4: Tiered System-View Rendering

This order gives the best risk-to-impact ratio.

## Concrete Quick Wins

These are the best immediate tasks:

1. Pause native preview scheduling while the camera is actively moving.
2. Add a strict per-frame replacement budget for native entities.
3. Add a short "visibility stability" delay before an object becomes eligible for loading.
4. Add cancellation for stale background decode jobs.
5. Reuse prepared scene-data for repeated archetypes.

## Success Metrics

The plan should be measured, not guessed.

Useful metrics:

- average UI frame time while orbiting in large systems
- maximum frame spike during native preview replacement
- time from object entering view to real 3D replacement
- number of active background decode jobs
- number of reused prepared archetype payloads
- number of live native previews vs placeholders

## Recommended Logging

To make this debuggable, add lightweight activity entries for:

- `3D queue: scheduled`
- `3D queue: canceled stale job`
- `3D decode: started`
- `3D decode: prepared in worker`
- `3D attach: main-thread batch`
- `3D reuse: cache hit`
- `3D reuse: cache miss`

## Final Recommendation

Yes, background-style loading is worth doing in FLAtlas.

The best practical path is not "make everything async", but:

- prepare scene-data in workers
- attach only tiny batches on the main thread
- reuse archetype work aggressively
- avoid loading objects that are not stable and visible

That will not make loading mathematically free, but it should make it feel much closer to invisible during normal editing.
