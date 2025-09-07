
# Performance Attribution Analysis

Attribution analysis decomposes a portfolio’s **active return** (portfolio return – benchmark return) into explanatory effects.  
It answers: *Why did the portfolio outperform or underperform its benchmark?*

---

## Inputs

- **portfolio_data** – Portfolio daily or period returns.
- **benchmark_data** – Benchmark weights and returns:
  - `group_id` – e.g., sector, asset class, region.
  - `benchmark_weight`
  - `benchmark_return`
- **positions_data** – Portfolio positions with mapping to benchmark groups.
- **model** – Attribution model:
  - `BRINSON_FACHLER` – Allocation, Selection, Interaction.
  - `BRINSON_HOOD_BEEBOWER` – Allocation, Selection.
- **linking_method** – For multi-period:
  - `MENCHERO` – Geometric linking of effects.
  - `ARITHMETIC` – Simple sum (not recommended).
- **hierarchy** – Optional grouping dimension (sector → industry → security).
- **emit** – Controls additional outputs (timeseries, by group, by effect).

---

## Outputs

- **active_return** – Portfolio return – benchmark return.
- **effects** – Dictionary of attribution effects:
  - `allocation`
  - `selection`
  - `interaction` (if model includes it)
- **by_group** – Effects broken down per group (sector, asset class, etc.).
- **multi_period_linked_effects** – Attribution over full evaluation window using Menchero linking.
- **meta / diagnostics / audit**

---

## Methodology

### 1. Active Return
\[
ActiveReturn = R_{Portfolio} - R_{Benchmark}
\]

### 2. Single-Period Effects

**Allocation Effect**  
\[
Allocation_g = (W_{p,g} - W_{b,g}) \times (R_{b,g} - R_b)
\]

**Selection Effect**  
\[
Selection_g = W_{b,g} \times (R_{p,g} - R_{b,g})
\]

**Interaction Effect** (Brinson-Fachler only)  
\[
Interaction_g = (W_{p,g} - W_{b,g}) \times (R_{p,g} - R_{b,g})
\]

Where:
- \( W_{p,g} \) = Portfolio weight in group g  
- \( W_{b,g} \) = Benchmark weight in group g  
- \( R_{p,g} \) = Portfolio return in group g  
- \( R_{b,g} \) = Benchmark return in group g  
- \( R_b \) = Total benchmark return

### 3. Multi-Period Linking
Using **Menchero (2004)** geometric method:
\[
LinkedEffect = \prod_{t=1}^{n} (1 + Effect_t) - 1
\]

This ensures compounded attribution matches the compounded active return.

### 4. Reconciliation
\[
ActiveReturn = \sum_g (Allocation_g + Selection_g + Interaction_g)
\]

Residuals are tracked and reported in the audit.

---

## Features

- Supports both Brinson-Hood-Beebower (BHB) and Brinson-Fachler (BF) models.
- Menchero geometric linking for multi-period attribution.
- Multi-level grouping (sector → industry → security).
- Reconciliation checks included in audit.
- Configurable outputs for CA dashboards or reports.

---

## Example

### Request
```json
{
  "portfolio_number": "ATTRIB_EXAMPLE_01",
  "model": "BRINSON_FACHLER",
  "linking_method": "MENCHERO",
  "portfolio_data": {
    "report_start_date": "2025-01-01",
    "report_end_date": "2025-01-31",
    "period_type": "MTD",
    "metric_basis": "NET",
    "daily_data": [
      { "perf_date": "2025-01-31", "begin_mv": 1000000, "end_mv": 1070000 }
    ]
  },
  "positions_data": [
    { "position_id": "Stock_A", "meta": { "sector": "Technology" }, "weight": 0.60, "return": 0.095 },
    { "position_id": "Stock_B", "meta": { "sector": "Healthcare" }, "weight": 0.40, "return": 0.030 }
  ],
  "benchmark_data": [
    { "group_id": "Technology", "benchmark_weight": 0.50, "benchmark_return": 0.080 },
    { "group_id": "Healthcare", "benchmark_weight": 0.50, "benchmark_return": 0.040 }
  ]
}
````

### Response (simplified)

```json
{
  "calculation_id": "uuid",
  "portfolio_number": "ATTRIB_EXAMPLE_01",
  "active_return": 0.01,
  "effects": {
    "allocation": 0.002,
    "selection": 0.006,
    "interaction": 0.002
  },
  "by_group": [
    {
      "group_id": "Technology",
      "allocation": 0.001,
      "selection": 0.004,
      "interaction": 0.001
    },
    {
      "group_id": "Healthcare",
      "allocation": 0.001,
      "selection": 0.002,
      "interaction": 0.001
    }
  ],
  "multi_period_linked_effects": {
    "allocation": 0.002,
    "selection": 0.006,
    "interaction": 0.002
  },
  "meta": { "...": "..." },
  "diagnostics": { "...": "..." },
  "audit": { "residual": 0.0 }
}
```

````
