# RFC 020: Multi-Currency & FX-Aware Analytics (Final)

**Status:** Final (For Approval)
**Owner:** Senior Architect
**Reviewers:** Perf Engine, Risk, Platform
**Related:** All core analytics endpoints, RFC-025 (Reproducibility)

## 1\. Executive Summary

This document specifies the final design for a comprehensive **Multi-Currency & FX-Aware Analytics** framework. Real-world portfolios hold assets in multiple currencies, and a significant portion of their return and risk comes from foreign exchange rate movements. This RFC extends our entire suite of analytics—TWR, MWR, Contribution, and Attribution—to correctly handle, decompose, and report on the effects of currency.

The core of this enhancement is to decompose every instrument's return into its **local performance** and its **FX contribution**. This framework will be integrated into all existing engines, allowing users to see a clear `local | fx | base` return split for any portfolio. It also introduces a powerful **currency attribution** model (based on Karnosky-Singer) to explain active returns driven by currency decisions.

The API is designed for flexibility, supporting configurable FX fixing sources and policies for handling currency hedging. This is a foundational upgrade that transforms our service into a true multi-currency analytics platform.

## 2\. Goals & Non-Goals

### Goals

  * Decompose TWR and Contribution into **local, FX, and base currency** components.
  * Provide a robust **currency attribution** model to explain active returns.
  * Support configurable modeling for **currency hedging**.
  * Ensure all calculations are stateless and auditable, integrating with the reproducibility framework.
  * Apply currency awareness consistently across all four core analytics endpoints.

### Non-Goals

  * The API will not source FX rates or other market data; the caller must provide it.
  * Advanced currency options hedging is out of scope for v1.

## 3\. Methodology

The framework is built on the daily decomposition of returns for each instrument.

### 3.1. Core Return Decomposition

For any instrument *j* held in a local currency *c(j)*, its return in the base (reporting) currency, $r^B$, is a combination of its local return, $r^L$, and the return of its currency against the base, $r^X$.

  * **Base Return Formula**:
    $$(1 + r^B_{j,t}) = (1 + r^L_{j,t}) \cdot (1 + r^X_{c(j),t})$$
    This can be approximated as $r^B \\approx r^L + r^X$. The engine calculates the `fx_contribution` for each instrument daily and aggregates it using the same Carino-smoothed linking as the core TWR engine to ensure the components perfectly sum to the total base return.

### 3.2. Hedging Models

The framework supports modeling the impact of currency hedging. The effective FX return, $r^X\_{eff}$, is adjusted based on the hedge ratio, *h*:

  * **Effective FX Return**: $r^X\_{eff} = (1 - h\_t) \\cdot r^X\_t$
    Where $h\_t=0$ is unhedged and $h\_t=1$ is fully hedged. This simple ratio model is the default. More advanced forward-rate-aware models can be added in the future.

### 3.3. Currency Attribution

For the Attribution endpoint, the engine implements a Karnosky-Singer style model that decomposes the total active return into four components for each currency bucket *i*:

1.  **Local Allocation (LA)**: Active return from allocating to different local markets.
    $$LA_i = (w^p_i - w^b_i) \cdot r^L_{b,i}$$
2.  **Local Selection (LS)**: Active return from selecting securities within local markets.
    $$LS_i = w^b_i \cdot (r^L_{p,i} - r^L_{b,i})$$
3.  **Currency Allocation (CA)**: Active return from overweighting/underweighting currencies.
    $$CA_i = (w^p_i - w^b_i) \cdot (1+r^L_{b,i}) \cdot r^X_i$$
4.  **Currency Selection (CS)**: A cross-product effect capturing the interaction between local returns and currency movements.
    $$CS_i = w^b_i \cdot (r^L_{p,i} - r^L_{b,i}) \cdot (1+r^X_i)$$

## 4\. API Design

### 4.1. Request Additions (Shared Blocks)

The following blocks will be added to the shared request envelope for all relevant endpoints.

```json
{
  "currency_mode": "BOTH",
  "report_ccy": "USD",
  "fx": {
    "source": "CLIENT_SUPPLIED",
    "fixing": "EOD",
    "rates": [
      { "date": "2025-09-07", "ccy": "EUR", "rate": 1.1050 }
    ]
  },
  "hedging": {
    "mode": "RATIO",
    "series": [
      { "date": "2025-09-07", "ccy": "EUR", "hedge_ratio": 0.50 }
    ]
  }
}
```

### 4.2. Response Additions (TWR Example)

The response for each endpoint will be enhanced to include the currency decomposition.

```json
{
  "portfolio_return": {
    "local": 0.042,
    "fx": 0.008,
    "base": 0.050336
  },
  "by_currency": [
    { "ccy": "EUR", "weight_avg": 0.45, "local_contrib": 0.021, "fx_contrib": 0.006 },
    { "ccy": "JPY", "weight_avg": 0.20, "local_contrib": -0.004, "fx_contrib": 0.001 }
  ],
  "meta": { "report_ccy": "USD", ... },
  "diagnostics": { ... },
  "audit": { ... }
}
```

### 4.3. HTTP Semantics & Errors

  * **200 OK**: Successful computation.
  * **400 Bad Request**: Invalid configuration (e.g., missing `report_ccy`).
  * **422 Unprocessable Entity**: Request is valid, but FX data is missing for a required currency and `fx.missing` is set to `ERROR`.

## 5\. Architecture & Implementation Plan

1.  **Extend Core Engine**:
      * Modify the daily return calculation in `engine/ror.py` and `engine/compute.py` to perform the `local + fx = base` decomposition. The calculation will ingest the new `fx` and `hedging` configurations.
2.  **Extend Analytics Modules**:
      * **Contribution**: Enhance `engine/contribution.py` to aggregate and report local vs. fx contributions.
      * **Attribution**: Enhance `engine/attribution.py` to compute the four Karnosky-Singer components.
3.  **Update API Layer**:
      * Add the new request and response models to the `app/models/` directory.
      * Update all four endpoint functions to handle the new currency-related logic.
4.  **Phased Rollout**:
      * **Phase 1**: Implement the TWR and Contribution extensions.
      * **Phase 2**: Implement the more complex Currency Attribution.
      * **Phase 3**: Implement the MWR FX decomposition.

## 6\. Testing & Validation Strategy

  * **Unit Tests**: The modified engine modules must achieve **100% test coverage**. This will include tests for the base return identity ($1+r^B = (1+r^L)(1+r^X)$), hedging logic, and each of the four currency attribution formulas.
  * **Integration Tests**: API-level tests will be created for each of the four main endpoints to validate the end-to-end multi-currency workflow.
  * **Characterization Test**: A test will be created for a multi-currency portfolio, validating the TWR `local|fx|base` split and the full currency attribution breakdown against a reference calculation from a Jupyter notebook.
  * **Overall Coverage**: The overall project test coverage must remain at or above **95%**.

## 7\. Acceptance Criteria

The implementation of this RFC is complete when:

1.  This RFC is formally approved by all stakeholders.
2.  All four primary analytics endpoints are fully FX-aware, supporting the new request blocks and returning the specified currency decompositions.
3.  The currency attribution model is fully functional within the `/performance/attribution` endpoint.
4.  The testing and validation strategy is fully implemented, all tests are passing, and the required coverage targets are met.
5.  The characterization test passes, confirming numerical results match the external reference.
6.  New documentation is added to `docs/guides/` and `docs/technical/` explaining the multi-currency framework and currency attribution methodology.