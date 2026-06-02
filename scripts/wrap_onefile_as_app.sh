#!/bin/bash
# Wrap PyInstaller onefile executable as macOS .app bundle

set -e

DIST_DIR="${1:-.}/dist"
EXEC_NAME="${2:-sendMailEditor_bin}"
APP_NAME="${3:-sendMailEditor}"
ICON_PATH="${4:-images/mail.png}"
BUNDLE_ID="${5:-be.sendmail.editor}"

EXEC_PATH="$DIST_DIR/$EXEC_NAME"
APP_PATH="$DIST_DIR/$APP_NAME.app"

if [[ ! -f "$EXEC_PATH" ]]; then
    echo "Error: Executable not found: $EXEC_PATH" >&2
    exit 1
fi

echo "Creating $APP_NAME.app bundle..."

# Remove old app if it exists
rm -rf "$APP_PATH"

# Create app bundle structure
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

# Copy executable
cp "$EXEC_PATH" "$APP_PATH/Contents/MacOS/$APP_NAME"
chmod +x "$APP_PATH/Contents/MacOS/$APP_NAME"

# Create Info.plist
cat > "$APP_PATH/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDisplayName</key>
    <string>$APP_NAME</string>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
    <key>CFBundleIdentifier</key>
    <string>$BUNDLE_ID</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>0.0.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSRequiresAquaSystemAppearance</key>
    <true/>
</dict>
</plist>
EOF

# Copy icon if provided
if [[ -f "$ICON_PATH" ]]; then
    cp "$ICON_PATH" "$APP_PATH/Contents/Resources/"
    # Update plist with icon reference
    sed -i '' -e "s|</dict>|    <key>CFBundleIconFile</key>\\n    <string>$(basename "$ICON_PATH")</string>\\n</dict>|" "$APP_PATH/Contents/Info.plist"
fi

echo "✓ Created $APP_PATH"
ls -lhd "$APP_PATH"
