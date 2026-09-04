# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(SPECPATH)
SRC = ROOT / "src" / "prize_bond_checker"

a = Analysis(
    ["check_prize_bonds.py"],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[
        (str(SRC / "web" / "templates"), "prize_bond_checker/web/templates"),
        (str(SRC / "web" / "static"), "prize_bond_checker/web/static"),
    ],
    hiddenimports=[
        "flask",
        "jinja2",
        "prize_bond_checker.web.app",
        "prize_bond_checker.scheduler",
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
    name="prize-bond-checker",
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
