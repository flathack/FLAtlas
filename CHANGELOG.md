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


## v0.7.1 -> v0.7.2 - Changelog ########################################################################################

### Changed
- Prepared the source tree for the next `v0.7.2` development cycle.

### Commits in this range
- Pending development changes for `v0.7.2`


## v0.7.0 -> v0.7.1 - Changelog ########################################################################################

### Added
- Added Mod Manager export for changed Freelancer files as ZIP or FLMOD packages.
- Added export scanning with progress feedback, changed-file listing, built-in exclusions, and manual per-file exclusions.
- Added editable export metadata fields plus direct `script.xml` editing for FLMOD packages.
- Added live zone rotation in the 2D system editor with mouse movement, mouse wheel rotation, and left-click confirmation.
- Added localized FLAtlas V2 release notice support so FLAtlas V1 can inform users when a newer V2 release is available.
- Added internationalized preview and room-editor UI labels.

### Changed
- Improved base creation with a visible progress dialog and step-specific status messages.
- Improved 2D system-view readability for dense object groups through better clustering and label behavior.
- Improved room preview and room template handling in the base creation workflow.
- Improved model preview loading with async loading and normalization-aware model handling.

### Fixed
- Fixed copied base NPC appearance so copied NPCs keep their source look. Solves `#64`.
- Fixed copied base NPC placement so bartenders, dealers, warehouse NPCs, and bar guests stay in the correct room / role. Solves `#63`.
- Fixed empty room-navigation areas on newly created bases.
- Fixed terminal popups during base creation by hiding resource-tool subprocess windows. Solves `#68`.
- Fixed ring-zone handling in the 3D system editor so rings are no longer flattened to `0,0,0`. Solves `#67`.
- Fixed NavMapScale 8x8 grid half-extent calculation. Solves `#72`.
- Fixed and completed the right-click room-editor workflow for bases. Solves `#59`.
- Fixed zone rotation rendering so zones update live in the 2D view and keep their saved orientation. Solves `#61`.

### Resolved Issues
- `#59` Right-click base room editor workflow
- `#60` Export Mod function
- `#61` Rotate zone function
- `#63` NPC location issues when creating a base and using copy NPCs
- `#64` Base Creation Function: copy NPCs with base creation will use generic NPC models
- `#65` 2D System View readability with many nearby objects
- `#67` Rings not displayed correctly in 3D System Editor
- `#68` Progress bar for creating bases
- `#72` 8x8 grid not correct
- `#73` FL Atlas V2 Info

