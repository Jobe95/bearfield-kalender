# Dynamic Deadlines Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace hardcoded task arrays in 3 files with a shared Python module that generates deadlines dynamically from org config.

**Architecture:** Shared `tasks.py` reads `config.json` and generates deadline tasks for a rolling 12-month window. `menuapp.py` and `notify.py` import it. Web UI fetches tasks via new `GET /api/tasks` endpoint. Interactive setup in `install.sh` creates `config.json`.

**Tech Stack:** Python 3, rumps, vanilla JS, OpenCorporates API (free tier), shell (bash)

**Design doc:** `docs/plans/2026-03-19-dynamic-deadlines-design.md`

---

### Task 1: Create `tasks.py` — config loading + deadline generation

**Files:**
- Create: `tasks.py`
- Create: `test_tasks.py`

**Step 1: Write test for config loading**

```python
# test_tasks.py
import json
import os
import tempfile
from tasks import load_config, generate_tasks

def test_load_config_defaults():
    """Missing config file returns defaults."""
    cfg = load_config("/nonexistent/path/config.json")
    assert cfg["fiscal_year_end"] == "12-31"
    assert cfg["vat_period"] == "quarterly"
    assert cfg["employer_registered"] is True
    assert cfg["notification_time"] == "08:00"

def test_load_config_from_file():
    """Reads config from JSON file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"org_nr": "5591234567", "company_name": "Test AB", "vat_period": "monthly"}, f)
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg["org_nr"] == "5591234567"
        assert cfg["company_name"] == "Test AB"
        assert cfg["vat_period"] == "monthly"
        # defaults still filled in
        assert cfg["fiscal_year_end"] == "12-31"
    finally:
        os.unlink(path)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest test_tasks.py -v`
Expected: ImportError — tasks module doesn't exist yet

**Step 3: Write `tasks.py` with config loading**

```python
#!/usr/bin/env python3
"""
BearField Kalender — Shared task generation module.
Reads config.json and generates Swedish AB accounting/tax deadlines.
"""

import json
import os
from datetime import date, timedelta
from calendar import monthrange

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
STATE_FILE = os.path.join(SCRIPT_DIR, "state.json")

DEFAULTS = {
    "org_nr": "",
    "company_name": "Mitt AB",
    "fiscal_year_end": "12-31",
    "vat_period": "quarterly",
    "employer_registered": True,
    "notification_time": "08:00",
}

LINKS = {
    "Moms": "https://www.skatteverket.se/foretag/moms",
    "Lön": "https://www.skatteverket.se/foretag/arbetsgivare",
    "Skatt": "https://www.skatteverket.se/foretag/skatter",
    "Bokföring": "https://www.bolagsverket.se/foretag/aktiebolag/arsredovisning",
    "Bokslut": "https://www.bolagsverket.se/foretag/aktiebolag/arsredovisning",
}


def load_config(path=None):
    """Load config from JSON file, filling in defaults for missing keys."""
    if path is None:
        path = CONFIG_FILE
    cfg = dict(DEFAULTS)
    try:
        with open(path) as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def load_state(path=None):
    """Load completion state from JSON file."""
    if path is None:
        path = STATE_FILE
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(done, path=None):
    """Save completion state to JSON file."""
    if path is None:
        path = STATE_FILE
    with open(path, "w") as f:
        json.dump(done, f, indent=2)
```

**Step 4: Run config tests**

Run: `python3 -m pytest test_tasks.py::test_load_config_defaults test_tasks.py::test_load_config_from_file -v`
Expected: PASS

**Step 5: Write tests for deadline generation**

Add to `test_tasks.py`:

