@echo off
setlocal ENABLEDELAYEDEXPANSION

cd /d %~dp0\..

if not exist .venv\Scripts\python.exe (
  echo Missing virtualenv at .venv\Scripts\python.exe
  exit /b 1
)

set PY=.venv\Scripts\python.exe

%PY% -m pip install --upgrade pip wheel
%PY% -m pip install --upgrade pyinstaller pefile

%PY% -m PyInstaller --noconfirm --clean FLAtlas.spec

echo Build finished: %CD%\dist\FLAtlas
endlocal
