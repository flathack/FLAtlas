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

## Execution Roadmap

The safest way to deliver this is as a series of small, testable commits instead of one large rewrite.

### Commit Group A: Scheduling and Main-Thread Protection

Scope:

- strengthen camera-idle gating
- fully pause new native scheduling during active camera motion
- add a hard per-tick replacement budget
- add an object "stability timer" before native work starts

Expected code areas:

- `fl_editor/view_3d.py`
- `tests/test_view_3d_widget_smoke.py`

Done when:

- camera motion does not trigger immediate native scheduling churn
- object replacement is visibly smoother
- the system viewer no longer rebuilds aggressively while orbiting

### Commit Group B: Worker-Prepared Scene Data

Scope:

- introduce background preparation jobs for decode-ready scene payloads
- keep worker output free of Qt3D and QWidget objects
- add cancellation for stale jobs
- attach only finished prepared payloads on the main thread

Expected code areas:

- `fl_editor/native_scene_loader.py`
- `fl_editor/native_scene_runtime.py`
- `fl_editor/native_scene_main_window_runtime.py`
- `fl_editor/view_3d.py`
- tests around runtime and loader behavior

Done when:

- stale work is cancelable
- decode/preparation can complete while the UI remains interactive
- main-thread work is limited to attach/replace steps

### Commit Group C: Archetype Reuse and Prepared Payload Cache

Scope:

- cache prepared scene payloads by model path + decode mode
- reuse one prepared payload for many object instances
- add bounded eviction

Expected code areas:

- `fl_editor/native_scene_loader.py`
- `fl_editor/native_preview_scene_data.py`
- `fl_editor/view_3d.py`
- cache-focused tests

Done when:

- repeated archetypes no longer trigger repeated full preparation
- cache hit/miss behavior is visible in debug/activity output

### Commit Group D: Tiered System-View Rendering

Scope:

- formalize Tier A / B / C rendering
- keep near visible objects detailed
- keep mid-distance objects cheap-native
- keep low-value far objects on placeholders

Expected code areas:

- `fl_editor/view_3d.py`
- `fl_editor/native_preview_scene_data.py`
- viewer smoke tests

Done when:

- total active native previews stay bounded in large systems
- system-view quality remains good near the camera
- far-scene cost is clearly lower

### Commit Group E: Instrumentation and Verification

Scope:

- add lightweight activity logging for queueing, worker prep, attach, cancel, reuse
- add timing counters or debug metrics
- validate with problem systems and large repeated-object scenes

Expected code areas:

- `fl_editor/main_window.py`
- `fl_editor/view_3d.py`
- runtime/helper files
- tests where feasible

Done when:

- the activity view explains what the loader is doing
- regressions are easier to diagnose
- the user can distinguish loading, waiting, cancellation, and reuse

## Concrete Quick Wins

These are the best immediate tasks:

1. Pause native preview scheduling while the camera is actively moving.
2. Add a strict per-frame replacement budget for native entities.
3. Add a short "visibility stability" delay before an object becomes eligible for loading.
4. Add cancellation for stale background decode jobs.
5. Reuse prepared scene-data for repeated archetypes.

## Recommended Commit Strategy

To keep risk under control, the best commit strategy is:

1. one commit for stronger scheduling and replacement throttling
2. one commit for worker-prepared scene-data plumbing
3. one commit for stale-job cancellation and lifecycle cleanup
4. one commit for archetype-level prepared payload reuse
5. one commit for tiered system-view rendering policy
6. one commit for instrumentation, activity messages, and verification helpers

This can be compressed if some steps land together cleanly, but this is the safest baseline.

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

## Risks

The main risks are:

- stale worker results attaching after the camera moved away
- race conditions between cancellation and attach
- memory growth from prepared payload caches
- breaking correctness for system-object placement while simplifying the path
- reintroducing placeholder/native flicker if attach timing is not stable

The mitigation is:

- version/ticket every camera-driven refresh cycle
- discard payloads whose ticket is no longer current
- use bounded caches with clear eviction
- keep placeholders alive until full replacement succeeds
- land the work in small commits with regression tests

## Definition of Done

The plan should be considered complete when all of the following are true:

- camera orbit in large systems no longer visibly hitches because of new native loads
- opening a system remains interactive while native previews continue in the background
- repeated archetypes are clearly reused rather than repeatedly rebuilt
- the activity/status output explains what the 3D loader is doing
- placeholder/native replacement is stable and does not flicker under normal navigation
- difficult systems still finish loading without getting stuck on partial progress

## Remaining Work Estimate

If implemented in the cautious sequence above, the remaining effort is roughly:

- best case: `4` commits
- realistic case: `6` commits
- conservative case: `7-8` commits

My honest estimate is that we need **about 6 more commits** to reach a solid first "finished" version of this background-streaming improvement, assuming no major decoder regressions appear during the worker/caching stages.

## Final Recommendation

Yes, background-style loading is worth doing in FLAtlas.

The best practical path is not "make everything async", but:

- prepare scene-data in workers
- attach only tiny batches on the main thread
- reuse archetype work aggressively
- avoid loading objects that are not stable and visible

That will not make loading mathematically free, but it should make it feel much closer to invisible during normal editing.
