# FLAtlas

## CHANGELOG POLICY (for future changes)
- Keep this file updated on every release and notable development step.
- Classify each user-visible change under exactly one section: `Added`, `Changed`, or `Fixed`.
- Add commit references in `### Commits in this range` using format: ``- `abcdef1` short message``.
- If a commit touches multiple areas, list it once where impact is strongest.
- Do not leave empty release blocks in final release state.
- Before publishing a release, ensure the version block in this file matches `fl_atlas.py` `APP_VERSION`.

### Release block template
```md
## vX.Y.Z -> vA.B.C - Changelog ############################################

### Added
- ...

### Changed
- ...

### Fixed
- ...

### Commits in this range
- `abcdef1` short message
```

## CURRENT BUGS:
- "Write changes to file" is highlighted even when nothing was changed.
- Planet ring options are missing. 3D ring objects in the 3D editor should match in-game orientation.

## v0.6.2.4 -> v0.6.2.5 - Changelog ########################################################################################

### Added
- Savegame editor was split into a dedicated module:
  - New file: `fl_editor/savegame_editor.py`
  - Integrated launch from FL Atlas remains unchanged
  - Standalone launch support added (`python -m fl_editor.savegame_editor`)
- Savegame editor now supports guarded story-mode handling:
  - Detects active campaign mission state (`StoryInfo.MissionNum`)
  - Prevents unsafe location edits (`system/base`) for active story saves
- Savegame editor UI/UX additions:
  - Dedicated menu bar (`File`, `Settings`)
  - Path settings dialog for savegame path and game/mod path
  - Savegame list labels include in-game save name where available
  - Savegame file backup on save (`.FLAtlasBAK`)
  - Loading progress indicator while parsing
- Reputation and map tooling improvements:
  - Faction labels resolved as `nickname - ingame name`
  - Reputation templates sourced from `initialworld.ini`
  - Added visited/locked map tabs with batch actions for JH/JG unlock workflows

### Changed
- Savegame editor layout was reworked into tabs for better navigation:
  - `General`, `Reputation`, `Ship`
- Ship tab now scales with window size for better visibility on large equipment sets.
- Savegame editor title branding updated to:
  - `FL Atlas - Savegame Editor by Aldenmar Odin - flathack`

### Fixed
- Save write stability:
  - Preserves `[Player]` section structure and replaces mutable key blocks in-place
  - Avoids destructive reordering of `visit/locked_gate/equip/cargo/house` lines
- Save crash prevention:
  - Blocks story-unsafe `system/base` changes that can crash Freelancer load
- Ship/equipment handling:
  - Fixed hardpoint extraction to include all `hp_type` mounts (`HpWeapon02+`, etc.)
  - Fixed dynamic hardpoint filtering and compatibility mapping
  - Preserves unknown/special mounted hardpoints (lights/contrails/headlights) during roundtrip save
- Visited map handling:
  - Unlock-all for JH/JG now also marks corresponding systems as visited for proper map reveal behavior

### Commits in this range
- `pending` savegame editor extraction, standalone support, UI restructure, story-safe save guards, hardpoint/filter fixes, visit unlock improvements, and save-write stability fixes

## v0.6.2.3 -> v0.6.2.4 - Changelog ########################################################################################

### Added
- New FLAtlas Settings tab structure:
  - `Allgemein` (now first tab)
  - `System Editor` (placeholder)
  - `Mod Manager`
  - `DEV Status`
- New `DEV Status` settings sub page with per-main-navigation status display.
- New centralized DEV status source in `fl_atlas.py`:
  - `DEV_STATUS_STATES` (5 feature maturity states from Pre Alpha to Gold)
  - `DEV_STATUS_BY_NAV`
- New manual update-check action in Help menu (`Check for Updates`).
- New update-check options:
  - `Beim Start automatisch auf Updates prüfen` in `Allgemein`
  - `Check auf Alpha release` (shown only if enabled via `fl_atlas.py`)
  - Welcome-screen checkbox for startup update checks (default enabled)
- New splash-screen startup support using `Splash-Screen.png` with user toggle in `Allgemein`.

### Changed
- Mod Manager path settings were moved from general settings content into the dedicated `Mod Manager` settings tab.
- Added a dedicated point-size slider next to zoom slider for better dense-object editing without changing camera zoom.
- Unified naming typo in settings caption:
  - `FLAtlass` -> `FLAtlas`
- Main window title now includes phase marker (`[Alpha]`).
- Feedback UX was redesigned:
  - more prominent modern `Give Feedback` button
  - feedback dialog now focuses on Discord
  - direct GitHub link/button added
- Splash-screen max display size increased to `500 x 1400`.
- Update-check backend improved with stable fallback behavior for GitHub API/redirect edge cases.
- Translation coverage in `main_window.py` was expanded:
  - moved additional menu, settings, dev-status, flight-HUD and history strings to `translations.json`
  - reduced remaining hardcoded visible UI texts in updated areas

