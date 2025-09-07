# RFC 019: Multi‑Level Contribution API (Final)

**Status:** Final (For Approval)  
**Owner:** Sandeep (Cyclops/PerformanceAnalytics)  
**Reviewers:** Perf Engine, Risk, Platform  
**Target Release:** v0.4.x  
**Related:** RFC‑014 (Envelope/Diagnostics), RFC‑015 (TWR), RFC‑017 (Contribution Enhancements), RFC‑018 (Attribution)

-----

## 1\. Executive Summary

This document specifies the final design for extending the `/performance/contribution` endpoint to support **multi-level, hierarchical contribution analysis**. The current engine calculates contribution at the instrument level. This enhancement generalizes that capability, allowing clients to request a full breakdown of performance drivers across multiple classification levels (e.g., *Asset Class → Sector → Industry → Security*) in a single API call.

The core of this proposal is to implement a **bottom-up aggregation** of daily, **Carino-smoothed** contributions. This methodology guarantees that the contributions at each level of the hierarchy **reconcile exactly** with each other and with the total portfolio's geometric TWR. The API will be highly configurable, supporting flexible weighting schemes, look-through allocations for complex instruments, and optional time-series outputs.

Crucially, this RFC aligns the `/contribution` endpoint with the **Unified API Envelope** established in RFC-014, ensuring a consistent request/response structure and providing rich diagnostic and audit metadata. All new functionality is introduced as optional and additive, guaranteeing **full backward compatibility** with existing clients.

-----

## 2\. Problem & Motivation

Portfolio teams need contribution analysis **at multiple levels of the classification hierarchy** in a single call, with outputs that **reconcile exactly** at each level and to the **portfolio return** for the chosen horizon. Current single‑level contribution works per instrument or per selected group; this RFC generalizes it to multi-level with:

  - Carino‑smoothed, **additive** contributions that sum from security to industry to sector to asset class to portfolio.
  - Flexible **weighting schemes** (BOD, Average Capital, TWR denominator).
  - NIP/reset‑aware daily handling, consistent with the TWR engine.
  - Snapshot totals **and** (optional) **time-series** per level with top‑N shaping.

-----

## 3\. Goals & Non‑Goals

### Goals

  - Support **arbitrary hierarchies** up to a configurable depth of 4, supplied via a `hierarchy` array (e.g., `["assetClass", "sector", "security"]`).
  - Compute **daily contributions** per instrument, apply **Carino smoothing** using portfolio daily returns, then aggregate **bottom‑up** across all levels.
  - Provide **snapshot totals** over the requested period and optional **per‑bucket time-series** (e.g., monthly contributions by sector & industry).
  - Preserve exact **reconciliation**: the sum of contributions at any level must equal the contribution of its parent, up to the total portfolio contribution (within rounding tolerances).
  - Fully integrate with the **RFC-014 Shared Envelope**, adopting its common request parameters and response footer.

### Non‑Goals

  - No factor‑based contribution (covered in RFC‑010 Factor Exposure).
  - No automated taxonomy inference (the caller must supply instrument metadata or look‑through allocations).

-----

## 4\. Methodology

The methodology extends the existing Carino-based contribution engine. It operates on a daily frequency within the effective period defined by the RFC-014 `periods` and `calendar` objects.

Let instruments be indexed by **j**, days by **t**, and hierarchy levels by **ℓ = 1..L** (where L≤4).

1.  **Position Daily Return ($r\_{j,t}$)**: Calculated using the standard Dietz-style daily formula, consistent with the TWR engine.
    $$r_{j,t} = \frac{EMV_{j,t} - BMV_{j,t} - CF_{j,t} - \text{Fees}_{j,t}}{|BMV_{j,t} + CF^{\text{BOD}}_{j,t}|}$$

2.  **Portfolio Daily Return ($R\_{p,t}$)**: Sourced directly from the TWR engine for the same period and calendar.

3.  **Daily Weight ($w\_{j,t}$)**: Calculated based on the chosen `weighting_scheme`:

      - **BOD**: $w\_{j,t} = \\frac{BMV\_{j,t} + CF^{\\text{BOD}}*{j,t}}{\\sum\_k (BMV*{k,t} + CF^{\\text{BOD}}\_{k,t})}$
      - **AVG\_CAPITAL**: $w\_{j,t} = \\frac{BMV\_{j,t} + 0.5 \\cdot CF\_{j,t}}{\\sum\_k (BMV\_{k,t} + 0.5 \\cdot CF\_{k,t})}$
      - **TWR\_DENOM**: $w\_{j,t} = \\frac{|BMV\_{j,t} + CF^{\\text{BOD}}*{j,t}|}{\\sum\_k |BMV*{k,t} + CF^{\\text{BOD}}\_{k,t}|}$

