# FLAtlas

FLAtlas is a desktop editor for **Freelancer** game data.
It combines universe/system editing, trade route tooling, and DLL string editors (`ids_name`, `ids_info`) in one application.

## Source Version

Current source tree version: `v0.7.0` (`fl_atlas.py`).

## Current Status

FLAtlas currently covers these product areas in one desktop tool:

- Universe and system editing
- Trade route tooling
- IDS Editor for name and infocard editing (`ids_name`, `ids_info`)
- File Explorer / text editor for Freelancer data
- Mod Manager
- Welcome/setup flow
- External Savegame Editor integration
- Character 3D viewing
- Base Builder workflows
- BINI conversion and fallback reading

The codebase was also refactored beyond the original monolithic window file:

- large page builders moved into dedicated UI modules
- repeated write paths moved into smaller helpers
- dialog data/workflow logic moved into dedicated helper modules
- smoke and pure-logic regression coverage established under `tests/`

## Releases

- GitHub Releases: `https://github.com/flathack/FLAtlas/releases`
- Packaged release numbers can lag behind the current repository state.

## Install and Run on Windows

1. Download `FLAtlas-v0.7.0-windows_x86_64.zip` from the release page.
2. Extract the ZIP to a folder, for example `C:\Apps\FLAtlas`.
3. Open the extracted folder.
4. Start `FLAtlas.exe`.

Notes:
- If SmartScreen appears, choose "More info" -> "Run anyway" only if you trust this build.
- Keep the `_internal` folder next to `FLAtlas.exe`.

## Install and Run on Linux

If a Linux build is published for the selected release, unzip it and run `./FLAtlas` from the extracted folder.

## Highlights

- Universe view and system view with 2D/3D visualization
- `8x8` grid workflow in 2D and 3D system view
- smoother 3D system-view background streaming for native models
- `3D Model Manager` with embedded live preview and grouped model browser
- `Character 3D Model Viewer` for assembled body/head/hand previews
- `Base Builder` for assembling multi-part base compositions with live 3D preview
- Object and zone editing directly on the map
- Trade Route Generator (economy-focused routes, not tradelanes)
- Name & Info Editor for `ids_name` and `ids_info` (DLL resources)
- `File Explorer` / text editor with tabs, minimap, linked navigation, file history, and Freelancer-focused context actions
- stronger 2D system-view editing flow with direct `ids_info` text editing and refined sidebar action layout
- Mod Manager workflows
- Tools menu for NPC, Rumor, News, and 3D model workflows
- Welcome flow for first-time setup
- External Savegame Editor integration
- BINI conversion support
- EN/DE translations
- persistent loading bar below the main navigation with live progress
- activity/status stream with dedicated `Activity` tab
- startup splash with progress until the app is ready to use
- packaged Windows self-update flow with dedicated updater launcher
- config import/export from the `File` menu

## v0.6.9 -> v0.7.0 Development Highlights

This repository range includes the current `v0.7.0` feature set and the issues solved on the way from `v0.6.9` to `v0.7.0`.

Highlights in this range:

- `IDS Editor` is now the product name shown in the UI instead of `Name & Info Editor`
- the Time Machine in `File Explorer` now offers side-by-side and inline diffs, minimaps, revision timeline markers, and section-based compact diff display
- the new `Clipboard Collector` can gather copied editor text and selected file paths, stays available as a floating helper window, and can paste selected snippets back into the editor
- file-editor context menus can now select and copy complete INI sections directly
- object, weapon-platform, wreck, depot, and base creation dialogs now include much stronger embedded 3D previews
- base editing now uses a real edit-mode dialog with clearer separation between general data and base-loadout content
- system-tab zoom/camera persistence was hardened so tab switches no longer reset the saved view state
- the 2D system sidebar was tightened into a more compact layout
- `FL Atlas Settings` now includes:
  - `Pinned Tools` for permanent main-tab control
  - `FL Atlas Suite Apps` for companion tools and web-tool launchers
  - `Tools` menu entries for the main built-in editors

Resolved GitHub issues in this range:

- `#4` safer default handling for patrol-zone population blocks
- `#6` new starsphere files now appear in background selection lists
- `#10` Time Machine diff view overhaul
- `#11` Clipboard Collector in the File Editor
- `#12` corrected `dock_with` / `base` link normalization on planetary bases
- `#13` Base Builder disabled for unsupported planet and docking-ring roots
- `#16` newly created systems now open in their own system tab
- `#17` planet deathzone and atmosphere defaults now derive from planet size
- `#19` docking-ring base creation defaults and room-copy workflow fixed
- `#20` section headers shown in the 2D object editor text view
- `#23` 3D previews in creation dialogs
- `#25` hover artifacts fixed in 2D system and universe views
- `#26` 2D sidebar action layout no longer collapses into unusable button stacks
- `#27` planet creation can create and prefill `ids_info` directly in the dialog
- `#28` center-tab dragging now works across the full tab bar
- `#32` Linux-safe rotation handling for 3D previews and 2D orientation edge cases
- `#35` editable `ids_info` support in the 2D object editor
- `#36` old user translations no longer pin outdated tab captions
- `#37` base edit dialog rework
- `#40` preserve zoom/camera when switching system tabs
- `#46` copy/select whole INI sections from the editor
- `#50` main-tab and suite-tool management in settings
- `#52` Free Cam `A`/`D` strafe direction fixed
- `#54` tradelane ring count recalculated when a route is repositioned

## First Start

Recommended setup:

1. Configure your mod repository (or register a direct in-game-folder mod).
2. Select one mod as active editing context.
3. Switch to Universe/System/Trade Routes/Name & Info Editor.

