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


## v0.6.4 -> v0.6.5 - Changelog ########################################################################################

### Added
- Added a dedicated `Tools` menu with tab-based access to:
  - `News Editor`
  - `NPC Editor`
  - `Rumor Editor`
  - `3D Model Manager`
- Added the integrated `3D Model Manager`:
  - embedded live 3D preview
  - search and grouped model listing
  - source/model deep links
  - details tab for archetype/model metadata
- Added persistent top-view icon workflows:
  - automatic cached 2D icons for vanilla content
  - optional per-mod icon generation in Mod Settings
  - prebuild action for mod icon cache
- Added a dedicated activity stream in the status area:
  - live status messages
  - `Activity` tab with categories and search/filter
  - background 3D queue/decode activity reporting
- Added system-background support for Freelancer starspheres in 3D:
  - `basic_stars`
  - `complex_stars`
  - `nebulae` handling with safer fallback behavior
- Added a separate `Free Cam` mode for the 3D system viewer with its own controls.
- Added project plans for 3D streaming/performance work:
  - `PROJECT_PLAN_3D_PERFORMANCE.md`
  - `PROJECT_PLAN_3D_BACKGROUND_STREAMING.md`

### Changed
- The 3D system viewer now uses a much smoother background-streaming path for native models:
  - stricter camera-idle scheduling
  - visibility stability window before loading
  - stale payload cancellation
  - prepared worker payloads
  - tiered native preview policy
  - duplicate-build staggering and cached reattach prioritization
  - per-tick finalize limits and batch time budget
- The 3D system viewer was simplified for performance:
  - no expensive material/texturing path for native system-view objects
  - coarse/system-friendly native preview policy
  - stronger placeholder usage for distant/low-priority objects
- The 2D editor now uses more realistic object sizing:
  - planets and suns render with world-size-based radius
  - regular objects can derive 2D size from native model bounds
  - tiny objects keep a minimum clickable size
- Search/filter fields across the app now use debounced execution and share a configurable global search delay.
- The startup/session workflow was tightened:
  - restoring open tabs is now optional and disabled by default
  - startup/load progress texts are more explicit about the current phase
- The visual identity was refreshed:
  - new app icon set
  - updated splash-screen artwork variants

### Fixed
- Fixed many native 3D/CMP preview issues across preview, model manager, and system view:
  - better Crossfire/native decode handling
  - fixed multiple family-split/FVF/stride cases
  - corrected several transform/path mismatch cases
  - restored compatibility after CMP viewer regressions by rolling back to the last good decoder baseline when needed
- Fixed system-view stability/performance issues:
  - reduced hangs when opening large systems
  - reduced placeholder/native flicker
  - reduced freezes on station preview open
  - prevented stale native preview batches from reattaching late
- Fixed multiple system/universe workflow issues:
  - active sector no longer falls back to `Sirius` unexpectedly on reload
  - opening a system INI from the system view now works even when the INI tree does not contain the item yet
  - switching the editing mod closes open tabs to prevent cross-mod inconsistencies
- Fixed 3D UI issues:
  - hidden legacy main toolbar can no longer appear outside the viewport
  - 3D sliders/layout were moved and reworked repeatedly to avoid overlap
  - wireframe visibility in the model manager now updates correctly for incrementally attached geometry
- Fixed activity/status transparency:
  - native scene runtime events now show meaningful queue/decode messages in the activity log

### Commits in this range
- `7117ee0` perf: smooth native 3d preview scheduling
- `8950e65` perf: add prepared native scene payloads
- `a8c4384` perf: drop stale native preview build payloads
- `2b594ec` perf: prioritize lighter prepared native payloads
- `9b36bdf` perf: add tiered native preview policy
- `b74d43a` perf: instrument native scene streaming activity
- `30182e1` perf: stagger duplicate native preview builds
- `44f8f16` perf: add native preview batch time budget
- `728dcd7` perf: prioritize cached native preview reattach


## v0.6.3 -> v0.6.4 - Changelog ########################################################################################

### Added
- Native 3D object viewer and CMP inspection were expanded into a much more capable workflow:
  - structured native CMP decode diagnostics and mesh-family analysis
  - texture/material handling in `MeshPreviewDialog`
  - jumpgate/jump object preview support
  - mesh visibility toggles, better contrast controls, and optional back-face culling disable
  - dedicated 3D viewer delivery/documentation in `3dobject_viewer_doc.md`
- Trade Routes were expanded into a real balancing and workflow tool:
  - dedicated market analysis dialog
  - cargo-based net profit and profit-per-jump analysis
  - local/inter-system route typing and stronger system filtering
  - direct deep-links into `goods.ini`, `market_commodities.ini`, source/target systems, and source/target bases
  - market editor/analysis actions directly in the trade-route sidebar
  - market editor previews for route impact and source/sink handling
- INI Editor was expanded into a much stronger modding workspace:
  - source-aware tree labels for `mod`, `vanilla`, and `install`
  - direct counterpart navigation between overlay and fallback files
  - file compare dialog with section-aware summary
  - `Find usages` across mod and vanilla roots
  - file status summary and compact one-line editor status bar
  - section inspector for structured key/value editing
  - basic validation hints for duplicate identifiers and empty values
- Mod Manager gained EXE version management and dedicated Mod Settings runtime/page support for EXE offsets.
- Added a project-local `launch.cmd` for starting FLAtlas directly from the repo checkout.

### Changed
- Native scene/runtime handling for 3D preview and system integration was refactored further:
  - more detailed debug-state snapshots in `MainWindow` and `view_3d`
  - clearer exposure of native preview render/detail state in the UI
  - more robust CMP loader architecture with family-aware metadata and structured decode plans
