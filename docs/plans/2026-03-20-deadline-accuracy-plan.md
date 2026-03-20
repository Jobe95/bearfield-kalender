# Deadline Accuracy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all deadline calculations to match Swedish law — correct bookkeeping lock rule per VAT period, add weekend/holiday shifting via a zero-dependency Swedish holiday engine.

**Architecture:** Add three private helpers to `tasks.py` (`_easter`, `_swedish_holidays`, `_next_business_day`), fix `_bookkeeping_lock_deadlines` to accept `vat_period`, then thread `_next_business_day` through every generator's `due` date before it's used. No new files, no new dependencies.

**Tech Stack:** Python 3, stdlib only (`datetime`, `calendar`)

---

### Task 1: Add Swedish holiday engine — tests

**Files:**
- Modify: `test_tasks.py`

**Step 1: Write failing tests for `_easter` and `_swedish_holidays`**

Add these imports and tests to `test_tasks.py`:

```python
from tasks import _easter, _swedish_holidays, _next_business_day
```

```python
def test_easter_known_dates():
    """Easter algorithm matches known dates."""
    assert _easter(2025) == date(2025, 4, 20)
    assert _easter(2026) == date(2026, 4, 5)
    assert _easter(2027) == date(2027, 3, 28)
    assert _easter(2030) == date(2030, 4, 21)

def test_swedish_holidays_fixed():
    """Fixed holidays are always present."""
    h = _swedish_holidays(2026)
    assert date(2026, 1, 1) in h    # Nyårsdagen
    assert date(2026, 1, 6) in h    # Trettondedag jul
    assert date(2026, 5, 1) in h    # Första maj
    assert date(2026, 6, 6) in h    # Nationaldagen
    assert date(2026, 12, 24) in h  # Julafton
    assert date(2026, 12, 25) in h  # Juldagen
    assert date(2026, 12, 26) in h  # Annandag jul
    assert date(2026, 12, 31) in h  # Nyårsafton

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
    assert date(2026, 10, 31) in h  # Alla helgons dag 2026
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/jonatanbengtsson/Dev/Source/Apps/BearFieldApp && python -m pytest test_tasks.py::test_easter_known_dates -v`
Expected: ImportError — `_easter` not found

---

### Task 2: Add Swedish holiday engine — implementation

**Files:**
- Modify: `tasks.py:84` (insert after `_add_months`, before `_quarter_end`)

**Step 1: Implement `_easter(year)`**

Insert after line 91 (after `_add_months`):

```python
def _easter(year):
    """Compute Easter Sunday for a given year (Anonymous Gregorian algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)
```

**Step 2: Implement `_swedish_holidays(year)`**

Insert right after `_easter`:

```python
def _swedish_holidays(year):
    """Return set of Swedish public holidays + non-working days for a year."""
    easter = _easter(year)
    holidays = {
        # Fixed
        date(year, 1, 1),    # Nyårsdagen
        date(year, 1, 6),    # Trettondedag jul
        date(year, 5, 1),    # Första maj
        date(year, 6, 6),    # Nationaldagen
        date(year, 12, 24),  # Julafton
        date(year, 12, 25),  # Juldagen
        date(year, 12, 26),  # Annandag jul
        date(year, 12, 31),  # Nyårsafton
        # Easter-derived
        easter + timedelta(days=-2),   # Långfredag
        easter + timedelta(days=1),    # Annandag påsk
        easter + timedelta(days=39),   # Kristi himmelsfärd
        easter + timedelta(days=49),   # Pingstdagen
    }
    # Midsommarafton: Friday between Jun 19-25
    for d in range(19, 26):
        candidate = date(year, 6, d)
        if candidate.weekday() == 4:  # Friday
            holidays.add(candidate)                  # Midsommarafton
            holidays.add(candidate + timedelta(days=1))  # Midsommardagen (Saturday)
            break
    # Alla helgons dag: Saturday between Oct 31–Nov 6
    for offset in range(7):
        candidate = date(year, 10, 31) + timedelta(days=offset)
        if candidate.weekday() == 5:  # Saturday
            holidays.add(candidate)
            break
    return holidays
```

**Step 3: Implement `_next_business_day(d)`**

Insert right after `_swedish_holidays`:

