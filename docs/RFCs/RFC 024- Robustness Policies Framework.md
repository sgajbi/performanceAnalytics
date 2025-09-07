# RFC 024: Robustness Policies Framework (Final)

**Status:** Final (For Approval)
**Owner:** Senior Architect
**Reviewers:** Perf Engine, Platform, Support, Compliance
**Related:** All core analytics endpoints and RFC-025 (Reproducibility)

## 1\. Executive Summary

This document specifies the final design for a new, uniform **Robustness Policies Framework**. Production data is imperfect; it contains outliers, gaps, and edge cases like full liquidations that lead to zero-denominators. This RFC moves the platform from implicit, hardcoded handling of these issues to an explicit, configurable, and fully auditable framework.

A new `data_policy` object will be added to the shared request envelope, giving users granular control over how the engine treats **outliers**, **data gaps**, **zero-denominators**, and **same-day cash flow timing**. All actions taken by the policy engine will be reported in the `diagnostics` block of the response, ensuring complete transparency.

Implementing this framework is a critical step in maturing the platform. It makes all existing and future analytics more resilient, predictable, and defensible under audit, directly reinforcing the principles of correctness and reliability that are core to our service.

## 2\. Goals & Non-Goals

### Goals

  * Introduce a single, consistent `data_policy` request object available on all major analytics endpoints.
  * Provide a deterministic, ordered pipeline for applying these data-cleaning and interpretation policies.
  * Ensure all policy actions are counted and sampled in the response `diagnostics` block for transparency.
  * Establish safe, minimally biased default policies.

### Non-Goals

  * This framework is not a substitute for upstream data quality assurance.
  * It will not attempt to infer or handle corporate actions.

## 3\. Methodology

The framework will apply a series of configurable policies in a strict, deterministic order before the core analytics are calculated.

### 3.1. Order of Operations

1.  **Canonicalize Inputs**: Align all time series and apply calendar/period masks.
2.  **Apply Gap Policies**: Fill or drop missing data points for prices, holdings, FX rates, and benchmark constituents.
3.  **Apply Outlier Policies**: Detect and treat outlier returns or weights using the configured method (e.g., cap, flag, or drop).
4.  **Apply Flow Timing Policies**: Interpret same-day cash flows (e.g., as Beginning-of-Day or End-of-Day), which directly impacts the calculation of TWR denominators and contribution weights.
5.  **Apply Zero-Denominator Policies**: Handle any days where the TWR denominator is at or near zero after applying flow timing.
6.  **Run Core Analytics**: Proceed with the TWR, Contribution, or Attribution calculations using the cleaned and prepared data.

### 3.2. Policy Details

  * **Outlier Handling**: The engine will support several statistical methods for identifying outliers in returns or weights, including **Median Absolute Deviation (MAD)** and **Winsorization**. The configured `action` determines whether an outlier is capped at a threshold (`CAP`), flagged for review (`FLAG`), or removed (`DROP`).
  * **Gap Filling**: Missing data points can be handled by `filling forward` the last known value, `linear interpolation` (for prices), or `dropping` the observation, subject to a `max_gap_days` limit.
  * **Zero-Denominator Handling**: By default (`SKIP_DAY`), any day with a zero or near-zero denominator will be treated like a No-Investment-Period (NIP) day, with a zero return.
  * **Flow Timing**: The default (`BOD`) treats all cash flows as occurring at the beginning of the day, making them available for investment. This directly impacts the TWR denominator ($BMV + BOD\_{CF}$) and contribution weights.

## 4\. API Design

### 4.1. Request Additions (`data_policy` block)

The following block will be added to the shared request envelope for all relevant endpoints.

```json
{
  "data_policy": {
    "outliers": {
      "enabled": true,
      "scope": ["SECURITY_RETURNS"],
      "method": "MAD",
      "params": { "mad_k": 5.0, "window": 63 },
      "action": "CAP"
    },
    "gaps": {
      "prices": { "strategy": "LINEAR", "max_gap_days": 5 },
      "holdings": { "strategy": "FILL_FWD", "max_gap_days": 10 },
      "on_exceed": "ERROR"
    },
    "zero_denominator": {
      "threshold": 1e-8,
      "policy": "SKIP_DAY"
    },
    "same_day_flow": {
      "timing": "BOD"
    }
  }
}
```

### 4.2. Response Additions (`diagnostics` block)

The `diagnostics` block in all responses will be extended to include a summary of policy actions.

```json
{
  "diagnostics": {
    "policy": {
      "outliers": { "capped_rows": 5, "dropped_rows": 0 },
      "gaps": { "filled_prices": 12, "filled_holdings": 2 },
      "zero_denominator": { "skipped_days": 1 }
    },
    "samples": {
      "outliers": [ { "date": "2025-03-12", "instrumentId": "XYZ", "raw_return": 1.5, "adjusted_return": 0.15 } ]
    }
  }
}
```

### 4.3. HTTP Semantics & Errors

  * **200 OK**: Successful computation.
  * **400 Bad Request**: Invalid policy configuration.
  * **422 Unprocessable Entity**: Request is valid, but a policy action fails (e.g., `gaps.on_exceed: "ERROR"` is triggered).

## 5\. Architecture & Implementation Plan

1.  **Create new module**:
      * `engine/policies.py`: To house the logic for each robustness policy (outlier detection, gap filling, etc.).
2.  **Integrate into Orchestrator**:
      * Modify `engine/compute.py` and other engine entry points to execute the policy pipeline in the correct order, using the `data_policy` from the request.
3.  **Update Diagnostics**:
      * Enhance the diagnostics collector to track and return the counts and samples of all policy actions.
4.  **Phased Rollout**:
      * **Phase 1**: Implement the zero-denominator and flow timing policies for the TWR engine.
      * **Phase 2**: Implement the gap-filling policies.
      * **Phase 3**: Implement the outlier detection framework.

## 6\. Testing & Validation Strategy

  * **Unit Tests**: The new `engine/policies.py` module must achieve **100% test coverage**. This will include tests for each outlier detection method, gap-filling strategy, and zero-denominator policy.
  * **Integration Tests**: API-level tests will be created to verify that a request with a specific `data_policy` results in the expected numerical output and the correct diagnostic report. For example, a test will inject an outlier and assert that the final return is capped and the `outliers.capped_rows` count is 1.
  * **Property-Based Testing**: Use property-based tests to ensure that the policy application is order-invariant where appropriate and that policies handle a wide range of random data inputs without crashing.
  * **Overall Coverage**: The overall project test coverage must remain at or above **95%**.

## 7\. Acceptance Criteria

The implementation of this RFC is complete when:

1.  This RFC is formally approved by all stakeholders.
2.  The `data_policy` block is added to the shared request envelope and is fully functional for all core analytics endpoints.
3.  The response `diagnostics` block is extended to transparently report all policy actions.
4.  The testing and validation strategy is fully implemented, all tests are passing, and the required coverage targets (**100% for engine**, **≥95% for project**) are met.
5.  All default policies are set to safe, minimally biased options that ensure backward compatibility with existing behavior.
6.  New documentation is added to `docs/guides/` and `docs/technical/` explaining the robustness framework and how to configure it.