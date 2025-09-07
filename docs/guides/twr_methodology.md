# TWR Methodology (Time-Weighted Return)

## Purpose
Time-Weighted Return (TWR) measures the portfolio’s return independent of external cash flows.  
It isolates the effect of investment decisions by neutralizing the timing and size of contributions/withdrawals.

---

## Inputs
- **Portfolio series**: daily or period-based rows with:
  - `date`
  - `begin_mv`
  - `bod_cf` (begin-of-day flows)
  - `fees` (management/advisory fees)
  - `tx_costs` (transaction/execution costs)
  - `eod_cf` (end-of-day flows)
  - `end_mv` (end-of-day MV after flows)
- **Config options**:
  - `periods` (EXPLICIT, YTD, QTD, ITD, rolling)
  - `annualization` (enabled, basis)
  - `metric_basis` (NET or GROSS)
  - `precision_mode`, `rounding`

---

## Outputs
- **Daily returns** (`ror`): period-by-period geometric returns
- **Cumulative return** (`cum_ror`): linked product of daily returns
- **Period return**: cumulative return over the requested window
- **Annualized return**: if requested, uses selected basis
- **Diagnostics**: resets, notes, bp residuals

---

## Methodology

### 1. Daily Return Calculation
For each day *t*:
```
ror_t = (end_mv_t - bod_cf_t - eod_cf_t - fees_t - tx_costs_t - begin_mv_t) /
         (begin_mv_t + bod_cf_t)
```
- Adjusts for flows and fees as configured (`metric_basis`).
- Returns may be computed **gross** (exclude fees/costs) or **net** (include them).

### 2. Cumulative Linking
```
cum_ror_T = Π (1 + ror_t) - 1
```
across all days in the period.

### 3. Periodization
- If `frequency=DAILY`: each row is 1 day.
- If `frequency=MONTHLY`: rows may represent month ends; linking applies the same way.
- ITD/YTD/QTD/MTD: resolved by `core/periods.py`.

### 4. Annualization
If enabled:
```
annualized = (1 + cum_ror_T)^(basis_days / elapsed_days) - 1
```
- `basis_days`: 252 (BUS_252), 365 (ACT_365), or actual days (ACT_ACT).
- `elapsed_days`: calendar or business days between start/end.

### 5. Resets & Diagnostics
- **NIP Days**: if `begin_mv=0`, ror is not computable; return = 0 with note.
- **Resets**: triggered by config (e.g., PERF_RESET flag).  
  Resets cut the linking chain and start new accumulation.
- **Residuals**: check that linked return matches portfolio NAV ratio within tolerance; differences reported in bps.

---

## Features
- Configurable `metric_basis` → choose NET vs GROSS return.
- Precision modes ensure deterministic output.
- Diagnostics provide transparency for audit/regulatory needs.
- Works for explicit periods or ITD/YTD/QTD/MTD/rolling windows.

---

## Example Walkthrough

### Input Series
| Date       | Begin MV | BOD CF | Fees | Tx Costs | EOD CF | End MV |
|------------|----------|--------|------|----------|--------|--------|
| 2025-01-02 | 1,000,000| 0      | 0    | 0        | 0      | 1,020,000 |
| 2025-01-03 | 1,020,000| 50,000 | -200 | -50      | 0      | 1,080,000 |
| 2025-01-04 | 1,080,000| 0      | 0    | 0        | 0      | 1,120,000 |

### Step 1: Daily Returns
- Day 1: (1,020,000 - 1,000,000) / 1,000,000 = 0.0200 (2.00%)
- Day 2: (1,080,000 - 50,000 - 1,020,000 - 200 - 50) / (1,020,000 + 50,000)
         = (1,080,000 - 1,070,250) / 1,070,000 = 0.000701 (0.07%)
- Day 3: (1,120,000 - 1,080,000) / 1,080,000 = 0.0370 (3.70%)

### Step 2: Cumulative Return
(1.02 × 1.000701 × 1.0370) - 1 = 0.0580 (5.80%)

### Step 3: Annualization (ACT/365, 3 days)
(1 + 0.0580)^(365/3) - 1 ≈ very large (illustrative only)

### Step 4: Output
```json
{
  "data": {
    "daily": [
      {"date": "2025-01-02", "ror": 0.0200, "cum_ror": 0.0200},
      {"date": "2025-01-03", "ror": 0.0007, "cum_ror": 0.0207},
      {"date": "2025-01-04", "ror": 0.0370, "cum_ror": 0.0580}
    ],
    "period": {
      "start": "2025-01-02",
      "end": "2025-01-04",
      "ror": 0.0580,
      "annualized_ror": 9.9999  // illustrative
    }
  },
  "meta": { "...": "..." },
  "diagnostics": {
    "notes": [],
    "residuals": {"bp_difference": 0.1}
  }
}
```

---

## Edge Cases
- `begin_mv=0`: return = 0.0, note emitted.
- Single-day periods: cum_ror = daily ror.
- Large flows → possible high/low denominator effects; ensure validation.
- Missing dates: must be contiguous when `frequency=DAILY`.

---

## References in Code
- `engine/ror.py`: daily return computation.
- `engine/compute.py`: linking and period aggregation.
- `core/annualize.py`: annualization bases.
- `core/periods.py`: period resolution.
- `core/envelope.py`: response structuring.