### Fixed
- 2D picking behavior improved:
  - Clicking text labels no longer selects objects
  - Labels no longer block clicks on underlying objects
  - Double-click selection now ignores labels consistently
- Update-check flow now supports environments where `releases/latest` is unavailable (e.g. pre-release-only publishing) and handles fallback lookup better.
- Fixed missing i18n labels for newly added settings/update/dev-status UI elements.

### Commits
- `pending` settings restructure, dev-status integration, update-check system, splash-screen controls, feedback dialog redesign, and 2D picking improvements

## v0.6.2.2 -> v0.6.2.3 - Changelog ########################################################################################

### Added
- Base Creator significantly expanded:
  - Improved template-based room setup
  - Added `ids_info` preview
  - Integrated NPC customization
- Improved and expanded object-group dialog and rumor workflow.
- Extended resolution handling with localized display (DE/EN).
- Updated help and translations to match current UI/workflows:
  - Renamed to **FLAtlas Settings**
  - Added documentation for NPC/Rumor/News editors in main navigation
  - Added notes for trade-route validation and base-template behavior

### Changed
- Mod Manager significantly reworked:
  - New UI structure
  - Consolidated path configuration
  - Optional launch-resolution opt-in
  - Better activation feedback (loading/status)
- Improved UI and creation workflows:
  - Reworked planet/wreck/buoy creation
  - Clearer and more robust edit states
- Hardened archetype handling (safe fallbacks + cleanup).
- Extended base creation/edit flow:
  - Virtual-room hotspots are preserved during navigation normalization
  - Fixture-based NPC room assignment is prioritized (prevents wrong room inference from `GF_NPC.room`)

### Fixed
- Stabilized window startup/launcher behavior (including resolution/startup flow).
- Fixed widescreen in-game patches and resolution selection.
- Fixed patrol/exclusion zone orientation:
  - Exclusion cylinder rotation aligned to patrol orientation
  - Patrol zone rotation now matches drawn axis
  - 3D patrol/path cylinders are now consistent with 2D view
- Fixed Linux- and Mod-Manager-specific issues.
- Stabilized base creation/editing:
  - Virtual-room/dealer hotspots in room INIs stay intact
  - Reduced duplicate/misplaced vendor NPCs caused by template inference

### Commits in this range
- `e958402` Base Creation Fix
- `033c9e8` Fix Edit Base Dialog
- `570b163` Fix Base Creator virtual-room hotspot handling and Deck NPC room casing
- `d52cef5` refactor: consolidate and update roadmap and known issues documentation
- `07bb4f9` feat(base-creator): overhaul template-based room setup, ids_info preview and NPC customization
- `e5a06ab` Fix exclusion cylinder placement rotation to match patrol-zone orientation
- `4cc29a9` Fix patrol zone creation rotation to match drawn axis
- `272076e` Fix 3D patrol/path cylinder orientation to match 2D view exactly
- `00ce145` Improve editor UX: object groups dialog, rumor workflow, and Linux/mod-manager fixes
- `9ac1e73` feat(ui): improve editing-state actions and creation workflows (planet/wreck/buoy)
- `f542dc0` refactor(mod-manager): redesign UI + move path config + add launch resolution opt-in + activation loading feedback
- `4b2cbf8` fix(ui,launcher): harden window startup + add selectable launch resolution and widescreen ingame patches
- `e09d13e` feat(main_window, translations): update resolution handling and add localization for resolution label
- `7fcd9cf` feat(main_window): enhance archetype handling with safe fallbacks and cleanup

## v0.6.2.1 -> 0.6.2.2 Changelog ##############################################################################

### Changed
- General preparation and consolidation for `v0.6.2.2`.
- Stabilized editor workflows.
- Hardened IDS tooling.
- Improved Mod Manager UX.
- Reworked cross-platform launch flow (Windows/Linux).

### Fixed
- Stability and compatibility fixes in Mod Manager, IDS, and system workflows.
- Improved Windows compatibility for `0.6.2.2` workflows.

### Internal
- Merged `development` into release state.

### Commits in this range
- `759ead4` preparation for 0.6.2.2 update
- `bda8e73` stabilize editor workflows, IDS tooling, Mod Manager UX, and cross-platform launch flow
- `bca2213` fix(mod-manager, ids, systems): stabilize 0.6.2.2 workflows and Windows compatibility
- `2af4109` Merge branch 'development'


## ROADMAP - TODOs ##########################################################################################
- Pop-out 3D editor with sync options between 2D and 3D view
- System info-card creator should follow current standards
- Update README.md, help pages, and translations
- Better base editor
- Game translator: translate FL from English to German
- Planet rings
- Missions editor
- Commodity creator/modifier
- Equipment Creator / Modifier
- Ship (ini) Creator / Modifier
- Editing of arbitrary INI files with an integrated editor

## TODOs for Later (do not implement yet) #########################################################
- View 3D objects in editor
- Use 3D objects in 3D editor for better visualization
