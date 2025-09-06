# RFC 016: MWR Enhancements (XIRR + Modified Dietz)

**Status:** Final (For Approval)  
**Owner:** Senior Architect  
**Reviewers:** Perf Engine, Risk, Platform  
**Target Release:** v0.4.x  
**Related:** RFC-014 (Cross-Cutting Consistency & Diagnostics Framework), `/performance/mwr`

## 1\. Executive Summary

This document specifies a significant upgrade to the `/performance/mwr` endpoint. The goal is to enhance its accuracy and transparency by introducing superior calculation methods and aligning it with the new API standards from RFC 014. The current implementation uses a simple Dietz method, which is less accurate for portfolios with intra-period cash flows.

This RFC proposes replacing the default calculation with the industry-standard **XIRR** (eXtended Internal Rate of Return) method, which correctly handles irregularly timed cash flows. We will also implement the **Modified Dietz** method as a robust fallback and retain the **Simple Dietz** method as a final failsafe. The endpoint will also gain support for **annualization** and provide detailed **convergence diagnostics** in the response.

## 2\. Current State Analysis

The existing `/performance/mwr` endpoint is functional but has several limitations:

  * **Limited Accuracy:** It relies on a simplified Dietz formula that does not time-weight cash flows, reducing accuracy when cash flows occur other than at the exact midpoint of the period.
  * **No Annualization:** The endpoint returns a periodic rate but does not provide a standard annualized equivalent, which is crucial for comparing returns over different time horizons.
  * **Lack of Transparency:** The response is minimal, offering no insight into the calculation process, the cash flows used, or whether the calculation was successful.
  * **Inconsistent API:** The endpoint does not yet conform to the new shared request and response envelope defined in RFC 014.

## 3\. Proposed Enhancements & Methodology

### 3.1 New Calculation Methods

The `engine/mwr.py` module will be upgraded to support three distinct methods, selectable via a new `mwr_method` field in the request.

1.  **XIRR (Default):** The primary method will be XIRR, which finds the discount rate that makes the net present value (NPV) of all cash flows (including beginning and ending market values) equal to zero. This requires an iterative numerical solver (e.g., Newton's method or Brent's method).
2.  **Modified Dietz:** This method calculates the gain over the period divided by the average capital invested. It improves on Simple Dietz by weighting each cash flow by the amount of time it was present in the portfolio.
3.  **Simple Dietz:** The legacy method will be retained as a final fallback.

### 3.2 Fallback Policy

To ensure resilience, the engine will implement a strict fallback policy:

  * The engine will first attempt the user-requested method (e.g., XIRR).
  * If the XIRR solver fails to converge or encounters a scenario with no valid root (e.g., no sign change in the NPV function), it will automatically fall back to the **Modified Dietz** method.
  * If Modified Dietz fails (e.g., average capital is zero), it will fall back to **Simple Dietz**.
  * The `method` field in the response will **always** report which calculation was ultimately used, and the `diagnostics.notes` will contain an entry explaining why a fallback occurred.

### 3.3 Annualization

The raw MWR/IRR is a rate for the specific period. The endpoint will now provide an annualized version.

  * **Trigger:** When a request is sent with `"annualization": {"enabled": true}`.
  * **Logic:** The annualized return will be calculated using the standard formula: $$(1 + MWR_{period})^{(365 / N_{days})} - 1$$, where $N\_{days}$ is the number of days in the period. This aligns with the `ACT/365` basis, which is standard for IRR.
  * **Output:** The response will contain both `mwr` (the periodic rate) and `mwr_annualized`.

## 4\. API Contract Changes

### 4.1 `MoneyWeightedReturnRequest` Additions

```jsonc
{
  // ... existing fields ...
  "mwr_method": "XIRR", // "XIRR" | "MODIFIED_DIETZ" | "DIETZ"
  "solver": { // Optional controls for the XIRR numerical solver
    "method": "brent",
    "max_iter": 200,
    "tolerance": 1e-10
  },
  "emit_cashflows_used": true,
  // --- Shared Envelope Fields from RFC 014 ---
  "as_of": "2025-08-31",
  "annualization": {"enabled": true, "basis": "ACT/365"}
}
```

### 4.2 `MoneyWeightedReturnResponse` Additions

```jsonc
{
  "mwr": 0.0712, // The periodic rate
  "mwr_annualized": 0.0740,
  "method": "XIRR", // The method successfully used
  "convergence": { // Diagnostics from the XIRR solver
    "iterations": 37,
    "residual": 1.7e-10,
    "converged": true
  },
  "cashflows_used": [
    {"date": "2025-01-15", "amount": -100000},
    // ...
  ],
  // ... shared footer (meta, diagnostics, audit) ...
}
```

## 5\. Testing Strategy

  * **Unit Tests:** Create new tests in `tests/unit/engine/test_mwr.py` for each of the three methods, validating their outputs against textbook examples and financial calculators.
  * **Fallback Logic Tests:** Design specific cash flow scenarios that are known to cause XIRR to fail (e.g., all positive flows, no sign change) and assert that the engine correctly falls back to Modified Dietz and reports it.
  * **Integration Test:** Create a new integration test in `tests/integration/test_mwr_api.py` that sends a request for an annualized XIRR and validates the entire response structure, including the annualized value and convergence diagnostics.

## 6\. Acceptance Criteria

The implementation of this RFC will be considered complete when:

1.  The `engine/mwr.py` module is updated with XIRR, Modified Dietz, and Simple Dietz methods, including the defined fallback logic.
2.  The `/performance/mwr` endpoint correctly handles the new request fields (`mwr_method`, `annualization`) and returns the new, richer response payload.
3.  The `scipy` dependency is added to `pyproject.toml` to support the numerical solver.
4.  All new unit and integration tests pass, including those that specifically validate the fallback mechanism and annualization math.
5.  Documentation in `docs/guides/api_reference.md` and `docs/guides/methodology.md` is updated to reflect the new MWR capabilities.
6.  This RFC is formally approved before implementation begins.