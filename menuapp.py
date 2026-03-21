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
from tasks import load_config, save_config, generate_tasks, load_state, save_state

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "kalender.html")
ICON_PATH  = os.path.join(SCRIPT_DIR, "icon.png")
PORT = 7331

VERSION = "v0.0.13"
GITHUB_USER = "Jobe95"
GITHUB_REPO = "bearfield-kalender"
GITHUB_API  = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"

def send_notification(title, subtitle, message):
    """Skicka macOS-notis med björnikon."""
    try:
        from Foundation import NSUserNotification, NSUserNotificationCenter
        n = NSUserNotification.alloc().init()
        n.setTitle_(title)
        n.setSubtitle_(subtitle)
        n.setInformativeText_(message)
        NSUserNotificationCenter.defaultUserNotificationCenter().deliverNotification_(n)
    except Exception:
        rumps.notification(title, subtitle, message)

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

def reload_notification_schedule(config):
    """Regenerera och ladda om launchd-plist med nytt notistid."""
    plist_src = os.path.join(SCRIPT_DIR, "se.bearfieldit.deadlinenotis.plist")
    plist_dest = os.path.expanduser("~/Library/LaunchAgents/se.bearfieldit.deadlinenotis.plist")
    if not os.path.isfile(plist_src):
        return
    time_str = config.get("notification_time", "08:00")
    parts = time_str.split(":")
    hour, minute = parts[0].lstrip("0") or "0", parts[1].lstrip("0") or "0"
    with open(plist_src) as f:
        content = f.read()
    content = content.replace("PLACEHOLDER_PATH", SCRIPT_DIR)
    content = content.replace("PLACEHOLDER_HOUR", hour)
    content = content.replace("PLACEHOLDER_MINUTE", minute)
    with open(plist_dest, "w") as f:
        f.write(content)
    subprocess.run(["launchctl", "unload", plist_dest], capture_output=True)
    subprocess.run(["launchctl", "load", plist_dest], capture_output=True)

def _app_bundle_path():
    """Hitta .app-bundle relativt till SCRIPT_DIR."""
    # When running from py2app bundle, SCRIPT_DIR is inside .app/Contents/Resources
    if ".app/Contents/Resources" in SCRIPT_DIR:
        return SCRIPT_DIR.split(".app/")[0] + ".app"
    # Fallback: look for app in dist/
    app_path = os.path.join(SCRIPT_DIR, "dist", "BearField IT.app")
    if os.path.isdir(app_path):
        return app_path
    return None

def relaunch_app():
    """Starta om appen via .app-bundle eller python3 som fallback."""
    app_path = _app_bundle_path()
    if not app_path:
        app_path = os.path.join(_git_root(), "dist", "BearField IT.app")
    # Launch after a delay so the current process has time to quit
    subprocess.Popen(["bash", "-c", f'sleep 2 && open "{app_path}"'])
    rumps.quit_application()

def _git_root():
    """Hitta git-rooten (kan vara utanför .app-bundle)."""
    if ".app/Contents/Resources" in SCRIPT_DIR:
        # .../BearFieldKalender/dist/BearField IT.app/Contents/Resources → .../BearFieldKalender
        app_path = SCRIPT_DIR.split(".app/Contents/Resources")[0] + ".app"
        return os.path.dirname(os.path.dirname(app_path))
    return SCRIPT_DIR

