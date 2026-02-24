Here is the final, implementable version of RFC 007, refined for approval.

-----

# RFC 007: Allocation Drift Monitoring API (Final)

**Status:** Final (For Approval)
**Owner:** Senior Architect
**Reviewers:** Perf Engine, Risk, Platform
**Related:** RFC-009 (Exposure Breakdown), RFC-013 (Active Analytics)

## 1\. Executive Summary

This document specifies the final design for a new, highly practical **Allocation Drift Monitoring API** to be implemented at `/portfolio/allocationDrift`. While other services analyze past performance or current exposures, this API provides an actionable workflow tool that addresses one of the most fundamental tasks in portfolio management: ensuring a portfolio remains aligned with its intended strategy.

The engine will empower portfolio managers to **measure drift** between a portfolio's current weights and its strategic targets, **identify tolerance band breaches**, and **simulate minimal-turnover rebalancing trades** required to restore alignment. The API is designed for maximum flexibility, supporting multi-level hierarchies, various target types (fixed, benchmark-based, or ranges), and practical rebalancing constraints like minimum trade sizes and cash buffer management.

This feature builds directly on the foundation of the Exposure Breakdown API (RFC 009), leveraging its ability to calculate current weights by group. The implementation will be stateless, deterministic, and adhere to our established architectural patterns and rigorous testing standards.

## 2\. Goals & Non-Goals

### Goals

  * Calculate portfolio drift against target allocations across multiple hierarchy levels.
  * Support flexible target definitions, including fixed weights, benchmark weights, or target ranges.
  * Identify and quantify breaches of user-defined tolerance bands.
  * Provide actionable rebalancing recommendations (deltas) to bring the portfolio back into alignment.
  * Support both snapshot (as-of) and timeseries analysis to monitor drift over time.

### Non-Goals

  * This API will not perform trade execution or tax optimization.
  * It is a stateless, computational API and will not source holdings or targets from external systems.
  * Transaction cost modeling is limited to a simple bps-based estimate.

## 3\. Methodology

### 3.1. Weight and Drift Calculation

For each group *i* at a given hierarchy level, the engine first calculates its current weight ($w\_i$) by summing the market values of its constituent instruments and dividing by the total portfolio market value. It then compares this to the target weight ($\\tau\_i$) provided in the request.

  * **Drift**: The primary output is the signed drift, calculated as: $d\_i = w\_i - \\tau\_i$.

### 3.2. Breach Detection

The engine uses tolerance bands to determine if a drift is significant enough to warrant action. A breach occurs if the current weight falls outside the band defined by the target and the tolerance.

  * **Breach Condition**: A breach exists if $w\_i \< (\\tau\_i - L\_i)$ or $w\_i \> (\\tau\_i + U\_i)$, where $L\_i$ and $U\_i$ are the lower and upper tolerance bands.

### 3.3. Rebalancing Simulation

If rebalancing is enabled, the engine simulates trades to resolve the breaches using a **Greedy Minimal-Turnover Algorithm**. The objective is to find the smallest set of trades that brings all weights back within their tolerance bands.

1.  **Identify Sources and Sinks**: The engine identifies all overweight groups that need to be sold (sources) and all underweight groups that need to be bought (sinks).
2.  **Prioritize Trades**: It prioritizes selling the most overweight groups and buying the most underweight groups.
3.  **Iterative Transfers**: The algorithm iteratively simulates transfers of capital from the top source to the top sink until one of them is back within its band.
4.  **Cash Management**: The `use_cash` policy dictates how cash is used. `buffer_first` will use the cash position to absorb sales or fund purchases before trading between other assets, minimizing turnover.
5.  **Apply Constraints**: Throughout the simulation, practical constraints like `min_trade` size and `lot_size` rounding are respected.
6.  **Output**: The final output is a set of recommended trade deltas (in both weight and currency value) for each group.

## 4\. API Design

### 4.1. Endpoint

`POST /portfolio/allocationDrift`

### 4.2. Request Schema (Pydantic)