```python
from datetime import date

def test_quarterly_vat_tasks():
    """Quarterly VAT generates 4 tasks per year."""
    cfg = dict(load_config("/nonexistent"))
    cfg["vat_period"] = "quarterly"
    tasks = generate_tasks(cfg, ref_date=date(2026, 3, 19))
    vat = [t for t in tasks if t["cat"] == "Moms"]
    assert len(vat) >= 3  # at least 3 within 12-month window
    # Q1 2026 due May 12
    q1 = next(t for t in vat if t["id"] == "vat-2026-Q1")
    assert q1["deadline"] == "2026-05-12"

def test_no_employer_skips_employer_tasks():
    """employer_registered=False omits arbetsgivardeklaration."""
    cfg = dict(load_config("/nonexistent"))
    cfg["employer_registered"] = False
    tasks = generate_tasks(cfg, ref_date=date(2026, 3, 19))
    employer = [t for t in tasks if "Arbetsgivardeklaration" in t["title"]]
    assert len(employer) == 0

def test_fiscal_year_end_affects_bokslut():
    """Bokslut deadline is 6 months after fiscal year end."""
    cfg = dict(load_config("/nonexistent"))
    cfg["fiscal_year_end"] = "06-30"
    tasks = generate_tasks(cfg, ref_date=date(2026, 3, 19))
    bokslut = [t for t in tasks if t["cat"] == "Bokslut"]
    assert len(bokslut) >= 1
    # FY ending 2026-06-30 → bokslut due 2026-12-31
    bs = next((t for t in bokslut if "2026" in t["deadline"]), None)
    assert bs is not None

def test_task_has_required_fields():
    """Every task has id, title, desc, deadline, cat, link."""
    cfg = load_config("/nonexistent")
    tasks = generate_tasks(cfg, ref_date=date(2026, 3, 19))
    assert len(tasks) > 0
    for t in tasks:
        assert all(k in t for k in ("id", "title", "desc", "deadline", "cat", "link")), f"Missing field in {t}"

def test_stable_ids():
    """Same config + date produces same task IDs."""
    cfg = load_config("/nonexistent")
    t1 = generate_tasks(cfg, ref_date=date(2026, 3, 19))
    t2 = generate_tasks(cfg, ref_date=date(2026, 3, 19))
    assert [t["id"] for t in t1] == [t["id"] for t in t2]
```

**Step 6: Run tests to verify they fail**

Run: `python3 -m pytest test_tasks.py -v`
Expected: FAIL — generate_tasks not implemented

**Step 7: Implement `generate_tasks()` in `tasks.py`**

Add to `tasks.py`:

