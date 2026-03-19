#!/usr/bin/env python3
"""
BearField IT — Deadline-notiser
Körs varje morgon via launchd. Skickar Mac-notis om deadline inom 7 dagar.
"""

import subprocess
import json
import os
from datetime import date, datetime

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

# Sökväg till avbocknings-state (samma mapp som detta skript)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "done_state.json")
APP_HTML = os.path.join(SCRIPT_DIR, "kalender.html")

def load_done():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def days_until(deadline_str):
    d = datetime.strptime(deadline_str, "%Y-%m-%d").date()
    return (d - date.today()).days

def notify(title, subtitle, message):
    script = f'''
    display notification "{message}" with title "{title}" subtitle "{subtitle}"
    '''
    subprocess.run(["osascript", "-e", script])

def open_app(_):
    subprocess.run(["open", APP_HTML])

def main():
    done = load_done()
    today = date.today()
    upcoming = []

    for task in TASKS:
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
