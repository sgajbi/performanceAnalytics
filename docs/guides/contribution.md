# Performance Contribution Methodology

Performance contribution analysis decomposes a portfolio's total Time-Weighted Return (TWR) into the contributions from its individual positions or groups. It is a powerful tool for answering the critical question: *"Which investments drove the portfolio’s performance?"*

The engine supports both single-level (by position) and multi-level hierarchical breakdowns (e.g., Asset Class -> Sector -> Security).

---

## Inputs

The Contribution endpoint (`POST /performance/contribution`) requires time series data for the total portfolio and for each underlying position.

-   **`portfolio_data`**: The daily time series for the total portfolio.
-   **`positions_data`**: A list of positions, each containing its unique `position_id`, `meta` data for grouping (e.g., `{"sector": "Technology"}`), and its own `daily_data` series.
-   **`hierarchy`**: An optional ordered list of `meta` fields to define the aggregation hierarchy (e.g., `["sector", "position_id"]`). If omitted, a single-level analysis is performed.
-   **`smoothing`**: The method for linking multi-period contributions. `CARINO` is the default and recommended method. `NONE` provides a simple arithmetic sum.
-   **`weighting_scheme`**: The method for calculating daily position weights. `BOD` (Beginning of Day) is the default.
-   **`emit`**: Flags to request additional outputs like daily time series data.

---

## Outputs

The response provides a detailed breakdown of contributions, either as a flat list or a hierarchical structure.

-   **`position_contributions`**: For single-level analysis, a list of contributions, average weights, and returns for each position.
-   **`summary` & `levels`**: For hierarchical analysis, a high-level summary and a detailed breakdown for each level of the hierarchy.
-   **`timeseries`**: Optional daily contribution data.
-   **Shared Envelope**: Includes `meta`, `diagnostics`, and `audit` blocks, including a key reconciliation check in `audit.sum_of_parts_vs_total_bp`.

---

## Methodology

The engine follows a rigorous, bottom-up approach to ensure that the sum of contributions perfectly reconciles to the total portfolio return.

### 1. Position Daily Return & Weight

For each position on each day, the engine first calculates two key metrics:

-   **Daily Return ($R_{p,t}$)**: The TWR for the position on day `t`, calculated using the same Modified Dietz formula as the main TWR engine.
-   **Daily Weight ($W_{p,t}$)**: The position's weight relative to the total portfolio, based on the selected `weighting_scheme`. For the default `BOD` scheme:
    $$ W_{p,t} = \frac{BMV_{position,t} + BOD_{CF,position,t}}{BMV_{portfolio,t} + BOD_{CF,portfolio,t}} $$

### 2. Single-Period Contribution

The raw contribution for a single day is simply the position's return multiplied by its weight.

$$
C_{p,t} = W_{p,t} \times R_{p,t}
$$

### 3. Multi-Period Linking (Carino Smoothing)

Simply adding daily contributions over time is mathematically incorrect because it ignores the effect of compounding. To solve this, the engine uses the **Carino Smoothing Algorithm** by default.

This algorithm calculates an adjustment factor for each day based on the **total portfolio's daily return**. This factor intelligently re-allocates the portfolio's geometric excess (the return generated from compounding) back to the individual positions based on their weight. The result is a "smoothed" daily contribution.

### 4. Hierarchical Aggregation

When a `hierarchy` is provided, the engine performs a **bottom-up aggregation**:

1.  The total smoothed contribution is calculated for every individual instrument over the entire period by summing its smoothed daily contributions.
2.  The engine groups these instrument-level contributions by the most granular level of the hierarchy (e.g., by `position_id`).
3.  The contributions are then summed up to each parent level (e.g., the contributions of all positions in the "Technology" sector are summed to get the total contribution for that sector).

This bottom-up approach guarantees that the sum of contributions at any level perfectly reconciles to the contribution of its parent, all the way to the total portfolio return.

### 5. Residual Allocation & Event Handling

-   **Residuals**: After smoothing, any tiny remaining difference between the sum of contributions and the total portfolio TWR (due to floating-point precision) is calculated and distributed across the positions, proportional to their average weights. This ensures a perfect final reconciliation.
-   **Event Handling**: On days flagged by the TWR engine as a **No-Investment-Period (NIP)** or a **Performance Reset**, the contribution for all positions is set to **zero** to remain consistent with the portfolio-level calculation.

---

## Features

-   **Multi-Level Analysis**: Decomposes performance across any user-defined hierarchy.
-   **Mathematically Exact**: Uses the Carino algorithm and residual distribution to ensure the sum of parts perfectly equals the whole.
-   **Consistent with TWR**: Respects all portfolio-level events like NIPs and resets from the core TWR engine.
-   **Configurable**: Supports different weighting schemes and allows smoothing to be disabled for simple arithmetic analysis.

---

## API Example

### Request

```json
{
  "portfolio_number": "CONTRIB_EXAMPLE_01",
  "hierarchy": [ "sector", "position_id" ],
  "portfolio_data": {
    "report_start_date": "2025-01-01",
    "report_end_date": "2025-01-02",
    "period_type": "YTD", "metric_basis": "NET",
    "daily_data": [
      { "day": 1, "perf_date": "2025-01-01", "begin_mv": 1000, "end_mv": 1020 },
      { "day": 2, "perf_date": "2025-01-02", "begin_mv": 1020, "bod_cf": 50, "end_mv": 1080 }
    ]
  },
  "positions_data": [
    {
      "position_id": "Stock_A", "meta": { "sector": "Technology" },
      "daily_data": [
        { "day": 1, "perf_date": "2025-01-01", "begin_mv": 600, "end_mv": 612 },
        { "day": 2, "perf_date": "2025-01-02", "begin_mv": 612, "bod_cf": 50, "end_mv": 670 }
      ]
    },
    {
      "position_id": "Stock_B", "meta": { "sector": "Healthcare" },
      "daily_data": [
        { "day": 1, "perf_date": "2025-01-01", "begin_mv": 400, "end_mv": 408 },
        { "day": 2, "perf_date": "2025-01-02", "begin_mv": 408, "end_mv": 410 }
      ]
    }
  ]
}
```

### Response (Excerpt)

```json
{
  "calculation_id": "uuid-goes-here",
  "portfolio_number": "CONTRIB_EXAMPLE_01",
  "summary": {
    "portfolio_contribution": 2.953...,
    "coverage_mv_pct": 100.0, "weighting_scheme": "BOD"
  },
  "levels": [
    {
      "level": 1, "name": "sector",
      "rows": [
        { "key": { "sector": "Technology" }, "contribution": 1.959..., "weight_avg": 61.30... },
        { "key": { "sector": "Healthcare" }, "contribution": 0.994..., "weight_avg": 38.69... }
      ]
    },
    {
      "level": 2, "name": "position_id", "parent": "sector",
      "rows": [
        { "key": { "sector": "Technology", "position_id": "Stock_A" }, ... },
        { "key": { "sector": "Healthcare", "position_id": "Stock_B" }, ... }
      ]
    }
  ],
  "meta": { ... }, "diagnostics": { ... }, "audit": { ... }
}
```