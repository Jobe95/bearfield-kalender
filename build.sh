#!/bin/bash
# BearField Kalender — Build Mac app with py2app
# Usage: bash build.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🐻 BearField Kalender — Bygger Mac-app..."

if ! python3 -c "import py2app" 2>/dev/null; then
    echo "📦 Installerar py2app..."
    pip3 install py2app --break-system-packages
fi

rm -rf build dist
python3 setup.py py2app --quiet 2>&1 | grep -v "^$" || true

APP_PATH="$SCRIPT_DIR/dist/BearField Kalender.app"
[ -d "$APP_PATH" ] || { echo "❌ Build misslyckades."; exit 1; }
echo "✅ App byggd: dist/BearField Kalender.app"

read -p "📂 Installera i /Applications? (j/n) " -n 1 -r; echo
if [[ $REPLY =~ ^[Jj]$ ]]; then
    rm -rf "/Applications/BearField Kalender.app"
    cp -r "$APP_PATH" "/Applications/"
    echo "✅ Installerad i /Applications"
    echo "🚀 Starta: open '/Applications/BearField Kalender.app'"
else
    echo "🚀 Starta: open '$APP_PATH'"
fi
