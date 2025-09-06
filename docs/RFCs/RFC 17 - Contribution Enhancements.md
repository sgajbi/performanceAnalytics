# RFC 17: Contribution Enhancements

**Status:** Final (For Approval)  
**Owner:** Senior Architect  
**Reviewers:** Perf Engine, Risk, Platform  
**Target Release:** v0.4.x  
**Related:** RFC-014 (Cross-Cutting Consistency & Diagnostics Framework), `/performance/contribution`

## 1\. Executive Summary

This document specifies enhancements for the `/performance/contribution` endpoint. [cite\_start]While the current engine correctly calculates multi-period contribution using the Carino smoothing algorithm[cite: 636], it lacks flexibility. This RFC introduces **configurable weighting schemes**, **explicit control over smoothing**, and **richer time-series outputs**. These features will allow users to perform more nuanced analysis, such as viewing un-smoothed daily contributions or using different standard methodologies for calculating position weights. This work aligns the endpoint with the shared API envelope from RFC 14 and increases its analytical power.

## 2\. Current State Analysis

The contribution endpoint is functionally correct but rigid.

  * **Hardcoded Logic:** The engine is hardcoded to use a single weighting scheme (based on beginning-of-day capital) and always applies Carino smoothing. There is no way for a client to request a simple arithmetic contribution sum for reconciliation or alternative analysis.
  * **Summary-Only Output:** The API returns only the final, total contribution for each position over the entire period. It does not provide a day-by-day breakdown of how that contribution was accumulated, which is essential for detailed performance analysis.
  * **Inconsistent API:** The endpoint has not yet been fully updated to use the shared response footer from RFC 14.

## 3\. Proposed Enhancements & Methodology

### 3.1 Configurable Weighting Schemes

A new `weighting_scheme` parameter in the request will allow users to select how a position's daily weight is calculated.

  * **Trigger:** The `weighting_scheme` field in the `ContributionRequest`.
  * **Options:**
      * `"BOD"` (Default): Beginning of Day Market Value + BOD Cashflow. This is the current behavior.
      * `"AVG_CAPITAL"`: An alternative standard method will be added.
  * **Logic:** The `_calculate_single_period_weights` function in `engine/contribution.py` will be refactored to implement a strategy pattern based on this input.

### 3.2 Explicit Smoothing Control

A new `smoothing` object will allow users to enable or disable the Carino algorithm.

  * **Trigger:** The `smoothing.method` field in the `ContributionRequest`.
  * **Options:**
      * [cite\_start]`"CARINO"` (Default): Applies the Carino smoothing algorithm as is currently done[cite: 636].
      * `"NONE"`: Skips the smoothing and adjustment steps, resulting in a simple arithmetic sum of daily contributions (`Weight * Return`). This is useful for simple validation and analysis that does not require perfect reconciliation for compounding.
  * **Logic:** The main loop in `engine.contribution.calculate_position_contribution` will conditionally apply the Carino adjustment factor.

### 3.3 Richer Time-Series Outputs

A new `emit` block in the request will enable the return of detailed daily data.

  * **Trigger:** The `emit.timeseries` field in the `ContributionRequest`.
  * **Logic:** When `true`, the engine will not only sum the daily contributions but also collect them into a series.
  * **Output:** The `ContributionResponse` will include a new optional `timeseries` field, containing a list of daily total portfolio contributions, and an optional `by_position` field with a breakdown for each position.

## 4\. API Contract Changes

### 4.1 `ContributionRequest` Additions

```jsonc
{
  // ... existing fields ...
  "weighting_scheme": "BOD", // "BOD" | "AVG_CAPITAL"
  "smoothing": { "method": "CARINO" }, // "CARINO" | "NONE"
  "emit": {
    "timeseries": true,
    "by_position_timeseries": true,
    "residual_per_position": true
  }
}
```

### 4.2 `ContributionResponse` Additions

```jsonc
{
  // ... existing fields ...
  "timeseries": [
    { "date": "2025-02-28", "total_contribution": 0.0019 }
  ],
  "by_position_timeseries": [
    {
      "position_id": "Stock_A",
      "series": [ { "date": "2025-02-28", "contribution": 0.0015 } ]
    }
  ],
  // ... shared footer from RFC 14 ...
}
```

## 5\. Testing Strategy

  * **Unit Tests:** New unit tests will be added to `tests/unit/engine/test_contribution.py` to validate the `"NONE"` smoothing method and any new weighting schemes.
  * **Integration Tests:** New tests will be added to `tests/integration/test_contribution_api.py` that enable the `emit` flags and assert that the `timeseries` and `by_position_timeseries` fields are present and contain correctly structured data.

## 6\. Acceptance Criteria

1.  The `/performance/contribution` endpoint is enhanced with configurable `weighting_scheme` and `smoothing` methods.
2.  The endpoint can optionally return daily time-series breakdowns of contribution when requested.
3.  The endpoint is fully integrated with the RFC 14 shared response envelope.
4.  All new and existing unit and integration tests for the contribution feature are passing.
5.  Documentation in `docs/guides/api_reference.md` is updated to reflect the new capabilities of the contribution endpoint.
6.  This RFC is formally approved before implementation begins.