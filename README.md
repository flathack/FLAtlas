# FL Atlas

FL Atlas is a desktop editor for **Freelancer** game data.
It provides visual editing for universe/system INI files, trade route tooling, and DLL string editors (`ids_name`, `ids_info`) in one application.

## Highlights

- Universe view and system view with 2D/3D visualization
- Object and zone editing directly on the map
- Trade Route Generator view (economy-focused routes, not tradelanes)
- Name & Info Editor for `ids_name` and `ids_info` (DLL resources)
- Mod Manager with mod repository workflows
- Welcome flow for first-time setup
- BINI conversion support (decode compressed `.ini` data)
- EN/DE UI translations

## Main Pages

- `Universe View`
- `System View`
- `Trade Routes`
- `Name & Info Editor`
- `Global Settings`
- `Mod Manager`

## Requirements

- Python 3.10+
- PySide6 (including Qt WebEngine and Qt3D modules)
- `pefile` (required for DLL string/resource reading and writing)

Example setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install PySide6 pefile
```

## Run From Source

```bash
source .venv/bin/activate
python fl_atlas.py
```

## First Start

On first launch, FL Atlas opens the Welcome flow and Mod Manager.
Recommended setup is:

1. Configure your mod repository (or register a direct-in-game-folder mod).
2. Select one mod as **active editing context**.
3. Switch to Universe/System/Trade Routes/Name & Info Editor.

Notes:

- In FL + Mod setups, edits are written to the mod side only.
- Missing files can fall back to vanilla data for reading.
- If vanilla data is BINI-compressed, use conversion options in Welcome/Global Settings.

## Build

### Linux

```bash
./scripts/build_linux.sh
```

Output:

- `dist/FLAtlas/`

Create release archive + checksum:

```bash
./scripts/release_linux.sh
```

Output:

- `release/v<version>/FLAtlas-v<version>-linux-x86_64.tar.gz`
- `release/v<version>/FLAtlas-v<version>-linux-x86_64.tar.gz.sha256`

### Windows

Run on a Windows machine:

```bat
scripts\build_windows.bat
```

Output:

- `dist\FLAtlas\`

## Install Linux Release (tar.gz)

Example for `FLAtlas-v0.6.0-linux-x86_64.tar.gz`:

```bash
mkdir -p ~/Apps
cd ~/Apps
tar -xzf /path/to/FLAtlas-v0.6.0-linux-x86_64.tar.gz
cd FLAtlas-v0.6.0-linux-x86_64
./FLAtlas
```

Optional launcher (`~/.local/share/applications/flatlas.desktop`):

```ini
[Desktop Entry]
Type=Application
Name=FL Atlas
Exec=/home/<user>/Apps/FLAtlas-v0.6.0-linux-x86_64/FLAtlas
Icon=/home/<user>/Apps/FLAtlas-v0.6.0-linux-x86_64/_internal/fl_editor/images/FLAtlas-Logo-256.png
Categories=Utility;
Terminal=false
```

## Versioning

Set version in one place:

- `fl_atlas.py` → `APP_VERSION = "x.y.z"`

This version is used by app UI and release scripts.

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

Manual regression test checklist:

- `QA_TESTCASES.md`

## License

No license file is currently included in this repository.
Add one before public distribution if needed.
