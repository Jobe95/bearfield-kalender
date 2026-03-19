#!/bin/bash
# BearField Kalender — Set up Git + GitHub
# Run once: bash setup_git.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🐻 BearField Kalender — Sätter upp Git + GitHub"

command -v git &>/dev/null || { echo "❌ Git saknas: brew install git"; exit 1; }

if ! command -v gh &>/dev/null; then
    echo "📦 Installerar GitHub CLI..."
    brew install gh
fi

gh auth status &>/dev/null || gh auth login

cat > .gitignore << 'EOF'
build/
dist/
__pycache__/
*.pyc
.DS_Store
done_state.json
EOF

[ -d .git ] || git init
git add .
git commit -m "Initial commit — BearField Kalender v1.0" 2>/dev/null \
    || git commit --allow-empty -m "Initial commit"

gh repo create "bearfield-kalender" \
    --private \
    --source=. \
    --remote=origin \
    --push \
    --description "BearField IT AB — Bolagskalender och deadline-notiser" 2>/dev/null \
    || { git push -u origin main 2>/dev/null || git push -u origin master; }

echo ""
echo "✅ Pushat till GitHub!"
gh repo view --json url -q .url 2>/dev/null || true
echo ""
echo "Vanliga kommandon:"
echo "  bash save.sh 'Beskrivning'       — spara ändringar"
echo "  bash release.sh v1.1 'Nyhet'     — publicera ny version"
echo "  git log --oneline                — se historik"