```python
def _add_months(d, months):
    """Add months to a date, clamping day to month end."""
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, monthrange(y, m)[1])
    return date(y, m, day)


def _quarter_end(year, q):
    """Return last day of quarter q (1-4)."""
    month = q * 3
    return date(year, month, monthrange(year, month)[1])


def _quarterly_vat_deadlines(ref_date):
    """Generate quarterly VAT declaration deadlines within 12-month window."""
    tasks = []
    window_start = ref_date - timedelta(days=30)
    window_end = ref_date + timedelta(days=365)

    for year in range(ref_date.year - 1, ref_date.year + 2):
        for q in range(1, 5):
            qe = _quarter_end(year, q)
            # Due 12th of 2nd month after quarter end
            due = _add_months(qe, 2).replace(day=12)
            if window_start <= due <= window_end:
                q_months = {1: "jan–mars", 2: "apr–juni", 3: "jul–sep", 4: "okt–dec"}
                tasks.append({
                    "id": f"vat-{year}-Q{q}",
                    "title": f"Momsdeklaration Q{q}",
                    "desc": f"{q_months[q]} {year}, sista dag {due.day} {_swedish_month(due.month)}",
                    "deadline": due.isoformat(),
                    "cat": "Moms",
                    "link": LINKS["Moms"],
                })
    return tasks


def _monthly_vat_deadlines(ref_date):
    """Generate monthly VAT declaration deadlines within 12-month window."""
    tasks = []
    window_start = ref_date - timedelta(days=30)
    window_end = ref_date + timedelta(days=365)

    for year in range(ref_date.year - 1, ref_date.year + 2):
        for month in range(1, 13):
            # Due 26th of next month, except December which is due 12th of Feb
            if month == 12:
                due = date(year + 1, 2, 12)
            else:
                next_m = month + 1
                due = date(year, next_m, 26)
            if window_start <= due <= window_end:
                m_name = _swedish_month(month)
                tasks.append({
                    "id": f"vat-{year}-{month:02d}",
                    "title": f"Momsdeklaration {m_name}",
                    "desc": f"{m_name} {year}, sista dag {due.day} {_swedish_month(due.month)}",
                    "deadline": due.isoformat(),
                    "cat": "Moms",
                    "link": LINKS["Moms"],
                })
    return tasks


def _employer_deadlines(ref_date):
    """Generate monthly employer declaration deadlines."""
    tasks = []
    window_start = ref_date - timedelta(days=30)
    window_end = ref_date + timedelta(days=365)

    for year in range(ref_date.year, ref_date.year + 2):
        for month in range(1, 13):
            # Employer declaration for previous month, due 12th
            due = date(year, month, 12)
            if window_start <= due <= window_end:
                prev_month = month - 1 if month > 1 else 12
                prev_year = year if month > 1 else year - 1
                m_name = _swedish_month(prev_month)
                tasks.append({
                    "id": f"employer-{prev_year}-{prev_month:02d}",
                    "title": f"Arbetsgivardeklaration {m_name}",
                    "desc": f"Om du har anställda — senast {due.day} {_swedish_month(due.month)}",
                    "deadline": due.isoformat(),
                    "cat": "Lön",
                    "link": LINKS["Lön"],
                })
    return tasks


def _prelim_tax_deadlines(ref_date):
    """Generate monthly preliminary tax deadlines."""
    tasks = []
    window_start = ref_date - timedelta(days=30)
    window_end = ref_date + timedelta(days=365)

    for year in range(ref_date.year, ref_date.year + 2):
        for month in range(1, 13):
            due = date(year, month, 12)
            if window_start <= due <= window_end:
                tasks.append({
                    "id": f"tax-{year}-{month:02d}",
                    "title": f"Betala preliminärskatt {_swedish_month(month)}",
                    "desc": f"Varje månad den 12:e",
                    "deadline": due.isoformat(),
                    "cat": "Skatt",
                    "link": LINKS["Skatt"],
                })
    return tasks


def _bookkeeping_lock_deadlines(ref_date):
    """Generate monthly bookkeeping lock deadlines (~30 days after month end)."""
    tasks = []
    window_start = ref_date - timedelta(days=30)
    window_end = ref_date + timedelta(days=365)

    for year in range(ref_date.year, ref_date.year + 2):
        for month in range(1, 13):
            # Lock period for this month, due ~end of next month
            next_m = month + 1 if month < 12 else 1
            next_y = year if month < 12 else year + 1
            due = date(next_y, next_m, monthrange(next_y, next_m)[1])
            if window_start <= due <= window_end:
                m_name = _swedish_month(month)
                tasks.append({
                    "id": f"lock-{year}-{month:02d}",
                    "title": f"Lås bokföringsperiod {m_name}",
                    "desc": f"Bokföring låst t.o.m {m_name} {year} — sista dag {due.day} {_swedish_month(due.month)}",
                    "deadline": due.isoformat(),
                    "cat": "Bokföring",
                    "link": LINKS["Bokföring"],
                })
    return tasks


def _quarterly_bookkeeping_deadlines(ref_date):
    """Generate quarterly 'book all transactions' deadlines."""
    tasks = []
    window_start = ref_date - timedelta(days=30)
    window_end = ref_date + timedelta(days=365)

    for year in range(ref_date.year, ref_date.year + 2):
        for q in range(1, 5):
            # Due end of month after quarter end
            qe = _quarter_end(year, q)
            due = _add_months(qe, 1)
            due = due.replace(day=monthrange(due.year, due.month)[1])
            if window_start <= due <= window_end:
                q_months = {1: "jan–mars", 2: "apr–juni", 3: "jul–sep", 4: "okt–dec"}
                tasks.append({
                    "id": f"bookkeep-{year}-Q{q}",
                    "title": f"Bokför alla transaktioner Q{q}",
                    "desc": f"Kontoutdrag, kvitton, leverantörsfakturor {q_months[q]}",
                    "deadline": due.isoformat(),
                    "cat": "Bokföring",
                    "link": LINKS["Bokföring"],
                })
    return tasks


def _annual_deadlines(cfg, ref_date):
    """Generate annual deadlines: bokslut, INK2, årsredovisning."""
    tasks = []
    window_start = ref_date - timedelta(days=30)
    window_end = ref_date + timedelta(days=365)

    fy_month, fy_day = map(int, cfg["fiscal_year_end"].split("-"))

    for year in range(ref_date.year - 1, ref_date.year + 2):
        fy_end = date(year, fy_month, fy_day)

        # Bokslut — 6 months after FY end
        bokslut_due = _add_months(fy_end, 6)
        if window_start <= bokslut_due <= window_end:
            tasks.append({
                "id": f"bokslut-{year}",
                "title": "Bokslut och årsredovisning",
                "desc": f"Räkenskapsår {year}, klart senast {bokslut_due.day} {_swedish_month(bokslut_due.month)} {bokslut_due.year}",
                "deadline": bokslut_due.isoformat(),
                "cat": "Bokslut",
                "link": LINKS["Bokslut"],
            })

        # INK2 — 1st of 7th month after FY end
        ink2_due = _add_months(fy_end, 7).replace(day=1)
        if window_start <= ink2_due <= window_end:
            tasks.append({
                "id": f"ink2-{year}",
                "title": "Inkomstdeklaration bolag (INK2)",
                "desc": f"Räkenskapsår {year}, lämnas senast {ink2_due.day} {_swedish_month(ink2_due.month)} {ink2_due.year}",
                "deadline": ink2_due.isoformat(),
                "cat": "Skatt",
                "link": LINKS["Skatt"],
            })

        # Årsredovisning till Bolagsverket — 7 months after FY end
        ar_due = _add_months(fy_end, 7)
        if window_start <= ar_due <= window_end:
            tasks.append({
                "id": f"arsredovisning-{year}",
                "title": "Årsredovisning till Bolagsverket",
                "desc": f"Räkenskapsår {year}, sista dag {ar_due.day} {_swedish_month(ar_due.month)} {ar_due.year}",
                "deadline": ar_due.isoformat(),
                "cat": "Bokslut",
                "link": LINKS["Bokslut"],
            })

    return tasks


def _swedish_month(m):
    """Return Swedish month name."""
    return ["januari", "februari", "mars", "april", "maj", "juni",
            "juli", "augusti", "september", "oktober", "november", "december"][m - 1]


def generate_tasks(cfg=None, ref_date=None):
    """Generate all deadline tasks based on config. Returns sorted list of task dicts."""
    if cfg is None:
        cfg = load_config()
    if ref_date is None:
        ref_date = date.today()

    tasks = []

    # VAT declarations
    if cfg["vat_period"] == "quarterly":
        tasks.extend(_quarterly_vat_deadlines(ref_date))
    elif cfg["vat_period"] == "monthly":
        tasks.extend(_monthly_vat_deadlines(ref_date))
    # yearly VAT is included with INK2, no separate task

    # Employer declarations
    if cfg["employer_registered"]:
        tasks.extend(_employer_deadlines(ref_date))

    # Preliminary tax
    tasks.extend(_prelim_tax_deadlines(ref_date))

    # Bookkeeping lock
    tasks.extend(_bookkeeping_lock_deadlines(ref_date))

    # Quarterly bookkeeping
    tasks.extend(_quarterly_bookkeeping_deadlines(ref_date))

    # Annual (bokslut, INK2, årsredovisning)
    tasks.extend(_annual_deadlines(cfg, ref_date))

    # Sort by deadline
    tasks.sort(key=lambda t: t["deadline"])
    return tasks
```

