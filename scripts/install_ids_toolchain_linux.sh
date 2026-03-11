#!/usr/bin/env sh
set -eu

echo "FLAtlas IDS Toolchain Installer (Linux)"
echo "======================================="

if command -v lld-link >/dev/null 2>&1 || command -v ld.lld >/dev/null 2>&1; then
  if command -v llvm-windres >/dev/null 2>&1 || command -v x86_64-w64-mingw32-windres >/dev/null 2>&1 || command -v i686-w64-mingw32-windres >/dev/null 2>&1 || command -v windres >/dev/null 2>&1 || command -v llvm-rc >/dev/null 2>&1; then
    echo "Toolchain already available. Nothing to do."
    exit 0
  fi
fi

run_as_admin() {
  cmd="$1"
  if command -v pkexec >/dev/null 2>&1; then
    pkexec /bin/sh -c "$cmd"
    return $?
  fi
  if command -v sudo >/dev/null 2>&1; then
    sudo /bin/sh -c "$cmd"
    return $?
  fi
  echo "ERROR: Neither pkexec nor sudo is available."
  return 1
}

install_cmd=""
if command -v apt-get >/dev/null 2>&1; then
  install_cmd="apt-get update && apt-get install -y llvm lld mingw-w64 binutils-mingw-w64"
elif command -v dnf >/dev/null 2>&1; then
  install_cmd="dnf install -y llvm lld mingw64-binutils mingw32-binutils"
elif command -v pacman >/dev/null 2>&1; then
  install_cmd="pacman -Sy --noconfirm llvm lld mingw-w64-binutils"
elif command -v zypper >/dev/null 2>&1; then
  install_cmd="zypper --non-interactive install llvm lld mingw64-cross-binutils"
else
  echo "ERROR: Unsupported distribution. Install required tools manually:"
  echo "  - lld-link (or ld.lld)"
  echo "  - llvm-windres (or x86_64-w64-mingw32-windres / i686-w64-mingw32-windres / windres / llvm-rc)"
  exit 1
fi

echo "Installing dependencies..."
run_as_admin "$install_cmd"

echo "Re-checking toolchain..."
if ! (command -v lld-link >/dev/null 2>&1 || command -v ld.lld >/dev/null 2>&1); then
  echo "ERROR: lld-link/ld.lld not found after install."
  exit 1
fi
if ! (command -v llvm-windres >/dev/null 2>&1 || command -v x86_64-w64-mingw32-windres >/dev/null 2>&1 || command -v i686-w64-mingw32-windres >/dev/null 2>&1 || command -v windres >/dev/null 2>&1 || command -v llvm-rc >/dev/null 2>&1); then
  echo "ERROR: windres/llvm-rc not found after install."
  exit 1
fi

echo "SUCCESS: Supported IDS toolchain is now available."
exit 0
