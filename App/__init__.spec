# -*- mode: python ; coding: utf-8 -*-


import os

spec_root = os.path.abspath(SPECPATH)

a = Analysis(
    ['__init__.py', 'fileSys.py', 'QEHelper.py', 'customElements.py', 'convert.py'],
    pathex=[spec_root],
    binaries=[],
    datas=[
        (os.path.join(spec_root, 'Images'), 'Images'),
        (os.path.join(spec_root, 'pref'), 'pref'),
        (os.path.join(spec_root, 'TamberTool'), 'TamberTool'),
    ],
    hiddenimports=[
        'PIL._tkinter_finder',
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'json',
        'os',
        'sys',
        'tempfile',
        'functools',
        'collections',
        'platform',
        'subprocess',
        'shutil',
        'io',
    ],
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
    name='Quad-Exporter',
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
    icon=os.path.join(spec_root, 'Images', 'Logo.png'),
)