**Step 8: Run all tests**

Run: `python3 -m pytest test_tasks.py -v`
Expected: ALL PASS

**Step 9: Commit**

```bash
git add tasks.py test_tasks.py
git commit -m "feat: add tasks.py — config-driven deadline generation"
```

---

### Task 2: Update `menuapp.py` to use `tasks.py`

**Files:**
- Modify: `menuapp.py`

**Step 1: Replace hardcoded TASKS and state functions with imports**

In `menuapp.py`, replace:
- Remove the `TASKS = [...]` array (lines 25-38)
- Remove `load_done()` and `save_done()` functions (lines 42-51)
- Remove `STATE_FILE` constant (line 16)
- Import from tasks.py: `from tasks import load_config, generate_tasks, load_state, save_state`
- Replace all `load_done()` calls with `load_state()`
- Replace all `save_done()` calls with `save_state()`
- Replace all `TASKS` references with `generate_tasks(config)`
- Load config once in `BearFieldApp.__init__` and store as `self.config`
- Use `self.config["company_name"]` in menu header instead of hardcoded "BearField IT AB"

**Step 2: Add `GET /api/tasks` endpoint**

In `Handler.do_GET`, add:
```python
elif self.path == "/api/tasks":
    from tasks import generate_tasks
    self.send_json(200, generate_tasks())
```

