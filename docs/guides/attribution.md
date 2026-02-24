# Performance Attribution Methodology

Performance attribution analysis decomposes a portfolio's **active return**—the difference between the portfolio's and the benchmark's return—into its core drivers. It systematically answers the question: *Why did the portfolio's performance differ from the benchmark?*

The engine evaluates two primary skills of a portfolio manager:

-   **Allocation**: The ability to overweight outperforming groups (e.g., sectors, asset classes) and underweight underperforming ones.
-   **Selection**: The ability to pick outperforming securities within those groups.

---

## Inputs

The Attribution endpoint (`POST /performance/attribution`) requires time series data for the portfolio and the benchmark.

-   **`mode`**: The format of the input data:
    -   `by_instrument`: The API is provided with instrument-level data for the portfolio, which it first aggregates to the group level.
    -   `by_group`: The API is provided with pre-aggregated, group-level data.
-   **`group_by`**: An ordered list of dimensions for the analysis (e.g., `["assetClass", "sector"]`).
-   **`portfolio_data` / `instruments_data`**: The portfolio's time series data.
-   **`benchmark_groups_data`**: The benchmark's time series data, including the weight and return for each group.
-   **`model`**: The Brinson-style model to use: `BF` (Brinson-Fachler, default) or `BHB` (Brinson-Hood-Beebower).
-   **`linking`**: The method for linking single-period effects over time. `carino` (geometric) is the default.

---

## Outputs

The response provides a detailed breakdown of the attribution effects for each level of the analysis.

-   **`levels`**: A list of results, one for each dimension in the `group_by` request. Each level contains:
    -   `groups`: A list of the attribution effects for each group (e.g., "Tech", "Health").
    -   `totals`: The summed effects for the entire level.
-   **`reconciliation`**: A block that explicitly validates the calculation, showing that the `sum_of_effects` equals the `total_active_return`.
-   **Shared Envelope**: Includes `meta`, `diagnostics`, and `audit` blocks.

---

## Methodology

### 1. Single-Period Attribution Models

For any single period (e.g., one month), the engine calculates three effects for each group *i*.

#### Brinson-Fachler (BF) Model (Default)

This is the industry-standard model.

-   **Allocation ($A_i$)**: Measures the impact of weighting decisions.
    $$ A_i = (w_{pi} - w_{bi}) \times (R_{bi} - R_b) $$
-   **Selection ($S_i$)**: Measures the impact of security selection within the group.
    $$ S_i = w_{bi} \times (R_{pi} - R_{bi}) $$
-   **Interaction ($I_i$)**: A hybrid term capturing the combined impact.
    $$ I_i = (w_{pi} - w_{bi}) \times (R_{pi} - R_{bi}) $$

Where:
-   $w_{pi}, w_{bi}$: Portfolio and Benchmark weight in group *i*.
-   $R_{pi}, R_{bi}$: Portfolio and Benchmark return of group *i*.
-   $R_b$: The total return of the benchmark for the period.

#### Brinson-Hood-Beebower (BHB) Model

This model uses a slightly different definition for the allocation effect.

-   **Allocation ($A_i$)**:
    $$ A_i = (w_{pi} - w_{bi}) \times R_{bi} $$
-   **Selection ($S_i$)**:
    $$ S_i = w_{pi} \times (R_{pi} - R_{bi}) $$

### 2. Multi-Period Linking

Simply adding single-period attribution effects over a long horizon is mathematically incorrect because it ignores **compounding**. An allocation gain from January is reinvested and also generates returns in February.

To solve this, the engine uses a **top-down geometric linking** method. It ensures the sum of the linked A, S, and I effects over the entire horizon perfectly reconciles to the total geometric active return ($TWR_{Portfolio} - TWR_{Benchmark}$). It works as follows:

1.  Calculate the true geometric active return over the entire period.
2.  Calculate the arithmetic active return (the simple sum of daily active returns).
3.  Compute a `scaling_factor = geometric_active_return / arithmetic_active_return`.
4.  Multiply each single-period attribution effect by this constant `scaling_factor` before summing them up.

### 3. Hierarchical & `by_instrument` Analysis

-   **Hierarchical**: When multiple dimensions are provided in `group_by`, the engine performs a **bottom-up aggregation**. Effects are calculated at the most granular level and then the dollar effects are summed up to the parent levels. This ensures perfect reconciliation across the hierarchy.
-   **`by_instrument` Mode**: When instrument-level data is provided, the engine first uses the core TWR engine to calculate daily returns for each instrument. It then aggregates these returns and weights up to the group level before performing the attribution calculations.
    -   Group Weight ($w_{pi}$): Sum of the weights of all instruments within the group.
    -   Group Return ($R_{pi}$): The weighted average of the returns of all instruments within the group.

---

## Features

-   **Multiple Models**: Supports both Brinson-Fachler and Brinson-Hood-Beebower models.
-   **Geometric Linking**: Correctly accounts for compounding over multiple periods to ensure perfect reconciliation.
-   **Multi-Level Hierarchy**: Decomposes active return across multiple dimensions in a single call.
-   **Flexible Inputs**: Can run attribution from either pre-aggregated group data or raw instrument-level data.

---

## API Example

### Request

```json
{
  "portfolio_id": "ATTRIB_EXAMPLE_01",
  "mode": "by_instrument",
  "group_by": [ "sector" ],
  "linking": "none",
  "frequency": "daily",
  "portfolio_data": {
    "report_start_date": "2025-01-01",
    "report_end_date": "2025-01-01",
    "metric_basis": "NET", "period_type": "YTD",
    "daily_data": [ { "day": 1, "perf_date": "2025-01-01", "begin_mv": 1000, "end_mv": 1018.5 } ]
  },
  "instruments_data": [
    {
      "instrument_id": "AAPL", "meta": { "sector": "Tech" },
      "daily_data": [ { "day": 1, "perf_date": "2025-01-01", "begin_mv": 600, "end_mv": 612 } ]
    },
    {
      "instrument_id": "JNJ", "meta": { "sector": "Health" },
      "daily_data": [ { "day": 1, "perf_date": "2025-01-01", "begin_mv": 400, "end_mv": 406.5 } ]
    }
  ],
  "benchmark_groups_data": [
    {
      "key": { "sector": "Tech" },
      "observations": [ { "date": "2025-01-01", "return": 0.015, "weight_bop": 0.5 } ]
    },
    {
      "key": { "sector": "Health" },
      "observations": [ { "date": "2025-01-01", "return": 0.02, "weight_bop": 0.5 } ]
    }
  ]
}
```

### Response (Excerpt)

```json
{
    "calculation_id": "uuid-goes-here",
    "portfolio_id": "ATTRIB_EXAMPLE_01",
    "model": "BF",
    "linking": "none",
    "levels": [
        {
            "dimension": "sector",
            "groups": [
                { "key": { "sector": "Health" }, "allocation": -0.025, "selection": -0.1875, "interaction": -0.025, "total_effect": -0.2375 },
                { "key": { "sector": "Tech" }, "allocation": 0.025, "selection": 0.25, "interaction": 0.05, "total_effect": 0.325 }
            ],
            "totals": { "allocation": 0.0, "selection": 0.0625, "interaction": 0.025, "total_effect": 0.0875 }
        }
    ],
    "reconciliation": { "total_active_return": 0.1, "sum_of_effects": 0.0875, "residual": 0.0125 },
    "meta": { ... }, "diagnostics": { ... }, "audit": { ... }
}
```