### Commits in this range
- `8a04721` Add FLAtlas.spec for PyInstaller configuration
- `04c94f9` Bump version to 0.7.1
- `1e48fbe` Fix base room editor workflow
- `bac0c38` Enhance room template handling with direct room switch conversion
- `3d3b764` Implement room preview functionality in base creation dialog
- `3b011da` Add splitter to BaseCreationDialog for improved layout management
- `e3ed92c` Implement async loading for model path previews and enhance room activation UI
- `d497929` Add normalization option to model loading functions and implement rotation multiplication
- `6b0abdf` Merge branch 'fix-room-editor-tab'
- `980efb0` Fixes #59
- `5a8a614` Add internationalization support for preview and room editor UI elements
- `3504f03` Tidy up
- `f65347a` Correct NavMapScale grid half-extent (closes #72)
- `3e9cc0f` Merge branch 'fix/issue-72-navmapscale-grid' (closes #72)
- `083065b` Implement ring zone data handling in planet ring resolver
- `5c92610` Fix copied base NPC appearance
- `655a57a` Fix base template room NPC copy
- `43d7785` Improve 2D system view clustering
- `7f4863c` Improve base creation progress
- `6fab461` Add FLAtlas V2 release notice
- `97c9527` Implement zone rotation interaction
- `6720bc5` Add mod export packaging


## v0.6.9 -> v0.7.0 - Changelog ########################################################################################

### Added
- Added editable `ids_info` text support directly to the 2D system-view object editor, so scene objects can now update both `ids_name` and infocard text from the same dialog.
- Added editable `ids_info` text support to planet creation, including automatic template text lookup from existing planets with the same archetype.
- Added a much stronger `Time Machine` workflow in the `File Explorer`:
  - side-by-side and inline diff modes
  - word-level diff highlighting
  - minimap strips with clearly marked changed regions
  - visible revision timeline segmentation with date display
  - compact GitHub-style diff focus on changed sections only
- Added a floating `Clipboard Collector` for the `File Explorer`:
  - copied editor text is automatically collected through normal `Copy` workflows
  - selected explorer paths can also be collected
  - collector entries can be removed, pasted back into the editor, or cleared
  - the collector window stays non-modal, always-on-top, and fades when it loses focus
- Added section-aware editor actions in the `File Explorer`:
  - `Select section`
  - `Copy section`
  - matching section actions in the right-side section list
- Added embedded 3D previews to creation workflows:
  - object creation
  - wreck / depot / weapon-platform creation
  - base creation with larger right-side preview area
- Added `FL Atlas Settings` improvements for tool management:
  - new `Pinned Tools` tab for permanent main-tab control
  - renamed `Editors` settings tab to `FL Atlas Suite Apps`
  - dedicated `FL Atlas Suite Apps` menu
  - companion-app launch/config rows for `FL Atlas Launcher` and `FL-Lingo`
  - one-row web-tool launcher list with internet-marked entries

### Changed
- Renamed core navigation captions toward the current product terminology, especially around `File Explorer` and `IDS Editor`.
- Reworked the 2D system-view right sidebar into a cleaner two-column action layout:
  - `Creation` now sits on the left
  - `Editing` now sits on the right
  - the selected-object dropdown and `Jump` button now live below the system settings button
  - spacing and top alignment were tightened so both columns stay visually consistent
- Reworked the base edit flow into a true edit-mode dialog:
  - `General` and `Base Loadout` tabs
  - `ids_info` as editable text field
  - base and object nickname fields aligned side by side
  - archetype locked during edit mode
  - creation-only options removed from edit mode
- Reworked object and base creation dialogs so 3D previews have much more usable space and are easier to read.
- Refined the `FL Atlas Suite Apps` settings page further:
  - web-app buttons now appear in one row
  - external suite apps use direct `Install / Update` actions like the savegame workflow
  - self-download for `FL Atlas` itself was removed from suite settings
- Removed the `Savegame Editor` button from the main navigation; it remains reachable via menu/settings instead.
- Made the right sidebar in the 2D system tab more compact.

### Fixed
- Fixed generated patrol-zone defaults so path-based patrol encounters use safer Freelancer-style settings. Solves `#4`.
- Fixed starsphere background option discovery so newly added `solar\starsphere` assets appear in FL Atlas without needing prior system references. Solves `#6`.
- Fixed old user translation files so outdated saved labels like `INI Editor` no longer override newer bundled tab names such as `File Explorer`.
- Fixed planetary base link normalization so planets keep `base = ...` while docking fixtures and rings keep `dock_with = ...` without cross-link corruption. Solves `#12`.
- Fixed Base Builder availability so unsupported planet and docking-ring roots no longer expose the workflow. Solves `#13`.
- Fixed new-system creation flow so a freshly created system opens in its own tab instead of hijacking the Universe tab. Solves `#16`.
- Fixed planet-creation defaults so deathzone radius and atmosphere range are prefilled from the detected planet size when possible. Solves `#17`.
- Fixed docking-ring and planetary-base creation defaults, nickname scaffolding, and template-copy normalization. Solves `#19`.
- Fixed the 2D object editor raw-text view so `[Object]` / `[Zone]` section headers are visible and still safe to apply back. Solves `#20`.
- Fixed 2D object editing so `ids_info` text is no longer missing while `ids_name` text is editable.
- Fixed hover rendering artifacts in the 2D system and universe views, especially while zooming. Solves `#25`.
- Fixed the 2D system-view action sidebar so cramped creation/edit controls are no longer squeezed into unusable vertical layouts on small windows.
- Fixed center-tab dragging so tabs can be moved across the full tab bar without only stepping one neighbor at a time. Solves `#28`.
- Fixed Linux-sensitive `+-180°` rotation/orientation edge cases in 3D previews and 2D system rendering without regressing Windows behavior. Solves `#32`.
- Fixed system-tab view restoration so switching tabs no longer resets the saved 2D zoom/pan or 3D camera state. Solves `#40`.
- Fixed the `BaseCreationDialog` preview initialization crash caused by `room_table` access before full widget setup.
- Fixed the context-menu crash in the INI editor where `_ini_editor_current_section_block_number` was called with the wrong signature. Solves `#46`.
- Fixed `Ctrl+C`, toolbar `Copy`, and context-menu `Copy` in the `File Explorer` so copied text reliably lands in the `Clipboard Collector`. Solves `#11`.
- Fixed section visibility in the Time Machine diff so whole changed INI sections remain visible instead of collapsing away important context. Solves `#10`.
- Fixed base-edit entry flow so the productive base editor now opens the correct edit-mode dialog instead of a mismatched creation-state variant. Solves `#37`.
- Fixed settings/menu tool routing so main editor tools and pinned-tab visibility are managed consistently from one place. Solves `#50`.
- Fixed Free Cam strafing in the 3D system view so `A` moves left and `D` moves right again. Solves `#52`.
- Fixed tradelane repositioning so resetting route endpoints recomputes the ring count from the preserved spacing instead of keeping an inconsistent old count. Solves `#54`.

### Resolved Issues
- `#4` Patrol-zone defaults for path-based encounters
- `#6` New starsphere files missing from background options
- `#10` Improve Time Machine diff display and navigation
- `#11` Add Clipboard Collector to the File Editor
- `#12` Wrong `dock_with` links on planetary base edits
- `#13` Base Builder should not be usable on planets / docking rings
- `#16` New systems should open as a separate tab
- `#17` Prefill planet deathzone and atmosphere from planet size
- `#19` Docking-ring base creation has several default-value issues
- `#20` Show `[Zone]` / `[Object]` headers in the 2D object editor
- `#23` Add object previews to creation dialogs
- `#25` Hover artifacts in 2D system and universe views
- `#26` 2D system creation buttons squeezed together on small windows
- `#27` Create planet `ids_info` directly in the dialog
- `#28` Dragging tabs only works one neighbor at a time
- `#32` Linux 3D preview orientation wrong on some child parts
- `#35` 2D object editing should also offer `ids_info` editing
- `#36` Some tab names do not update for users with old configs
- `#37` Rework the base edit dialog flow
- `#40` Preserve system-tab zoom/camera state
- `#46` Add section actions in the File Editor
- `#50` Main tab management in settings
- `#52` Free Cam `A`/`D` mismatch
- `#54` Recompute tradelane ring count after endpoint reset

### Commits in this range
- `f76f688` Fix wrong `dock_with` links on planetary base edits
- `1b79da2` Fix patrol zone defaults for path-based encounters
- `4a0b2f9` Fix starsphere background options not showing new files
- `d53d550` Prefill planet deathzone and atmosphere from planet size
- `5504adb` Disable Base Builder for planets and docking rings
- `b648cfe` Open newly created systems in a separate tab
- `48583ed` Fix docking ring creation workflow and planetary base normalization
- `6e785dc` Show INI section headers in 2D object editor
- `5dd7506` Fix hover artifacts in 2D system and universe views
- `df25c7d` Fix center tab dragging and suppress reloads while reordering
- `965d8af` Add editable planet ids_info creation in solar dialog
- `c9953ff` Add ids_info text editing to 2D object editor
- `6083677` Prefer bundled tab labels for legacy user translations
- `e02ac26` Refine 2D system sidebar button layout
- `eafb32e` Fix #40 preserve system tab zoom state
- `622d542` Add object previews to creation dialogs
- `99c2fc9` Add clipboard collector to file editor
- `ae13368` Fix ±180° gimbal-lock rotation for 3D preview and 2D system view
- `28200f9` Merge pull request #47 from flathack/fix-issue-10-timemachine-diff
- `b9dc249` Merge pull request #48 from flathack/fix-issue-46-file-editor-section-actions
- `e7ed97b` Merge pull request #49 from flathack/fix-issue-37-base-edit-dialog
- `a0a0419` Merge pull request #51 from flathack/fix-issue-50-main-tab-management
- `1614f1f` Merge pull request #56 from flathack/fix-issue-52-free-cam-strafe
- `027f9a4` Merge pull request #57 from flathack/fix-issue-54-tradelane-ring-count


## v0.6.8 -> v0.6.9 - Changelog ########################################################################################

### Added
- Added a recycle-bin workflow for the `File Explorer`:
  - deleted files now move into `.flatlas/history/trash` instead of being removed immediately
  - deleted files can be restored from a dedicated trash dialog in the explorer toolbar
- Expanded `Nebula` zone creation with more Freelancer-authentic zone options:
  - `visit`
  - `spacedust`
  - `spacedust_maxparticles`
  - `interference`
  - `property_flags`
  - `property_fog_color`
- Expanded `Asteroid Field` zone creation with more Freelancer-authentic zone options:
  - `property_flags`
  - `visit`
  - `sort`
  - `spacedust`
  - `spacedust_maxparticles`
  - `comment`
- Added Base Builder 3D viewport improvements:
  - color-coded XYZ axis gizmo at the grid corner with labeled arrows (red X, green Y, blue Z)
  - large yellow "N" north marker outside the grid at the −Z edge for orientation
  - color-coded Move/Rot/Axis buttons matching gizmo colors (red X, green Y, blue Z)
  - active-state highlighting for Mode buttons (Nav/Move/Rot) and Axis buttons (X/Y/Z)
  - live rotation display (X/Y/Z) for the currently selected object
  - step-size spin box (1–360°, default 15°) for precision stepping via +/− buttons
  - Reset Camera button and Zoom slider moved into the main toolbar row for quicker access
  - vertical separators between transform groups and mode groups for clearer visual structure
- Added minimal 3D part preview mode for the Base Builder (mesh + wireframe only, no tabs or details)
- Added parent-child co-movement: moving a parent base object now moves all linked children in the 2D editor
- Added child-object interactivity lockdown: child objects with a parent are non-interactive in the 2D editor; deleting a parent shows a confirmation dialog for its children
- Added Faction Editor – inline IDS editing: name, short name, and info text can now be edited directly in the General tab without detour through the IDS editor
- Added Faction Editor – reputation sliders: 3-column reputation table with interactive sliders per faction, color-coded by value
- Added Faction Editor – empathy rate sliders: editable empathy rate table with sliders (range −1.0 to 1.0), color-coded
- Added Faction Editor – reputation presets: one-click presets (All Friendly, All Neutral, All Hostile, Hostile to Lawful)
- Added Faction Editor – delete faction: removes a faction from all three INI files with optional reference replacement dialog
- Added Faction Editor – data integrity check: 18 validation checks across critical/warning/info severity levels covering missing references, out-of-range values, duplicate entries, and structural issues

### Changed
- The zone-creation dialog now gives asteroid and nebula fields clearer Freelancer-oriented presets and explanations instead of leaving important values implicit or hardcoded.
- Zone generation now writes substantially richer field-zone metadata for newly created nebulae and asteroid fields, bringing FL Atlas output much closer to real Freelancer system files.
- Removed the header text from the Base Builder dialog for a cleaner layout.
- Faction Editor reputation coloring now uses ±0.59 thresholds (was ±0.3) across graph, matrix, table, and sliders.

### Fixed
- Fixed ring-zone deletion so removing a ring also removes the corresponding `ring = ...` reference from its parent object, and undo restores both pieces together.
- Fixed File Explorer deletion so right-click delete is available again for actual file entries in the context menu.
- Fixed File Explorer delete behavior so deleted files are no longer lost immediately when using explorer delete actions.
- Fixed generated asteroid-field zones to no longer force incorrect defaults like `property_flags = 0` and `visit = 0` when field-specific values are intended.
- Fixed Qt3D render-thread crash in Base Builder caused by use-after-free during rapid scene rebuilds (debounced rebuilds, safe entity deletion, geometry validation guards).

### Commits in this range
- Pending local workspace changes for `0.6.9`


## v0.6.7 -> v0.6.8 - Changelog ########################################################################################

### Added
- Added a much stronger `Zone Population` editing workflow:
  - profile-aware defaults for field, patrol, lane, and generic zone styles
  - Freelancer-aware validation for encounter levels, chances, and faction weights
  - inline guidance/tooltips for encounter and faction values
  - sum checks so encounter chances and faction weights per encounter do not exceed `1.0`
- Added dynamic Discord invite resolution via the FL Atlas GitHub wiki so expired hardcoded invites no longer break the feedback flow.
- Added a local updater test path for packaged builds via `--test-updater-zip`, making it possible to test the full updater workflow against a local release ZIP.
- Added a much stronger `File Explorer` history workflow:
  - persistent file revision history stored under `.flatlas/history`
  - undo/redo that still works after closing and reopening a file
  - deleted-line browsing with direct line restore at the current cursor position
  - a `Time Machine` side-by-side view with slider-based revision browsing

### Changed
- Replaced the built-in help dialog with a direct link to the FL Atlas GitHub wiki.
- Reworked Windows self-update flow toward a dedicated updater-driven process:
  - FL Atlas now launches `FLAtlasUpdater.exe`
  - the updater is intended to handle download, extraction, file replacement, and restart
  - startup update checks are now scheduled after the app is fully shown, preventing update dialogs from appearing behind the splash screen
- Improved general editor workflows:
  - the file tree now preserves expansion state better
  - the File Editor gained a breadcrumb/path bar
  - `Archetype = ...` lines can open related 3D models and definition INIs directly
  - undo/redo in the File Explorer now uses FL Atlas revision history instead of only the short-lived in-memory editor stack
- Expanded base and NPC workflows:
  - copied base-template NPCs now preserve their source appearance
  - create/edit base workflows can randomize NPC head/body appearance
  - base child objects now use the correct parent nickname and `visit = 0`

### Fixed
- Fixed several Base Builder problems:
  - freshly added parts now refresh more reliably in preview
  - the newest moved part now keeps its position correctly on save/close
  - base child/parent persistence is now more consistent
- Fixed jump hole/gate persistence issues caused by dirty open system tabs overwriting newly created connections.
- Fixed 3D system viewer overlays so grids and zones remain visible instead of disappearing behind other objects.
- Fixed generated nebula/asteroid zone files and generated base room files to avoid excess blank lines.
- Fixed File Editor UX issues:
  - removed the modified-date column from the tree
  - tree collapse behavior on reload
- Fixed update UX problems:
  - clearer handling of invalid downloaded update archives
  - update checks no longer run too early during splash/startup

### Commits in this range
- `473a699` feat: update blogpost for v0.6.8 release with new features and improvements
- `4e982ff` feat: update application version to 0.6.8
- `be21231` feat: update application version to 0.6.1 and schedule startup update check
- `9560c2a` feat: enhance asset selection logic for Windows updates and add related tests
- `f99c665` feat: update help functionality to open GitHub Wiki instead of dialog
- `db637ed` feat: add Discord invite URL resolution and related tests
- `2167071` feat: enhance ZonePopulationDialog with profile detection and validation for population settings
- `a84a37c` feat: update ini editor to hide modified date column and adjust related tests
- `aff52de` feat: add randomization options for NPC appearance and preserve source appearance in room NPCs
- `476a142` feat: implement normalization for room ini text to collapse extra blank lines
- `d8cbb83` feat: enhance ini editor with path bar updates and breadcrumb navigation
- `864ec2f` feat: add normalization method for generated zone ini text to collapse extra blank lines
- `069647e` feat: refactor base builder logic to use parent_nickname and add visit entry
- `def0e8b` feat: add header launch button to mod manager and update translations
- `7bb4549` feat: add archetype handling in ini editor with extraction, opening, and related tests
- `7b43319` feat: implement tree state preservation for ini editor during reload
- `3eea0e8` feat: enhance reference overlay with always-on-top material state and add related tests
- `752dd9c` feat: add preservation of active system tab document on save and enhance related test
- `0c2cb1d` feat: implement synchronization of draft objects with real objects and enhance refresh logic for base builder dialog
- `aaf99bb` feat: refactor toolbar buttons for ini editor with compact design and add short translations
- `8f51150` feat: add project overview and version changelog to FORUM_POST_DE.md
- `0112628` feat: add status summary label to INI editor toolbar
- `6857dbf` chore: update application version to 0.6.8


## v0.6.6 -> v0.6.7 - Changelog ########################################################################################

### Added
- Added a dedicated `Character 3D Model Viewer` with assembled body-part preview support for Freelancer characters.
- Added an `8x8` grid layout option for both the 2D and 3D system views.
- Expanded the file/text editor into a much stronger Freelancer-focused workspace:
  - Explorer tabs for opening multiple files in parallel
  - direct open-in-new-tab actions from the file explorer
  - integrated line/file history stored under the mod-local `.flatlas` folder
  - path-aware right-click actions for opening linked files, folders, systems, and 3D models
  - IDS-aware line actions for resolving `ids_name` and `ids_info` values from DLL resources
  - inline minimap support for text files, similar to Visual Studio Code
  - file creation and deletion directly from the explorer
- Added a stronger `3D Base Builder` workflow with better base/child-object awareness and editing support.

### Changed
- The former `INI Editor` was renamed and evolved into a broader `File Explorer` / `Dateiexplorer` workflow.
- Text-editing workflows were pushed further toward a Visual-Studio-Code-like experience, but tailored to Freelancer modding:
  - direct tab-based editing
  - selected-text search actions from the context menu
  - linked navigation between related files and assets
  - better handling of counterpart files and direct file opening
- 3D model handling inside the File Explorer was expanded:
  - model files can open in dedicated tabs
  - `system.ini` files can open directly in the 2D System Viewer
  - model-path references inside text files can jump straight into 3D preview workflows
- The editor toolbar and general File Explorer UX were refined with larger buttons, light-theme support, more tab actions, and a resizable global-search results area.

### Fixed
- Improved line-history tracking so history follows the actual logical line instead of only the old line number after inserts/deletes.
- Reduced lag and responsiveness issues when working with large files such as `market_misc.ini`.
- Fixed multiple File Explorer and preview UX issues:
  - closable/resizable global search panel
  - 3D model preview layout issues in embedded tabs
  - clipped first characters in editor lines
  - startup crash from early `_ini_editor_current_file` access during initialization
- Fixed and polished many smaller alpha-stage issues across system editing, file workflows, previews, and base-building experimentation.

### Commits in this range
- `aa4c3b8` docs: prepare v0.6.7 release notes
- `c77cd5c` Add Character 3D Model Viewer functionality
- `94e0ef5` feat: enhance INI editor with new file creation and search functionality
- `19d13b3` Improve file explorer tabs, previews, and editor UX


## v0.6.5 -> v0.6.6 - Changelog ########################################################################################

### Added
- Added `Base Builder` dialog for assembling multi-part base compositions:
  - embedded live 3D preview with ground grid visualization
  - axis gizmo overlay and precision step controls for position/rotation
  - orbit drag functionality and enhanced camera controls
  - undo/history management for Add/Delete/Move/Rotate operations
- Added vertex normals support and texture configuration for improved 3D geometry rendering.
- Added `select_equip.ini` to default archetype files for broader equipment coverage.
- Added automatic context switching when creating a new repo mod.

### Changed
- System reference calculations now use `NavMapScale` division for more accurate 2D map framing.
- Zoom reference rect functionality added for tighter system-map fit behavior.
- Improved 2D object label visibility policy and selection handling for child objects.
- Improved UI layout and tooltip functionality for object combo in the main window.
- Refactored INI editor functionality and updated translations.
- Refactored code structure for improved readability and maintainability.
- Light/dark theme color alpha and pen widths now adapt based on the active mode.

### Fixed
- Fixed universe view zoom: zooming no longer causes all systems to disappear (zoom clamping was broken when scene zoom limits were disabled).
- Fixed string and XML resource handling in INI files and DLL generation.
- Fixed XML normalization: cleaned up unwanted characters.
- Fixed 3D placeholder size factors and fallback radii in System3DView.
- Fixed Qt3D native preview: `build_native_geometry_renderer` now provides normals to prevent `Failed to create input layout` on Windows D3D11.

### Commits in this range
- `5d571c8` Refactor INI editor functionality and update translations
- `8e04994` feat: Add axis gizmo overlay and precision step controls in BaseBuilderDialog
- `4471eda` feat: Adjust layout parameters in BaseBuilderDialog and MeshPreviewDialog
- `960fce7` feat: Implement ground grid visualization in BaseAssemblyPreviewView
- `83c697f` feat: Adjust theme color alpha and pen width based on light/dark mode
- `ce82e3f` feat: Update system reference calculations to use division for NavMapScale
- `bb94416` feat: Enhance system reference calculations and add zoom reference rect
- `178da78` feat: Add method to calculate max object map half extent
- `5505f94` feat: Add select_equip.ini to default archetype files
- `7d9de38` feat: Implement orbit drag functionality in preview dialogs
- `d314d2a` feat: Enhance geometry rendering by adding vertex normals support
- `06cff2e` refactor: Remove outdated 3D background streaming plan document
- `9af3cae` feat: Implement undo functionality in Base Builder dialog
- `477e86a` feat: Implement Base Builder functionality and improve Mesh Preview Dialog
- `9466861` feat: add preview fitting and camera synchronization in MeshPreviewDialog
- `fef5781` feat: implement 2D object label visibility policy
- `fa83f4f` feat: improve UI layout and tooltip functionality
- `e32c40e` feat: enhance base builder dialog layout and improve event handling
- `6668bac` feat: Enhance base builder functionality and UI
- `7e718d2` feat: enhance view state restoration and system document handling
- `8c67ad4` Refactor code structure for improved readability and maintainability
- `47dc3a7` fix: clean up unwanted characters in XML normalization
- `a82a5cf` feat: enhance string and XML resource handling
- `5366ad2` feat: implement automatic context switching for repo mod creation
- `56891d5` fix: update application version to 0.6.6


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
