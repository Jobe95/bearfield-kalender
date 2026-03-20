# Settings Page Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a web-based settings page at `/settings` so users can configure their company without editing JSON manually.

**Architecture:** New `settings.html` form pre-populated from `GET /api/config`. Org nr lookup via `GET /api/lookup-org` (proxied through menuapp.py to OpenCorporates). Save via `POST /api/config` which writes config.json and reloads the menu bar app's config. Menu bar gets an "Inställningar" item.

**Tech Stack:** Python 3, vanilla JS, OpenCorporates API (free tier)

---

### Task 1: Add `save_config()` to `tasks.py`

**Files:**
- Modify: `tasks.py`
- Modify: `test_tasks.py`

**Step 1: Write test for save_config**

Add to `test_tasks.py`:

```python
def test_save_and_load_config():
    """save_config writes JSON that load_config reads back."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    try:
        cfg = {"org_nr": "5591234567", "company_name": "Test AB", "vat_period": "monthly",
               "fiscal_year_end": "06-30", "employer_registered": False, "notification_time": "09:00"}
        from tasks import save_config
        save_config(cfg, path)
        loaded = load_config(path)
        assert loaded["org_nr"] == "5591234567"
        assert loaded["vat_period"] == "monthly"
        assert loaded["employer_registered"] is False
    finally:
        os.unlink(path)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest test_tasks.py::test_save_and_load_config -v`
Expected: ImportError — save_config doesn't exist

**Step 3: Implement save_config in tasks.py**

Add after `load_config`:

```python
def save_config(cfg, path=None):
    """Save config to JSON file."""
    if path is None:
        path = CONFIG_FILE
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
```

**Step 4: Run test**

Run: `python3 -m pytest test_tasks.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add tasks.py test_tasks.py
git commit -m "feat: add save_config to tasks.py"
```

---

### Task 2: Add API endpoints to `menuapp.py`

**Files:**
- Modify: `menuapp.py`

**Step 1: Add `POST /api/config` endpoint**

In `Handler.do_POST`, add before the `else` clause:

```python
elif self.path == "/api/config":
    length = int(self.headers.get("Content-Length", 0))
    try:
        data = json.loads(self.rfile.read(length))
        from tasks import save_config
        save_config(data)
        if _app:
            _app.config = load_config()
            _app.rebuild_menu()
        self.send_json(200, {"ok": True})
    except Exception as e:
        self.send_json(400, {"error": str(e)})
```

**Step 2: Add `GET /api/lookup-org` endpoint**

In `Handler.do_GET`, add before the `else` clause:

```python
elif self.path.startswith("/api/lookup-org?nr="):
    org_nr = self.path.split("nr=")[1]
    try:
        url = f"https://api.opencorporates.com/v0.4/companies/se/{org_nr}"
        req = urllib.request.Request(url, headers={"User-Agent": "BearFieldKalender"})
        with urllib.request.urlopen(req, timeout=5) as r:
            result = json.loads(r.read())
        name = result["results"]["company"]["name"]
        self.send_json(200, {"name": name})
    except Exception:
        self.send_json(200, {"name": ""})
```

**Step 3: Add `/settings` route**

In `Handler.do_GET`, add before the `else` clause:

```python
elif self.path == "/settings":
    settings_file = os.path.join(SCRIPT_DIR, "settings.html")
    with open(settings_file, "rb") as f:
        body = f.read()
    self.send_response(200)
    self.send_header("Content-Type", "text/html; charset=utf-8")
    self.send_header("Content-Length", len(body))
    self.end_headers()
    self.wfile.write(body)
```

**Step 4: Update import**

Update the import line at the top:

```python
from tasks import load_config, generate_tasks, load_state, save_state, save_config
```

**Step 5: Add "Inställningar" menu item**

In `BearFieldApp.rebuild_menu`, add after the "Öppna kalender" item (line 173):

```python
items.append(rumps.MenuItem("⚙️  Inställningar",        callback=self.open_settings))
```

Add the callback method to BearFieldApp:

```python
def open_settings(self, _):
    subprocess.run(["open", f"http://localhost:{PORT}/settings"])
```

**Step 6: Commit**

```bash
git add menuapp.py
git commit -m "feat: add settings endpoints and menu item"
```

---

### Task 3: Create `settings.html`

**Files:**
- Create: `settings.html`

**Step 1: Create settings.html**

