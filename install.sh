#!/bin/bash
# BearField Kalender — Installer
# Usage:
#   Latest version:   curl -fsSL https://raw.githubusercontent.com/Jobe95/bearfield-kalender/main/install.sh | bash
#   Specific version: curl -fsSL https://raw.githubusercontent.com/Jobe95/bearfield-kalender/main/install.sh | bash -s v1.1

set -e

REPO="Jobe95/bearfield-kalender"
INSTALL_DIR="$HOME/Applications/BearFieldKalender"
GITHUB_API="https://api.github.com/repos/$REPO"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${BLUE}ℹ️  $1${RESET}"; }
success() { echo -e "${GREEN}✅ $1${RESET}"; }
warn()    { echo -e "${YELLOW}⚠️  $1${RESET}"; }
error()   { echo -e "${RED}❌ $1${RESET}"; exit 1; }

echo -e "${BOLD}"
echo "  🐻 BearField Kalender — Installationsskript"
echo -e "${RESET}"

# ── Check dependencies ─────────────────────────────────────────────────────────
info "Kontrollerar beroenden..."

command -v python3 &>/dev/null || error "Python 3 saknas. Installera från https://python.org"
command -v git    &>/dev/null || error "Git saknas. Installera med: brew install git"
command -v pip3   &>/dev/null || error "pip3 saknas."

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python $PYTHON_VERSION hittad"

# ── Resolve version ────────────────────────────────────────────────────────────
REQUESTED_VERSION="${1:-}"

if [ -z "$REQUESTED_VERSION" ]; then
    info "Hämtar senaste versionen från GitHub..."
    LATEST=$(curl -fsSL "$GITHUB_API/releases/latest" \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['tag_name'])" 2>/dev/null || echo "")
    if [ -z "$LATEST" ]; then
        warn "Kunde inte hämta release — använder main-branch"
        VERSION="main"
        USE_BRANCH=true
    else
        VERSION="$LATEST"
        USE_BRANCH=false
    fi
else
    VERSION="$REQUESTED_VERSION"
    USE_BRANCH=false
fi

info "Installerar version: ${BOLD}$VERSION${RESET}"

# ── Clone or update ────────────────────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
    info "Befintlig installation hittad — uppdaterar..."
    git -C "$INSTALL_DIR" fetch --tags -q
    if [ "$USE_BRANCH" = true ]; then
        git -C "$INSTALL_DIR" pull -q
    else
        git -C "$INSTALL_DIR" checkout -q "$VERSION"
    fi
    success "Uppdaterad till $VERSION"
else
    info "Klonar repo till $INSTALL_DIR..."
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone -q "https://github.com/$REPO.git" "$INSTALL_DIR"
    if [ "$USE_BRANCH" != true ]; then
        git -C "$INSTALL_DIR" checkout -q "$VERSION"
    fi
    success "Klonat till $INSTALL_DIR"
fi

# ── Patch GITHUB_USER in menuapp.py ───────────────────────────────────────────
sed -i '' 's/GITHUB_USER = "DITT_GITHUB_USERNAME"/GITHUB_USER = "Jobe95"/' \
    "$INSTALL_DIR/menuapp.py" 2>/dev/null || true

# ── Set permissions ────────────────────────────────────────────────────────────
info "Sätter behörigheter..."
find "$INSTALL_DIR" -name "*.sh" -exec chmod +x {} \;
find "$INSTALL_DIR" -name "*.py" -exec chmod +x {} \;

# Create done_state.json if missing
[ -f "$INSTALL_DIR/done_state.json" ] || echo '{}' > "$INSTALL_DIR/done_state.json"
success "Behörigheter satta"

# ── Install Python dependencies ────────────────────────────────────────────────
info "Installerar rumps..."
pip3 install rumps --break-system-packages -q 2>/dev/null \
    || pip3 install rumps -q 2>/dev/null \
    || error "Kunde inte installera rumps. Prova: pip3 install rumps --break-system-packages"
success "rumps installerat"

# ── Set up launchd daily notifications ────────────────────────────────────────
PLIST_SRC="$INSTALL_DIR/se.bearfieldit.deadlinenotis.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/se.bearfieldit.deadlinenotis.plist"

if [ -f "$PLIST_SRC" ]; then
    info "Konfigurerar dagliga notiser (08:00)..."
    sed "s|PLACEHOLDER_PATH|$INSTALL_DIR|g" "$PLIST_SRC" > "$PLIST_DEST"
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    launchctl load "$PLIST_DEST"
    success "Dagliga notiser aktiverade"
fi

# ── Set up autostart ───────────────────────────────────────────────────────────
info "Konfigurerar autostart vid inloggning..."
MENU_PLIST="$HOME/Library/LaunchAgents/se.bearfieldit.menuapp.plist"
cat > "$MENU_PLIST" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>se.bearfieldit.menuapp</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$INSTALL_DIR/menuapp.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/bearfield_menu.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/bearfield_menu_error.log</string>
</dict>
</plist>
PLISTEOF
launchctl unload "$MENU_PLIST" 2>/dev/null || true
launchctl load "$MENU_PLIST"
success "Autostart aktiverad"

# ── Start the menu app ─────────────────────────────────────────────────────────
info "Startar BearField Kalender..."
pkill -f "menuapp.py" 2>/dev/null || true
sleep 1
nohup python3 "$INSTALL_DIR/menuapp.py" > /tmp/bearfield_menu.log 2>&1 &
sleep 2

if pgrep -f "menuapp.py" > /dev/null; then
    success "Menyappen körs — björnen 🐻 syns i menyraden"
else
    warn "Appen startade inte automatiskt. Starta manuellt:"
    echo "   python3 \"$INSTALL_DIR/menuapp.py\""
fi

# ── Done ───────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}🎉 Installation klar!${RESET}"
echo ""
echo -e "  Version:       ${BOLD}$VERSION${RESET}"
echo -e "  Installerad i: ${BOLD}$INSTALL_DIR${RESET}"
echo ""
echo -e "${YELLOW}  Avinstallera:${RESET}"
echo "    launchctl unload $PLIST_DEST && rm $PLIST_DEST"
echo "    launchctl unload $MENU_PLIST && rm $MENU_PLIST"
echo "    rm -rf $INSTALL_DIR"
echo ""
