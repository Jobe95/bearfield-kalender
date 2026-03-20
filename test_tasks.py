import json
import os
import tempfile
from datetime import date
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