```python
def _next_business_day(d):
    """Advance date to next business day if it falls on weekend or Swedish holiday."""
    holidays = _swedish_holidays(d.year) | _swedish_holidays(d.year + 1)
    while d.weekday() >= 5 or d in holidays:
        d += timedelta(days=1)
    return d
```

Note: We union with next year's holidays to handle Dec 31 → Jan shifts.

**Step 4: Run all holiday tests**

Run: `cd /Users/jonatanbengtsson/Dev/Source/Apps/BearFieldApp && python -m pytest test_tasks.py -k "easter or holiday or helgon or midsommar" -v`
Expected: All PASS

**Step 5: Commit**

```
feat: add Swedish holiday engine
```

---

### Task 3: Add `_next_business_day` tests

**Files:**
- Modify: `test_tasks.py`

**Step 1: Write tests for `_next_business_day`**

```python
def test_next_business_day_weekday_unchanged():
    """A regular weekday stays unchanged."""
    assert _next_business_day(date(2026, 3, 18)) == date(2026, 3, 18)  # Wednesday

def test_next_business_day_saturday():
    """Saturday advances to Monday."""
    assert _next_business_day(date(2026, 3, 21)) == date(2026, 3, 23)  # Sat → Mon

def test_next_business_day_sunday():
    """Sunday advances to Monday."""
    assert _next_business_day(date(2026, 3, 22)) == date(2026, 3, 23)  # Sun → Mon

def test_next_business_day_holiday():
    """Holiday on weekday advances to next business day."""
    # 2026-01-06 is Trettondedag jul (Tuesday)
    assert _next_business_day(date(2026, 1, 6)) == date(2026, 1, 7)  # Wed

def test_next_business_day_holiday_before_weekend():
    """Friday holiday advances past weekend to Monday."""
    # 2026-04-03 is Långfredag (Friday) → skip Sat+Sun → Mon Apr 6 is Annandag påsk → Tue Apr 7
    assert _next_business_day(date(2026, 4, 3)) == date(2026, 4, 7)

def test_next_business_day_christmas_chain():
    """Dec 24 (Thu 2026) → skip 24,25,26 (holidays) → next check 27 (Sat) → 28 (Sun) → Mon 29."""
    # 2026: Dec 24=Thu(holiday), 25=Fri(holiday), 26=Sat(holiday+weekend), 27=Sun, 28=Mon
    assert _next_business_day(date(2026, 12, 24)) == date(2026, 12, 28)

def test_next_business_day_new_years_eve():
    """Dec 31 is a holiday. 2025-12-31 is Wednesday → Jan 1 (holiday Thu) → Jan 2 Fri."""
    assert _next_business_day(date(2025, 12, 31)) == date(2026, 1, 2)
```

**Step 2: Run tests**

Run: `cd /Users/jonatanbengtsson/Dev/Source/Apps/BearFieldApp && python -m pytest test_tasks.py -k "next_business" -v`
Expected: All PASS (implementation already exists from Task 2)

**Step 3: Commit**

```
test: add _next_business_day tests
```

---

### Task 4: Fix bookkeeping lock deadlines — tests

**Files:**
- Modify: `test_tasks.py`

**Step 1: Write failing tests for new bookkeeping lock logic**

```python
def test_bookkeeping_lock_quarterly_50_day_rule():
    """Quarterly VAT: lock deadline = 50 days after month end."""
    cfg = dict(load_config("/nonexistent"))
    cfg["vat_period"] = "quarterly"
    tasks = generate_tasks(cfg, ref_date=date(2026, 3, 20))
    lock_jan = next(t for t in tasks if t["id"] == "lock-2026-01")
    # Jan 31 + 50 days = Mar 22 (Sunday) → Mar 23 (Monday)
    assert lock_jan["deadline"] == "2026-03-23"

def test_bookkeeping_lock_quarterly_feb():
    """Quarterly VAT: February lock = 50 days after Feb 28."""
    cfg = dict(load_config("/nonexistent"))
    cfg["vat_period"] = "quarterly"
    tasks = generate_tasks(cfg, ref_date=date(2026, 4, 1))
    lock_feb = next(t for t in tasks if t["id"] == "lock-2026-02")
    # Feb 28 + 50 days = Apr 19 (Sunday) → Apr 20 (Monday)
    assert lock_feb["deadline"] == "2026-04-20"

def test_bookkeeping_lock_monthly_uses_vat_deadline():
    """Monthly VAT: lock deadline = 12th of 2nd month after."""
    cfg = dict(load_config("/nonexistent"))
    cfg["vat_period"] = "monthly"
    tasks = generate_tasks(cfg, ref_date=date(2026, 3, 20))
    lock_jan = next(t for t in tasks if t["id"] == "lock-2026-01")
    # January → 12th of March = Mar 12 (Thursday, no shift)
    assert lock_jan["deadline"] == "2026-03-12"
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/jonatanbengtsson/Dev/Source/Apps/BearFieldApp && python -m pytest test_tasks.py::test_bookkeeping_lock_quarterly_50_day_rule -v`
Expected: FAIL — deadline is still "2026-02-28"