Notes:
- In FL + Mod setups, edits are written to the mod side only.
- Missing files can fall back to vanilla data for reading.
- If vanilla data is BINI-compressed, use conversion options in Welcome/Global Settings.

## Startup Defaults (Language/Theme)

You can define startup defaults directly in `fl_atlas.py`:

- `FORCE_STARTUP_SETTINGS`
- `STARTUP_LANGUAGE`
- `STARTUP_THEME`

Behavior:
- If `FORCE_STARTUP_SETTINGS = True`, FLAtlas writes these values to config on every start.
- If `False`, saved user settings remain unchanged.

## Build (Windows)

Run on a Windows machine:

```bat
scripts\build_windows.bat
```

Output:
- `dist\FLAtlas\`
- `dist\FLAtlas\FLAtlas.exe`
- `dist\FLAtlas\FLAtlasUpdater.exe`
- optional ZIP: `FLAtlas-v<version>-windows_x86_64.zip`

## Build (Linux)

Prepare build environment and metadata (does not build yet):

```bash
scripts/prepare_linux_build.sh
```

This creates:
- `build/linux-build-info.txt` (tool/runtime snapshot for reproducible builds)

Run the actual build later:

```bash
scripts/build_linux.sh
```

Output:
- `dist/FLAtlas/`

Optional release package:

```bash
scripts/release_linux.sh
```

Output:
- `release/v<version>/FLAtlas-v<version>-linux-x86_64.tar.gz`
- `release/v<version>/FLAtlas-v<version>-linux-x86_64.tar.gz.sha256`

## Versioning

Set version in one place:

- `fl_atlas.py` -> `APP_VERSION = "x.y.z"`
- `fl_atlas.py` -> `APP_VERSION = "x.y.z.w"`

Packaged Windows releases can self-update only when they are started from the extracted release folder with both `FLAtlas.exe` and `FLAtlasUpdater.exe` present.

## Project Structure

- `fl_atlas.py`: app entry point
- `fl_editor/main_window.py`: main UI and feature orchestration
- `fl_editor/welcome_page.py`: welcome page builder
- `fl_editor/global_settings_page.py`: global settings page builder
- `fl_editor/trade_routes_page.py`: trade routes page builder
- `fl_editor/name_editor_page.py`: name and info editor page builder
- `fl_editor/ini_editor_page.py`: INI editor page builder
- `fl_editor/mod_manager_page.py`: mod manager page builder
- `fl_editor/infocard_utils.py`: infocard XML helper logic
- `fl_editor/help_content.py`: help-tree parsing and fallback loading
- `fl_editor/dev_status.py`: DEV-status metadata and normalization
- `fl_editor/ini_section_writes.py`: shared INI serialization/write helpers
- `fl_editor/text_write_utils.py`: shared text write and atomic write helpers
- `fl_editor/dialogs.py`: dialogs/edit forms
- `fl_editor/base_dialog_logic.py`: base-creation dialog rules and workflow helpers
- `fl_editor/base_edit_logic.py`: base-edit dialog data and market helpers
- `fl_editor/dll_resources.py`: DLL string/resource handling
- `fl_editor/bini.py`: BINI decoding
- `fl_editor/help/`: built-in help pages
- `tests/`: smoke and pure-logic regression tests
- `scripts/`: build/release scripts
- `FLAtlas.spec`: PyInstaller spec

## Troubleshooting

### "No systems found in universe.ini"

- Check active mod/game paths in Mod Manager.
- Ensure `DATA/UNIVERSE/universe.ini` exists in active context or fallback source.

### DLL names are not resolved

- Ensure `pefile` is installed in the runtime environment.
- Verify configured `freelancer.ini` and resource DLL entries.

### BINI-compressed files are unreadable

- Use BINI conversion in Welcome flow or Global Settings.

### Windows: icon missing in taskbar

- FLAtlas sets a Windows AppUserModelID and app icon at runtime.
- For packaged builds, ensure `FLAtlas-Suite-Dreadnought-Front-Logo.ico` is present and rebuild via the provided Windows build script.

## QA

Automated baseline checks:

```powershell
.\.venv\Scripts\python.exe -m pytest
Get-ChildItem fl_atlas.py, fl_editor\*.py, tests\*.py | ForEach-Object { .\.venv\Scripts\python.exe -m py_compile $_.FullName }
```

Covered baseline:

- startup smoke
- navigation smoke
- view/mode switching smoke
- language/retranslate smoke
- critical pure-logic helpers for mod manager, writes, infocards, BINI, dialog state and editor state

Current regression baseline in repository:

- `591` collected tests in the reviewed source state from `2026-03-11`
- current local verification on Windows from `2026-03-12`: `638 passed, 4 skipped`
- the skipped tests are the expected Qt3D preview cases in headless/offscreen test mode

Recommended review flow before packaging:

1. Run `.\.venv\Scripts\python.exe -m pytest`
2. Run `Get-ChildItem fl_atlas.py, fl_editor\*.py, tests\*.py | ForEach-Object { .\.venv\Scripts\python.exe -m py_compile $_.FullName }`
3. Validate one real startup/navigation smoke path with the active Freelancer/mod context
4. Re-check `README.md`, `TODO.md`, `SOLL_IST_ABGLEICH.md`, `BUILD_INFO.md`, `CHANGELOG.md` and the active `PROJECT_PLAN_*.md` files

Project review artifacts:
- `PROJECT_PLAN_FLATLAS.md`
- `PROJECT_PLAN_3DEDITOR.md`
- `PROJECT_PLAN_INIEDITOR.md`
- `PROJECT_PLAN_TRADEROUTE.md`
- `SOLL_IST_ABGLEICH.md`
- `TODO.md`

## License

No license file is currently included in this repository.
Add one before wider public distribution.
