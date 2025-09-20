# RFC 029: Unified Multi-Period Analysis Framework

**Status:** Final (For Approval)  
**Owner:** Senior Architect  
**Reviewers:** Perf Engine, Risk, Platform  
**Related:** RFC-014 (Cross-Cutting Consistency), RFC-025 (Reproducibility)

## 1\. Executive Summary

This document specifies the final design for a new, platform-wide **Unified Multi-Period Analysis Framework**. A critical limitation of our current analytics suite is its "one-period-per-request" model. Clients needing to analyze and compare performance across multiple time horizons (e.g., MTD, YTD, and 1-Year) must make separate, redundant API calls, resubmitting the same large data payloads each time. This is inefficient, costly for both client and server, and provides a poor developer experience.

This RFC addresses this limitation by introducing a new `periods` array to the shared API request envelope. This will allow clients to request a comprehensive set of standard and custom time horizons—`1D`, `1W`, `MTD`, `QTD`, `YTD`, `1Y`, `3Y`, `5Y`, `ITD`, and `EXPLICIT`—in a single, optimized API call. The engine will be enhanced to perform its core daily calculations once on the supplied data, then efficiently slice and aggregate the results for each requested period.

The response structure will be updated to a clear, dictionary-based format, mapping each requested period to its corresponding analytical result. This change is **fully backward-compatible** and will be consistently applied across all relevant endpoints (TWR, MWR, Contribution, Attribution), dramatically improving the efficiency, power, and usability of the entire analytics suite.

-----

## 2\. Problem & Motivation

The current API design, which uses a single `period_type` field, forces a sequential, inefficient workflow for any user requiring multi-period analysis. To generate a standard reporting table with MTD, QTD, YTD, and 1-Year returns, a client must:

1.  Send a `POST /performance/twr` request with `period_type: "MTD"` and the full `daily_data`.
2.  Send another request with `period_type: "QTD"` and the same `daily_data`.
3.  Send a third request with `period_type: "YTD"`, again with the same data.
4.  Send a fourth request for the 1-Year period.

This pattern is problematic for several reasons:

  - **Redundant Data Transfer:** The same (often large) `daily_data` payload is serialized, sent over the network, and deserialized multiple times.
  - **Wasted Computation:** The server performs redundant daily return calculations on the same underlying data for each request.
  - **Increased Latency:** The client must wait for four separate round trips to assemble a single report.
  - **Poor Developer Experience:** It places an unnecessary burden on the API consumer to orchestrate multiple calls and stitch the results together.

This RFC proposes a "calculate once, aggregate many" model that solves these problems, providing a more powerful and efficient analytical workflow.

-----

## 3\. Goals & Non-Goals

### Goals

  - **Standardize Period Definitions:** Establish a single, canonical set of period type enums and resolution logic to be used by all analytics engines.
  - **Support Multiple Periods per Request:** Allow clients to pass a list of desired period types (e.g., `["MTD", "YTD", "1Y"]`) in a single API call.
  - **Optimize Performance:** Refactor the core engines to process the full input data once, then perform lightweight slicing and aggregation for each requested period, eliminating redundant calculations.
  - **Provide a Clear Response Structure:** Return results in a dictionary where keys are the requested period types and values are the corresponding analytics, making the output easy to parse.
  - **Maintain Consistency:** Apply this new pattern uniformly across all relevant endpoints, including TWR, MWR, Contribution, and Attribution.
  - **Ensure Backward Compatibility:** The existing `period_type` field will continue to be supported to avoid breaking existing client integrations.

### Non-Goals

  - The API will not infer or automatically add periods; the client must explicitly request them.
  - The service will not persist data. The client remains responsible for providing a `daily_data` series that covers the longest requested period.
  - This RFC does not introduce support for custom fiscal calendars; all periods are based on standard calendar conventions.

-----

## 4\. Methodology

The core of this enhancement is a new **Period Resolver** and an adaptation of the engines to a **slice-and-aggregate** pattern.

### 4.1. Period Resolution

A new `PeriodResolver` utility will be implemented in `core/periods.py`. This utility will take the `as_of` date, `performance_start_date` (for `ITD`), and the list of requested period enums as input. Its output will be a list of `(period_name, start_date, end_date)` tuples. This expands the existing period resolution logic into a more powerful, multi-period service.

For example, given `as_of: "2025-08-31"`, `performance_start_date: "2022-01-01"`, and a request for `["MTD", "YTD", "1Y", "ITD"]`, the resolver will produce:

  - `("MTD", 2025-08-01, 2025-08-31)`
  - `("YTD", 2025-01-01, 2025-08-31)`
  - `("1Y", 2024-09-01, 2025-08-31)`
  - `("ITD", 2022-01-01, 2025-08-31)`

### 4.2. Engine Adaptation: Slice and Aggregate

The core analytics engines (`TWR`, `Contribution`, etc.) will be refactored to adopt the following workflow:

1.  **Calculate Once:** The engine will run its most computationally expensive, daily-level calculations (e.g., daily returns, daily smoothed contributions) exactly once on the full `daily_data` series provided by the client. This produces a single, comprehensive `daily_results_df`.
2.  **Slice and Aggregate:** For each `(period_name, start_date, end_date)` tuple generated by the `PeriodResolver`, the engine will:
    a.  Create an efficient slice of the `daily_results_df` where dates fall within the `[start_date, end_date]` range.
    b.  Perform the final, lightweight aggregation step on this slice (e.g., geometrically linking the daily returns for TWR, summing the daily contributions).
    c.  Store the aggregated result in a dictionary, keyed by `period_name`.

