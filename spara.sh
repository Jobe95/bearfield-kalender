#!/bin/bash
# Snabbspara ändringar till GitHub
# Användning: bash spara.sh "Vad du ändrade"
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

MSG="${1:-Uppdatering}"

git add .
git commit -m "$MSG" && git push && echo "✅ Sparat: $MSG" || echo "ℹ️  Inga ändringar att spara."
