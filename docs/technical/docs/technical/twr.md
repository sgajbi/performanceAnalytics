
# Time-Weighted Return (TWR)

The Time-Weighted Return (TWR) measures portfolio performance by neutralizing the impact of external cash flows.  
It is the industry standard for comparing portfolio managers, since it isolates investment skill from investor-driven contributions or withdrawals.

---

## Inputs

- **performance_start_date** – Portfolio inception or first available day.
- **report_start_date / report_end_date** – Reporting window.
- **metric_basis** – `NET` (after fees) or `GROSS` (before fees).
- **period_type** – Defines reporting window (YTD, MTD, ITD, Explicit, etc.).
- **frequencies** – Output breakdowns: `daily`, `monthly`, `quarterly`, `yearly`.
- **daily_data** – Array of daily records with:
  - `day` – Sequential day index.
  - `perf_date` – Date.
  - `begin_mv` – Beginning market value.
  - `end_mv` – Ending market value.
  - `bod_cf` – Cash flow at start of day.
  - `eod_cf` – Cash flow at end of day.
  - `mgmt_fees` – Fees impacting NAV.

---

## Outputs

- **breakdowns** – Dictionary keyed by frequency:
  - Each entry has:
    - `period` – e.g., `2025-01-01` or `2025-Q1`.
    - `summary` – Includes:
      - `begin_mv`, `end_mv`
      - `net_cash_flow`
      - `period_return_pct`
      - `cumulative_return_pct_to_date`
      - `annualized_return_pct` (if enabled)
- **meta** – Calculation ID, engine version, precision, periods.
- **diagnostics** – NIP days, reset days, notes.
- **audit** – Row counts, reconciliation checks.
- **reset_events** – Optional; lists any resets applied to calculation.

---

## Methodology

### 1. Daily Return Calculation
For each day `t`:
\[
ROR_t = \frac{EndMV_t - (BeginMV_t + BODCF_t + EODCF_t + Fees_t)}{BeginMV_t + BODCF_t}
\]

Where:
- **EndMV** – Ending market value.
- **BeginMV** – Beginning market value.
- **BODCF** – Beginning-of-day cash flows.
- **EODCF** – End-of-day cash flows.
- **Fees** – Management fees (reduce NAV).

### 2. Geometric Linking
To compute multi-day return:
\[
TWR_{1..n} = \prod_{t=1}^{n} (1 + ROR_t) - 1
\]

This ensures compounding is respected.

### 3. Breakdown Aggregation
- **Daily** – Raw daily RORs.
- **Monthly/Quarterly/Yearly** – Group by calendar period and compound daily returns.
- **Cumulative** – Track cumulative compounded return over reporting window.

### 4. Annualization
If enabled:
\[
Annualized = (1 + TWR)^{\frac{PeriodsPerYear}{N}} - 1
\]
Where `N` = number of periods in the reporting window.

---

## Features

- Vectorized Pandas/NumPy calculations for speed.
- Supports multiple breakdown frequencies in one request.
- Net vs. Gross returns controlled via `metric_basis`.
- Optional annualization with configurable basis (`BUS/252`, `ACT/365`, `ACT/ACT`).
- Diagnostics for reset events (e.g., portfolio inception resets).

---

## Example

### Request
```json
{
  "portfolio_number": "TWR_EXAMPLE_01",
  "performance_start_date": "2024-12-31",
  "metric_basis": "NET",
  "report_start_date": "2025-01-01",
  "report_end_date": "2025-01-05",
  "period_type": "YTD",
  "frequencies": ["daily", "monthly"],
  "daily_data": [
    { "day": 1, "perf_date": "2025-01-01", "begin_mv": 100000, "end_mv": 101000 },
    { "day": 2, "perf_date": "2025-01-02", "begin_mv": 101000, "end_mv": 102500 },
    { "day": 3, "perf_date": "2025-01-03", "begin_mv": 102500, "bod_cf": 5000, "end_mv": 108000 },
    { "day": 4, "perf_date": "2025-01-04", "begin_mv": 108000, "eod_cf": -2000, "end_mv": 106500 },
    { "day": 5, "perf_date": "2025-01-05", "begin_mv": 106500, "end_mv": 107000 }
  ]
}
````

### Response (simplified)

```json
{
  "calculation_id": "uuid",
  "portfolio_number": "TWR_EXAMPLE_01",
  "breakdowns": {
    "daily": [
      {
        "period": "2025-01-01",
        "summary": {
          "begin_mv": 100000,
          "end_mv": 101000,
          "net_cash_flow": 0,
          "period_return_pct": 1.0,
          "cumulative_return_pct_to_date": 1.0
        }
      },
      { "...": "..." }
    ],
    "monthly": [
      {
        "period": "2025-01",
        "summary": {
          "begin_mv": 100000,
          "end_mv": 107000,
          "net_cash_flow": 3000,
          "period_return_pct": 7.0,
          "cumulative_return_pct_to_date": 7.0
        }
      }
    ]
  },
  "meta": { "...": "..." },
  "diagnostics": { "...": "..." },
  "audit": { "...": "..." }
}
```
 