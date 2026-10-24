#!/bin/sh
# Free self-signed code signing for sendMailEditor

set -e

APP_PATH="${1:-../dist_nuitka/editor.app}"
IDENTITY_NAME="sendMailEditor Developer"

# Check if certificate exists, if not create one
if ! security find-identity -v -p codesigning | grep -q "$IDENTITY_NAME"; then
    echo "Creating self-signed certificate..."
    
    # Create certificate and key
    openssl req -x509 -newkey rsa:2048 -keyout cert.key -out cert.crt \
        -days 3650 -nodes -subj "/CN=$IDENTITY_NAME/O=Local Development/OU=sendMailEditor/"
    
    # Create p12 file
    openssl pkcs12 -export -out cert.p12 -inkey cert.key -in cert.crt \
        -passout pass: -name "$IDENTITY_NAME"
    
    # Import certificate (requires GUI or manual import)
    echo "⚠️  Please double-click cert.p12 to import into Keychain Access"
    echo "   Then run this script again."
    exit 1
fi

echo "Signing $APP_PATH with identity: $IDENTITY_NAME"
ENTITLEMENTS="$(dirname "$0")/editor.entitlements"
codesign --force --deep --sign "$IDENTITY_NAME" --timestamp=none \
    --options runtime --entitlements "$ENTITLEMENTS" "$APP_PATH"
codesign -v --deep --verbose=2 "$APP_PATH"

echo "✓ Signed successfully: $APP_PATH"
