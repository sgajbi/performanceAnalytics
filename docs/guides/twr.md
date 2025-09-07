# Time-Weighted Return (TWR) Methodology

The Time-Weighted Return (TWR) measures the compounded growth rate of a portfolio. It is the industry standard for judging the performance of a portfolio manager because it **neutralizes the distorting effects of cash flows** (i.e., deposits and withdrawals), isolating the performance attributable to investment decisions.

---

## Inputs

The TWR endpoint (`POST /performance/twr`) requires a time series of daily portfolio data.

-   **`performance_start_date`**: The earliest date for calculations (e.g., inception).
-   **`report_start_date` / `report_end_date`**: The specific window for the final report.
-   **`metric_basis`**: `NET` (after fees) or `GROSS` (before fees).
-   **`period_type`**: How the reporting window is defined (`YTD`, `ITD`, `EXPLICIT`, etc.).
-   **`frequencies`**: A list of desired aggregation periods (`daily`, `monthly`, `quarterly`, `yearly`).
-   **`daily_data`**: An array of daily records, each containing `perf_date`, `begin_mv`, `end_mv`, `bod_cf`, `eod_cf`, and `mgmt_fees`.

---

## Outputs

The response contains performance data aggregated into the requested `frequencies`.

-   **`breakdowns`**: A dictionary where each key is a frequency (e.g., `"monthly"`) and the value is a list of period results.
-   **`summary`**: Each period's summary includes:
    -   `begin_mv`, `end_mv`, `net_cash_flow`
    -   `period_return_pct`: The return for that specific period.
    -   `cumulative_return_pct_to_date`: The running cumulative TWR up to the end of that period (optional).
    -   `annualized_return_pct`: The annualized return for the period (optional).
-   **`reset_events`**: A list of any performance resets that occurred during the period (optional).
-   **Shared Envelope**: Includes `meta`, `diagnostics`, and `audit` blocks.

---

## Methodology

The TWR calculation is a multi-step process designed to handle complex scenarios like portfolios switching between long and short exposure.

### 1. Daily Return Calculation

For each day, the engine calculates a rate of return using a formula equivalent to the Modified Dietz method. This isolates the day's investment performance from its cash flows.

$$
R_{day} = \frac{EMV - BMV - (BOD_{CF} + EOD_{CF})}{BMV + BOD_{CF}}
$$

-   If `metric_basis` is `"NET"`, management fees (`mgmt_fees`) are added to the numerator, reducing the return.
-   If the denominator (`BMV + BOD_{CF}`) is zero, the daily return is zero.

### 2. Geometric Linking

To calculate the return over multiple days, the daily returns are geometrically linked (compounded).

$$
TWR_{period} = \left[ (1 + R_{day1}) \times (1 + R_{day2}) \times \dots \times (1 + R_{dayN}) \right] - 1
$$

### 3. Long & Short Sleeve Compounding

To correctly handle portfolios that can flip from net long to net short, the engine maintains two independent performance streams ("sleeves") and combines them.

-   **Long Sleeve**: Compiles returns only on days the portfolio is net long (`sign = 1`). The growth factor is $(1 + R_{day})$.
-   **Short Sleeve**: Compiles returns only on days the portfolio is net short (`sign = -1`). The growth factor is $(1 - R_{day})$. A gain in a short position (a drop in market value) results in a positive return.

The final cumulative return for any given day is the combination of the two sleeves:

$$
R_{final} = (1 + R_{long\_cumulative}) \times (1 + R_{short\_cumulative}) - 1
$$

### 4. Breakdown Aggregation & Annualization

-   **Aggregation**: After calculating the full daily performance series, the `breakdown` module groups the daily results by the requested `frequencies` (monthly, quarterly, etc.) and geometrically links the daily returns within each period.
-   **Annualization**: If requested, the period return is annualized using the standard formula, respecting the chosen `basis` (e.g., business days vs. calendar days).
    $$ Annualized = (1 + R_{period})^{\frac{\text{PeriodsPerYear}}{\text{NumPeriods}}} - 1 $$

### 5. Advanced Rules & Edge Cases

The engine applies several rules to ensure mathematical robustness.

-   **No Investment Period (NIP)**: A day is flagged as NIP if the portfolio starts and ends with a zero balance (`BMV + BOD_CF = 0` and `EMV + EOD_CF = 0`). On NIP days, the daily return is zero, and the previous day's cumulative return is carried forward.
-   **Performance Resets (NCTRL Flags)**: To prevent mathematically unsound compounding after a total loss of capital, the cumulative TWR for a sleeve is reset to zero. This is triggered by specific conditions, such as a long sleeve's cumulative return dropping below -100% (`NCTRL 1`) or a short sleeve's value inverting and rising above +100% (`NCTRL 2`).

---

## Features

-   **High-Performance**: Core daily calculations are vectorized using Pandas and NumPy.
-   **Flexible Breakdowns**: Aggregates daily performance into monthly, quarterly, or yearly summaries in a single call.
-   **Robust Logic**: Correctly handles long/short sign flips, NIP days, and performance resets.
-   **Configurable**: Supports NET/GROSS basis, multiple period types, and optional annualization.
-   **Auditable**: Provides detailed diagnostic information, including reset events, in the response.

---

## API Example

### Request

```json
{
  "portfolio_number": "TWR_EXAMPLE_01",
  "performance_start_date": "2024-12-31",
  "metric_basis": "NET",
  "report_start_date": "2025-01-01",
  "report_end_date": "2025-01-05",
  "period_type": "YTD",
  "frequencies": [
    "daily",
    "monthly"
  ],
  "daily_data": [
    { "day": 1, "perf_date": "2025-01-01", "begin_mv": 100000.0, "end_mv": 101000.0 },
    { "day": 2, "perf_date": "2025-01-02", "begin_mv": 101000.0, "end_mv": 102500.0 },
    { "day": 3, "perf_date": "2025-01-03", "begin_mv": 102500.0, "bod_cf": 5000.0, "end_mv": 108000.0 },
    { "day": 4, "perf_date": "2025-01-04", "begin_mv": 108000.0, "eod_cf": -2000.0, "end_mv": 106500.0 },
    { "day": 5, "perf_date": "2025-01-05", "begin_mv": 106500.0, "end_mv": 107000.0 }
  ]
}
```

### Response (Excerpt)

```json
{
  "calculation_id": "uuid-goes-here",
  "portfolio_number": "TWR_EXAMPLE_01",
  "breakdowns": {
    "daily": [
      {
        "period": "2025-01-01",
        "summary": { "begin_mv": 100000.0, "end_mv": 101000.0, "net_cash_flow": 0.0, "period_return_pct": 1.0, ... }
      }
    ],
    "monthly": [
      {
        "period": "2025-01",
        "summary": { "begin_mv": 100000.0, "end_mv": 107000.0, "net_cash_flow": 3000.0, "period_return_pct": 3.931..., ... }
      }
    ]
  },
  "meta": { ... },
  "diagnostics": { ... },
  "audit": { ... }
}
```