- Trade-route internals were decoupled further:
  - runtime helpers moved out of `main_window.py`
  - route payload/filter construction is now more modular and testable
- INI Editor workflow was tightened around the editor itself:
  - status information is now compressed into a single summary line instead of a large multi-row info block
  - compare, validation, navigation, and structured editing are now grouped around the main editing path
- Release/build hygiene was tightened further:
  - `.gitignore` now also excludes the dedicated release virtual environments and architecture-specific build output folders

### Fixed
- Fixed CMP/native preview issues:
  - corrected CMP orientation handling
  - fixed CMP transform hints so part names/translations are shown correctly
  - improved handling of relative UTF offsets and legacy `VMeshRef` layouts
- Fixed trade-route correctness issues:
  - routes with implicit base-price buyers are now included correctly
  - weaker but still valid local/system-filtered routes are no longer dropped too early
  - unreachable routes are no longer shown as fake 1-jump connections
  - trade-route navigation hides non-implemented `_miner` leftovers and other invalid destinations more reliably
- Fixed INI editor ergonomics for heavy editing sessions by reducing header noise and keeping detailed path data in tooltips instead of a wide info panel.

### Commits in this range
- `89af662` Bump version to v0.6.4, enhance native scene runtime with debug event tracking, and add debug state snapshot functionality in main window and view 3D
- `57aa9fe` Refactor native scene handling in main window and view 3D; enhance debug state snapshot and sync functionality
- `1c78cfc` Improve 3D viewer native scene runtime diagnostics
- `8e35213` Improve real CMP part matching diagnostics
- `455f0b4` Add native CMP decode diagnostics
- `d9443e7` Add jumpgate support in MeshPreviewDialog and update model file handling in MainWindow
- `e848c43` Handle relative UTF data offsets in CMP loader
- `3889468` Prefer VMS stride hints in preview layout guess
- `aa8eaa3` Classify real CMP VMeshData block patterns
- `0cc56b1` Resolve real CMP VMesh refs via Freelancer CRC
- `e1102f5` Group related CMP VMeshData blocks into families
- `2de06bb` Propagate CMP VMesh family context into preview metadata
- `bca6875` Add family-aware CMP preview layout metadata
- `d8b9ae7` Use stream blocks for family-aware CMP layout guesses
- `1be8077` Add family-aware CMP decode diagnostics
- `4832d68` Add combined family fit diagnostics for CMP decode
- `a055404` Detect CMP header end-vertex semantics
- `64b116b` Name CMP mesh header end-range semantics
- `7dc6d4d` Match CMP mesh header group end semantics
- `86aa548` Build structured CMP mesh header records
- `6006f6e` Mark structured CMP decode targets
- `ebf8074` Build initial structured CMP decode plans
- `79beafd` Use structured decode plans in native preview geometry
- `d9aa4eb` Refine 3D viewer plan for first visible Freelancer models
- `36c0329` Detail 3D viewer delivery path for Freelancer files
- `5aa33d8` Add 3D viewer reference acceptance and blocker criteria
- `b888086` Decode first real jump_gatel Level4 preview geometry
- `d51f803` Decode first real jump_gatel Level3 family geometry
- `29027f5` Expose native preview render path in UI
- `dd7f4d3` Expose selected native detail state in main window snapshot
- `9f9e875` Move 3D preview details into separate tab
- `26fc38d` Constrain 3D preview dialog to screen height
- `fc795d0` Refactor tests for path utilities and add new image assets
- `7de6e9f` Enhance vmesh reference parsing to support legacy layout and infer vertex/index counts
- `a619e7c` 3d objekte in system view
- `ed6119b` 3d model debug
- `be0fdbe` Add EXE version management features to Mod Manager
- `7e530d6` feat: Add mod settings page and runtime handling for EXE offsets
- `c92ffc9` feat: Enhance trade route filtering and UI
- `fa4ba2b` fix: Correct model orientation for CMP files in 3D viewer
- `a41052f` feat: Add CMP up correction handling and related tests
- `e8d9b88` Refactor and enhance CMP loader and mesh data handling
- `0eb6fe2` feat: Add comprehensive documentation for the 3D Object Viewer, covering architecture, data formats, and algorithms
- `e85f1af` fix: Update CMP transform hints to correctly reflect part names and translations
- `ed2b0e5` feat: Enhance MeshPreviewDialog with mesh visibility toggle and improve color settings for better contrast
- `0a3dcf6` feat: Implement material library handling and enhance MeshPreviewDialog with texture support
- `b327dfc` feat: Implement back-face culling disable functionality for Qt3D materials in MeshPreviewDialog
- `536a068` Add trade route market analysis dialog
- `e78ea98` Add goods.ini deep link for trade routes
- `b225e85` Add cargo-based net profit to trade routes
- `da7c209` Add profit-per-jump route analysis filters
- `b672185` Extract trade route runtime helpers
- `11d7275` Improve trade route market editor previews
- `eee790b` Add trade route base deep links
- `e46fa9b` Add market section deep links for trade routes
- `63cad2f` Account for implicit base-price trade routes
- `7ec408d` Keep implicit trade route pairs in route scan
- `9c7c403` Drop unreachable trade routes from analysis
- `ad9c2bc` Add market editor and analysis buttons to trade route sidebar
- `a9d85fd` Add launch script for running FLAtlas application
- `aea017a` Improve INI editor modding workflow
- `6d6ff98` Add section-aware INI comparison
- `5cc37fe` Add INI editor find usages search
- `b4d0157` Add INI editor file status panel
- `58c3b71` Add INI section inspector editor
- `47bdaa7` Add INI editor validation hints
- `a7e7a1a` Refactor INI editor status panel to use summary label and update tooltip information
- `2254997` Update .gitignore to include additional virtual environments and build artifacts


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
