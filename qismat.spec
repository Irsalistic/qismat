# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(SPECPATH)
SRC = ROOT / "src" / "qismat"

a = Analysis(
    ["check_prize_bonds.py"],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[
        (str(SRC / "web" / "templates"), "qismat/web/templates"),
        (str(SRC / "web" / "static"), "qismat/web/static"),
    ],
    hiddenimports=[
        "flask",
        "jinja2",
        "qismat.web.app",
        "qismat.scheduler",
    ],
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
    a.binaries,
    a.datas,
    [],
    name="qismat",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
