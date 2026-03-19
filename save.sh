#!/bin/bash
# BearField Kalender — Quick save to GitHub
# Usage: bash save.sh "What changed"
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

MSG="${1:-Update}"
git add .
git commit -m "$MSG" && git push && echo "✅ Saved: $MSG" || echo "ℹ️  Nothing to save."
