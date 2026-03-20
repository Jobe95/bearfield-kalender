# BearField Kalender 🐻

Menu bar app for BearField IT AB — tracks accounting and tax deadlines.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/Jobe95/bearfield-kalender/main/install.sh | bash
```

Specific version:
```bash
curl -fsSL https://raw.githubusercontent.com/Jobe95/bearfield-kalender/main/install.sh | bash -s v1.1
```

## Files

| File | Purpose |
|------|---------|
| `menuapp.py` | Menu bar app + local web server (port 7331) |
| `kalender.html` | Web UI for viewing and checking off tasks |
| `notify.py` | Sends Mac notifications when deadline is within 7 days |
| `tasks.py` | Dynamic deadline generation from org config |
| `config.json` | Org type, registration date, VAT/employer settings |
| `state.json` | Shared completion state (used by all three) |
| `setup.py` | py2app configuration |
| `build.sh` | Build standalone .app |
| `install.sh` | One-line installer |
| `release.sh` | Tag and publish a new release |
| `save.sh` | Quick commit and push |
| `setup_git.sh` | First-time Git + GitHub setup |

## Setup

Run the installer to configure your org:

```bash
bash install.sh
```

This creates `config.json` with your org type, registration date, and VAT/employer settings. Deadlines are generated dynamically from this config.

To reconfigure, re-run `install.sh` or edit `config.json` directly.

## Usage

The bear 🐻 lives in your menu bar. Click it to:
- See upcoming deadlines
- Check off completed tasks
- Open the calendar web UI
- Test a notification
- Check for updates

## Releasing a new version

```bash
bash release.sh v1.1 "What changed in this version"
```

This updates the version in code, commits, tags, pushes, and creates a GitHub Release.
The app will notify users automatically on next start.

## Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/se.bearfieldit.deadlinenotis.plist
launchctl unload ~/Library/LaunchAgents/se.bearfieldit.menuapp.plist
rm ~/Library/LaunchAgents/se.bearfieldit.deadlinenotis.plist
rm ~/Library/LaunchAgents/se.bearfieldit.menuapp.plist
rm -rf ~/Applications/BearFieldKalender
```
