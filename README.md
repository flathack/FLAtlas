# FL Atlas

Desktop editor for Freelancer INI data (Universe/System/Trade Routes).

## Versioning

Set the release version in one place:

- `fl_atlas.py` → `APP_VERSION = "x.y.z"`

This version is used by the app title/about dialog and release scripts.

## Build (Linux)

1. Create venv and install runtime dependencies (your current project setup).
2. Run:

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

## Build (Windows)

Run on a Windows machine:

```bat
scripts\build_windows.bat
```

Output:

- `dist\FLAtlas\`

## PyInstaller

- Spec file: `FLAtlas.spec`
- Entry point: `fl_atlas.py`
- Includes package data from `fl_editor` (help, images, translations, etc.)
