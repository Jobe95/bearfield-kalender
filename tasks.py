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


def save_config(cfg, path=None):
    """Save config to JSON file."""
    if path is None:
        path = CONFIG_FILE
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)


def load_state(path=None):
    """Load completion state from JSON file."""
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


def save_state(done, path=None):
    """Save completion state to JSON file."""
    if path is None:
        path = STATE_FILE
    with open(path, "w") as f:
        json.dump(done, f, indent=2)


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


def _swedish_month(m):
    """Return Swedish month name."""
    return ["januari", "februari", "mars", "april", "maj", "juni",
            "juli", "augusti", "september", "oktober", "november", "december"][m - 1]


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
                    "desc": "Varje månad den 12:e",
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
