#!/bin/sh

cd "$(git rev-parse --show-toplevel)"
rm -fr ./dist ./build

# Build onefile executable
echo "Building onefile executable..."
pyinstaller editor.spec

# Wrap executable in .app bundle
echo "Creating .app bundle..."
bash scripts/wrap_onefile_as_app.sh . sendMailEditor_bin sendMailEditor images/mail.png be.sendmail.editor

# Clean up temporary binary
rm dist/sendMailEditor_bin

echo "✓ Build complete: dist/sendMailEditor.app"