Same visual style as `kalender.html` — SF Pro font, warm gray background (#F5F4F0), white card, purple accents (#534AB7), dark mode support. The form:

```html
<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Inställningar — Bolagskalender</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
    background: #F5F4F0;
    color: #1a1a1a;
    min-height: 100vh;
  }
  .app { max-width: 520px; margin: 0 auto; padding: 2rem 1.5rem 4rem; }
  .header { margin-bottom: 2rem; }
  .header h1 { font-size: 22px; font-weight: 600; letter-spacing: -0.3px; }
  .header p { font-size: 13px; color: #666; margin-top: 4px; }
  .back { font-size: 13px; color: #534AB7; text-decoration: none; display: inline-block; margin-bottom: 1rem; }
  .back:hover { text-decoration: underline; }

  .card { background: white; border-radius: 12px; padding: 1.5rem; }

  .field { margin-bottom: 1.25rem; }
  .field:last-child { margin-bottom: 0; }
  .field label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 4px; }
  .field .hint { font-size: 12px; color: #888; margin-top: 2px; }

  input[type="text"], input[type="time"] {
    width: 100%; padding: 8px 10px; font-size: 14px; border: 1px solid #D0CEC8;
    border-radius: 8px; font-family: inherit; background: #FAFAF8;
    transition: border-color 0.15s;
  }
  input:focus { outline: none; border-color: #534AB7; }

  .org-row { display: flex; gap: 8px; align-items: flex-start; }
  .org-row input { flex: 1; }
  .org-row .lookup-status { font-size: 12px; color: #888; margin-top: 6px; white-space: nowrap; }

  .radio-group { display: flex; flex-direction: column; gap: 6px; }
  .radio-option { display: flex; align-items: center; gap: 8px; font-size: 14px; cursor: pointer; }
  .radio-option input[type="radio"] { accent-color: #534AB7; }
  .radio-option .radio-hint { font-size: 12px; color: #888; margin-left: 4px; }

  .toggle-row { display: flex; align-items: center; justify-content: space-between; }
  .toggle { position: relative; width: 44px; height: 24px; }
  .toggle input { opacity: 0; width: 0; height: 0; }
  .toggle .slider { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: #CCC; border-radius: 12px; cursor: pointer; transition: 0.2s; }
  .toggle .slider:before { content: ''; position: absolute; height: 18px; width: 18px; left: 3px; bottom: 3px; background: white; border-radius: 50%; transition: 0.2s; }
  .toggle input:checked + .slider { background: #534AB7; }
  .toggle input:checked + .slider:before { transform: translateX(20px); }

  .actions { margin-top: 1.5rem; display: flex; gap: 10px; }
  .btn { padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; border: none; font-family: inherit; transition: all 0.15s; }
  .btn-primary { background: #534AB7; color: white; }
  .btn-primary:hover { background: #453DA0; }
  .btn-primary:disabled { background: #B0ACD0; cursor: not-allowed; }
  .btn-secondary { background: #E8E6E0; color: #666; }
  .btn-secondary:hover { background: #D8D6D0; }

  .toast { position: fixed; bottom: 2rem; left: 50%; transform: translateX(-50%); background: #1a1a1a; color: white; padding: 10px 20px; border-radius: 8px; font-size: 14px; opacity: 0; transition: opacity 0.3s; pointer-events: none; }
  .toast.show { opacity: 1; }

  @media (prefers-color-scheme: dark) {
    body { background: #1C1C1E; color: #F2F2F7; }
    .card { background: #2C2C2E; }
    input[type="text"], input[type="time"] { background: #3A3A3C; border-color: #555; color: #F2F2F7; }
    .btn-secondary { background: #3A3A3C; color: #CCC; }
    .btn-secondary:hover { background: #4A4A4C; }
    .back { color: #AFA9EC; }
    .header p, .field .hint, .radio-option .radio-hint, .org-row .lookup-status { color: #999; }
    .toggle .slider { background: #555; }
    .toast { background: #F2F2F7; color: #1C1C1E; }
  }
</style>
</head>
<body>
<div class="app">
  <a href="/" class="back">← Tillbaka till kalendern</a>
  <div class="header">
    <h1>Inställningar</h1>
    <p>Konfigurera ditt bolag</p>
  </div>

  <div class="card">
    <div class="field">
      <label>Organisationsnummer</label>
      <div class="org-row">
        <input type="text" id="org-nr" placeholder="5591234567" maxlength="12">
        <div id="lookup-status" class="lookup-status"></div>
      </div>
      <div class="hint">10 siffror, bindestreck tillåtet</div>
    </div>

    <div class="field">
      <label>Företagsnamn</label>
      <input type="text" id="company-name" placeholder="Mitt AB">
    </div>

    <div class="field">
      <label>Räkenskapsår slutar</label>
      <input type="text" id="fy-end" placeholder="12-31">
      <div class="hint">Format: MM-DD (t.ex. 12-31 för kalenderår, 06-30 för brutet)</div>
    </div>

    <div class="field">
      <label>Momsredovisningsperiod</label>
      <div class="radio-group">
        <label class="radio-option">
          <input type="radio" name="vat" value="quarterly" checked>
          Kvartalsvis <span class="radio-hint">(vanligast, omsättning 1–40 MSEK)</span>
        </label>
        <label class="radio-option">
          <input type="radio" name="vat" value="monthly">
          Månadsvis <span class="radio-hint">(omsättning > 40 MSEK)</span>
        </label>
        <label class="radio-option">
          <input type="radio" name="vat" value="yearly">
          Årsvis <span class="radio-hint">(omsättning < 1 MSEK)</span>
        </label>
      </div>
    </div>

    <div class="field">
      <div class="toggle-row">
        <label>Arbetsgivarregistrerad</label>
        <label class="toggle">
          <input type="checkbox" id="employer" checked>
          <span class="slider"></span>
        </label>
      </div>
      <div class="hint">Stäng av om du inte har anställda</div>
    </div>

    <div class="field">
      <label>Notistid</label>
      <input type="time" id="notif-time" value="08:00">
      <div class="hint">När daglig deadline-påminnelse skickas</div>
    </div>
  </div>

  <div class="actions">
    <button class="btn btn-primary" id="save-btn" onclick="saveConfig()">Spara</button>
    <button class="btn btn-secondary" onclick="window.location='/'">Avbryt</button>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
let debounceTimer;

async function loadConfig() {
  try {
    const r = await fetch('http://localhost:7331/api/config');
    const cfg = await r.json();
    document.getElementById('org-nr').value = cfg.org_nr || '';
    document.getElementById('company-name').value = cfg.company_name || '';
    document.getElementById('fy-end').value = cfg.fiscal_year_end || '12-31';
    document.querySelector(`input[name="vat"][value="${cfg.vat_period || 'quarterly'}"]`).checked = true;
    document.getElementById('employer').checked = cfg.employer_registered !== false;
    document.getElementById('notif-time').value = cfg.notification_time || '08:00';
  } catch(e) {}
}

function setupOrgLookup() {
  const input = document.getElementById('org-nr');
  const status = document.getElementById('lookup-status');
  const nameInput = document.getElementById('company-name');

  input.addEventListener('input', () => {
    const nr = input.value.replace(/[-\s]/g, '');
    clearTimeout(debounceTimer);
    if (nr.length === 10) {
      status.textContent = 'Söker...';
      debounceTimer = setTimeout(async () => {
        try {
          const r = await fetch(`http://localhost:7331/api/lookup-org?nr=${nr}`);
          const data = await r.json();
          if (data.name) {
            status.textContent = '✓';
            if (!nameInput.value || nameInput.value === 'Mitt AB') {
              nameInput.value = data.name;
            }
          } else {
            status.textContent = 'Ej hittat';
          }
        } catch(e) {
          status.textContent = '';
        }
      }, 500);
    } else {
      status.textContent = '';
    }
  });
}

