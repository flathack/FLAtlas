# AGENTS.md

## Project
FLAtlas is a desktop editor suite for Freelancer data, including universe/system editing, trade routes, DLL text editing, mod workflows, and supporting tools.
The codebase centers around `fl_atlas.py` and the `fl_editor/` package, with PySide-based UI and a large amount of file-format-specific logic.

## Main Entry Points
- App start: `python fl_atlas.py`
- Windows convenience launcher: `launch.cmd`
- Packaging spec: `FLAtlas.spec`
- Main package: `fl_editor/`
- Tests: `tests/`

## Setup
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-build.txt
python fl_atlas.py
```

Alternative local launcher:
```powershell
launch.cmd
```

## Build And Release
- Windows build:
```powershell
scripts\build_windows.bat
```
- Linux prep:
```bash
scripts/prepare_linux_build.sh
```
- Linux build:
```bash
scripts/build_linux.sh
```

## Validation
- Run the test suite:
```powershell
.\.venv\Scripts\python.exe -m pytest
```
- Run compile sanity checks:
```powershell
Get-ChildItem fl_atlas.py, fl_editor\*.py, tests\*.py | ForEach-Object { .\.venv\Scripts\python.exe -m py_compile $_.FullName }
```
- For UI-heavy changes, also verify one real startup/manual smoke path.

## Important Paths
- `fl_atlas.py`: app entry point and top-level startup settings
- `fl_editor/`: UI, helpers, dialogs, format logic, and feature modules
- `tests/`: regression and smoke coverage
- `scripts/`: build/release helpers
- `build/`, `dist/`, `release/`: generated artifacts

## Working Rules
- No quick fixes. Prefer correct, maintainable solutions that fit the existing architecture.
- Preserve a clean structure and align changes with established software engineering standards.
- Avoid unnecessary or circular code changes where one layer undoes or duplicates another layer's work.
- Prefer localized edits in the relevant `fl_editor/` module rather than adding more logic to `fl_atlas.py` unless startup behavior truly belongs there.
- Preserve existing user workflows for mod paths, fallback reads, and write behavior.
- Be careful with file-writing helpers and serialization code because small changes can affect many editor features.
- Keep UI wording and EN/DE behavior consistent with the existing app style.
- Avoid broad refactors during feature or bug work unless explicitly requested.

## Guardrails
- Do not commit generated output from `build/`, `dist/`, or `release/` unless explicitly requested.
- Do not silently change save/write semantics for Freelancer data files, DLL resources, or BINI handling.
- Do not break fallback behavior where reads can use vanilla data while writes target the active mod context.
- Be cautious when editing updater, packaging, or versioning behavior because release artifacts depend on it.
- Do not add workaround logic that hides the real source of a problem when the root cause can be fixed properly.

## Review Context
- If a task may impact packaging or release readiness, also check `README.md`, `BUILD_INFO.md`, `CHANGELOG.md`, `todo.md`, and active `PROJECT_PLAN_*.md` files as needed.
- If a change affects startup defaults, inspect `FORCE_STARTUP_SETTINGS`, `STARTUP_LANGUAGE`, and `STARTUP_THEME` in `fl_atlas.py`.

## Response Expectations
- Summarize user-visible impact first.
- Mention test coverage that was run and any manual checks still recommended.
- Explicitly note risks when a change touches shared write helpers, editor state, or packaging.