```json
{
  "portfolio_id": "DRIFT_MONITOR_01",
  "as_of": "2025-09-07",
  "mode": "snapshot",
  "holdings": {
    "by": "instrument",
    "series": [
      {"instrumentId": "AAA", "meta": {"assetClass": "Equity"}, "observations": [{"date": "2025-09-07", "mv": 670000}]},
      {"instrumentId": "BBB", "meta": {"assetClass": "Bond"},   "observations": [{"date": "2025-09-07", "mv": 290000}]},
      {"instrumentId": "CASH", "meta": {"assetClass": "Cash"},   "observations": [{"date": "2025-09-07", "mv": 40000}]}
    ]
  },
  "groupBy": ["assetClass"],
  "target": {
    "mode": "fixed",
    "fixed": {
      "level": "assetClass",
      "weights": [
        {"key": {"assetClass": "Equity"}, "weight": 0.60},
        {"key": {"assetClass": "Bond"},   "weight": 0.35},
        {"key": {"assetClass": "Cash"},   "weight": 0.05}
      ]
    }
  },
  "tolerance": {"default": {"lower": 0.02, "upper": 0.02}},
  "rebalance": {"enabled": true, "to": "bands", "min_trade": 1000.0, "use_cash": "buffer_first"}
}
```

### 4.3. Response Schema

```json
{
  "as_of": "2025-09-07",
  "level": "assetClass",
  "totals": { "mv_total": 1000000.0, "turnover_est": 50000.0, "cost_est": 25.0 },
  "groups": [
    {
      "key": {"assetClass": "Equity"},
      "current_weight": 0.67,
      "target_weight": 0.60,
      "lower": 0.58, "upper": 0.62,
      "drift": 0.07,
      "breach": {"type": "over", "amount": 0.05},
      "delta_weight": -0.05,
      "delta_value": -50000.0,
      "notes": ["reduced to upper band"]
    },
    {
      "key": {"assetClass": "Bond"},
      "current_weight": 0.29,
      "target_weight": 0.35,
      "lower": 0.33, "upper": 0.37,
      "drift": -0.06,
      "breach": {"type": "under", "amount": 0.04},
      "delta_weight": 0.04,
      "delta_value": 40000.0,
      "notes": ["increased to lower band"]
    }
  ],
  "meta": { ... },
  "diagnostics": { ... },
  "audit": { ... }
}
```

### 4.4. HTTP Semantics & Errors

  * **200 OK**: Successful computation.
  * **400 Bad Request**: Schema validation errors (e.g., target weights do not sum to 1).
  * **422 Unprocessable Entity**: Request is valid, but data is insufficient or rebalancing is infeasible under the given constraints.
  * **413 Payload Too Large**: Request payload exceeds configured limits.

## 5\. Architecture & Implementation Plan

1.  **Create new modules**:
      * `engine/allocation.py`: To house the core logic for drift calculation and the rebalancing simulation.
      * `app/models/allocation_drift_requests.py` and `app/models/allocation_drift_responses.py`: To define the API contract.
2.  **Update endpoint router**:
      * Add the `POST /portfolio/allocationDrift` endpoint to `app/api/endpoints/portfolio.py`.
3.  **Implementation Steps**:
      * First, implement the core drift and breach calculation logic.
      * Next, implement the greedy rebalancing algorithm.
      * Finally, add support for timeseries and rolling-window modes.

## 6\. Testing & Validation Strategy

  * **Unit Tests**: The new `engine/allocation.py` module must achieve **100% test coverage**. This will include tests for weight calculation, breach detection with various bands, and detailed validation of the rebalancing algorithm's convergence and constraint handling.
  * **Integration Tests**: API-level tests will validate the end-to-end flow for snapshot and timeseries modes, ensuring all request flags correctly influence the outcome.
  * **Characterization Test**: A test will be created for a realistic multi-asset portfolio with several breached positions. The API's rebalancing deltas and turnover estimate will be validated against a reference calculation from a Jupyter notebook.
  * **Overall Coverage**: The overall project test coverage must remain at or above **95%**.

## 7\. Acceptance Criteria

The implementation of this RFC is complete when:

1.  This RFC is formally approved by all stakeholders.
2.  All new modules are created and fully integrated into the existing architecture.
3.  The `POST /portfolio/allocationDrift` endpoint is fully functional, supporting all specified modes, targets, and rebalancing controls.
4.  The testing and validation strategy is fully implemented, all tests are passing, and the required coverage targets (**100% for engine**, **≥95% for project**) are met.
5.  The characterization test passes, confirming the rebalancing simulation is numerically correct.
6.  New documentation is added to `docs/guides/` and `docs/technical/` for the Allocation Drift API, ensuring documentation remains current.
