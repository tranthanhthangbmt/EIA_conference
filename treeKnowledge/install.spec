# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

block_cipher = None

hidden_streamlit_auth = collect_submodules('streamlit_authenticator')

a = Analysis(
    ['launcher.py'],          # 🔴 ĐIỂM QUAN TRỌNG: dùng launcher.py, KHÔNG dùng app.py
    pathex=['.'],
    binaries=[],
    datas=[
        ('app.py', '.'),                  # 🔴 COPY app.py ra dist/
        ('pages/*', 'pages'),
        ('knowledge/*', 'knowledge'),
        ('config.yaml', '.'),
        ('user_progress.db', '.'),
    ] + copy_metadata('streamlit'),
    hiddenimports=hidden_streamlit_auth,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='TreeKnowledge',   # tên exe
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,           # nên để True để xem log
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TreeKnowledge'
)
