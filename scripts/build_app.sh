#!/bin/sh

cd "$(git rev-parse --show-toplevel)"
rm -fr ./dist ./build
# create the .app file
pyinstaller editor.spec

## Create a folder (named dmg) to prepare our DMG in (if it doesn't already exist).
mkdir -p dist/dmg
# Empty the dmg folder.
rm -r dist/dmg/*
## Copy the app bundle to the dmg folder.
cp -r dist/sendMail.app dist/dmg
## If the DMG already exists, delete it.
#test -f "dist/sendMail.dmg" && rm "dist/sendMail.dmg"
#create-dmg \
#  --volname "sendMail" \
#  --volicon "images/sendMail.icns" \
#  --window-pos 200 120 \
#  --window-size 600 300 \
#  --icon-size 100 \
#  --icon "o2eb.app" 175 120 \
#  --hide-extension "o2eb.app" \
#  --app-drop-link 425 120 \
#  "dist/o2eb.dmg" \
#  "dist/dmg/"
