@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\pythonw.exe" start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0fl_atlas.py" & exit /b 0
if exist "%~dp0.venv\Scripts\python.exe" start "" "%~dp0.venv\Scripts\python.exe" "%~dp0fl_atlas.py" & exit /b 0
start "" py -3 "%~dp0fl_atlas.py"
endlocal
