# FLAtlas

FLAtlas is a desktop editor suite for **Freelancer** modding.

It brings common editing tasks into one tool: systems, universe data, bases, trade routes, IDS/infocard text, INI files, NPC-related data, 3D previews, and mod workflows.

The project is currently maintained as the classic FLAtlas V1 codebase. A newer FLAtlas V2 exists separately, but V1 remains usable and still receives focused fixes.

## Current Version

Source version: `v0.7.2`

## Run From Source

On Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-build.txt
python fl_atlas.py
```

You can also use:

```bat
launch.cmd
```

## Build

Windows builds use the existing project script:

```bat
scripts\build_windows.bat
```

The app entry point is [fl_atlas.py](C:/Users/steve/Github/FLAtlas/fl_atlas.py).
Most application code lives in [fl_editor](C:/Users/steve/Github/FLAtlas/fl_editor).

## Tests

Run the test suite with:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

For quick compile checks:

```powershell
Get-ChildItem fl_atlas.py, fl_editor\*.py, tests\*.py | ForEach-Object { .\.venv\Scripts\python.exe -m py_compile $_.FullName }
```

## Releases

Packaged builds are published on GitHub:

https://github.com/flathack/FLAtlas/releases

Download the ZIP for your Windows architecture, extract it, and start `FLAtlas.exe`. Keep the `_internal` folder next to the executable.
