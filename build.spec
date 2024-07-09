# -*- mode: python ; coding: utf-8 -*-
block_cipher = None
from PyInstaller.utils.hooks import collect_data_files

fua_data = collect_data_files('fake_useragent', include_py_files=True)
datas = [
            ('./res/github-mark.png', 'res/'),
            ('./res/github-mark-white.png', 'res/'),
            ('./res/image2.jpg', 'res/')
        ]
datas.extend(fua_data)

a = Analysis(
    ['mainGUI.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='DBDRegion.exe',
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
    version='res\\version_file.txt',
    uac_admin=True,
    icon=['res\\image2.ico'],
)
