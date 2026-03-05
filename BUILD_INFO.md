# FLAtlas Build Info (Windows)

Diese Datei beschreibt den schnellsten Weg, um einen lauffaehigen Windows-Build zu erstellen.

## 0) Roadmap aktualisieren

- `ROADMAP_&_BUGS.md` um die neuen Features/Fixes erweitern
- Build-/Release-Eintrag mit Version und Datum ergaenzen

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

## 9) Tag auf GitHub erstellen
## 10) Release auf Github erstellen, als Text den Info Text aus der Roadmap, welcher zum Release Version passt, nehmen.
## 11) release datei nach github hochladen.
## 12) development branch in den Default-Branch mergen (master/main je nach Repo)
## 13) lokale Umgebung zurück nach development switchen.
