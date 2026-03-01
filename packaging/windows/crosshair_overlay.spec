# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None
script_dir = os.path.dirname(os.path.abspath(SPECPATH))
repo_root = os.path.join(script_dir, '..', '..')

a = Analysis(
    [os.path.join(repo_root, 'windows', 'crosshair_overlay.py')],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['pystray._win32'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CrosshairOverlay',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(script_dir, 'crosshair-overlay.ico'),
)
