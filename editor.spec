# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for the sendMail WYSIWYG editor.
# Build: pyinstaller editor.spec
#
# NOTE: This is separate from sendMail.spec to keep the CLI binary lightweight.
# Qt/WebEngine adds ~80-150 MB to the bundle (Chromium engine).
#
# macOS: produces a .app bundle (required by Chromium's helper process model).
# Windows/Linux: produces a single windowed executable.

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None

# Chromium resource files (ICU data, translations, etc.) MUST be bundled
# or QWebEngineView fails silently at runtime.
qt_webengine_datas = collect_data_files("PyQt6.QtWebEngineCore", include_py_files=False)

base_dir = Path(SPECPATH).resolve() / "src"
project_dir = Path(SPECPATH).resolve()

editor_asset_datas = [
    (str(path), "editor_assets")
    for path in (base_dir / "editor_assets").rglob("*")
    if path.is_file()
]
css_datas = [
    (str(path), "css")
    for path in (project_dir / "css").rglob("*")
    if path.is_file()
]

# Bundle src/ .py files as data so they can be imported at runtime
src_module_files = [
    (str(base_dir / "sendMail.py"), "."),
    (str(base_dir / "googleDriveLib.py"), "."),
    (str(base_dir / "filter_validator.py"), "."),
]

gs_datas, gs_binaries, gs_imports = collect_all("getSecrets")

a = Analysis(
    ["src/editor.py"],
    pathex=["src"],
    binaries=gs_binaries,
    datas=editor_asset_datas + css_datas + src_module_files + gs_datas + qt_webengine_datas,
    hiddenimports=gs_imports + [
        "PyQt6.QtWebEngineWidgets",
        "PyQt6.QtWebEngineCore",
        "PyQt6.QtWebChannel",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.sip",
        "html2text",
        "bs4",
        "markdown2",
        "yaml",
        "getSecrets",
    ] + collect_submodules("PyQt6"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="sendMailEditor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # windowed app (no console window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="images/mail.png" if sys.platform != "linux" else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="sendMailEditor",
)

# macOS: bundle as .app (required for Chromium helper processes)
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="sendMailEditor.app",
        icon="images/mail.png",
        bundle_identifier="be.sendmail.editor",
        info_plist={
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": True,  # force light mode
        },
    )
