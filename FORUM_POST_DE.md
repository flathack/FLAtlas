FL Atlas - Freelancer Modding Suite
===================================

FL Atlas is a desktop tool for Freelancer that brings together several common modding workflows in a single application. The goal of the project is not just to edit individual files, but to support connected workflows directly inside one central editor.

Download links:
- GitHub: https://github.com/flathack/FLAtlas
- ModDB: https://www.moddb.com/games/freelancer/downloads/fl-atlas-visual-freelancer-editor-for-systems-modding-and-ids-workflows

Related tools and companion projects:
- FL Lingo: https://www.moddb.com/games/freelancer/downloads/fl-lingo-a-freelancer-translator
- Savegame Editor: https://www.moddb.com/games/freelancer/downloads/flatlas-savegame-editor
- FL Atlas Launcher: https://github.com/flathack/FL-Atlas-Launcher

The focus is on practical tools for system building, universe editing, base workflows, text/INI editing, DLL/infocard handling, and 3D previewing. Instead of constantly switching between small helper tools and text editors, FL Atlas is meant to cover as many everyday tasks as possible inside one consistent interface.

At the moment, FL Atlas covers areas such as:

- Universe and system editing with 2D and 3D views
- Direct editing of objects, zones, jump connections, and bases
- Trade-route tools for economy and market workflows
- Name and infocard editing for ids_name and ids_info
- A Freelancer-focused file explorer / text editor with tabs, search, and history
- Mod management for mod contexts and write targets
- 3D Model Manager and Character 3D Viewer
- Base Builder with 3D preview for assembled bases
- Tools for NPCs, rumors, and news
- BINI support, vanilla fallbacks, and DE/EN language support

What matters most is that FL Atlas is not only meant to display data, but to speed up actual modding workflows. Many features are therefore linked together directly. Files, references, models, systems, and resources should be reachable with as little friction as possible.

The first post of this thread is intended to remain the full project overview at all times. New version sections will then be added below it, so the current state of the tool and its development history can always be tracked in one place.


Project Focus
=============

FL Atlas is aimed at Freelancer modders who want to:

- Edit systems and universe data visually
- Create or adjust bases, zones, objects, and connections faster
- Manage DLL text, infocards, and related file references centrally
- Stop relying on a basic text editor for large INI and text files
- Inspect 3D models, character assets, and base compositions directly inside the tool


Version Changelog For The Forum Post
====================================

v0.6.7
------

This version expanded FL Atlas most strongly in the areas of the File Explorer, Character Viewer, and base-related workflows.

Added:
- Character 3D Model Viewer for assembled Freelancer characters
- 8x8 grid layout in both the 2D and 3D system view
- Major expansion of the file/text editor into a more complete Freelancer-focused File Explorer
- Explorer tabs for working with multiple files in parallel
- File and line history stored in the mod-local .flatlas folder
- Context actions for linked files, folders, systems, and 3D models
- IDS-aware actions for ids_name and ids_info
- Minimap support for text files
- File creation and deletion directly inside the explorer
- Stronger 3D Base Builder workflows

Changed:
- The former INI Editor was expanded into the broader File Explorer
- Text editing now leans more toward a VS-Code-like workflow, but tailored specifically to Freelancer modding
- 3D models can now open directly in dedicated tabs
- system.ini files can be sent directly into the 2D system view
- The toolbar and overall File Explorer UX were refined further

Fixed:
- Line history now follows the logical line even after inserts and deletes
- Less lag when editing large files such as market_misc.ini
- Multiple UX issues in the File Explorer and previews were fixed
- Startup crash caused by early _ini_editor_current_file access was fixed

Commits in this range:
- bdcd768 Improve file explorer tabs, previews, and editor UX
- d96ba07 feat: Enhance INI editor with new file creation and search functionality
- 87f28b3 Add Character 3D Model Viewer functionality


v0.6.6
------

The main focus of this version was the Base Builder, 3D presentation, and structural improvements.

Added:
- Base Builder for multi-part base compositions
- Live 3D preview with ground grid
- Axis gizmo and precision controls for position and rotation
- Orbit drag and improved camera controls
- Undo/history workflows for add, delete, move, and rotate
- Vertex normals and texture configuration for improved 3D geometry
- select_equip.ini in the default archetype files
- Automatic context switching when creating a new repo mod

Changed:
- System references now use NavMapScale more accurately for 2D map framing
- Zoom reference rectangle for better system fitting
- Improved label and selection behavior for child objects
- INI editor functionality and translations were refactored further
- Theme alpha values and pen widths now react to light/dark mode

Fixed:
- Universe zoom no longer causes systems to disappear
- String and XML resource handling in INIs and DLLs was improved
- Unwanted characters in XML normalization were cleaned up
- 3D placeholder sizes and fallback radii were improved
- Qt3D native preview was hardened with normals against Failed to create input layout on Windows

