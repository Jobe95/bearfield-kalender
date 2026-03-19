# BearField Kalender 🐻

Menyapp för BearField IT AB — håller koll på bokförings- och skattedeadlines.

## Filer

| Fil | Syfte |
|-----|-------|
| `menuapp.py` | Menyappen + lokal webbserver (port 7331) |
| `kalender.html` | Webbgränssnitt för att se och bocka av uppgifter |
| `notify.py` | Skickar Mac-notiser om deadline inom 7 dagar |
| `done_state.json` | Delade avbockningar (läses av alla tre) |
| `setup.py` | py2app-konfiguration |
| `bygg.sh` | Byggskript |

## Bygg appen

```bash
bash bygg.sh
```

Kräver Python 3 och installerar py2app automatiskt.

## Starta

```bash
open "/Applications/BearField Kalender.app"
```

Björnen 🐻 dyker upp i menyraden. Appen körs i bakgrunden utan Dock-ikon.

## Autostart

Lägg till i **Systeminställningar → Allmänt → Inloggningsobjekt**
så startar den automatiskt vid inloggning.

## Dagliga notiser

Notiser skickas automatiskt varje morgon 08:00 om en deadline är inom 7 dagar.
Avbockade uppgifter skickar aldrig notis.

Aktivera manuellt (körs redan om du kört installera.sh):
```bash
# Schemalägg notify.py via launchd
launchctl load ~/Library/LaunchAgents/se.bearfieldit.deadlinenotis.plist
```

## Avinstallera

```bash
rm -rf "/Applications/BearField Kalender.app"
launchctl unload ~/Library/LaunchAgents/se.bearfieldit.deadlinenotis.plist
launchctl unload ~/Library/LaunchAgents/se.bearfieldit.menuapp.plist
```
