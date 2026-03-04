# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules


project_root = Path(SPECPATH).resolve()
icon_ico = project_root / "fl_editor" / "images" / "FLAtlas-Logo.ico"
icon_png = project_root / "fl_editor" / "images" / "FLAtlas-Logo-256.png"
tools_root = project_root / "tools"
ids_toolchain_installer = project_root / "scripts" / "install_ids_toolchain_windows.cmd"

datas = collect_data_files("fl_editor")
if tools_root.exists():
    # Bundle optional local toolchain files (e.g. llvm-windres/lld-link) under "tools/".
    for src in tools_root.rglob("*"):
        if not src.is_file():
            continue
        rel_parent = src.relative_to(tools_root).parent
        target_dir = Path("tools") / rel_parent
        datas.append((str(src), str(target_dir)))
if ids_toolchain_installer.exists():
    datas.append((str(ids_toolchain_installer), "scripts"))
hiddenimports = []
hiddenimports += collect_submodules("fl_editor")
hiddenimports += [
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebChannel",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DExtras",
]
pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all("PySide6")
datas += pyside6_datas
hiddenimports += pyside6_hiddenimports


a = Analysis(
    ["fl_atlas.py"],
    pathex=[str(project_root)],
    binaries=pyside6_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FLAtlas",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_ico) if icon_ico.exists() else (str(icon_png) if icon_png.exists() else None),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FLAtlas",
)
