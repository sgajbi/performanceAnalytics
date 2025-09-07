# RFC 008: Fixed-Income Metrics API (Final)

**Status:** Final (For Approval)
**Owner:** Senior Architect
**Reviewers:** Perf Engine, Risk, Platform
**Related:** RFC-009 (Exposure Breakdown), RFC-011 (Scenario Analysis)

## 1\. Executive Summary

This document specifies the final design for a new, foundational **Fixed-Income Metrics API** to be implemented at `/analytics/fixedIncomeMetrics`. While other APIs provide high-level portfolio analysis, they rely on having accurate, instrument-level risk sensitivities. This API provides that critical data by serving as a dedicated, high-precision calculator for core fixed-income metrics.

The engine will calculate a standard suite of analytics for individual bonds, including **Price, Yield-to-Maturity (YTM), Macaulay and Modified Duration, Convexity, DV01 (Dollar Value of a 1 basis point change), and Key Rate Durations (KRDs)**. It is designed to be a robust, "enabling" service; its outputs are the essential inputs required by higher-level services like the Exposure Breakdown (RFC 009) and Scenario Analysis (RFC 011) APIs to accurately assess fixed-income risk.

The implementation will be a pure, standalone engine for pricing and risk calculation, adhering to our established architectural patterns and rigorous testing standards to ensure its results are correct and can be trusted by all dependent services.

## 2\. Goals & Non-Goals

### Goals

  * Provide a stateless API to calculate a standard set of price, yield, and risk metrics for vanilla fixed-income instruments.
  * Support standard bond structures (e.g., fixed-coupon bullet bonds, zero-coupon bonds).
  * Calculate metrics based on either a provided `price` or a `yield_curve`.
  * Decompose interest rate risk into **Key Rate Durations (KRDs)** for granular analysis.
  * Serve as the canonical source of fixed-income sensitivities for other APIs in the suite.

### Non-Goals

  * The v1 engine will not support complex, path-dependent instruments like callable/putable bonds or mortgage-backed securities (MBS).
  * The API is purely computational and will not source market data (e.g., yield curves).
  * It will not perform portfolio-level aggregation; it operates on a list of individual instruments.

## 3\. Methodology

The engine uses standard, industry-accepted formulas for fixed-income calculations.

### 3.1. Price & Yield