Commits in this range:
- 5d571c8 Refactor INI editor functionality and update translations
- 8e04994 feat: Add axis gizmo overlay and precision step controls in BaseBuilderDialog
- 4471eda feat: Adjust layout parameters in BaseBuilderDialog and MeshPreviewDialog
- 960fce7 feat: Implement ground grid visualization in BaseAssemblyPreviewView
- 83c697f feat: Adjust theme color alpha and pen width based on light/dark mode
- ce82e3f feat: Update system reference calculations to use division for NavMapScale
- bb94416 feat: Enhance system reference calculations and add zoom reference rect
- 178da78 feat: Add method to calculate max object map half extent
- 5505f94 feat: Add select_equip.ini to default archetype files
- 7d9de38 feat: Implement orbit drag functionality in preview dialogs
- d314d2a feat: Enhance geometry rendering by adding vertex normals support
- 06cff2e refactor: Remove outdated 3D background streaming plan document
- 9af3cae feat: Implement undo functionality in Base Builder dialog
- 477e86a feat: Implement Base Builder functionality and improve Mesh Preview Dialog
- 9466861 feat: add preview fitting and camera synchronization in MeshPreviewDialog
- fef5781 feat: implement 2D object label visibility policy
- fa83f4f feat: improve UI layout and tooltip functionality
- e32c40e feat: enhance base builder dialog layout and improve event handling
- 6668bac feat: Enhance base builder functionality and UI
- 7e718d2 feat: enhance view state restoration and system document handling
- 8c67ad4 Refactor code structure for improved readability and maintainability
- 47dc3a7 fix: clean up unwanted characters in XML normalization
- a82a5cf feat: enhance string and XML resource handling
- 5366ad2 feat: implement automatic context switching for repo mod creation
- 56891d5 fix: update application version to 0.6.6


v0.6.5
------

This version expanded FL Atlas with several standalone tool areas and pushed the 3D workflows much further.

Added:
- Tools menu with News Editor, NPC Editor, Rumor Editor, and 3D Model Manager
- Integrated 3D Model Manager with live preview, search, and grouped model listing
- Persistent top-view icon workflows for vanilla content and mods
- Activity tab for status messages, categories, and filters
- Background support for Freelancer starspheres in 3D
- Separate Free Cam mode for the 3D system view

Changed:
- Much smoother background streaming path for native 3D models
- Simplified native 3D rendering in system view for better performance
- More realistic 2D object sizing
- Global search and filter fields now use debouncing and shared search delay
- Startup/session flow and the overall visual identity were reworked

Fixed:
- Many native 3D and CMP preview problems were resolved
- Stability and performance when opening large systems were improved
- Several universe/system workflow issues were fixed
- Multiple 3D UI issues and activity-log transparency issues were improved

Commits in this range:
- 7117ee0 perf: smooth native 3d preview scheduling
- 8950e65 perf: add prepared native scene payloads
- a8c4384 perf: drop stale native preview build payloads
- 2b594ec perf: prioritize lighter prepared native payloads
- 9b36bdf perf: add tiered native preview policy
- b74d43a perf: instrument native scene streaming activity
- 30182e1 perf: stagger duplicate native preview builds
- 44f8f16 perf: add native preview batch time budget
- 728dcd7 perf: prioritize cached native preview reattach


v0.6.4
------

This version significantly expanded the 3D viewer, trade routes, the former INI editor, and the Mod Manager.

Added:
- Expanded native 3D object viewer and CMP inspection workflow
- Trade routes as a stronger balancing and analysis tool
- Heavily expanded INI editor with compare, Find usages, status summary, and section inspector
- EXE version management and mod-settings support in the Mod Manager
- Local launch.cmd for starting FL Atlas directly from the repo

Changed:
- Native scene and runtime handling in 3D preview and system integration was refactored further
- Trade-route internals became more modular and testable
- INI editor workflow was grouped more tightly around the main editing path
- Release/build hygiene was improved further

Fixed:
- CMP/native preview problems involving orientation, transform hints, and legacy layouts were fixed
- Trade-route correctness was improved for base-price handling, weaker valid routes, and unreachable connections
- INI editor ergonomics were improved for longer editing sessions

