# FLAtlas Build Info (Windows)

Diese Datei beschreibt den schnellsten Weg, um einen lauffaehigen Windows-Build zu erstellen.

## 0) Release-Doku aktualisieren

- `CHANGELOG.md` um die neuen Features/Fixes erweitern
- `README.md`, `TODO.md` und betroffene `PROJECT_PLAN_*.md` auf den Release-Stand pruefen

## Voraussetzungen

- Windows 10/11
- Python 3.11+ (im PATH)
- `pip` verfuegbar

## 1) In Projektordner wechseln

```powershell
cd C:\Users\STAdmin\FLAtlas\FLAtlas
```

## 2) Virtuelle Umgebung (empfohlen)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

## 3) Build-Abhaengigkeiten installieren

```powershell
python -m pip install --upgrade pip
pip install -r requirements-build.txt
```

Hinweis:

- `requirements-build.txt` enthaelt jetzt auch `pytest`, damit der dokumentierte QA-Schritt in derselben `.venv` direkt lauffaehig ist.

## 4) Version setzen

In `fl_atlas.py`:

- `APP_VERSION = "x.y.z"` oder `APP_VERSION = "x.y.z.w"`

## 5) Build starten

Variante A (empfohlen, falls vorhanden):

```powershell
scripts\build_windows.bat
```

Variante B (direkt mit PyInstaller):

```powershell
pyinstaller --clean --noconfirm FLAtlas.spec
```

## 6) Build-Ergebnis

- App-Ordner: `dist\FLAtlas\`
- Startdatei: `dist\FLAtlas\FLAtlas.exe`

## 7) Optional: Release ZIP + SHA256

```powershell
$version = "v0.0.0"
$zipName = "FLAtlas-$version-windows_x86_64.zip"
Compress-Archive -Path "dist\\FLAtlas\\*" -DestinationPath $zipName -Force
Get-FileHash -Algorithm SHA256 $zipName | ForEach-Object { $_.Hash.ToLower() + "  " + $zipName } | Set-Content "$zipName.sha256"
```

## 8) Kurztest vor Release

- Startet `FLAtlas.exe` ohne Fehlermeldung
- Splash/Welcome erscheint korrekt
- Sprache wechseln funktioniert
- Help-Fenster oeffnet und Inhalte werden geladen
- Mod Manager oeffnet und Profile sind bedienbar
- `.venv\\Scripts\\python.exe -m pytest` bzw. `.venv\\Scripts\\pytest.exe` laeuft grün
- `Get-ChildItem fl_atlas.py, fl_editor\\*.py, tests\\*.py | ForEach-Object { .\\.venv\\Scripts\\python.exe -m py_compile $_.FullName }` laeuft grün

Verifizierte lokale Basis vom 2026-03-11:

- `599 passed, 4 skipped` unter Windows
- die 4 Skips sind erwartete Qt3D-Preview-Faelle in Headless-/Offscreen-Testumgebungen

## 9) Tag auf GitHub erstellen
## 10) Release auf Github erstellen, als Text die passende Zusammenfassung aus `CHANGELOG.md` verwenden.
## 11) release datei nach github hochladen.
## 12) development branch in den Default-Branch mergen (master/main je nach Repo)
## 13) lokale Umgebung zurück nach development switchen.
