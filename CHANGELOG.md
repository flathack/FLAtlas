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
- Neuer Mod Button ist ausgegraut, obwohl Mod Repo existiert.


## v0.6.2.4 -> v0.6.3 - Changelog ########################################################################################

### Added
- Config import/export in the `File` menu for moving FL Atlas settings between installations.
- Dedicated packaged Windows updater launcher (`FLAtlasUpdater.exe`) for self-update installs and restart handling.
- Startup splash progress so the main window appears only after startup content is ready.
- Mod Manager was expanded into an installation-aware workflow:
  - Direct Mods can now be marked as the target installation directly in the Mod Manager
  - Separate savegame profiles are switched per installation/mod
  - Added quick access to the global savegame folder
- Repo mods now support FLMM-style `script.xml` activation inside FL Atlas:
  - tolerant parser for legacy FLMM scripts
  - supports `append`, `sectionappend`, `sectionreplace`, `filereplace`, and `renamefile`
  - supports `options default`, `stringdata`, `xmldata`, `GENERATESTRRES`, and `GENERATEXMLRES`
- Added a dedicated `INI Editor` main tab:
  - file tree for the active context on the left
  - INI editor with line numbers and syntax highlighting in the center
  - section navigator on the right for direct jumps to `[Section]` blocks

### Changed
- Main navigation was reworked into a real top tab bar:
  - old duplicate main-navigation buttons were removed
  - fixed core tabs now sit in the header area
  - savegame editor and settings stay available as separate actions on the right
- Long-running data views now use the shared loading runtime:
  - Name & Info Editor, Trade Routes, Universe and System loading paths were moved to shared async loading with a persistent top loading bar
  - larger list/table renders now fill incrementally to keep the UI responsive
- INI Editor tree loading was changed to lazy expansion, so large `DATA` folder trees no longer block the initial editor open.
- Packaged Windows update flow now asks first and only installs after explicit confirmation instead of silently starting the update.
- System-tab handling was expanded into a document-oriented workflow:
  - system tabs now preserve in-memory state instead of relying only on file reloads
  - 2D/3D mode, 2D zoom/transform, 3D camera, selection, pending placement modes, undo/history and change log are now restored per system tab
  - tab sessions are stored and restored on the next program start where possible
- Workspace layout control was centralized:
  - system, universe, trade routes, name editor, mod manager, settings, welcome, NPC, rumor and news views now switch shared UI regions through a common workspace-layout path
- Tab workflow was expanded further:
  - system tabs now also preserve visible editor/panel state such as editor text, cursor position, quick-editor fields and zone-link editors
  - tabs can now be reordered and their order is restored with the saved tab session
  - system tabs can be opened in a separate FL Atlas window via `Open In New Window`
  - separate system windows are isolated by design:
    - no drag-and-drop detach from the tab bar
    - no shared live state between windows
    - isolated system windows do not load or overwrite the normal tab session
- Sidebar/workspace routing was tightened:
  - the universe browser is intended for the `Universe` tab only
  - system tabs restore their own editor sidebar instead of the global browser
- Mod Manager navigation and workflow were reworked further:
  - `Mod Manager` now opens first on startup and is placed first in the main navigation
  - normal mods/installations and direct mods are visually separated in the table
  - mod-specific sidebar options now show a dedicated header for the selected entry
  - right-click activation action is now the first context-menu entry for normal mods
- Launch configuration was refined:
  - added aspect-ratio selector for resolution filtering
  - camera FOV values now follow the documented `WinCamera`/`Other` presets for `4:3`, `16:10`, and `16:9`
- Mod activation/deactivation UX was improved:
  - progress dialog now shows percentages
  - long file paths are shortened in the dialog with middle elision
  - multiple compatible mods can now stay active at the same time
  - FLMM-based repo mods are marked with `FLMM - <name>` in the list
- Mod Manager compatibility feedback was refined:
  - hard conflicts stay red and block activation
  - partial FLMM overlaps are now shown in yellow as `Partially compatible`
  - mod info and table tooltips now explain overlap/conflict context in more detail
