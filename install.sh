#!/bin/bash
# BearField Kalender — Installationsskript
# Användning:
#   Senaste versionen:  curl -fsSL https://raw.githubusercontent.com/Jobe95/bearfield-kalender/main/install.sh | bash
#   Specifik version:   curl -fsSL https://raw.githubusercontent.com/Jobe95/bearfield-kalender/main/install.sh | bash -s v1.1

set -e

REPO="Jobe95/bearfield-kalender"
INSTALL_DIR="$HOME/Applications/BearFieldKalender"
GITHUB_API="https://api.github.com/repos/$REPO"

# ── Färger ─────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${BLUE}ℹ️  $1${RESET}"; }
success() { echo -e "${GREEN}✅ $1${RESET}"; }
warn()    { echo -e "${YELLOW}⚠️  $1${RESET}"; }
error()   { echo -e "${RED}❌ $1${RESET}"; exit 1; }

echo -e "${BOLD}"
echo "  🐻 BearField Kalender — Installationsskript"
echo -e "${RESET}"

# ── Kontrollera beroenden ──────────────────────────────────────────────────────
info "Kontrollerar beroenden..."

if ! command -v python3 &>/dev/null; then
    error "Python 3 saknas. Installera från https://python.org"
fi
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python $PYTHON_VERSION hittad"

if ! command -v git &>/dev/null; then
    error "Git saknas. Installera med: brew install git"
fi

if ! command -v pip3 &>/dev/null; then
    error "pip3 saknas."
fi

# ── Bestäm version ─────────────────────────────────────────────────────────────
REQUESTED_VERSION="${1:-}"

if [ -z "$REQUESTED_VERSION" ]; then
    info "Hämtar senaste versionen från GitHub..."
    LATEST=$(curl -fsSL "$GITHUB_API/releases/latest" | python3 -c "import sys,json; print(json.load(sys.stdin)['tag_name'])" 2>/dev/null || echo "")
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

# ── Installera eller uppdatera ─────────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
    info "Befintlig installation hittad — uppdaterar..."
    git -C "$INSTALL_DIR" fetch --tags -q
    git -C "$INSTALL_DIR" reset --hard -q 2>/dev/null || true
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

# ── Uppdatera GITHUB_USER i menuapp.py ────────────────────────────────────────
sed -i '' 's/GITHUB_USER = "DITT_GITHUB_USERNAME"/GITHUB_USER = "Jobe95"/' \
    "$INSTALL_DIR/menuapp.py" 2>/dev/null || true

# ── Sätt behörigheter ─────────────────────────────────────────────────────────
info "Sätter behörigheter..."
find "$INSTALL_DIR" -name "*.sh" -exec chmod +x {} \;
find "$INSTALL_DIR" -name "*.py" -exec chmod +x {} \;

# Skapa state.json om den saknas
[ -f "$INSTALL_DIR/state.json" ] || echo '{}' > "$INSTALL_DIR/state.json"
success "Behörigheter satta"

# ── Installera Python-beroenden ────────────────────────────────────────────────
info "Installerar rumps..."
if pip3 install rumps --break-system-packages -q 2>/dev/null; then
    success "rumps installerat"
elif pip3 install rumps -q 2>/dev/null; then
    success "rumps installerat"
else
    error "Kunde inte installera rumps. Prova: pip3 install rumps --break-system-packages"
fi

# ── Sätt upp launchd-notiser ───────────────────────────────────────────────────
info "Konfigurerar dagliga notiser (08:00)..."
PLIST_SRC="$INSTALL_DIR/se.bearfieldit.deadlinenotis.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/se.bearfieldit.deadlinenotis.plist"

if [ -f "$PLIST_SRC" ]; then
    sed "s|PLACEHOLDER_PATH|$INSTALL_DIR|g" "$PLIST_SRC" > "$PLIST_DEST"
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    launchctl load "$PLIST_DEST"
    success "Dagliga notiser aktiverade"
else
    warn "Plist-fil saknas — notiser ej konfigurerade"
fi

# ── Starta menyappen ───────────────────────────────────────────────────────────
info "Startar BearField Kalender..."

# Stoppa eventuell gammal instans
pkill -f "menuapp.py" 2>/dev/null || true
sleep 1

# Starta i bakgrunden
nohup python3 "$INSTALL_DIR/menuapp.py" > /tmp/bearfield_menu.log 2>&1 &
sleep 2

if pgrep -f "menuapp.py" > /dev/null; then
    success "Menyappen körs — björnen 🐻 syns i menyraden"
else
    warn "Appen startade inte automatiskt. Starta manuellt:"
    echo "   python3 \"$INSTALL_DIR/menuapp.py\""
fi

# ── Autostart vid inloggning ───────────────────────────────────────────────────
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

# ── Klart ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}🎉 Installation klar!${RESET}"
echo ""
echo -e "  Version:       ${BOLD}$VERSION${RESET}"
echo -e "  Installerad i: ${BOLD}$INSTALL_DIR${RESET}"
echo ""
echo -e "  Björnen 🐻 sitter nu i din menyrad."
echo -e "  Appen startar automatiskt vid nästa inloggning."
echo ""
echo -e "${YELLOW}  Avinstallera:${RESET}"
echo "    launchctl unload $PLIST_DEST && rm $PLIST_DEST"
echo "    launchctl unload $MENU_PLIST && rm $MENU_PLIST"
echo "    rm -rf $INSTALL_DIR"
echo ""
