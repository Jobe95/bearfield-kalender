#!/bin/bash
# BearField IT — Sätt upp Git + GitHub
# Kör en gång: bash git_setup.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🐻 BearField IT — Sätter upp Git + GitHub"
echo ""

# 1. Kontrollera att git är installerat
if ! command -v git &>/dev/null; then
    echo "❌ Git saknas. Installera med: brew install git"
    exit 1
fi

# 2. Kontrollera att gh (GitHub CLI) är installerat
if ! command -v gh &>/dev/null; then
    echo "📦 Installerar GitHub CLI (gh)..."
    brew install gh
fi

# 3. Logga in på GitHub om det behövs
if ! gh auth status &>/dev/null; then
    echo "🔑 Loggar in på GitHub..."
    gh auth login
fi

# 4. Skapa .gitignore
cat > .gitignore << 'EOF'
build/
dist/
__pycache__/
*.pyc
.DS_Store
done_state.json
EOF
echo "✅ .gitignore skapad (done_state.json ignoreras — den är personlig)"

# 5. Initiera git om det inte redan finns
if [ ! -d .git ]; then
    git init
    echo "✅ Git initierat"
fi

# 6. Första commit
git add .
git commit -m "Initial commit — BearField Kalender v1.0" 2>/dev/null || \
git commit --allow-empty -m "Initial commit — BearField Kalender v1.0"

# 7. Skapa GitHub-repo och pusha
REPO_NAME="bearfield-kalender"
echo ""
echo "📡 Skapar GitHub-repo '$REPO_NAME'..."
gh repo create "$REPO_NAME" \
    --private \
    --source=. \
    --remote=origin \
    --push \
    --description "BearField IT AB — Bolagskalender och deadline-notiser" \
    2>/dev/null || {
    # Repo finns redan — pusha bara
    git push -u origin main 2>/dev/null || git push -u origin master
}

echo ""
echo "✅ Pushat till GitHub!"
REPO_URL=$(gh repo view --json url -q .url 2>/dev/null || echo "github.com")
echo "   $REPO_URL"
echo ""
echo "📌 Vanliga kommandon:"
echo "   git add . && git commit -m 'Beskrivning' && git push   — spara ändringar"
echo "   git log --oneline                                       — se historik"
echo "   git diff                                               — se vad som ändrats"
