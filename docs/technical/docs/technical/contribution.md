
# Performance Contribution Analysis

Contribution analysis decomposes portfolio performance into contributions from individual **positions** or **groups**.  
It answers: *Which positions (or sectors) drove the portfolio’s return?*

---

## Inputs

- **portfolio_data** – Total portfolio daily series.
- **positions_data** – List of positions, each with:
  - `position_id`
  - `meta` – e.g., sector, region
  - `daily_data` – Array of daily values:
    - `perf_date`, `begin_mv`, `end_mv`, `bod_cf`, `eod_cf`, `mgmt_fees`
- **hierarchy** – Optional list of group-by fields (e.g., `["sector", "position_id"]`).
- **weighting_scheme** – Denominator convention:
  - `BOD` – Beginning-of-day market value.
  - `AVG_CAPITAL` – Average invested capital.
  - `TWR_DENOM` – Matches TWR denominator.
- **smoothing** – Multi-period linking method:
  - `CARINO` – Adjusts daily contributions to ensure exact reconciliation.
  - `NONE` – No smoothing applied.
- **emit** – Controls additional outputs:
  - `timeseries` – Total portfolio contribution by day.
  - `by_position_timeseries` – Per-position daily contributions.
  - `by_level` – Aggregated contributions by hierarchy level.
  - `top_n_per_level` – Limit results per group.
- **lookthrough** – Optional, enables multi-layer fund-of-fund decomposition.
- **bucketing** – Optional bucketing rules for grouping.

---

## Outputs

- **total_portfolio_return** – Portfolio TWR over the window.
- **total_contribution** – Sum of contributions across all positions.
- **position_contributions** – List with:
  - `position_id`
  - `total_contribution`
  - `average_weight`
  - `total_return`
- **timeseries** – Daily total contribution.
- **by_position_timeseries** – Per-position contribution series.
- **levels** – Hierarchical breakdown if `hierarchy` provided.
- **summary** – High-level stats:
  - Portfolio contribution
  - Coverage %
  - Weighting scheme used
- **meta / diagnostics / audit**

---

## Methodology

### 1. Position Daily Return
For each position:
\[
ROR_{p,t} = \frac{EndMV_{p,t} - (BeginMV_{p,t} + BODCF_{p,t} + EODCF_{p,t} + Fees_{p,t})}{BeginMV_{p,t} + BODCF_{p,t}}
\]

### 2. Position Weight
\[
Weight_{p,t} = \frac{BeginMV_{p,t} + BODCF_{p,t}}{BeginMV_{Portfolio,t} + BODCF_{Portfolio,t}}
\]

### 3. Daily Contribution
\[
Contrib_{p,t} = ROR_{p,t} \times Weight_{p,t}
\]

### 4. Multi-Period Linking
Daily contributions are compounded. To ensure reconciliation with portfolio TWR, **Carino smoothing** is applied:
- Adjusts each period’s contribution so that:
  \[
  \sum_p Contrib_{p} = TWR_{Portfolio}
  \]
- Residuals are distributed pro-rata by average weights.

### 5. Hierarchical Aggregation
- Contributions rolled up by `hierarchy` fields (e.g., sector → industry → position).
- “Other” and “Unclassified” buckets handled per config.

### 6. Reconciliation & Audit
- Residual (difference between total contribution and portfolio return) reported.
- Audit counts: positions processed, calculation days.

---

## Features

- **Single-level and multi-level contribution**.
- **Carino smoothing** for exact reconciliation.
- **Flexible weighting schemes** (BOD, average capital).
- **Lookthrough** for nested portfolios/funds.
- **Configurable output** – timeseries, by-position, by-level.
- **Residual tracking** for audit transparency.

---

## Example

### Request
```json
{
  "portfolio_number": "CONTRIB_EXAMPLE_01",
  "hierarchy": ["sector", "position_id"],
  "portfolio_data": {
    "report_start_date": "2025-01-01",
    "report_end_date": "2025-01-02",
    "period_type": "YTD",
    "metric_basis": "NET",
    "daily_data": [
      { "day": 1, "perf_date": "2025-01-01", "begin_mv": 1000, "end_mv": 1020 },
      { "day": 2, "perf_date": "2025-01-02", "begin_mv": 1020, "bod_cf": 50, "end_mv": 1080 }
    ]
  },
  "positions_data": [
    {
      "position_id": "Stock_A",
      "meta": { "sector": "Technology" },
      "daily_data": [
        { "day": 1, "perf_date": "2025-01-01", "begin_mv": 600, "end_mv": 612 },
        { "day": 2, "perf_date": "2025-01-02", "begin_mv": 612, "bod_cf": 50, "end_mv": 670 }
      ]
    },
    {
      "position_id": "Stock_B",
      "meta": { "sector": "Healthcare" },
      "daily_data": [
        { "day": 1, "perf_date": "2025-01-01", "begin_mv": 400, "end_mv": 408 },
        { "day": 2, "perf_date": "2025-01-02", "begin_mv": 408, "end_mv": 410 }
      ]
    }
  ]
}
````

### Response (simplified)

```json
{
  "calculation_id": "uuid",
  "portfolio_number": "CONTRIB_EXAMPLE_01",
  "total_portfolio_return": 7.0,
  "total_contribution": 7.0,
  "position_contributions": [
    { "position_id": "Stock_A", "total_contribution": 5.8, "average_weight": 0.60, "total_return": 9.5 },
    { "position_id": "Stock_B", "total_contribution": 1.2, "average_weight": 0.40, "total_return": 3.0 }
  ],
  "summary": {
    "portfolio_contribution": 7.0,
    "coverage_mv_pct": 100,
    "weighting_scheme": "BOD"
  },
  "levels": [
    {
      "level": 1,
      "name": "sector",
      "rows": [
        { "key": { "sector": "Technology" }, "contribution": 5.8, "weight_avg": 0.60 },
        { "key": { "sector": "Healthcare" }, "contribution": 1.2, "weight_avg": 0.40 }
      ]
    }
  ],
  "meta": { "...": "..." },
  "diagnostics": { "...": "..." },
  "audit": { "sum_of_parts_vs_total_bp": 0.0, "counts": { "input_positions": 2, "calculation_days": 2 } }
}
```