---

### Task 5: Fix bookkeeping lock deadlines — implementation

**Files:**
- Modify: `tasks.py:203-225` (`_bookkeeping_lock_deadlines`)
- Modify: `tasks.py:327` (call site in `generate_tasks`)

**Step 1: Update `_bookkeeping_lock_deadlines` signature and logic**

Replace the entire `_bookkeeping_lock_deadlines` function (lines 203-225):

```python
def _bookkeeping_lock_deadlines(ref_date, vat_period):
    """Generate monthly bookkeeping lock deadlines based on VAT period.

    BFL 5:2 rules:
    - quarterly/yearly VAT: 50 days after month end
    - monthly VAT: 12th of 2nd month after (aligns with VAT return due date)
    """
    tasks = []
    window_start = ref_date - timedelta(days=30)
    window_end = ref_date + timedelta(days=365)

    for year in range(ref_date.year, ref_date.year + 2):
        for month in range(1, 13):
            month_end = date(year, month, monthrange(year, month)[1])
            if vat_period in ("quarterly", "yearly"):
                due = _next_business_day(month_end + timedelta(days=50))
            else:
                # monthly: 12th of 2nd month after
                due = _next_business_day(_add_months(month_end, 2).replace(day=12))
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
```

**Step 2: Update call site in `generate_tasks` (line 327)**

Change:
```python
    tasks.extend(_bookkeeping_lock_deadlines(ref_date))
```
To:
```python
    tasks.extend(_bookkeeping_lock_deadlines(ref_date, cfg["vat_period"]))
```

**Step 3: Run bookkeeping lock tests**

Run: `cd /Users/jonatanbengtsson/Dev/Source/Apps/BearFieldApp && python -m pytest test_tasks.py -k "bookkeeping_lock" -v`
Expected: All PASS

**Step 4: Commit**

```
fix: bookkeeping lock uses BFL 5:2 rules per VAT period
```

---

### Task 6: Apply `_next_business_day` to all other generators

**Files:**
- Modify: `tasks.py` — all generator functions

**Step 1: Update `_quarterly_vat_deadlines` (line 116)**

Change:
```python
            due = _add_months(qe, 2).replace(day=12)
```
To:
```python
            due = _next_business_day(_add_months(qe, 2).replace(day=12))
```

**Step 2: Update `_monthly_vat_deadlines` (lines 140, 143)**

Change:
```python
                due = date(year + 1, 2, 12)
```
To:
```python
                due = _next_business_day(date(year + 1, 2, 12))
```

Change:
```python
                due = date(year, next_m, 26)
```
To:
```python
                due = _next_business_day(date(year, next_m, 26))
```

**Step 3: Update `_employer_deadlines` (line 166)**

Change:
```python
            due = date(year, month, 12)
```
To:
```python
            due = _next_business_day(date(year, month, 12))
```

**Step 4: Update `_prelim_tax_deadlines` (line 190)**

Change:
```python
            due = date(year, month, 12)
```
To:
```python
            due = _next_business_day(date(year, month, 12))
```

**Step 5: Update `_quarterly_bookkeeping_deadlines` (lines 238-239)**

Change:
```python
            due = _add_months(qe, 1)
            due = due.replace(day=monthrange(due.year, due.month)[1])
```
To:
```python
            due = _add_months(qe, 1)
            due = _next_business_day(due.replace(day=monthrange(due.year, due.month)[1]))
```

**Step 6: Update `_annual_deadlines` — bokslut (line 265)**

