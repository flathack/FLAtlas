@echo off
setlocal EnableExtensions EnableDelayedExpansion

title FLAtlas - Install IDS Toolchain

echo ==========================================
echo FLAtlas IDS Toolchain Installer (Windows)
echo ==========================================
echo.

set "HAS_PAIR=0"
set "WINGET_EXE="

call :check_pair
if "%HAS_PAIR%"=="1" (
  echo Toolchain already available. Nothing to do.
  goto :done
)

echo Required tools not found.
echo Trying automatic installation via winget (LLVM)...
echo.

call :find_winget
if not defined WINGET_EXE (
  echo ERROR: winget is not available on this system.
  echo Please install one of these toolchains manually:
  echo   1^) llvm-windres + lld-link
  echo   2^) llvm-rc + lld-link
  echo   3^) rc.exe + link.exe ^(MSVC Build Tools^)
  goto :fail
)

"%WINGET_EXE%" install -e --id LLVM.LLVM --accept-package-agreements --accept-source-agreements --disable-interactivity
if errorlevel 1 (
  echo.
  echo WARNING: winget install returned an error.
  echo Continuing with post-install checks...
)

echo.
echo Refreshing PATH for this session...
if exist "C:\Program Files\LLVM\bin" (
  set "PATH=C:\Program Files\LLVM\bin;%PATH%"
)

echo.
echo Re-checking toolchain...
set "HAS_PAIR=0"
call :check_pair
if "%HAS_PAIR%"=="1" (
  echo.
  echo SUCCESS: Supported resource toolchain is now available.
  goto :done
)

echo.
echo ERROR: Tools still not found in PATH.
echo You may need to:
echo   - Close and reopen terminal/session
echo   - Reboot
echo   - Add LLVM bin to PATH manually:
echo     C:\Program Files\LLVM\bin
goto :fail

:find_winget
for /f "delims=" %%I in ('where winget.exe 2^>nul') do (
  set "WINGET_EXE=%%I"
  goto :find_winget_done
)
if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\winget.exe" (
  set "WINGET_EXE=%LOCALAPPDATA%\Microsoft\WindowsApps\winget.exe"
)
:find_winget_done
if defined WINGET_EXE (
  echo winget: %WINGET_EXE%
)
exit /b 0

:check_pair
set "WINDRES="
set "LLVMRC="
set "LLDLINK="
set "RCEXE="
set "LINKEXE="

for /f "delims=" %%I in ('where llvm-windres 2^>nul') do set "WINDRES=%%I"
for /f "delims=" %%I in ('where llvm-rc 2^>nul') do set "LLVMRC=%%I"
for /f "delims=" %%I in ('where lld-link 2^>nul') do set "LLDLINK=%%I"
for /f "delims=" %%I in ('where rc.exe 2^>nul') do set "RCEXE=%%I"
for /f "delims=" %%I in ('where link.exe 2^>nul') do set "LINKEXE=%%I"

echo --- Detected tools ---
if defined WINDRES (echo llvm-windres: !WINDRES!) else (echo llvm-windres: MISSING)
if defined LLVMRC  (echo llvm-rc:      !LLVMRC!)  else (echo llvm-rc:      MISSING)
if defined LLDLINK (echo lld-link:     !LLDLINK!) else (echo lld-link:     MISSING)
if defined RCEXE   (echo rc.exe:       !RCEXE!)   else (echo rc.exe:       MISSING)
if defined LINKEXE (echo link.exe:     !LINKEXE!) else (echo link.exe:     MISSING)
echo.

if defined WINDRES if defined LLDLINK set "HAS_PAIR=1"
if defined LLVMRC if defined LLDLINK set "HAS_PAIR=1"
if defined RCEXE if defined LINKEXE set "HAS_PAIR=1"

if "%HAS_PAIR%"=="1" (
  echo Supported pair found.
) else (
  echo No supported pair found.
)
echo.
exit /b 0

:fail
echo.
echo Installer finished with errors.
echo.
pause
exit /b 1

:done
echo.
echo Installer finished successfully.
echo.
pause
exit /b 0