**Step 3: Test manually**

Run: `python3 menuapp.py`
- Verify bear icon appears
- Verify menu shows generated tasks
- Verify "Öppna kalender" works
- Verify toggling tasks works
- Visit `http://localhost:7331/api/tasks` in browser — verify JSON response

**Step 4: Commit**

```bash
git add menuapp.py
git commit -m "refactor: menuapp.py uses tasks.py, add /api/tasks endpoint"
```

---

### Task 3: Update `notify.py` to use `tasks.py`

**Files:**
- Modify: `notify.py`

**Step 1: Replace hardcoded TASKS and state with imports**

- Remove `TASKS = [...]` array (lines 12-25)
- Remove `load_done()` function (lines 32-37)
- Remove `days_until()` function (lines 39-41)
- Remove `STATE_FILE` and `APP_HTML` constants (lines 29-30)
- Import: `from tasks import generate_tasks, load_state`
- Add local `days_until()` (simple, keeps notify.py self-contained for date calc):
  ```python
  def days_until(deadline_str):
      return (datetime.strptime(deadline_str, "%Y-%m-%d").date() - date.today()).days
  ```
- In `main()`: replace `TASKS` with `generate_tasks()`, `load_done()` with `load_state()`

**Step 2: Test manually**

Run: `python3 notify.py`
- If deadlines within 7 days: verify notification appears
- If no urgent deadlines: verify silent exit

**Step 3: Commit**

```bash
git add notify.py
git commit -m "refactor: notify.py uses tasks.py instead of hardcoded array"
```

---

### Task 4: Update `kalender.html` to fetch tasks from API

**Files:**
- Modify: `kalender.html`

**Step 1: Remove hardcoded TASKS array and fetch from API**

Replace the hardcoded `const TASKS = [...]` (lines 116-129) with:
```javascript
let TASKS = [];
```

Update `loadState()` to also fetch tasks:
```javascript
async function loadState() {
  try {
    const [tasksRes, doneRes] = await Promise.all([
      fetch('http://localhost:7331/api/tasks'),
      fetch('http://localhost:7331/api/done')
    ]);
    TASKS = await tasksRes.json();
    doneState = await doneRes.json();
  } catch(e) { TASKS = []; doneState = {}; }
  TASKS.forEach(t => t.done = !!doneState[t.id]);
  renderAll();
}
```

**Step 2: Update polling to also refresh tasks**

