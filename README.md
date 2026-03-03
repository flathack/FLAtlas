# FLAtlas

FLAtlas is a desktop editor for **Freelancer** game data.
It combines universe/system editing, trade route tooling, and DLL string editors (`ids_name`, `ids_info`) in one application.

## First Public Release

`v0.6.2` is the **first public release** of FLAtlas.

## Download v0.6.2

- GitHub Releases: `https://github.com/flathack/FLAtlas/releases/tag/v0.6.2`
- Windows package: `FLAtlas-0.6.2.zip`

## Install and Run on Windows (v0.6.2)

1. Download `FLAtlas-0.6.2.zip` from the release page.
2. Extract the ZIP to a folder, for example `C:\Apps\FLAtlas`.
3. Open the extracted folder.
4. Start `FLAtlas.exe`.

Notes:
- If SmartScreen appears, choose "More info" -> "Run anyway" only if you trust this build.
- Keep the `_internal` folder next to `FLAtlas.exe`.

## Install and Run on Linux

A prebuilt Linux binary is published in `v0.6.2`.
Download, unzip and run ./FLAtlas in unzipped folder.



## Highlights

- Universe view and system view with 2D/3D visualization
- Object and zone editing directly on the map
- Trade Route Generator (economy-focused routes, not tradelanes)
- Name & Info Editor for `ids_name` and `ids_info` (DLL resources)
- Mod Manager workflows
- Welcome flow for first-time setup
- BINI conversion support
- EN/DE translations

## First Start

Recommended setup:

1. Configure your mod repository (or register a direct in-game-folder mod).
2. Select one mod as active editing context.
3. Switch to Universe/System/Trade Routes/Name & Info Editor.

Notes:
- In FL + Mod setups, edits are written to the mod side only.
- Missing files can fall back to vanilla data for reading.
- If vanilla data is BINI-compressed, use conversion options in Welcome/Global Settings.

## Build (Windows)

Run on a Windows machine:

```bat
scripts\build_windows.bat
```

Output:
- `dist\FLAtlas\`
- optional ZIP: `dist\FLAtlas-<version>.zip`

## Versioning

Set version in one place:

- `fl_atlas.py` -> `APP_VERSION = "x.y.z"`

## Project Structure

- `fl_atlas.py`: app entry point
- `fl_editor/main_window.py`: main UI and feature orchestration
- `fl_editor/dialogs.py`: dialogs/edit forms
- `fl_editor/dll_resources.py`: DLL string/resource handling
- `fl_editor/bini.py`: BINI decoding
- `fl_editor/help/`: built-in help pages
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

## QA

Manual regression checklist:
- `QA_TESTCASES.md`

## License

No license file is currently included in this repository.
Add one before wider public distribution.
