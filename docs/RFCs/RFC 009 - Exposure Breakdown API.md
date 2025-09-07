# RFC 009: Exposure Breakdown API (Final)

**Status:** Final (For Approval)
**Owner:** Senior Architect
**Reviewers:** Perf Engine, Risk, Platform
**Related:** RFC-014 (Envelope), RFC-008 (Fixed-Income), RFC-010 (Factor Exposure)

## 1\. Executive Summary

This document specifies the final design for a new, high-performance **Exposure Breakdown API** to be implemented at `/portfolio/exposureBreakdown`. The current analytics suite excels at explaining historical performance but lacks the fundamental capability to describe a portfolio's current composition and risk characteristics. This API closes that gap by providing a configurable, on-demand breakdown of portfolio exposures across any classification dimension (e.g., asset class, sector, region, currency).

The engine is designed to be highly flexible, supporting **gross, net, long, and short** exposures, as well as critical **risk-adjusted measures** like delta-adjusted, beta-adjusted, and duration-weighted exposures. It will support both **snapshot (as-of)** and **timeseries** analysis. In line with our architectural principles, the API is **fully configurable**, allowing client advisors to request only the measures they need.

The implementation will follow our established pattern of a decoupled, vectorized `engine` module, ensuring scalability and reusability. Rigorous testing will guarantee numerical correctness and 100% test coverage for the new engine logic.

## 2\. Goals & Non-Goals

### Goals

  * Compute exposures by a chosen `dimension` and optional `groupBy` hierarchy.
  * Support a configurable set of measures: **gross, net, long, short** exposures and **weights**.
  * Optionally compute **risk-adjusted** exposures, including **delta-adjusted**, **beta-adjusted**, and **duration/DV01-weighted**.
  * Support both **snapshot** (as-of) and **timeseries** modes.
  * Provide robust output shaping controls, including `top_n` filtering and bucketing for "Other" and "Unclassified" groups.

### Non-Goals

  * No data persistence or scheduling; the API is stateless.
  * No internal risk model estimation; the caller supplies all sensitivities (e.g., delta, beta) and metadata.
  * No automatic fund look-through retrieval; callers must supply look-through vectors if needed.

## 3\. Methodology

### 3.1. Input Processing & Classification

The engine first normalizes all holdings into a standard panel. For snapshot mode, it uses the single `as_of` date. For timeseries mode, it resamples the market values to the requested frequency. Each instrument is then mapped to a group based on the requested `dimension` and any `bucketing` rules (e.g., mapping a `maturity` date to a "3-7Y" bucket). Instruments with missing classification data are mapped to an "Unclassified" group unless `strict_dimension` is enabled.

### 3.2. Core Exposure Calculation

For each group *i*, the engine calculates the four fundamental exposure measures in the portfolio's base currency. An instrument's market value ($MV\_j$) is treated as negative if its `side` is "short".

  * **Long Exposure**: $L\_i = \\sum\_{j \\in i} \\max(MV\_j, 0)$
  * **Short Exposure**: $S\_i = \\sum\_{j \\in i} \\max(-MV\_j, 0)$
  * **Gross Exposure**: $G\_i = L\_i + S\_i$
  * **Net Exposure**: $N\_i = L\_i - S\_i = \\sum\_{j \\in i} MV\_j$
  * **Net Weight**: $w^{net}\_i = N\_i / \\sum\_j MV\_j$

### 3.3. Risk-Adjusted Exposure Calculation

If the required sensitivities are provided in the payload and the measure is requested, the engine computes risk-adjusted exposures.

  * **Derivative Mapping**: The `derivative_policy` flag controls how derivatives are handled. The default, `delta_notional`, is the most robust, calculating exposure as `delta × underlying_notional`. If delta is missing, it can fall back to using the instrument's market value.
  * **Beta-Adjusted**: $E^{\\beta}*i = \\sum*{j \\in i} \\beta\_j \\cdot MV\_j$
  * **Duration-Weighted**: $E^{Dur}*i = \\sum*{j \\in i} Dur\_j \\cdot MV\_j$
  * **DV01 Exposure**: $E^{DV01}*i = \\sum*{j \\in i} DV01\_j$ (additive)

### 3.4. Hierarchical Aggregation & Output Shaping

If a `groupBy` hierarchy is provided, the engine performs a bottom-up aggregation, summing the calculated exposures from the most granular `dimension` up to the parent levels. Finally, the results are sorted, and any groups falling below the `threshold_weight` are aggregated into an "Other" bucket if requested.

## 4\. API Design

### 4.1. Endpoint

`POST /portfolio/exposureBreakdown`

### 4.2. Request Schema (Pydantic)