Update the `setInterval` block (line 293) to also fetch tasks:
```javascript
setInterval(async () => {
  try {
    const [tasksRes, doneRes] = await Promise.all([
      fetch('http://localhost:7331/api/tasks'),
      fetch('http://localhost:7331/api/done')
    ]);
    const newTasks = await tasksRes.json();
    const s = await doneRes.json();
    const tasksChanged = JSON.stringify(newTasks.map(t=>t.id)) !== JSON.stringify(TASKS.map(t=>t.id));
    const stateChanged = JSON.stringify(s) !== JSON.stringify(doneState);
    if(tasksChanged || stateChanged) {
      TASKS = newTasks;
      doneState = s;
      TASKS.forEach(t => t.done = !!doneState[t.id]);
      renderAll();
    }
  } catch(e) {}
}, 2000);
```

**Step 3: Make header dynamic**

Replace hardcoded `<h1>BearField IT AB</h1>` with `<h1 id="company-name"></h1>` and set it from the first task fetch or a new `/api/config` endpoint. Simplest approach: add a `GET /api/config` endpoint in menuapp.py that returns the config, then:

```javascript
async function loadConfig() {
  try {
    const r = await fetch('http://localhost:7331/api/config');
    const cfg = await r.json();
    document.getElementById('company-name').textContent = cfg.company_name || 'Bolagskalender';
  } catch(e) {
    document.getElementById('company-name').textContent = 'Bolagskalender';
  }
}
```

Add `GET /api/config` to `menuapp.py`'s Handler:
```python
elif self.path == "/api/config":
    self.send_json(200, load_config())
```

**Step 4: Make tabs dynamic**

Replace hardcoded month tabs. Instead of "Mars" and "Q1-Q2", use:
- "Just nu" (always)
- Current month name (dynamic)
- Current + next quarter label (dynamic)
- "Hela året" (always)

Generate tab labels in JS based on `today`:
```javascript
const currentMonth = today.toLocaleDateString('sv-SE', {month: 'long'});
const currentMonthCap = currentMonth.charAt(0).toUpperCase() + currentMonth.slice(1);
```

Update tab buttons and render functions to use dynamic date ranges.

**Step 5: Remove hardcoded progress bar date filter**

In `renderNu()`, the progress bar currently filters by `<= 60 days || <= '2026-03-31'`. Change to use all tasks within 90 days:
```javascript
const total = TASKS.filter(t => daysUntil(t.deadline) <= 90).length;
const done = TASKS.filter(t => t.done && daysUntil(t.deadline) <= 90).length;
```

**Step 6: Test manually**

Run: `python3 menuapp.py` then open `http://localhost:7331/`
- Verify company name shows dynamically
- Verify tasks load from API
- Verify tabs show current month / quarter
- Verify toggling tasks works
- Verify polling sync works

**Step 7: Commit**

```bash
git add kalender.html menuapp.py
git commit -m "refactor: web UI fetches tasks from API, dynamic tabs and header"
```

---

### Task 5: Migrate state file

**Files:**
- Modify: `menuapp.py` (already done in task 2 — uses `state.json`)
- Modify: `install.sh`

**Step 1: Add migration logic in `tasks.py`**

Add at the bottom of `load_state()`:
```python
def load_state(path=None):
    if path is None:
        path = STATE_FILE
    # Migrate from old done_state.json if state.json doesn't exist
    if not os.path.exists(path):
        old_path = os.path.join(os.path.dirname(path), "done_state.json")
        if os.path.exists(old_path):
            try:
                with open(old_path) as f:
                    data = json.load(f)
                save_state(data, path)
                return data
            except Exception:
                pass
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}
```

**Step 2: Update `install.sh`**

Replace `done_state.json` reference with `state.json`:
```bash
[ -f "$INSTALL_DIR/state.json" ] || echo '{}' > "$INSTALL_DIR/state.json"
```

**Step 3: Test migration**

- Create a `done_state.json` with some state
- Delete `state.json` if it exists
- Run `python3 -c "from tasks import load_state; print(load_state())"`
- Verify it reads from `done_state.json` and creates `state.json`

**Step 4: Commit**

```bash
git add tasks.py install.sh
git commit -m "feat: migrate done_state.json to state.json"
```

