#!/bin/bash
# BearField IT — Publicera ny version
# Användning: bash release.sh v1.1 "Lade till testa notis och uppdateringskoll"
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VERSION="${1}"
NOTES="${2:-Ny version}"

if [ -z "$VERSION" ]; then
    echo "Användning: bash release.sh v1.1 'Vad som är nytt'"
    exit 1
fi

# 1. Uppdatera VERSION i menuapp.py
sed -i '' "s/^VERSION = \".*\"/VERSION = \"$VERSION\"/" menuapp.py
echo "✅ VERSION uppdaterad till $VERSION i menuapp.py"

# 2. Commit + tag + push
git add .
git commit -m "Release $VERSION — $NOTES"
git tag "$VERSION"
git push && git push --tags
echo "✅ Pushat till GitHub med tagg $VERSION"

# 3. Skapa GitHub Release
gh release create "$VERSION" \
    --title "BearField Kalender $VERSION" \
    --notes "$NOTES"

echo ""
echo "🎉 Version $VERSION publicerad!"
echo "   Appen notifierar automatiskt om uppdatering nästa gång den startar."
