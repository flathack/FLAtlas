# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


project_root = Path(SPECPATH).resolve()
tools_root = project_root / "tools"
ids_toolchain_installer = project_root / "scripts" / "install_ids_toolchain_windows.cmd"

datas = collect_data_files("fl_editor")
if tools_root.exists():
    for src in tools_root.rglob("*"):
        if not src.is_file():
            continue
        rel_parent = src.relative_to(tools_root).parent
        datas.append((str(src), str(Path("tools") / rel_parent)))
if ids_toolchain_installer.exists():
    datas.append((str(ids_toolchain_installer), "scripts"))

hiddenimports = collect_submodules("fl_editor")
hiddenimports += [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DExtras",
]


a = Analysis(
    ["fl_atlas.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebChannel",
        "PySide6.QtWebView",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuick3D",
        "PySide6.QtSql",
        "PySide6.QtDesigner",
        "PySide6.QtBluetooth",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtGraphs",
        "PySide6.QtHelp",
        "PySide6.QtMultimedia",
        "PySide6.QtPdf",
        "PySide6.QtPositioning",
        "PySide6.QtSensors",
        "PySide6.QtTextToSpeech",
    ],
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