This approach maximizes computational reuse and minimizes redundant work, leading to significant performance gains for multi-period requests.

-----

## 5\. API Design

### 5.1. Request Changes

The shared request envelope defined in RFC-014 will be modified. The existing `period_type: PeriodType` field will be deprecated in documentation and replaced by a new `periods: List[PeriodTypeEnum]` field.

**New `periods` Field:**

```jsonc
// In any analytics request (TWR, MWR, Contribution, etc.)
{
  "as_of": "2025-08-31",
  "periods": ["MTD", "QTD", "YTD", "1Y", "ITD"],
  // ... other request fields ...
  "daily_data": [ /* ... data covering the full 1-year period ... */ ]
}
```

**Backward Compatibility:** If a client sends a request using the old `period_type` field, the API adapter will internally convert it to a single-element `periods` array (e.g., `"period_type": "YTD"` becomes `"periods": ["YTD"]`).

### 5.2. Response Changes

The response structure will be modified to accommodate results for multiple periods. Instead of a single result at the top level, the payload will contain a `results_by_period` object.

**New Response Structure (TWR Example):**

```jsonc
{
  "calculation_id": "a4b7e289-7e28-4b7e-8e28-7e284b7e8e28",
  "portfolio_number": "MULTI_PERIOD_01",
  "results_by_period": {
    "MTD": {
      // Standard TWR breakdown object for the MTD period
      "breakdowns": {
        "monthly": [
          {
            "period": "2025-08",
            "summary": { "period_return_pct": 1.52, /* ... */ }
          }
        ]
      }
    },
    "YTD": {
      // Standard TWR breakdown object for the YTD period
      "breakdowns": {
        "yearly": [
          {
            "period": "2025",
            "summary": { "period_return_pct": 8.75, /* ... */ }
          }
        ]
      }
    },
    "1Y": {
      // Standard TWR breakdown object for the 1-Year period
      "breakdowns": {
        "yearly": [
          {
            "period": "1Y",
            "summary": { "period_return_pct": 12.34, /* ... */ }
          }
        ]
      }
    }
  },
  // --- Shared Response Footer ---
  "meta": { /* ... */ },
  "diagnostics": { /* ... */ },
  "audit": { /* ... */ }
}
```

-----

## 6\. Architecture & Files Affected

  - **`core/envelope.py`**: Update `BaseRequest` and `BaseResponse` Pydantic models to reflect the new `periods` and `results_by_period` fields.
  - **`core/periods.py`**: Enhance with the new multi-period `PeriodResolver` utility.
  - **`engine/compute.py` (TWR)**: Refactor the main orchestrator to implement the "calculate once, slice and aggregate" pattern.
  - **`engine/contribution.py`**: Refactor to sum contributions across multiple resolved time slices.
  - **`engine/attribution.py`**: Refactor to run the attribution analysis across multiple resolved time slices.
  - **`app/api/endpoints/*.py`**: Update all relevant endpoint functions to handle the new request array and construct the new dictionary-based response.
  - **`adapters/api_adapter.py`**: Add logic to handle backward compatibility for the legacy `period_type` field.

-----

## 7\. Testing Strategy

  - **Unit Tests:**
      - The `PeriodResolver` in `core/periods.py` must achieve **100% test coverage**. This includes tests for every period enum (`1D`, `1W`, `MTD`, etc.) and edge cases, such as `as_of` dates at the beginning/end of months or years.
  - **Integration Tests:**
      - Create new integration tests for each major endpoint (TWR, Contribution, etc.) that send a single request with multiple `periods`.
      - Assert that the response contains a key in `results_by_period` for each requested period.
      - Assert that the numerical result for each period in the multi-period response is **identical** to the result from a separate, single-period API call for that same period type. This ensures correctness.
      - Add a test to verify the backward-compatibility logic by sending a request with the legacy `period_type` field and asserting a correct response.
  - **Characterization Tests:**
      - Update the existing characterization test suite to use the new `periods` array format. The tests must continue to pass with **no change to the numerical output**, guaranteeing the core engine logic has not regressed.
  - **Coverage Requirement:** Maintain **100%** unit test coverage for the `engine` and `core` modules and **≥95%** for the overall project.

-----

## 8\. Acceptance Criteria

The implementation of this RFC will be considered complete when the following criteria are met:

1.  This RFC is formally approved by all stakeholders.
2.  The shared API request envelope is updated to accept a `periods` array, with backward compatibility for the legacy `period_type` field.
3.  All relevant analytics endpoints (TWR, MWR, Contribution, Attribution) are refactored to efficiently process multi-period requests and return results in the new `results_by_period` dictionary format.
4.  The `PeriodResolver` is fully implemented and unit-tested.
5.  The testing strategy is fully implemented, all new and existing tests are passing, and the required coverage targets are met.
6.  The updated integration tests confirm that multi-period results are numerically identical to single-period results.
7.  All relevant documentation, including `README.md`, `docs/guides/api_reference.md`, and all usage examples, is updated to reflect the new multi-period request and response structure.