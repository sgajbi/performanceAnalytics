# RFC 015: TWR Enhancements

**Status:** Final (For Approval)  
**Owner:** Senior Architect  
**Reviewers:** Perf Engine, Risk, Platform  
**Target Release:** v0.4.x  
**Related:** RFC-014 (Cross-Cutting Consistency & Diagnostics Framework)

## 1\. Executive Summary

This document specifies a set of targeted enhancements for the `/performance/twr` endpoint. Building upon the consistent foundation established in RFC 014, this initiative introduces critical, client-facing features: **optional return annualization**, an **explicit cumulative return series**, improved response field clarity with **backward compatibility**, and transparent reporting of **engine reset events**. These changes directly address common user requests for more insightful and flexible TWR analysis without altering the core vectorized calculation engine.

## 2\. Current State Analysis

The TWR endpoint is robust and performant. However, its output is limited and requires client-side post-processing for common analytical tasks.

  * **No Annualization:** The API does not provide a native way to annualize period returns, forcing clients to implement this logic themselves, which can lead to inconsistencies.
  * **Implicit Cumulative Return:** The final cumulative return is available, but there is no easy way to see a running cumulative return alongside each period in a monthly or quarterly breakdown.
  * **Unclear Field Naming:** The primary field for daily returns, `"Final Cumulative ROR %"`, is confusing as it represents the single-day return in that context, not a cumulative figure.
  * **Opaque Engine Behavior:** The core engine can trigger performance resets (NCTRL flags) under specific conditions. These events are critical for understanding performance but are currently invisible to the API user.

## 3\. Proposed Enhancements & Methodology

### 3.1 Optional Annualization

The `annualization` block, introduced in the RFC 014 request envelope, will be made fully functional for the TWR endpoint.

  * **Trigger:** When a request is sent with `"annualization": {"enabled": true}`.
  * **Logic:** The `engine/breakdown.py` module will calculate the non-annualized period return first. It will then call the `core.annualize.annualize_return` helper function, passing the period return, number of days in the period, and the basis details from the request.
  * **Output:** The `PerformanceSummary` model will include a new optional field, `annualized_return_pct`, which will be populated in the response.

### 3.2 Cumulative Return Series

The `output` block in the request envelope will be used to control the inclusion of a running cumulative return.

  * **Trigger:** When a request is sent with `"output": {"include_cumulative": true}`.
  * **Logic:** The `engine/breakdown.py` module will use the `final_cum_ror` column from the last day of each period (monthly, quarterly, etc.) to populate the cumulative value.
  * **Output:** The `PerformanceSummary` model will include a new optional field, `cumulative_return_pct_to_date`.

### 3.3 Response Field Rename & Backward Compatibility

To improve clarity, the primary return field will be renamed.

  * [cite\_start]**Change:** The field representing the return for a given period will be `period_return_pct`[cite: 1392]. In the context of a daily breakdown, this replaces the confusing `"Final Cumulative ROR %"`.
  * **Compatibility:** To avoid breaking existing clients, a compatibility flag will be used. [cite\_start]When a request includes `"flags": {"compat_legacy_names": true}`, the adapter will ensure the old field name (`"Final Cumulative ROR %"`) is used in the JSON response for daily breakdowns[cite: 1417]. The new name is the default.

### 3.4 Reset Event Reporting

The engine's internal reset events will be surfaced to the client.

  * **Trigger:** When a request is sent with `"reset_policy": {"emit": true}`.
  * **Logic:** The `engine/compute.py` module will be enhanced to collect the date and reason (NCTRL flags) for any performance reset it triggers. This list of events will be returned as part of the diagnostics dictionary.
  * [cite\_start]**Output:** The `PerformanceResponse` will include a new optional field, `reset_events: List[ResetEvent]`, which will be populated by the API endpoint if requested[cite: 1393].

## 4\. API Contract Changes

### 4.1 `PerformanceRequest` Additions

```jsonc
{
  // ... existing fields ...
  "fee_effect": {"enabled": false}, // For future use
  "reset_policy": {"emit": false} // Set to true to receive reset_events
}
```

### 4.2 `PerformanceResponse` Additions

```jsonc
{
  // ... existing breakdowns ...
  "reset_events": [
    {
      "date": "2025-01-02",
      "reason": "NCTRL_1", // Engine-specific reset code
      "impacted_rows": 1
    }
  ],
  // ... shared footer ...
}
```

## 5\. Testing Strategy

  * **Unit Tests:** New tests will be added to `tests/unit/engine/test_breakdown.py` to validate the correctness of the annualization and cumulative return calculations under various conditions.
  * **Integration Tests:** New tests will be added to `tests/integration/test_performance_api.py` to verify the end-to-end behavior of each new feature flag:
      * A test sending `annualization.enabled: true` and asserting the `annualized_return_pct` is correctly calculated.
      * A test sending `output.include_cumulative: true` and asserting the `cumulative_return_pct_to_date` is present and correct.
      * A test using a scenario that triggers an engine reset, sent with `reset_policy.emit: true`, asserting the `reset_events` array is correctly populated.
      * A test sending `flags.compat_legacy_names: true` and asserting the old field name is present in the daily breakdown response.

## 6\. Acceptance Criteria

The implementation of this RFC will be considered complete when:

1.  All four enhancements (Annualization, Cumulative Return, Field Rename, Reset Events) are fully implemented for the `/performance/twr` endpoint.
2.  All new and existing unit and integration tests pass.
3.  The `compat_legacy_names` flag is proven to maintain backward compatibility for the daily breakdown response structure.
4.  The `README.md` and `docs/guides/api_reference.md` are updated to document the new request and response fields for the TWR endpoint.
5.  This RFC is formally approved before the corresponding feature branch is merged.