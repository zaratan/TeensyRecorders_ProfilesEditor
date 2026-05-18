# -*- mode: python ; coding: utf-8 -*-
import os
import platform
import tomllib

datas = [
    ('initial_profile/Profiles.ini', 'initial_profile/'),
    ('img/logo_PR.png', 'img/'),
]

with open('pyproject.toml', 'rb') as f:
    version = tomllib.load(f)['project']['version']

codesign_id = os.environ.get('APPLE_SIGNING_IDENTITY', None) or None
entitlements = 'entitlements.plist' if codesign_id else None

a = Analysis(
    ['launcher.py'],
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

if platform.system() == 'Darwin':
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='TeensyProfilesEditor',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=codesign_id,
        entitlements_file=entitlements,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='TeensyProfilesEditor',
    )
    app = BUNDLE(
        coll,
        name='TeensyProfilesEditor.app',
        icon='img/logo_PR.icns',
        bundle_identifier='com.zaratan.teensyprofileseditor',
        info_plist={
            'CFBundleName': 'TeensyProfilesEditor',
            'CFBundleDisplayName': 'TeensyRecorders Profiles Editor',
            'CFBundleVersion': version,
            'CFBundleShortVersionString': version,
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '11.0',
        },
        codesign_identity=codesign_id,
        entitlements_file=entitlements,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='TeensyProfilesEditor',
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
        icon='img/logo_PR_ico.ico' if os.path.exists('img/logo_PR_ico.ico') else None,
    )
