# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, copy_metadata


project_root = Path(SPECPATH).resolve().parents[1]

datas = [
    (str(project_root / "static"), "static"),
    (str(project_root / "ssl"), "ssl"),
]
datas += collect_data_files("ua_parser_builtins")
datas += copy_metadata("user-agents")
datas += copy_metadata("ua-parser-builtins")

hiddenimports = [
    "flask_sock",
    "simple_websocket",
    "simple_websocket.ws",
    "ua_parser.user_agent_parser",
    "ua_parser_builtins",
]

a = Analysis(
    [str(project_root / "ankerctl.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ankerctl",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ankerctl",
)