---

### Task 6: Add interactive setup to `install.sh`

**Files:**
- Modify: `install.sh`

**Step 1: Add setup function after dependency checks**

After the "Installera eller uppdatera" section and before "Sätt behörigheter", add:

```bash
# ── Konfigurera bolaget ──────────────────────────────────────────────────────
CONFIG_FILE="$INSTALL_DIR/config.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo ""
    echo -e "${BOLD}  🏢 Konfigurera ditt bolag${RESET}"
    echo ""

    # Org nr
    read -p "  Organisationsnummer (10 siffror): " ORG_NR
    ORG_NR=$(echo "$ORG_NR" | tr -d '- ')

    # Fetch company name from OpenCorporates
    COMPANY_NAME=""
    if [ -n "$ORG_NR" ]; then
        info "Söker företagsnamn..."
        COMPANY_NAME=$(curl -fsSL "https://api.opencorporates.com/v0.4/companies/se/$ORG_NR" 2>/dev/null \
            | python3 -c "import sys,json; print(json.load(sys.stdin)['results']['company']['name'])" 2>/dev/null || echo "")
    fi

    if [ -n "$COMPANY_NAME" ]; then
        read -p "  Företagsnamn [$COMPANY_NAME]: " INPUT_NAME
        COMPANY_NAME="${INPUT_NAME:-$COMPANY_NAME}"
    else
        read -p "  Företagsnamn: " COMPANY_NAME
        COMPANY_NAME="${COMPANY_NAME:-Mitt AB}"
    fi

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
```

**Step 2: Update launchd notification plist to use configured time**

After writing config, read notification time and use it for the plist:

```bash
# Read notification time from config
NOTIF_HOUR=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['notification_time'].split(':')[0])" 2>/dev/null || echo "08")
NOTIF_MIN=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['notification_time'].split(':')[1])" 2>/dev/null || echo "00")
```

Use `$NOTIF_HOUR` and `$NOTIF_MIN` in the plist StartCalendarInterval.

**Step 3: Remove the `sed` for GITHUB_USER**

Now that config is separate, remove:
```bash
sed -i '' 's/GITHUB_USER = "DITT_GITHUB_USERNAME"/GITHUB_USER = "Jobe95"/' ...
```

**Step 4: Test the setup flow**

Run: `bash install.sh`
- Verify prompts appear
- Verify config.json is written correctly
- Verify app starts with configured company name

**Step 5: Commit**

```bash
git add install.sh
git commit -m "feat: interactive org setup in install.sh, configurable notification time"
```

---

### Task 7: Add `.gitignore` entries and clean up

**Files:**
- Modify or create: `.gitignore`

**Step 1: Add config and state to .gitignore**

```
config.json
state.json
done_state.json
__pycache__/
*.pyc
```

These are user-specific and should not be committed.

**Step 2: Update README.md**

Add brief setup section mentioning the interactive installer and config.json overrides.

**Step 3: Final integration test**

1. Delete `config.json` and `state.json` if they exist
2. Run `python3 menuapp.py` — should use defaults
3. Create a `config.json` manually with test data
4. Restart — verify it picks up config
5. Open `http://localhost:7331/` — verify web UI loads tasks from API
6. Toggle a task in menu bar — verify web UI updates within 2s
7. Toggle a task in web UI — verify menu updates

**Step 4: Commit**

```bash
git add .gitignore README.md
git commit -m "chore: add gitignore, update readme for dynamic setup"
```

---

## Summary of commits

1. `feat: add tasks.py — config-driven deadline generation`
2. `refactor: menuapp.py uses tasks.py, add /api/tasks endpoint`
3. `refactor: notify.py uses tasks.py instead of hardcoded array`
4. `refactor: web UI fetches tasks from API, dynamic tabs and header`
5. `feat: migrate done_state.json to state.json`
6. `feat: interactive org setup in install.sh, configurable notification time`
7. `chore: add gitignore, update readme for dynamic setup`
