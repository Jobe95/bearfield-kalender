#!/usr/bin/env python3
"""
BearField IT — Menyapp med lokal webbserver + auto-uppdatering
"""

import rumps
import json
import os
import subprocess
import threading
import urllib.request
from datetime import date, datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "done_state.json")
HTML_FILE  = os.path.join(SCRIPT_DIR, "kalender.html")
PORT = 7331

VERSION = "v0.0.4"
GITHUB_USER = "DITT_GITHUB_USERNAME"   # ← ändra detta
GITHUB_REPO = "bearfield-kalender"
GITHUB_API  = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"

TASKS = [
    {"id": "t1",  "title": "Lås bokföringsperiod januari",      "deadline": "2026-03-22", "cat": "Bokföring"},
    {"id": "t4",  "title": "Lås bokföringsperiod februari",     "deadline": "2026-03-31", "cat": "Bokföring"},
    {"id": "t5",  "title": "Lås bokföringsperiod mars",         "deadline": "2026-04-30", "cat": "Bokföring"},
    {"id": "t6",  "title": "Arbetsgivardeklaration mars",       "deadline": "2026-04-12", "cat": "Lön"},
    {"id": "t7",  "title": "Betala preliminärskatt april",      "deadline": "2026-04-12", "cat": "Skatt"},
    {"id": "t2",  "title": "Bokför alla transaktioner Q1",      "deadline": "2026-04-30", "cat": "Bokföring"},
    {"id": "t3",  "title": "Momsdeklaration Q1",                "deadline": "2026-05-12", "cat": "Moms"},
    {"id": "t8",  "title": "Momsdeklaration Q2",                "deadline": "2026-08-17", "cat": "Moms"},
    {"id": "t9",  "title": "Momsdeklaration Q3",                "deadline": "2026-11-17", "cat": "Moms"},
    {"id": "t10", "title": "Momsdeklaration Q4",                "deadline": "2027-02-12", "cat": "Moms"},
    {"id": "t11", "title": "Bokslut och årsredovisning",        "deadline": "2027-06-30", "cat": "Bokslut"},
    {"id": "t12", "title": "Inkomstdeklaration bolag (INK2)",   "deadline": "2027-07-01", "cat": "Skatt"},
]

# ── State ──────────────────────────────────────────────────────────────────────

def load_done():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def save_done(done):
    with open(STATE_FILE, "w") as f:
        json.dump(done, f, indent=2)

# ── Uppdateringskoll ───────────────────────────────────────────────────────────

