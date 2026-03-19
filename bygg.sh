#!/bin/bash
# BearField IT — Bygg Mac-app
# Kör från projektmappen: bash bygg.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🐻 BearField IT — Bygger Mac-app..."
echo ""

# 1. Installera py2app om det saknas
if ! python3 -c "import py2app" 2>/dev/null; then
    echo "📦 Installerar py2app..."
    pip3 install py2app --break-system-packages
fi

# 2. Rensa gamla byggen
rm -rf build dist

# 3. Bygg appen
echo "🔨 Bygger .app..."
python3 setup.py py2app --quiet 2>&1 | grep -v "^$" || true

APP_PATH="$SCRIPT_DIR/dist/BearField Kalender.app"

if [ ! -d "$APP_PATH" ]; then
    echo "❌ Något gick fel — dist/-mappen saknas."
    exit 1
fi

echo "✅ App byggd: dist/BearField Kalender.app"
echo ""

# 4. Flytta till Applications?
read -p "📂 Vill du installera appen i /Applications? (j/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Jj]$ ]]; then
    rm -rf "/Applications/BearField Kalender.app"
    cp -r "$APP_PATH" "/Applications/"
    echo "✅ Installerad i /Applications/BearField Kalender.app"
    echo ""
    echo "🚀 Starta appen:"
    echo "   open '/Applications/BearField Kalender.app'"
else
    echo ""
    echo "🚀 Starta appen:"
    echo "   open '$APP_PATH'"
fi

echo ""
echo "🎉 Klart! Björnen 🐻 dyker upp i menyraden när appen körs."
echo ""
echo "💡 Tips: Lägg till i Inloggningsobjekt under"
echo "   Systeminställningar → Allmänt → Inloggningsobjekt"
echo "   så startar den automatiskt."
