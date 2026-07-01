#!/usr/bin/env python3
"""
Nuitka build script for sendMailEditor — replaces editor.spec (PyInstaller).

Usage:
    python build_editor.py [--dry-run]

Produces:
    dist_nuitka/editor.dist/          (Linux/Windows)
    dist_nuitka/sendMailEditor.app/   (macOS)

Requires:
    pip install nuitka ordered-set zstandard   # zstandard speeds up compression
    # macOS icon: convert images/mail.png to images/mail.icns first
    # Windows icon: convert images/mail.png to images/mail.ico first
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DIST = ROOT / "dist_nuitka"


PLATFORM: str = sys.platform  # named var prevents Pyright static branch elimination


def icon_path() -> str | None:
    """Return platform-appropriate icon path, or None if not found."""
    if PLATFORM == "darwin":
        p = ROOT / "images" / "mail.icns"
    elif PLATFORM == "win32":
        p = ROOT / "images" / "mail.ico"
    else:
        return None
    return str(p) if p.exists() else None


def build() -> None:
    dry_run = "--dry-run" in sys.argv

    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        # ── Core ──────────────────────────────────────────────────────────
        "--standalone",  # self-contained directory
        "--enable-plugin=pyside6",  # handles QtWebEngineProcess + qt.conf
        "--nofollow-import-to=pytest,_pytest",
        # ── Qt WebEngine resources (auto-handled by plugin, but be explicit) ─
        "--include-qt-plugins=platforms,styles,imageformats,tls",
        # ── Data directories ──────────────────────────────────────────────
        f"--include-data-dir={SRC / 'editor_assets'}=editor_assets",
        f"--include-data-dir={ROOT / 'css'}=css",
        # ── Companion .py modules (loaded at runtime via importlib/exec) ──
        f"--include-data-files={SRC / 'sendMail.py'}=sendMail.py",
        f"--include-data-files={SRC / 'googleDriveLib.py'}=googleDriveLib.py",
        f"--include-data-files={SRC / 'filter_validator.py'}=filter_validator.py",
        f"--include-data-files={SRC / 'profile_manager.py'}=profile_manager.py",
        # ── Hidden imports ────────────────────────────────────────────────
        "--include-module=getSecrets",
        "--include-module=html2text",
        "--include-module=bs4",
        "--include-module=markdown2",
        "--include-module=yaml",
        "--include-module=PIL",
        "--include-module=PIL.Image",
        "--include-module=gspread",
        "--include-module=gspread.auth",
        "--include-module=googleapiclient",
        "--include-module=googleapiclient.discovery",
        "--include-module=googleapiclient.http",
        "--include-module=google.auth",
        "--include-module=google.auth.transport",
        "--include-module=google.auth.transport.requests",
        "--include-module=google.api_core",
        "--include-module=google.api_core.gapic_v1",
        "--include-module=requests",
        # ── Output ────────────────────────────────────────────────────────
        f"--output-dir={DIST}",
        "--output-filename=sendMailEditor",
    ]

    # ── Platform-specific ─────────────────────────────────────────────────
    if PLATFORM == "darwin":
        cmd += [
            "--macos-create-app-bundle",
            "--macos-app-name=sendMailEditor",
            "--macos-app-version=1.13.2",
            # Chromium requires these entitlements on macOS 10.15+
            "--macos-signed-app-name=com.hc.sendMailEditor",
        ]
    elif PLATFORM == "win32":
        cmd += [
            "--windows-disable-console",
            "--windows-company-name=HC",
            "--windows-product-name=sendMailEditor",
            "--windows-file-version=1.13.2.0",
            "--windows-product-version=1.13.2.0",
        ]
    # Linux: no extra flags needed

    icon = icon_path()
    if icon:
        cmd.append(f"--macos-app-icon={icon}" if PLATFORM == "darwin" else f"--windows-icon-from-ico={icon}")

    # ── Entry point ───────────────────────────────────────────────────────
    cmd.append(str(SRC / "editor.py"))

    print("Nuitka command:")
    print(" \\\n  ".join(cmd))
    print()

    if dry_run:
        print("[dry-run] Not executing.")
        return

    DIST.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(cmd, check=False)
    sys.exit(result.returncode)


if __name__ == "__main__":
    build()