4.  **Carino Smoothing**: A daily smoothing scalar ($k\_t$) is calculated from the portfolio's daily return to ensure geometric linking.
    $$k_t = \begin{cases} \ln(1+R_{p,t})/R_{p,t}, & R_{p,t} \ne 0 \\ 1, & R_{p,t} = 0\end{cases}$$
    The smoothed daily contribution for each instrument is then:
    $$\tilde{c}_{j,t} = k_t \cdot (w_{j,t} \cdot r_{j,t})$$

5.  **Instrument Total Contribution ($C\_j$)**: The sum of smoothed daily contributions over the horizon.
    $$C_j = \sum_{t\in T} \tilde{c}_{j,t}$$

6.  **Hierarchy Aggregation**:

      - For each instrument **j**, its classification key for each level **ℓ** is determined from its metadata.
      - For the most granular level **L**, group contributions ($C\_g$) are calculated by summing the instrument contributions within that group: $C\_g = \\sum\_{j\\in g} C\_j$.
      - This process is repeated, aggregating the child group contributions up to the parent level, until the top level (ℓ=1) is reached. The sum of contributions at the top level will equal the total portfolio contribution.

7.  **NIP & Reset Handling**:

      - On **NIP days**, $r\_{j,t}$ and therefore $\\tilde{c}\_{j,t}$ are set to zero for all instruments.
      - On **Reset (NCTRL) days**, the compounding segment is terminated, and the smoothing factor sequence restarts, consistent with the TWR engine.

-----

## 5\. API Design

This RFC **extends** the existing `/performance/contribution` endpoint. Multi-level functionality is activated by providing the `hierarchy` array in the request.

### 5.1 Endpoint

`POST /performance/contribution`

### 5.2 Request Schema

The request model will be updated to include the new fields and will **fully adopt the RFC-014 Shared Request Envelope**.

```jsonc
// POST /performance/contribution
{
  // --- RFC-014 Shared Envelope Fields ---
  "as_of": "2025-08-31",
  "periods": {"type": "YTD"},
  "calendar": {"type": "BUSINESS"},
  "precision_mode": "FLOAT64",
  // ... other shared fields ...

  // --- RFC-019 Multi-Level Contribution Fields ---
  "hierarchy": ["assetClass", "sector", "industry", "security"],
  "weighting_scheme": "BOD",                 // "BOD" | "AVG_CAPITAL" | "TWR_DENOM"
  "lookthrough": {                             // Optional: For allocating instrument contributions
    "enabled": false,
    "fallback_policy": "error"                 // "error" | "unclassified" | "scale_to_1"
  },
  "bucketing": {                               // Optional: For mapping numeric values to categories
    "maturityBucket": { "rules": [ {"name":"0-1Y","lte_years":1}, {"name":"1-3Y","gt_years":1,"lte_years":3} ] }
  },
  "emit": {
    "by_level": true,                          // If true, include blocks for every hierarchy level
    "timeseries": true,                        // If true, add bucketed time-series data per level
    "top_n_per_level": 20,                     // Shape output by showing top N contributors per level
    "threshold_weight": 0.005,                 // Group contributions from positions with <0.5% weight into "Other"
    "include_other": true,
    "include_unclassified": true,
    "residual_per_position": true              // Show rounding residuals at the leaf (security) level
  },

  // --- Existing Contribution Fields ---
  "portfolio_data": { /* ... */ },
  "positions_data": [ /* ... */ ]
}
```

### 5.3 Response Schema

The response model will be updated to include the hierarchical breakdown and will **always include the RFC-014 Shared Response Footer**.