```json
{
  "portfolio_number": "PORT123",
  "as_of": "2025-08-31",
  "currency": "USD",
  "mode": "snapshot",
  "dimension": "sector",
  "groupBy": ["assetClass"],
  "holdings": {
    "by": "instrument",
    "series": [
      {
        "instrumentId": "AAPL",
        "meta": { "assetClass": "Equity", "sector": "Tech" },
        "observations": [{ "date": "2025-08-31", "mv": 125000.0, "beta": 1.10 }]
      },
      {
        "instrumentId": "SPX_FUT",
        "meta": { "assetClass": "Equity Derivative", "sector": "Index" },
        "observations": [{ "date": "2025-08-31", "mv": -50000.0, "qty": -2, "price": 5200, "multiplier": 50, "delta": 1.0 }]
      },
      {
        "instrumentId": "UST_2030",
        "meta": { "assetClass": "Bond", "sector": "UST", "maturity": "2030-11-15" },
        "observations": [{ "date": "2025-08-31", "mv": 400000.0, "dv01": 2200.0, "duration": 6.1 }]
      }
    ]
  },
  "bucketing": {
    "maturityBucket": { "rules": [ { "name": "7-15Y", "gt_years": 7, "lte_years": 15 } ] }
  },
  "measures": {
    "net": true,
    "weight_net": true,
    "beta_adjusted": true,
    "delta_adjusted": true,
    "dv01": true
  },
  "output": {
    "top_n": 20,
    "threshold_weight": 0.005,
    "include_other": true,
    "sort_by": "net"
  },
  "flags": {
    "derivative_policy": "delta_notional"
  }
}
```

### 4.3. Response Schema

```json
{
  "as_of": "2025-08-31",
  "dimension": "sector",
  "groupBy": ["assetClass"],
  "totals": { "mv_net": 475000.0, "dv01_total": 2200.0 },
  "groups": [
    {
      "key": { "assetClass": "Bond", "sector": "UST" },
      "net": 400000.0, "weight_net": 0.8421, "dv01": 2200.0
    },
    {
      "key": { "assetClass": "Equity", "sector": "Tech" },
      "net": 125000.0, "weight_net": 0.2632, "beta_adjusted": 137500.0, "delta_adjusted": 125000.0
    },
    {
      "key": { "assetClass": "Equity Derivative", "sector": "Index" },
      "net": -50000.0, "weight_net": -0.1053, "delta_adjusted": -520000.0,
      "notes": ["futures mapped by delta_notional: qty*price*multiplier"]
    }
  ],
  "meta": { ... },
  "diagnostics": { ... },
  "audit": { ... }
}
```

### 4.4. HTTP Semantics & Errors

  * **200 OK**: Successful computation.
  * **400 Bad Request**: Schema or validation errors (e.g., unknown dimension, invalid bucketing rule).
  * **422 Unprocessable Entity**: Request is valid, but data is insufficient (e.g., no holdings on the `as_of` date).
  * **413 Payload Too Large**: Request payload exceeds configured limits.

## 5\. Architecture & Implementation Plan

The new feature will be integrated into the existing architecture.

1.  **Create new modules**:
      * `engine/exposure.py`: To house the core vectorized logic for classification, aggregation, and calculation.
      * `app/models/exposure_requests.py` and `app/models/exposure_responses.py`: To define the Pydantic API contract.
2.  **Create new endpoint**:
      * Add a new router for `/portfolio` in `app/api/endpoints/portfolio.py`.
      * Implement the `POST /portfolio/exposureBreakdown` endpoint, which calls the adapter and the new exposure engine.
3.  **Update `main.py`**:
      * Register the new `/portfolio` router with the FastAPI application.

## 6\. Testing & Validation Strategy

  * **Unit Tests**: Create a comprehensive suite in `tests/unit/engine/test_exposure.py`. Tests will validate each core calculation (L/S/G/N), each risk-adjusted measure, all derivative policies, bucketing logic, and handling of edge cases (e.g., division by zero when normalizing weights).
  * **Integration Tests**: Add API-level tests in `tests/integration/test_exposure_api.py` to validate the end-to-end flow, including schema validation, correct handling of all request flags, and the structure of the final JSON response.
  * **Characterization Test**: A new test will be created using a realistic, multi-asset portfolio. The output of the API will be compared against a reference calculation performed in a Pandas/Jupyter notebook to ensure numerical correctness.
  * **Coverage Enforcement**: The new `engine/exposure.py` module must achieve **100% test coverage**. The overall project coverage must remain at or above **95%**.

## 7\. Acceptance Criteria

The implementation of this RFC is complete when:

1.  This RFC is formally approved by all stakeholders.
2.  All new modules (`engine/exposure.py`, `app/models/exposure_*.py`, `app/api/endpoints/portfolio.py`) are created and integrated.
3.  The `POST /portfolio/exposureBreakdown` endpoint is fully functional and meets all requirements specified in this document.
4.  The testing and validation strategy is fully implemented, and the required test coverage targets (**100% for the engine**, **≥95% for the project**) are met and verified in the CI pipeline.
5.  The characterization test passes, confirming numerical results are correct against the external reference.
6.  New documentation is added to `docs/guides/` and `docs/technical/` explaining the Exposure Breakdown API's methodology, inputs, and outputs, ensuring the documentation stays current with the codebase.