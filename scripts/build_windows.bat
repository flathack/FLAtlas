@echo off
setlocal ENABLEDELAYEDEXPANSION

cd /d %~dp0\..

if not exist .venv\Scripts\python.exe (
  echo Missing virtualenv at .venv\Scripts\python.exe
  exit /b 1
)

set PY=.venv\Scripts\python.exe
set UPDATER_ICON=%CD%\fl_editor\images\FLAtlas-Suite-Dreadnought-Front-Logo.ico

%PY% -m pip install --upgrade pip wheel
%PY% -m pip install --upgrade -r requirements-build.txt

%PY% -m PyInstaller --noconfirm --clean FLAtlas.spec
%PY% -m PyInstaller --noconfirm --clean --specpath build --onefile --windowed --name FLAtlasUpdater --icon "%UPDATER_ICON%" flatlas_updater.py

if not exist dist\FLAtlas mkdir dist\FLAtlas
copy /Y dist\FLAtlasUpdater.exe dist\FLAtlas\FLAtlasUpdater.exe >nul

echo Build finished: %CD%\dist\FLAtlas
endlocal
