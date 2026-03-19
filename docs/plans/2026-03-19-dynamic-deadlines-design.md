# Dynamic Deadlines from Org Setup

## Problem

Tasks/deadlines are hardcoded in 3 files (menuapp.py, kalender.html, notify.py). Dates expire yearly. Only works for BearField IT AB. Not usable by other Swedish AB owners.

## Decision

Approach B: Shared Python module (`tasks.py`) as single source of truth. Config-driven deadline generation based on org registration data.

## Target User

Any Swedish AB owner. AB-only scope. Shell installer distribution.

## Scope

Reminder/calendar system only. No workflow, no notes, no attachments. Direct links to Skatteverket/Bolagsverket pages per task.

## Setup Flow

1. `install.sh` prompts for org nr (10 digits)
2. Fetch company name from OpenCorporates free API — prefill, user confirms
3. User confirms/overrides:
   - Rackenskapsaar (fiscal year end) — default 12-31
   - Momsperiod — quarterly/monthly/yearly (default quarterly)
   - Arbetsgivarregistrerad — yes/no (default yes)
   - Notification time — default 08:00
4. Writes `config.json`

## Config File (`config.json`)

```json
{
  "org_nr": "5591234567",
  "company_name": "BearField IT AB",
  "fiscal_year_end": "12-31",
  "vat_period": "quarterly",
  "employer_registered": true,
  "notification_time": "08:00"
}
```

All fields overridable by editing config.json directly.

## Shared Module (`tasks.py`)

Reads config.json, generates deadlines for rolling 12-month window.

### Generated task types

| Task | Condition | Deadline rule |
|---|---|---|
| Momsdeklaration | vat_period != yearly | Quarterly: 12th of 2nd month after Q end. Monthly: 26th of next month (12th for Dec) |
| Arbetsgivardeklaration | employer_registered | 12th of each month |
| Preliminarskatt | Always | 12th of each month |
| Las bokforingsperiod | Always | ~30 days after month end |
| Bokfor alla transaktioner | Always | Quarterly, end of month after Q |
| Bokslut & arsredovisning | Always | 6 months after fiscal_year_end |
| INK2 | Always | 1st of 7th month after fiscal_year_end |
| Arsredovisning till Bolagsverket | Always | 7 months after fiscal_year_end |

### Task ID format

Stable IDs for state persistence: `vat-2026-Q1`, `employer-2026-03`, `bookkeeping-lock-2026-01`

### Output format

```json
{"id": "vat-2026-Q1", "title": "Momsdeklaration Q1", "desc": "...", "deadline": "2026-05-12", "cat": "Moms", "link": "https://..."}
```

## State Management

`state.json` (renamed from done_state.json) — same boolean map:

```json
{"vat-2026-Q1": true, "employer-2026-03": true}
```

## API Changes

- `GET /api/tasks` — new, returns generated tasks
- `GET /api/done` — unchanged, returns state.json
- `POST /api/done` — unchanged, saves state.json

## File Changes

### New files
- `tasks.py` — shared deadline generation module
- `config.json` — org setup (created by installer)

### Modified files
- `menuapp.py` — import tasks.py, add GET /api/tasks, read notification_time from config
- `notify.py` — import tasks.py instead of hardcoded array
- `kalender.html` — remove hardcoded TASKS, fetch from /api/tasks
- `install.sh` — add interactive setup (org nr, API fetch, config questions)

### Renamed
- `done_state.json` → `state.json`

## Architecture

```
config.json          <- installer writes, user can edit
    |
tasks.py             <- reads config, generates deadlines
    |
+------------+------------+---------------+
| menuapp.py | notify.py  | GET /api/tasks|
| (import)   | (import)   | (serves JSON) |
+------------+------------+------+--------+
                                 |
                           kalender.html
                           (fetches tasks)
```

## What stays the same

- rumps menu bar app
- Web UI design/styling
- Polling sync (2s)
- JSON state (boolean map)
- Shell installer distribution
- launchd notifications
- Auto-update via GitHub