```jsonc
{
  // --- RFC-019 Multi-Level Contribution Body ---
  "summary": {
    "portfolio_contribution": 0.0182,
    "coverage_mv_pct": 0.997,
    "weighting_scheme": "BOD"
  },
  "levels": [
    {
      "level": 1,
      "name": "assetClass",
      "rows": [
        {"key": {"assetClass": "Equity"}, "contribution": 0.0114, "weight_avg": 0.62},
        {"key": {"assetClass": "Bond"},   "contribution": 0.0061, "weight_avg": 0.35},
        {"key": {"assetClass": "Other"},  "contribution": 0.0007, "weight_avg": 0.03, "is_other": true}
      ]
    },
    {
      "level": 2,
      "name": "sector",
      "parent": "assetClass",
      "rows": [ {"key": {"assetClass":"Equity", "sector":"Tech"}, "contribution": 0.0071, "children_count": 12 } ]
    }
    // ... other levels ...
  ],
  "timeseries": { // Optional: Included if emit.timeseries = true
    "mode": "timeseries",
    "frequency": "M", // From request.periods or default
    "levels": [
      {
        "level": 2,
        "name": "sector",
        "series": [
          {"key": {"assetClass":"Equity", "sector":"Tech"},
           "observations": [ {"date":"2025-01-31", "contribution": 0.0012}, {"date":"2025-02-28", "contribution": 0.0013} ]}
        ]
      }
    ]
  },

  // --- RFC-014 Shared Response Footer ---
  "meta": { /* ... */ },
  "diagnostics": { /* ... */ },
  "audit": {
    "sum_leaf_equals_portfolio_bp": 0.0,
    "residual_distribution_policy": "proportional",
    "nip_days": 2,
    "reset_events": [ {"date":"2025-03-15", "reason":"NCTRL2"} ]
  }
}
```

-----

## 6\. Architecture & Files Affected

The implementation will extend existing modules.

```
engine/
  contribution.py              # Extend with hierarchical mapper and bottom‑up aggregator.

app/models/
  contribution_requests.py     # Add hierarchy, lookthrough, bucketing, and emit options.
  contribution_responses.py    # Add multi‑level and time-series response shapes.

app/api/endpoints/
  contribution.py              # No new path; activate feature via request payload.
```

  - **Reuse:** `core/periods.py`, `core/envelope.py`, `core/errors.py` from RFC-014.

-----

## 7\. Backward Compatibility

These changes are **fully backward compatible**.

  - The multi-level functionality is triggered only when the new `hierarchy` field is present in the request.
  - Existing single-level contribution requests that do not contain the `hierarchy` field will continue to work exactly as before.
  - All new request fields are optional.

-----

## 8\. Testing Strategy

  - **Unit Tests:**
      - **Additivity**: Test that for a synthetic 3-level hierarchy, Σ security contributions == industry contribution, and Σ industry contributions == sector contribution.
      - **Carino Correctness**: Confirm that the sum of contributions at the top level reconciles to the portfolio's geometric TWR.
      - **Weighting Schemes**: Test that each weighting scheme (`BOD`, `AVG_CAPITAL`, `TWR_DENOM`) produces correct and different results on a toy dataset.
      - **Look-through**: Test that a single instrument's contribution is correctly split according to allocation weights and that the sum matches the unsplit total.
      - **NIP/Reset**: Confirm contributions are zeroed on NIP/reset days.
  - **API & Integration Tests:**
      - Schema validation for new request fields.
      - Test `top_n_per_level` shaping and the `Other`/`Unclassified` bucket aggregation.
      - Test time-series output shape and correctness for different frequencies (M/Q/Y).
      - An end-to-end test with a realistic portfolio, comparing results to a reference notebook and ensuring the audit residual is within 0.1 bp.
  - **Coverage Requirement:** Unit test coverage for `engine/contribution.py` must be **100%**. Overall project test coverage must be **≥95%**.

-----

## 9\. Observability & Limits

  - **Logs:** `hierarchy_depth`, `weighting_scheme`, `coverage_mv_pct`, `nip_days`, `reset_count`, `top_n_per_level`.
  - **Metrics:** Latency histograms by hierarchy depth; percentage of MV in `Other`/`Unclassified`; residual magnitude distribution.
  - **Limits:** Max hierarchy depth ≤ 4; max instruments ≤ 50k; max payload size ≤ 25 MB.

-----

## 10\. Acceptance Criteria

The implementation of this RFC will be considered complete when the following criteria are met:

1.  This RFC is formally approved by all stakeholders.
2.  The `ContributionRequest` and `ContributionResponse` models in `app/models/` are updated to include the new fields and fully adopt the RFC-014 shared envelope.
3.  The `engine/contribution.py` module is extended to perform Carino-smoothed contribution calculations with hierarchical, bottom-up aggregation.
4.  All new configurable features are implemented: `weighting_scheme`, `lookthrough`, `bucketing`, and `emit` controls for time-series and output shaping.
5.  All existing single-level contribution functionality remains unchanged and passes all existing tests.
6.  The testing strategy is fully implemented, and the required test coverage targets (100% for engine, ≥95% for project) are met.
7.  End-to-end integration tests confirm the mathematical reconciliation and correct API behavior for multi-level scenarios.
8.  Documentation in `docs/` is created or updated to reflect the new capabilities, including:
      - An update to `docs/guides/api_reference.md` detailing the new request/response fields.
      - A new guide, `docs/guides/contribution_multilevel.md`, explaining the methodology.

 