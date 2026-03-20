# Deadline Accuracy — Design

## Problem

Task deadlines are incorrect in several ways:

1. **Bokföring lock uses wrong rule for quarterly/yearly VAT reporters** — app uses "end of following month" but BFL 5:2 requires 50 days after month end. Example: January 2026 shows Feb 28, actual deadline is March 23 (50 days + weekend shift).
2. **No weekend/holiday adjustment** — Swedish law shifts deadlines falling on Sat/Sun/helgdag to next business day. None of the generators account for this.

## Solution

### 1. Swedish Holiday Engine (in tasks.py)

- `_easter(year)` — Gregorian Easter via anonymous algorithm
- `_swedish_holidays(year)` — returns `set[date]`:
  - Fixed: Jan 1, Jan 6, May 1, Jun 6, Dec 24, Dec 25, Dec 26, Dec 31
  - Easter-derived: Långfredag (-2), Annandag påsk (+1), Kristi himmelsfärd (+39), Pingstdagen (+49)
  - Midsommarafton: Friday between Jun 19-25
  - Midsommardagen: Saturday between Jun 20-26
  - Alla helgons dag: Saturday between Oct 31–Nov 6
- `_next_business_day(d)` — advance past weekends and holidays

### 2. Fix Bokföring Lock (`_bookkeeping_lock_deadlines`)

New parameter: `vat_period`

| VAT period | Rule | Jan 2026 example |
|---|---|---|
| quarterly/yearly | month_end + 50 days | Mar 22 → Mar 23 (Sun→Mon) |
| monthly | 12th of 2nd month after | Mar 12 |

### 3. Apply `_next_business_day()` to All Generators

- `_quarterly_vat_deadlines` — 12th dates
- `_monthly_vat_deadlines` — 26th/12th dates
- `_employer_deadlines` — 12th dates
- `_prelim_tax_deadlines` — 12th dates
- `_quarterly_bookkeeping_deadlines` — month-end dates
- `_annual_deadlines` — bokslut/INK2/årsredovisning dates

### 4. Tests

- Easter spot-checks (known years)
- `_next_business_day` with weekend + holiday inputs
- Bokföring lock quarterly → 50 days
- Bokföring lock monthly → 12th of 2nd month
- January 2026 quarterly → March 23
