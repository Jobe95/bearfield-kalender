import json
import os
import tempfile
from datetime import date
from tasks import load_config, save_config, generate_tasks, _easter, _swedish_holidays, _next_business_day

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

def test_save_and_load_config():
    """save_config writes JSON that load_config reads back."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = f.name
    try:
        cfg = {"org_nr": "5591234567", "company_name": "Test AB", "vat_period": "monthly",
               "fiscal_year_end": "06-30", "employer_registered": False, "notification_time": "09:00"}
        save_config(cfg, path)
        loaded = load_config(path)
        assert loaded["org_nr"] == "5591234567"
        assert loaded["vat_period"] == "monthly"
        assert loaded["employer_registered"] is False
    finally:
        os.unlink(path)

def test_easter_known_dates():
    """Easter algorithm matches known dates."""
    assert _easter(2025) == date(2025, 4, 20)
    assert _easter(2026) == date(2026, 4, 5)
    assert _easter(2027) == date(2027, 3, 28)
    assert _easter(2030) == date(2030, 4, 21)

def test_swedish_holidays_fixed():
    """Fixed holidays are always present."""
    h = _swedish_holidays(2026)
    assert date(2026, 1, 1) in h
    assert date(2026, 1, 6) in h
    assert date(2026, 5, 1) in h
    assert date(2026, 6, 6) in h
    assert date(2026, 12, 24) in h
    assert date(2026, 12, 25) in h
    assert date(2026, 12, 26) in h
    assert date(2026, 12, 31) in h

def test_swedish_holidays_easter_derived():
    """Easter-derived holidays for 2026 (Easter = Apr 5)."""
    h = _swedish_holidays(2026)
    assert date(2026, 4, 3) in h   # Långfredag (Easter-2)
    assert date(2026, 4, 6) in h   # Annandag påsk (Easter+1)
    assert date(2026, 5, 14) in h  # Kristi himmelsfärd (Easter+39)
    assert date(2026, 5, 24) in h  # Pingstdagen (Easter+49)

def test_swedish_holidays_midsommar():
    """Midsommarafton is Friday Jun 19-25, Midsommardagen is Saturday Jun 20-26."""
    h = _swedish_holidays(2026)
    assert date(2026, 6, 19) in h  # Midsommarafton (Friday)
    assert date(2026, 6, 20) in h  # Midsommardagen (Saturday)

def test_swedish_holidays_alla_helgons_dag():
    """Alla helgons dag is Saturday Oct 31–Nov 6."""
    h = _swedish_holidays(2026)
    assert date(2026, 10, 31) in h

def test_next_business_day_weekday_unchanged():
    """A regular weekday stays unchanged."""
    assert _next_business_day(date(2026, 3, 18)) == date(2026, 3, 18)

def test_next_business_day_saturday():
    """Saturday advances to Monday."""
    assert _next_business_day(date(2026, 3, 21)) == date(2026, 3, 23)

def test_next_business_day_sunday():
    """Sunday advances to Monday."""
    assert _next_business_day(date(2026, 3, 22)) == date(2026, 3, 23)

def test_next_business_day_holiday():
    """Holiday on weekday advances to next business day."""
    assert _next_business_day(date(2026, 1, 6)) == date(2026, 1, 7)

def test_next_business_day_holiday_before_weekend():
    """Friday holiday advances past weekend to Monday."""
    # 2026-04-03 is Långfredag (Friday) → Sat → Sun → Mon Apr 6 is Annandag påsk → Tue Apr 7
    assert _next_business_day(date(2026, 4, 3)) == date(2026, 4, 7)

def test_next_business_day_christmas_chain():
    """Dec 24 (Thu 2026) → skip 24,25,26 (holidays) → 27 (Sat) → 28 (Sun) → Mon 29."""
    assert _next_business_day(date(2026, 12, 24)) == date(2026, 12, 28)

def test_next_business_day_new_years_eve():
    """Dec 31 is holiday. 2025-12-31 is Wed → Jan 1 (holiday Thu) → Jan 2 Fri."""
    assert _next_business_day(date(2025, 12, 31)) == date(2026, 1, 2)
