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

# ── Konfigurera bolaget ──────────────────────────────────────────────────────
CONFIG_FILE="$INSTALL_DIR/config.json"

if [ ! -f "$CONFIG_FILE" ]; then
    # Check if stdin is a terminal (not piped via curl | bash)
    if [ -t 0 ]; then
        echo ""
        echo -e "${BOLD}  🏢 Konfigurera ditt bolag${RESET}"
        echo ""

        # Org nr
        read -p "  Organisationsnummer (10 siffror): " ORG_NR
        ORG_NR=$(echo "$ORG_NR" | tr -d ' -')

        read -p "  Företagsnamn: " COMPANY_NAME
        COMPANY_NAME="${COMPANY_NAME:-Mitt AB}"

        # Fiscal year end
        read -p "  Räkenskapsår slutar (MM-DD) [12-31]: " FY_END
        FY_END="${FY_END:-12-31}"

        # VAT period
        echo "  Momsredovisningsperiod:"
        echo "    1) Kvartalsvis (vanligast, omsättning 1-40 MSEK)"
        echo "    2) Månadsvis (omsättning > 40 MSEK)"
        echo "    3) Årsvis (omsättning < 1 MSEK)"
        read -p "  Välj [1]: " VAT_CHOICE
        case "$VAT_CHOICE" in
            2) VAT_PERIOD="monthly" ;;
            3) VAT_PERIOD="yearly" ;;
            *) VAT_PERIOD="quarterly" ;;
        esac

        # Employer registered
        read -p "  Arbetsgivarregistrerad? (j/n) [j]: " EMPLOYER
        if [ "$EMPLOYER" = "n" ] || [ "$EMPLOYER" = "N" ]; then
            EMPLOYER_REG="false"
        else
            EMPLOYER_REG="true"
        fi

        # Notification time
        read -p "  Notistid (HH:MM) [08:00]: " NOTIF_TIME
        NOTIF_TIME="${NOTIF_TIME:-08:00}"
    else
        warn "Icke-interaktiv installation — använder standardvärden"
        warn "Konfigurera via inställningar i appen efteråt"
        ORG_NR=""
        COMPANY_NAME="Mitt AB"
        FY_END="12-31"
        VAT_PERIOD="quarterly"
        EMPLOYER_REG="true"
        NOTIF_TIME="08:00"
    fi

    # Write config
    cat > "$CONFIG_FILE" << CFGEOF
{
  "org_nr": "$ORG_NR",
  "company_name": "$COMPANY_NAME",
  "fiscal_year_end": "$FY_END",
  "vat_period": "$VAT_PERIOD",
  "employer_registered": $EMPLOYER_REG,
  "notification_time": "$NOTIF_TIME"
}
CFGEOF

    success "Konfiguration sparad"
else
    info "Befintlig konfiguration hittad — behåller"
fi

# ── Sätt behörigheter ─────────────────────────────────────────────────────────
info "Sätter behörigheter..."
find "$INSTALL_DIR" -name "*.sh" -exec chmod +x {} \;
find "$INSTALL_DIR" -name "*.py" -exec chmod +x {} \;

# Skapa state.json om den saknas
[ -f "$INSTALL_DIR/state.json" ] || echo '{}' > "$INSTALL_DIR/state.json"
success "Behörigheter satta"

# ── Installera Python-beroenden ────────────────────────────────────────────────
info "Installerar beroenden..."
for pkg in rumps py2app; do
    if pip3 install "$pkg" --break-system-packages -q 2>/dev/null; then
        true
    elif pip3 install "$pkg" -q 2>/dev/null; then
        true
    else
        error "Kunde inte installera $pkg"
    fi
done
success "Python-beroenden installerade"

# ── Sätt upp launchd-notiser ───────────────────────────────────────────────────
# Read notification time from config
NOTIF_HOUR=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['notification_time'].split(':')[0])" 2>/dev/null || echo "08")
NOTIF_MIN=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['notification_time'].split(':')[1])" 2>/dev/null || echo "00")

info "Konfigurerar dagliga notiser ($NOTIF_HOUR:$NOTIF_MIN)..."
PLIST_SRC="$INSTALL_DIR/se.bearfieldit.deadlinenotis.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/se.bearfieldit.deadlinenotis.plist"

if [ -f "$PLIST_SRC" ]; then
    sed -e "s|PLACEHOLDER_PATH|$INSTALL_DIR|g" \
        -e "s|PLACEHOLDER_HOUR|$NOTIF_HOUR|g" \
        -e "s|PLACEHOLDER_MINUTE|$NOTIF_MIN|g" \
        "$PLIST_SRC" > "$PLIST_DEST"
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    launchctl load "$PLIST_DEST"
    success "Dagliga notiser aktiverade"
else
    warn "Plist-fil saknas — notiser ej konfigurerade"
fi

# ── Bygg .app-bundle ──────────────────────────────────────────────────────────
info "Bygger applikation..."
APP_DIR="$INSTALL_DIR/dist/BearField IT.app"
(cd "$INSTALL_DIR" && python3 setup.py py2app --dist-dir "$INSTALL_DIR/dist" -q 2>/dev/null)
if [ -d "$APP_DIR" ]; then
    success "Applikation byggd"
else
    error "Kunde inte bygga .app-bundle"
fi

# ── Starta menyappen ───────────────────────────────────────────────────────────
info "Startar BearField Kalender..."

# Stoppa eventuell gammal instans
pkill -f "BearField IT" 2>/dev/null || true
pkill -f "menuapp.py" 2>/dev/null || true
sleep 1

open "$APP_DIR"
sleep 2

if pgrep -f "BearField IT" > /dev/null; then
    success "Menyappen körs — björnen 🐻 syns i menyraden"
else
    warn "Appen startade inte automatiskt. Starta manuellt:"
    echo "   open \"$APP_DIR\""
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
        <string>/usr/bin/open</string>
        <string>$APP_DIR</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
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