Commits in this range:
- 89af662 Bump version to v0.6.4, enhance native scene runtime with debug event tracking, and add debug state snapshot functionality in main window and view 3D
- 57aa9fe Refactor native scene handling in main window and view 3D; enhance debug state snapshot and sync functionality
- 1c78cfc Improve 3D viewer native scene runtime diagnostics
- 8e35213 Improve real CMP part matching diagnostics
- 455f0b4 Add native CMP decode diagnostics
- d9443e7 Add jumpgate support in MeshPreviewDialog and update model file handling in MainWindow
- e848c43 Handle relative UTF data offsets in CMP loader
- 3889468 Prefer VMS stride hints in preview layout guess
- aa8eaa3 Classify real CMP VMeshData block patterns
- 0cc56b1 Resolve real CMP VMesh refs via Freelancer CRC
- e1102f5 Group related CMP VMeshData blocks into families
- 2de06bb Propagate CMP VMesh family context into preview metadata
- bca6875 Add family-aware CMP preview layout metadata
- d8b9ae7 Use stream blocks for family-aware CMP layout guesses
- 1be8077 Add family-aware CMP decode diagnostics
- 4832d68 Add combined family fit diagnostics for CMP decode
- a055404 Detect CMP header end-vertex semantics
- 64b116b Name CMP mesh header end-range semantics
- 7dc6d4d Match CMP mesh header group end semantics
- 86aa548 Build structured CMP mesh header records
- 6006f6e Mark structured CMP decode targets
- ebf8074 Build initial structured CMP decode plans
- 79beafd Use structured decode plans in native preview geometry
- d9aa4eb Refine 3D viewer plan for first visible Freelancer models
- 36c0329 Detail 3D viewer delivery path for Freelancer files
- 5aa33d8 Add 3D viewer reference acceptance and blocker criteria
- b888086 Decode first real jump_gatel Level4 preview geometry
- d51f803 Decode first real jump_gatel Level3 family geometry
- 29027f5 Expose native preview render path in UI
- dd7f4d3 Expose selected native detail state in main window snapshot
- 9f9e875 Move 3D preview details into separate tab
- 26fc38d Constrain 3D preview dialog to screen height
- fc795d0 Refactor tests for path utilities and add new image assets
- 7de6e9f Enhance vmesh reference parsing to support legacy layout and infer vertex/index counts
- a619e7c 3d objekte in system view
- ed6119b 3d model debug
- be0fdbe Add EXE version management features to Mod Manager
- 7e530d6 feat: Add mod settings page and runtime handling for EXE offsets
- c92ffc9 feat: Enhance trade route filtering and UI
- fa4ba2b fix: Correct model orientation for CMP files in 3D viewer
- a41052f feat: Add CMP up correction handling and related tests
- e8d9b88 Refactor and enhance CMP loader and mesh data handling
- 0eb6fe2 feat: Add comprehensive documentation for the 3D Object Viewer, covering architecture, data formats, and algorithms
- e85f1af fix: Update CMP transform hints to correctly reflect part names and translations
- ed2b0e5 feat: Enhance MeshPreviewDialog with mesh visibility toggle and improve color settings for better contrast
- 0a3dcf6 feat: Implement material library handling and enhance MeshPreviewDialog with texture support
- b327dfc feat: Implement back-face culling disable functionality for Qt3D materials in MeshPreviewDialog
- 536a068 Add trade route market analysis dialog
- e78ea98 Add goods.ini deep link for trade routes
- b225e85 Add cargo-based net profit to trade routes
- da7c209 Add profit-per-jump route analysis filters
- b672185 Extract trade route runtime helpers
- 11d7275 Improve trade route market editor previews
- eee790b Add trade route base deep links
- e46fa9b Add market section deep links for trade routes
- 63cad2f Account for implicit base-price trade routes
- 7ec408d Keep implicit trade route pairs in route scan
- 9c7c403 Drop unreachable trade routes from analysis
- ad9c2bc Add market editor and analysis buttons to trade route sidebar
- a9d85fd Add launch script for running FLAtlas application
- aea017a Improve INI editor modding workflow
- 6d6ff98 Add section-aware INI comparison
- 5cc37fe Add INI editor find usages search
- b4d0157 Add INI editor file status panel
- 58c3b71 Add INI section inspector editor
- 47bdaa7 Add INI editor validation hints
- a7e7a1a Refactor INI editor status panel to use summary label and update tooltip information
- 2254997 Update .gitignore to include additional virtual environments and build artifacts


Template For Future Updates
===========================

You can reuse this block for each new version and insert it below the project overview:

vX.Y.Z
------

Short introduction in 2 to 4 sentences:
What is the main focus of this version?
Is it mainly about new features, workflow improvements, performance, or fixes?

- Feature 1
- Feature 2
- Feature 3
- Feature 4

Optional ending:
A short sentence about what you want to work on next or what kind of feedback you are looking for.


Short Version For The Thread Start
==================================

FL Atlas is a Freelancer modding suite that combines universe and system editing, 2D/3D views, trade-route tools, DLL/infocard editing, a Freelancer-focused file explorer, mod management, and 3D viewer/base workflows inside a single tool.

The first post of this thread is meant to stay the permanent project overview. With each new version, this post can be extended with another section so that the major features and development steps remain collected in one place.