The fundamental relationship between a bond's price and its yield is its discounted cash flow (DCF) formula.

  * **Price from Yield**: Given a yield (*y*), the price (*P*) is calculated by discounting all future cash flows (coupons *C* and face value *F*).
    $$P = \sum_{t=1}^{N} \frac{C_t}{(1+y/k)^{kt}} + \frac{F}{(1+y/k)^{kN}}$$
    (Where *k* is the coupon frequency and *N* is the number of years).
  * **Yield from Price**: Given a price, the Yield-to-Maturity (YTM) is calculated by iteratively solving the above equation for *y* using a numerical root-finding algorithm (e.g., Newton's method).

### 3.2. Duration & Convexity

  * **Macaulay Duration**: The weighted-average time to receive the bond's cash flows.
  * **Modified Duration**: A measure of a bond's price sensitivity to changes in yield. It is derived from the Macaulay Duration and is a first-order approximation of the price change.
    $$D_{mod} = -\frac{1}{P} \frac{\partial P}{\partial y}$$
  * **Convexity**: A measure of the curvature in the price-yield relationship. It is the second derivative of price with respect to yield and is used to improve the accuracy of price change estimates for large yield shifts.

### 3.3. "Bump-and-Revalue" Risk Metrics

For more precise risk measurement, the engine uses a bump-and-revalue approach.

  * **DV01 (Dollar Value of '01)**: The absolute change in a bond's price for a 1 basis point (0.01%) parallel downward shift in the yield curve. It is a direct measure of interest rate sensitivity in currency terms.
  * **Key Rate Durations (KRDs)**: A decomposition of a bond's interest rate risk into specific tenors (e.g., 2Y, 5Y, 10Y). KRDs are calculated by independently shocking each tenor on the yield curve by 1 basis point, repricing the bond, and recording the price change. The sum of all KRDs for a bond is approximately equal to its total duration.

## 4\. API Design

### 4.1. Endpoint

`POST /analytics/fixedIncomeMetrics`

### 4.2. Request Schema (Pydantic)

```json
{
  "calculation_date": "2025-09-07",
  "metrics_to_calculate": ["price", "ytm", "mod_duration", "dv01", "krds"],
  "yield_curve": {
    "id": "USD_GOVT",
    "nodes": [
      { "tenor": "2Y", "rate": 0.045 },
      { "tenor": "5Y", "rate": 0.042 },
      { "tenor": "10Y", "rate": 0.043 }
    ]
  },
  "bonds": [
    {
      "bond_id": "UST_2035_08_15",
      "price": 98.50,
      "settlement_date": "2025-09-09",
      "maturity_date": "2035-08-15",
      "coupon_rate": 0.040,
      "face_value": 1000,
      "frequency": 2
    }
  ]
}
```

### 4.3. Response Schema

```json
{
  "calculation_date": "2025-09-07",
  "results": [
    {
      "bond_id": "UST_2035_08_15",
      "price": 98.50,
      "ytm": 0.0421,
      "mod_duration": 7.85,
      "convexity": 71.4,
      "dv01": 0.773,
      "krds": {
        "2Y": 0.15,
        "5Y": 1.52,
        "10Y": 6.18
      }
    }
  ],
  "meta": { ... },
  "diagnostics": { ... },
  "audit": { ... }
}
```

### 4.4. HTTP Semantics & Errors

  * **200 OK**: Successful computation.
  * **400 Bad Request**: Schema or validation errors (e.g., maturity date is before settlement date).
  * **422 Unprocessable Entity**: Request is valid, but a metric cannot be calculated (e.g., YTM solver fails to converge).
  * **413 Payload Too Large**: Request payload exceeds configured limits.

## 5\. Architecture & Implementation Plan

1.  **Create new modules**:
      * `engine/fixed_income.py`: To house the core pricing and risk calculation logic. This will include functions for cash flow generation, a yield solver, and bump-and-revalue logic.
      * `app/models/fi_requests.py` and `app/models/fi_responses.py`: To define the API contract.
2.  **Update endpoint router**:
      * Add the `POST /analytics/fixedIncomeMetrics` endpoint to `app/api/endpoints/analytics.py`.
3.  **Implementation Steps**:
      * Build the cash flow generation and bond pricing functions first.
      * Implement the YTM solver.
      * Layer on the duration and convexity calculations.
      * Implement the bump-and-revalue logic for DV01 and KRDs.

## 6\. Testing & Validation Strategy

  * **Unit Tests**: The new `engine/fixed_income.py` module must achieve **100% test coverage**. This will include tests for each individual metric (price, yield, duration, DV01, etc.) across different bond structures (e.g., premium, discount, zero-coupon).
  * **Integration Tests**: API-level tests will validate the end-to-end flow, ensuring the `metrics_to_calculate` request field correctly shapes the response.
  * **Characterization Test**: A suite of tests will be created comparing the API's output against a trusted, industry-standard financial library (e.g., QuantLib) for a set of well-known bond examples. This is critical to guarantee numerical correctness.
  * **Overall Coverage**: The overall project test coverage must remain at or above **95%**.

## 7\. Acceptance Criteria

The implementation of this RFC is complete when:

1.  This RFC is formally approved by all stakeholders.
2.  All new modules are created and fully integrated into the existing architecture.
3.  The `POST /analytics/fixedIncomeMetrics` endpoint is fully functional and can correctly calculate all specified metrics.
4.  The testing and validation strategy is fully implemented, all tests are passing, and the required coverage targets (**100% for engine**, **≥95% for project**) are met.
5.  The characterization test passes, confirming numerical results match the external reference library.
6.  New documentation is added to `docs/guides/` and `docs/technical/` for the Fixed-Income Metrics API.