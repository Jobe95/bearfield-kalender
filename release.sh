#!/bin/bash
# BearField Kalender — Publish a new release
# Usage: bash release.sh v1.1 "What changed"
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VERSION="${1}"; NOTES="${2:-New release}"
[ -z "$VERSION" ] && { echo "Usage: bash release.sh v1.1 'What changed'"; exit 1; }

sed -i '' "s/^VERSION = \".*\"/VERSION = \"$VERSION\"/" menuapp.py
echo "✅ VERSION updated to $VERSION in menuapp.py"

git add .
git commit -m "Release $VERSION — $NOTES"
git tag "$VERSION"
git push && git push --tags
echo "✅ Pushed to GitHub with tag $VERSION"

gh release create "$VERSION" \
    --title "BearField Kalender $VERSION" \
    --notes "$NOTES"

echo ""
echo "🎉 Version $VERSION publicerad!"