- Data lookup for utility views was refined:
  - `Trade Routes` and `Name & Info Editor` now use the effective data/game root instead of only the raw mod source path where required
- Internal architecture was decoupled further after the initial feature work:
  - large `main_window.py`, `dialogs.py`, `view_3d.py`, and `flight_mode.py` responsibilities were split into focused helper modules
  - dialog payload/state logic now lives in dedicated pure-logic modules instead of being mixed into widget classes
  - shared INI/text write paths were unified behind reusable helpers
- Regression coverage was expanded from a small baseline into a broad repo-level suite:
  - smoke coverage now includes startup/navigation flows, main editor views, and key dialogs
  - pure-logic tests now cover helper modules for writes, infocards, mod manager, base dialogs, 3D view, and flight mode

### Fixed
- Fixed `ids_resource_runtime.py` calling a non-existent `MainWindow._ci_find` helper during startup.
- Fixed Name & Info Editor usage lists after the incremental table rendering refactor so `Usage of this ids_name` / `ids_info` refresh immediately again.
- Fixed Universe/System in-game-name refresh after async loading so name display mode is applied consistently.
- Fixed delayed in-game/nickname mode refresh that previously required a tab switch before the labels updated.
- Fixed Universe 2D panning to use exact scene-coordinate deltas instead of scale-dependent translate math.
- Fixed IDS toolchain auto-detection on Windows by checking additional LLVM install paths.
- Fixed Savegame Editor updater crash caused by missing `time` import.
- Fixed current-tab fallback on close so views without valid Freelancer context no longer try to jump into `Universe`; the Mod Manager is used as safe fallback.
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
- Mod Manager and launcher stability fixes:
  - `New Mod` is blocked until initial setup is complete and no longer falls back to the FLAtlas project folder
  - duplicate `Direct Mod` installations are prevented via normalized path comparison
  - disabling `Apply resolution on launch` now restores default `cameras.ini` FOV values
  - patrol/path zone rotations in `2D` and `3D` were corrected again after the regression
  - exclusion cylinder zones in the `2D` editor were realigned to the expected legacy yaw behavior
  - FLMM option scripts now prompt the user before activation instead of always using defaults
  - incompatible mods are now detected more precisely for FLMM scripts by file, section, nickname, and key scope
  - `Launch FL` now starts the active/target `Direct Mod` installation instead of incorrectly trying to launch normal repo mods
  - FLMM-based INI patching no longer injects excessive blank lines from XML source blocks into target INI files
  - deactivating a mod now closes open system tabs under the affected installation root before teardown
- Tab/workspace stability fixes:
  - switching between system tabs no longer loses unsaved in-memory editor state
  - switching between system tabs no longer drops unsaved right-side editor text or visible zone helper editors
  - closing non-active system tabs now supports document-based `Save / Discard / Cancel`
  - tab fallback selection after close is now more consistent and no longer always jumps back to the mod manager
  - documentation/QA references now point to the real repository artifacts and current regression baseline
  - old global undo persistence from config was removed so stale undo stacks are not revived across unrelated tab/document contexts
  - fixed host startup for the first system-editor host so wallpaper/theme application no longer crashes before `self.view` exists
  - fixed host/tab close lifecycle so page switches no longer access already deleted `SystemView` objects
  - removed remaining unsafe `mouse_moved.disconnect(...)` paths that could produce runtime warnings during tab/view transitions
  - dock-ring preview signal lifecycle was stabilized to avoid repeated disconnect warnings during placement/tab transitions
  - scene wallpaper updates now apply consistently to all existing system hosts instead of only the active one
  - main-tab routing now reopens `Trade Routes`, `Name & Info Editor`, and related pages through their full load paths instead of only switching the central widget
- Base / IDS toolchain fixes:
  - temporary RC files for generated resource DLLs now use an explicit UTF-8 code page, preventing `STRINGTABLE` compiler failures on non-ASCII characters during base creation

### Commits in this range
- `pending` release range includes the integrated refactor/build state currently packaged as `v0.6.3`

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
