
# RFC 17: Contribution Enhancements

**Status:** Final (For Approval)  
**Owner:** Senior Architect  
**Reviewers:** Perf Engine, Risk, Platform  
**Target Release:** v0.4.x  
**Related:** RFC-014 (Cross-Cutting Consistency & Diagnostics Framework), `/performance/contribution`

-----

## 1\. Executive Summary

This document specifies enhancements for the `/performance/contribution` endpoint. While the current engine correctly calculates multi-period contribution using the Carino smoothing algorithm, it lacks flexibility and is not aligned with the latest API standards. This RFC introduces **configurable weighting schemes**, **explicit control over smoothing**, and **richer time-series outputs**. These features will allow users to perform more nuanced analysis, such as viewing un-smoothed daily contributions for reconciliation or using alternative standard methodologies for calculating position weights.

Critically, this work fully aligns the endpoint with the **shared request envelope and response footer** from RFC 14, ensuring a consistent and auditable client experience.

-----

## 2\. Current State Analysis

The contribution endpoint is functionally correct but rigid and outdated.

  * **Hardcoded Logic:** The engine is hardcoded to use a single weighting scheme (based on beginning-of-day capital) and always applies Carino smoothing. There is no way for a client to request a simple arithmetic contribution sum for reconciliation or alternative analysis.
  * **Summary-Only Output:** The API returns only the final, total contribution for each position over the entire period. It does not provide a day-by-day breakdown of how that contribution accumulated, which is essential for detailed performance analysis.
  * **Inconsistent API:** The endpoint has not been updated to use the shared request parameters or the shared response footer (`meta`, `diagnostics`, `audit`) defined in RFC 14.

-----

## 3\. Proposed Enhancements & Methodology

### 3.1 Configurable Weighting Schemes

A new `weighting_scheme` parameter in the request will allow users to select how a position's daily weight is calculated.

  * **Trigger:** The `weighting_scheme` field in the `ContributionRequest`.
  * **Options:**
      * `"BOD"` (Default): Beginning of Day Market Value + BOD Cashflow. This preserves the current behavior.
      * `"AVG_CAPITAL"`: An alternative standard method will be added to provide more analytical flexibility.
  * **Logic:** The `_calculate_single_period_weights` function in `engine/contribution.py` will be refactored to implement a strategy pattern based on this input.

### 3.2 Explicit Smoothing Control

A new `smoothing` object will allow users to enable or disable the Carino algorithm for linking multi-period contributions.

  * **Trigger:** The `smoothing.method` field in the `ContributionRequest`.
  * **Options:**
      * `"CARINO"` (Default): Applies the Carino smoothing algorithm as is currently done to ensure the sum of contributions geometrically links to the total portfolio TWR.
      * `"NONE"`: Skips the smoothing and adjustment steps. The total contribution will be a simple arithmetic sum of the daily `Weight * Return` values. This is useful for simple validation and analysis that does not require perfect reconciliation with a compounding portfolio return.
  * **Logic:** The main loop in `engine.contribution.calculate_position_contribution` will conditionally apply the Carino adjustment factor based on the request setting.

### 3.3 Richer Time-Series Outputs

A new `emit` block in the request will enable the return of detailed daily data for deeper analysis.

  * **Trigger:** The `emit` block in the `ContributionRequest`.
  * **Logic:** When flags within the `emit` block are set to `true`, the engine will not only sum the daily contributions but also collect them into a time series.
  * **Output:** The `ContributionResponse` will include new optional fields:
      * `timeseries`: A list of daily total portfolio contributions.
      * `by_position_timeseries`: A breakdown of daily contributions for each individual position.

-----

## 4\. API Contract Changes

### 4.1 `ContributionRequest` Additions

The request model will be updated to include the new configuration options and will inherit the shared envelope from RFC 14.

```jsonc
{
  "calculation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "portfolio_id": "CONTRIB_ENHANCED_01",
  "portfolio_data": { /* ... */ },
  "positions_data": [ /* ... */ ],

  // --- RFC 17 Enhancements ---
  "weighting_scheme": "BOD", // "BOD" | "AVG_CAPITAL"
  "smoothing": {
    "method": "CARINO" // "CARINO" | "NONE"
  },
  "emit": {
    "timeseries": true,
    "by_position_timeseries": true
  },

  // --- RFC 14 Shared Envelope Fields ---
  "as_of": "2025-02-28",
  "currency": "USD",
  "precision_mode": "FLOAT64", // "FLOAT64" | "DECIMAL_STRICT"
  "annualization": { "enabled": false }, // Not used by contribution, but part of envelope
  "periods": { "type": "EXPLICIT", "explicit": {"start": "2025-02-01", "end": "2025-02-28"} }
}
```

### 4.2 `ContributionResponse` Additions

The response model will be updated to include the optional time-series fields and the mandatory shared footer from RFC 14.

```jsonc
{
  "calculation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "portfolio_id": "CONTRIB_ENHANCED_01",
  "report_start_date": "2025-02-01",
  "report_end_date": "2025-02-28",
  "total_portfolio_return": 1.25,
  "total_contribution": 1.25,
  "position_contributions": [ /* ... */ ],

  // --- RFC 17 Enhancements ---
  "timeseries": [
    { "date": "2025-02-28", "total_contribution": 0.0019 }
  ],
  "by_position_timeseries": [
    {
      "position_id": "Stock_A",
      "series": [ { "date": "2025-02-28", "contribution": 0.0015 } ]
    }
  ],

  // --- RFC 14 Shared Response Footer ---
  "meta": {
    "engine_version": "0.4.0",
    /* ... other meta fields ... */
  },
  "diagnostics": {
    "nip_days": 0,
    "reset_days": 0,
    /* ... other diagnostic fields ... */
  },
  "audit": {
    "counts": { "input_positions": 5, "days_calculated": 28 }
  }
}
```

-----

## 5\. Testing Strategy

  * **Unit Tests:** New unit tests will be added to `tests/unit/engine/test_contribution.py` to:
      * Validate the output of the `"AVG_CAPITAL"` weighting scheme against a known-good calculation.
      * Assert that when `smoothing.method` is `"NONE"`, the total contribution for each position is the simple arithmetic sum of its daily `Weight * Return` values.
  * **Integration Tests:** New tests will be added to `tests/integration/test_contribution_api.py` to:
      * Send a request with `emit.timeseries` and `emit.by_position_timeseries` set to `true` and assert that the corresponding fields are present and contain correctly structured data with the expected number of data points.
      * Send a request with a shared envelope parameter (e.g., a specific `periods` block) and assert that the calculation correctly respects the date range and that the `meta` block in the response reflects the request.

-----

## 6\. Acceptance Criteria

1.  The `/performance/contribution` endpoint is enhanced with configurable `weighting_scheme` and `smoothing` methods as specified.
2.  The endpoint can optionally return daily time-series breakdowns of contribution for the total portfolio and for each position when requested via the `emit` block.
3.  The endpoint is **fully integrated** with the RFC 14 shared request envelope and response footer, correctly processing shared parameters and always returning the `meta`, `diagnostics`, and `audit` blocks.
4.  All new and existing unit and integration tests for the contribution feature are passing.
5.  Documentation in `docs/guides/api_reference.md` is updated to reflect the new capabilities, request parameters, and response structure of the contribution endpoint.
6.  This RFC is formally approved before implementation begins.