Change:
```python
        bokslut_due = _add_months(fy_end, 6)
```
To:
```python
        bokslut_due = _next_business_day(_add_months(fy_end, 6))
```

**Step 7: Update `_annual_deadlines` — INK2 (line 277)**

Change:
```python
        ink2_due = _add_months(fy_end, 7).replace(day=1)
```
To:
```python
        ink2_due = _next_business_day(_add_months(fy_end, 7).replace(day=1))
```

**Step 8: Update `_annual_deadlines` — årsredovisning (line 289)**

Change:
```python
        ar_due = _add_months(fy_end, 7)
```
To:
```python
        ar_due = _next_business_day(_add_months(fy_end, 7))
```

**Step 9: Run full test suite**

Run: `cd /Users/jonatanbengtsson/Dev/Source/Apps/BearFieldApp && python -m pytest test_tasks.py -v`
Expected: Some existing tests may need date adjustments (Task 7)

**Step 10: Commit**

```
fix: apply weekend/holiday shift to all deadline generators
```

---

### Task 7: Fix existing tests for business day shifts

**Files:**
- Modify: `test_tasks.py`

**Step 1: Update `test_quarterly_vat_tasks`**

The Q1 2026 VAT deadline is May 12, 2026 (Tuesday) — no shift needed. This test should still pass.
Verify by running: `cd /Users/jonatanbengtsson/Dev/Source/Apps/BearFieldApp && python -m pytest test_tasks.py::test_quarterly_vat_tasks -v`

**Step 2: Run full suite and fix any broken assertions**

Run: `cd /Users/jonatanbengtsson/Dev/Source/Apps/BearFieldApp && python -m pytest test_tasks.py -v`

If any tests fail due to shifted dates, update the expected values. The `test_stable_ids` and `test_task_has_required_fields` tests should pass unchanged. The `test_fiscal_year_end_affects_bokslut` test checks loosely (`"2026" in deadline`) so should pass.

**Step 3: Commit**

```
test: update assertions for business day shifts
```

---

### Task 8: Add integration test for Jan 2026 quarterly scenario

**Files:**
- Modify: `test_tasks.py`

**Step 1: Write the user's real-world scenario as a test**

```python
def test_jan_2026_quarterly_full_scenario():
    """Real-world: quarterly VAT, Jan 2026 lock = Mar 23, Q1 VAT = May 12."""
    cfg = dict(load_config("/nonexistent"))
    cfg["vat_period"] = "quarterly"
    cfg["employer_registered"] = False
    tasks = generate_tasks(cfg, ref_date=date(2026, 3, 20))

    # Bookkeeping lock for January: 50 days after Jan 31 = Mar 22 (Sun) → Mar 23
    lock_jan = next(t for t in tasks if t["id"] == "lock-2026-01")
    assert lock_jan["deadline"] == "2026-03-23"

    # Q1 VAT declaration: May 12 (Tue, no shift)
    vat_q1 = next(t for t in tasks if t["id"] == "vat-2026-Q1")
    assert vat_q1["deadline"] == "2026-05-12"

    # Preliminärskatt March: Mar 12 (Thu, no shift)
    tax_mar = next(t for t in tasks if t["id"] == "tax-2026-03")
    assert tax_mar["deadline"] == "2026-03-12"
```

**Step 2: Run the test**

Run: `cd /Users/jonatanbengtsson/Dev/Source/Apps/BearFieldApp && python -m pytest test_tasks.py::test_jan_2026_quarterly_full_scenario -v`
Expected: PASS

**Step 3: Commit**

```
test: add Jan 2026 quarterly integration test
```

---

### Task 9: Final verification

**Step 1: Run full test suite**

Run: `cd /Users/jonatanbengtsson/Dev/Source/Apps/BearFieldApp && python -m pytest test_tasks.py -v`
Expected: All tests PASS

**Step 2: Smoke test with actual config**

Run: `cd /Users/jonatanbengtsson/Dev/Source/Apps/BearFieldApp && python -c "from tasks import generate_tasks; [print(f'{t[\"id\"]:30s} {t[\"deadline\"]}  {t[\"title\"]}') for t in generate_tasks()]"`
Expected: Printed list of tasks with shifted deadlines. Verify lock-2026-01 shows 2026-03-23.