def check_for_update():
    """Kollar GitHub releases API. Returnerar (latest_tag, release_notes) eller None."""
    try:
        req = urllib.request.Request(GITHUB_API, headers={"User-Agent": "BearFieldKalender"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
        latest = data.get("tag_name", "")
        notes  = data.get("body", "").strip()[:200]
        if latest and latest != VERSION:
            return latest, notes
    except Exception:
        pass
    return None

def do_update():
    """Kör git pull och startar om appen."""
    try:
        subprocess.run(["git", "-C", SCRIPT_DIR, "pull", "--ff-only"], check=True)
        # Starta om appen
        subprocess.Popen(["python3", os.path.join(SCRIPT_DIR, "menuapp.py")])
        rumps.quit_application()
    except subprocess.CalledProcessError as e:
        rumps.alert("Uppdatering misslyckades", f"git pull returnerade fel:\n{e}")

# ── Webbserver ─────────────────────────────────────────────────────────────────

_app = None

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def send_json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path in ("/", "/kalender.html"):
            with open(HTML_FILE, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/done":
            self.send_json(200, load_done())
        else:
            self.send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/api/done":
            length = int(self.headers.get("Content-Length", 0))
            try:
                data = json.loads(self.rfile.read(length))
                save_done(data)
                self.send_json(200, {"ok": True})
                if _app:
                    _app.rebuild_menu()
            except Exception as e:
                self.send_json(400, {"error": str(e)})
        else:
            self.send_json(404, {"error": "not found"})

# ── Hjälpfunktioner ────────────────────────────────────────────────────────────

def days_until(deadline_str):
    return (datetime.strptime(deadline_str, "%Y-%m-%d").date() - date.today()).days

def deadline_label(task, done):
    d = days_until(task["deadline"])
    prefix = "✓ " if done.get(task["id"]) else ""
    if d < 0:     days_str = f"FÖRSENAD {abs(d)}d"
    elif d == 0:  days_str = "idag!"
    elif d == 1:  days_str = "imorgon"
    elif d <= 7:  days_str = f"om {d}d ⚠️"
    elif d <= 30: days_str = f"om {d}d"
    else:         days_str = task["deadline"]
    return f"{prefix}[{task['cat']}] {task['title']} — {days_str}"

# ── Menyapp ────────────────────────────────────────────────────────────────────

class BearFieldApp(rumps.App):
    def __init__(self):
        super().__init__("🐻", quit_button=None)
        self.rebuild_menu()
        # Kolla uppdateringar i bakgrunden vid start
        threading.Thread(target=self._bg_update_check, daemon=True).start()

    def _bg_update_check(self):
        result = check_for_update()
        if result:
            latest, notes = result
            rumps.notification(
                "BearField IT — Uppdatering tillgänglig",
                f"Version {latest} finns",
                "Klicka på 🔄 Sök uppdateringar i menyn för att installera."
            )

    def rebuild_menu(self):
        done = load_done()
        urgent = [t for t in TASKS if not done.get(t["id"]) and 0 <= days_until(t["deadline"]) <= 7]
        self.title = f"🐻 {len(urgent)}" if urgent else "🐻"

        items = []
        items.append(rumps.MenuItem(f"BearField IT AB  {VERSION}", callback=None))
        items.append(rumps.separator)

        if urgent:
            items.append(rumps.MenuItem("⚠️  Inom 7 dagar", callback=None))
            for t in sorted(urgent, key=lambda x: x["deadline"]):
                items.append(self.make_item(t, done))
            items.append(rumps.separator)

        upcoming = [t for t in TASKS if not done.get(t["id"]) and days_until(t["deadline"]) > 7]
        if upcoming:
            items.append(rumps.MenuItem("Kommande", callback=None))
            for t in sorted(upcoming, key=lambda x: x["deadline"])[:6]:
                items.append(self.make_item(t, done))
            items.append(rumps.separator)

        done_tasks = [t for t in TASKS if done.get(t["id"])]
        if done_tasks:
            sub = rumps.MenuItem("Avklarade")
            for t in done_tasks:
                sub.add(self.make_item(t, done))
            items.append(sub)
            items.append(rumps.separator)

        items.append(rumps.MenuItem("📅  Öppna kalender",       callback=self.open_calendar))
        items.append(rumps.MenuItem("🔔  Testa notis",           callback=self.test_notification))
        items.append(rumps.MenuItem("🔄  Sök uppdateringar",     callback=self.check_update))

        self.menu.clear()
        self.menu = items

    def make_item(self, task, done):
        item = rumps.MenuItem(deadline_label(task, done), callback=self.toggle_done)
        item.task_id = task["id"]
        return item

    def toggle_done(self, sender):
        done = load_done()
        if done.get(sender.task_id):
            del done[sender.task_id]
        else:
            done[sender.task_id] = True
        save_done(done)
        self.rebuild_menu()

    def open_calendar(self, _):
        subprocess.run(["open", f"http://localhost:{PORT}/"])

    def test_notification(self, _):
        done = load_done()
        upcoming = [t for t in TASKS if not done.get(t["id"]) and days_until(t["deadline"]) >= 0]
        if not upcoming:
            rumps.notification("BearField IT", "Inga kommande deadlines", "Alla uppgifter är avklarade!")
            return
        task = sorted(upcoming, key=lambda t: t["deadline"])[0]
        d = days_until(task["deadline"])
        days_str = "idag!" if d == 0 else ("imorgon!" if d == 1 else f"om {d} dagar")
        rumps.notification(
            "BearField IT — Deadline",
            task["title"],
            f"{task['cat']} · {days_str} ({task['deadline']})"
        )

    @rumps.clicked("🔄  Sök uppdateringar")
    def check_update(self, _):
        def _check():
            result = check_for_update()
            if not result:
                rumps.notification("BearField IT", "Redan uppdaterad", f"Du kör senaste versionen ({VERSION})")
                return
            latest, notes = result
            msg = f"Version {latest} finns tillgänglig.\n\n{notes}\n\nVill du uppdatera nu?"
            response = rumps.alert(
                title="Uppdatering tillgänglig",
                message=msg,
                ok="Uppdatera",
                cancel="Senare"
            )
            if response == 1:
                do_update()
        threading.Thread(target=_check, daemon=True).start()

    @rumps.timer(3600)
    def auto_refresh(self, _):
        self.rebuild_menu()

if __name__ == "__main__":
    threading.Thread(
        target=lambda: HTTPServer(("127.0.0.1", PORT), Handler).serve_forever(),
        daemon=True
    ).start()
    app = BearFieldApp()
    _app = app
    app.run()