async function saveConfig() {
  const btn = document.getElementById('save-btn');
  btn.disabled = true;
  btn.textContent = 'Sparar...';

  const cfg = {
    org_nr: document.getElementById('org-nr').value.replace(/[-\s]/g, ''),
    company_name: document.getElementById('company-name').value || 'Mitt AB',
    fiscal_year_end: document.getElementById('fy-end').value || '12-31',
    vat_period: document.querySelector('input[name="vat"]:checked').value,
    employer_registered: document.getElementById('employer').checked,
    notification_time: document.getElementById('notif-time').value || '08:00',
  };

  try {
    const r = await fetch('http://localhost:7331/api/config', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(cfg)
    });
    if (!r.ok) throw new Error('Save failed');
    showToast('Inställningar sparade ✓');
    setTimeout(() => window.location = '/', 1200);
  } catch(e) {
    showToast('Kunde inte spara');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Spara';
  }
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2500);
}

loadConfig();
setupOrgLookup();
</script>
</body>
</html>
```

**Step 2: Commit**

```bash
git add settings.html
git commit -m "feat: add settings.html — config form with org lookup"
```

---

### Task 4: Update `setup.py` to include `settings.html`

**Files:**
- Modify: `setup.py`

**Step 1: Add settings.html to DATA_FILES**

In the `DATA_FILES` list, add `'settings.html'` alongside the other files.

**Step 2: Commit**

```bash
git add setup.py
git commit -m "chore: include settings.html in build"
```

---

## Summary of commits

1. `feat: add save_config to tasks.py`
2. `feat: add settings endpoints and menu item`
3. `feat: add settings.html — config form with org lookup`
4. `chore: include settings.html in build`