def do_update():
    """Kör git pull, bygg om .app och starta om."""
    log = os.path.expanduser("/tmp/bearfield_update.log")
    try:
        git_root = _git_root()
        with open(log, "w", encoding="utf-8") as f:
            f.write(f"git_root: {git_root}\n")
            f.write(f"SCRIPT_DIR: {SCRIPT_DIR}\n")

        def _run(cmd, **kwargs):
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", **kwargs)
            with open(log, "a", encoding="utf-8") as f:
                f.write(f"\n$ {' '.join(cmd)}\nrc={r.returncode}\nout: {r.stdout}\nerr: {r.stderr}\n")
            if r.returncode != 0:
                raise RuntimeError(f"{' '.join(cmd)}\n{r.stderr.strip()}")
            return r

        _run(["git", "-C", git_root, "fetch", "--tags"])
        _run(["git", "-C", git_root, "reset", "--hard"])
        _run(["git", "-C", git_root, "clean", "-fd"])
        _run(["git", "-C", git_root, "checkout", "main"])
        _run(["git", "-C", git_root, "reset", "--hard", "origin/main"])
        # Rebuild .app using system python (not bundled)
        sys_python = "/opt/homebrew/bin/python3"
        if not os.path.isfile(sys_python):
            sys_python = "/usr/bin/python3"
        dist_dir = os.path.join(git_root, "dist")
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        _run([sys_python, "setup.py", "py2app", "--dist-dir", dist_dir, "-q"], cwd=git_root, env=env)
        relaunch_app()
    except Exception as e:
        rumps.alert("Uppdatering misslyckades", str(e))

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
            self.send_json(200, load_state())
        elif self.path == "/api/tasks":
            self.send_json(200, generate_tasks())
        elif self.path == "/api/config":
            self.send_json(200, load_config())
        elif self.path == "/settings":
            settings_file = os.path.join(SCRIPT_DIR, "settings.html")
            with open(settings_file, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/api/done":
            length = int(self.headers.get("Content-Length", 0))
            try:
                data = json.loads(self.rfile.read(length))
                save_state(data)
                self.send_json(200, {"ok": True})
                if _app:
                    _app.rebuild_menu()
            except Exception as e:
                self.send_json(400, {"error": str(e)})
        elif self.path == "/api/config":
            length = int(self.headers.get("Content-Length", 0))
            try:
                data = json.loads(self.rfile.read(length))
                save_config(data)
                cfg = load_config()
                reload_notification_schedule(cfg)
                if _app:
                    _app.config = cfg
                    _app.rebuild_menu()
                self.send_json(200, {"ok": True})
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
        self.config = load_config()
        self.rebuild_menu()
        # Kolla uppdateringar i bakgrunden vid start
        threading.Thread(target=self._bg_update_check, daemon=True).start()

    def _bg_update_check(self):
        result = check_for_update()
        if result:
            latest, notes = result
            self._prompt_update(latest, notes)

    def rebuild_menu(self):
        done = load_state()
        tasks = generate_tasks(self.config)
        urgent = [t for t in tasks if not done.get(t["id"]) and 0 <= days_until(t["deadline"]) <= 7]
        self.title = f"🐻 {len(urgent)}" if urgent else "🐻"

        items = []
        items.append(rumps.MenuItem(f"{self.config['company_name']}  {VERSION}", callback=None))
        items.append(rumps.separator)

        if urgent:
            items.append(rumps.MenuItem("⚠️  Inom 7 dagar", callback=None))
            for t in sorted(urgent, key=lambda x: x["deadline"]):
                items.append(self.make_item(t, done))
            items.append(rumps.separator)

        upcoming = [t for t in tasks if not done.get(t["id"]) and days_until(t["deadline"]) > 7]
        if upcoming:
            items.append(rumps.MenuItem("Kommande", callback=None))
            for t in sorted(upcoming, key=lambda x: x["deadline"])[:6]:
                items.append(self.make_item(t, done))
            items.append(rumps.separator)

        done_tasks = [t for t in tasks if done.get(t["id"])]
        if done_tasks:
            sub = rumps.MenuItem("Avklarade")
            for t in done_tasks:
                sub.add(self.make_item(t, done))
            items.append(sub)
            items.append(rumps.separator)

        items.append(rumps.MenuItem("📅  Öppna kalender",       callback=self.open_calendar))
        items.append(rumps.MenuItem("⚙️  Inställningar",        callback=self.open_settings))
        items.append(rumps.MenuItem("🔔  Testa notis",           callback=self.test_notification))
        items.append(rumps.MenuItem("🔄  Sök uppdateringar",     callback=self.check_update))
        items.append(rumps.separator)
        items.append(rumps.MenuItem("Starta om",                 callback=self.restart_app))

        self.menu.clear()
        self.menu = items

    def make_item(self, task, done):
        item = rumps.MenuItem(deadline_label(task, done), callback=self.toggle_done)
        item.task_id = task["id"]
        return item

    def toggle_done(self, sender):
        done = load_state()
        if done.get(sender.task_id):
            del done[sender.task_id]
        else:
            done[sender.task_id] = True
        save_state(done)
        self.rebuild_menu()

    def open_calendar(self, _):
        subprocess.run(["open", f"http://localhost:{PORT}/"])

    def open_settings(self, _):
        subprocess.run(["open", f"http://localhost:{PORT}/settings"])

    def test_notification(self, _):
        done = load_state()
        tasks = generate_tasks(self.config)
        upcoming = [t for t in tasks if not done.get(t["id"]) and days_until(t["deadline"]) >= 0]
        if not upcoming:
            send_notification("BearField IT", "Inga kommande deadlines", "Alla uppgifter är avklarade!")
            return
        task = sorted(upcoming, key=lambda t: t["deadline"])[0]
        d = days_until(task["deadline"])
        days_str = "idag!" if d == 0 else ("imorgon!" if d == 1 else f"om {d} dagar")
        send_notification(
            "BearField IT — Deadline",
            task["title"],
            f"{task['cat']} · {days_str} ({task['deadline']})"
        )

    def restart_app(self, _):
        relaunch_app()

    def _prompt_update(self, latest, notes):
        msg = f"Version {latest} finns tillgänglig.\n\n{notes}\n\nVill du uppdatera nu?"
        response = rumps.alert(
            title="Uppdatering tillgänglig",
            message=msg,
            ok="Uppdatera",
            cancel="Hoppa över"
        )
        if response == 1:
            do_update()

    @rumps.clicked("🔄  Sök uppdateringar")
    def check_update(self, _):
        result = check_for_update()
        if not result:
            rumps.alert("Redan uppdaterad", f"Du kör senaste versionen ({VERSION})")
            return
        latest, notes = result
        self._prompt_update(latest, notes)

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
