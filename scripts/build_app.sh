#!/bin/sh
# Build sendMailEditor.app using Nuitka (replaces PyInstaller editor.spec)

set -e
cd "$(git rev-parse --show-toplevel)"

# Convert icon if needed
if [ ! -f images/mail.icns ]; then
  echo "Converting icon..."
  mkdir -p images/mail.iconset
  sips -z 16  16  images/mail.png --out images/mail.iconset/icon_16x16.png
  sips -z 32  32  images/mail.png --out images/mail.iconset/icon_32x32.png
  sips -z 128 128 images/mail.png --out images/mail.iconset/icon_128x128.png
  sips -z 256 256 images/mail.png --out images/mail.iconset/icon_256x256.png
  sips -z 512 512 images/mail.png --out images/mail.iconset/icon_512x512.png
  iconutil -c icns images/mail.iconset -o images/mail.icns
fi

rm -rf dist_nuitka
echo "Building with Nuitka..."
python build_editor.py

echo "✓ Build complete: dist_nuitka/editor.app"
