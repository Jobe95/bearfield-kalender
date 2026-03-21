#!/usr/bin/env python3
"""
BearField IT — Deadline-notiser
Körs varje morgon via launchd. Skickar Mac-notis om deadline inom 7 dagar.
"""

import os
import subprocess
from datetime import date, datetime

from tasks import generate_tasks, load_state

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(SCRIPT_DIR, "icon.png")

def days_until(deadline_str):
    return (datetime.strptime(deadline_str, "%Y-%m-%d").date() - date.today()).days

def notify(title, subtitle, message):
    try:
        from Foundation import NSUserNotification, NSUserNotificationCenter
        n = NSUserNotification.alloc().init()
        n.setTitle_(title)
        n.setSubtitle_(subtitle)
        n.setInformativeText_(message)
        NSUserNotificationCenter.defaultUserNotificationCenter().deliverNotification_(n)
    except Exception:
        script = f'display notification "{message}" with title "{title}" subtitle "{subtitle}"'
        subprocess.run(["osascript", "-e", script])

def main():
    done = load_state()
    today = date.today()
    upcoming = []

    for task in generate_tasks():
        if done.get(task["id"]):
            continue
        d = days_until(task["deadline"])
        if 0 <= d <= 7:
            upcoming.append((d, task))

    if not upcoming:
        return  # Inget att notifiera om

    upcoming.sort(key=lambda x: x[0])

    if len(upcoming) == 1:
        d, task = upcoming[0]
        if d == 0:
            days_str = "idag!"
        elif d == 1:
            days_str = "imorgon!"
        else:
            days_str = f"om {d} dagar"
        notify(
            title="BearField IT — Deadline",
            subtitle=task["title"],
            message=f"{task['cat']} · {days_str} ({task['deadline']})"
        )
    else:
        # Flera deadlines — en sammanfattning + individuella notiser
        names = ", ".join(t["title"] for _, t in upcoming[:2])
        extra = f" +{len(upcoming)-2} till" if len(upcoming) > 2 else ""
        notify(
            title=f"BearField IT — {len(upcoming)} deadlines inom 7 dagar",
            subtitle=names + extra,
            message="Öppna BearField Kalender för detaljer"
        )
        # En notis per uppgift
        for d, task in upcoming:
            days_str = "idag" if d == 0 else ("imorgon" if d == 1 else f"om {d} dagar")
            notify(
                title=task["title"],
                subtitle=f"{task['cat']} · {days_str}",
                message=f"Deadline {task['deadline']} — klicka för att öppna"
            )

if __name__ == "__main__":
    main()
