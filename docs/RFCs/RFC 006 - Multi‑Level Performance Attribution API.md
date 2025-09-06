
# RFC 006: Multi-Level Performance Attribution API

**Status:** Final
**Owner:** Senior Architect
**Reviewers:** Perf Engine, Risk, Platform
**Target Release:** v0.3.0
**Related:** RFC-001, RFC-002, RFC-003, RFC-004

## 1\. Executive Summary

This document specifies the design and implementation of a new, high-performance **Multi-Level Performance Attribution Engine** and its corresponding API endpoint, `/performance/attribution`. This engine will provide stakeholders with Brinson-style attribution, decomposing a portfolio's active return against a benchmark into **Allocation, Selection, and Interaction** effects.

The implementation will adhere to the principles established in previous RFCs: a decoupled, standalone `engine` module, vectorized computations where possible, and a clean separation of concerns. The engine will support configurable attribution models (Brinson-Fachler, Brinson-Hood-Beebower), multi-period linking using our existing **Carino smoothing algorithm**, and a hierarchical, top-down analysis across multiple grouping levels (e.g., Asset Class → Sector).

Crucially, this engine is designed as an explanatory layer for our core TWR engine. This ensures that all analytics—TWR, Contribution, and Attribution—are derived from a single, consistent calculation core, providing a unified explanation of portfolio performance.

-----

## 2\. Core Principles & Cohesion

  * **Methodological Consistency:** The attribution engine is not a standalone calculator; it is an explanatory layer built upon our core TWR engine. All returns used in its calculations must be identical to those produced by `engine.compute.run_calculations`.
  * **Unified Data Model:** The API contract for providing time series data will reuse the established data models from the TWR and Contribution engines, ensuring a consistent interface for the client.
  * **Pattern Reuse:** The implementation will reuse existing, validated components wherever possible, specifically the Carino smoother from the contribution engine.

-----

## 3\. Target Architecture & Data Flow

The new components will be integrated into our existing architecture, maintaining a strict separation of concerns.

```plaintext
└── sgajbi-performanceanalytics/
    ├── app/
    │   ├── api/
    │   │   └── endpoints/
    │   │       └── performance.py  # Add POST /performance/attribution router
    │   ├── models/
    │   │   ├── attribution_requests.py   # New: Pydantic models for attribution
    │   │   └── attribution_responses.py  # New: Pydantic models for attribution
    │   └── ...
    ├── adapters/
    │   └── ...
    └── engine/
        ├── attribution.py          # New: Core attribution logic (A/S/I, linking)
        └── ...                     # Reuse: compute.py, rules.py (for Carino), etc.
```

### Data Flow

1.  **Request & Validation:** The `/performance/attribution` endpoint receives and validates the request using models from `attribution_requests.py`.
2.  **Computation (`engine/attribution.py`):**
    a. **Pre-processing:** The engine normalizes dates and prepares data.
    b. **Return Calculation (for `by_instrument` mode):** The engine first invokes `engine.compute.run_calculations` on the time series for the total portfolio and each individual instrument to generate consistent daily TWRs.
    c. **Group Aggregation:** It then calculates beginning-of-period weights and aggregates the instrument returns and weights into the group structures defined by `groupBy`. For `by_group` mode, this step is skipped as the data is pre-aggregated.
    d. **Top-Down Attribution:** The engine iterates through the `groupBy` hierarchy. For each level, it computes single-period A/S/I effects.
    e. **Multi-Period Linking:** It applies the specified linking algorithm (Carino) to the single-period effects.
    f. **Reconciliation:** A final residual distribution step ensures the sum of attribution effects perfectly matches the total active return.
3.  **Response Formatting:** The `api_adapter` formats the engine's output into the Pydantic response models.

-----

## 4\. Core Methodology

All portfolio and group-level returns ($R^p\_{i,t}$) are derived from the existing, validated TWR engine (`engine.compute`) to ensure methodological consistency. Weights ($w^p\_{i,t}$) are strictly **beginning-of-period** market value weights.

### 4.1 Single-Period Effects

  * **Brinson-Fachler (BF, default)**

      * Allocation ($A\_{i,t}$): $(w^p\_{i,t} - w^b\_{i,t}) \\cdot (R^b\_{i,t} - R^b\_t)$
      * Selection ($S\_{i,t}$): $w^b\_{i,t} \\cdot (R^p\_{i,t} - R^b\_{i,t})$
      * Interaction ($I\_{i,t}$): $(w^p\_{i,t} - w^b\_{i,t}) \\cdot (R^p\_{i,t} - R^b\_{i,t})$

  * **Brinson-Hood-Beebower (BHB)**

      * Allocation ($A\_{i,t}$): $(w^p\_{i,t} - w^b\_{i,t}) \\cdot R^b\_{i,t}$
      * Selection ($S\_{i,t}$): $w^p\_{i,t} \\cdot (R^p\_{i,t} - R^b\_{i,t})$
      * Interaction ($I\_{i,t}$): Same as BF.

### 4.2 Multi-Period Linking

The **Carino Smoothing Algorithm**, adapted from `engine.contribution`, will be the default method. It applies a smoothing factor to each period's effects, ensuring the sum of the linked effects equals the total geometric active return over the horizon.

### 4.3 Multi-Level Grouping

For a `groupBy` list like `["assetClass", "sector"]`, attribution is computed top-down. The "benchmark" for the `sector` level analysis within a specific `assetClass` (e.g., "Equity") is the "Equity" slice of the main benchmark.

-----

## 5\. API Contract

### 5.1 Endpoint

`POST /performance/attribution`

### 5.2 Request Model

The contract reuses our existing `DailyInputData` pattern from the TWR and Contribution engines for consistency.

`AttributionRequest.json`

```json
{
  "portfolio_number": "ATTRIB_001",
  "mode": "by_instrument", // "by_instrument" or "by_group"
  "frequency": "M", // "D", "W", "M", "Q", "Y"
  "groupBy": ["assetClass", "sector"],
  "model": "BF", // "BF" or "BHB"
  "linking": "carino", // "carino", "log", "none"
  
  // For 'by_instrument' mode:
  "portfolio_data": { /* PortfolioData model for total portfolio */ },
  "instruments_data": [
    {
      "instrumentId": "AAPL",
      "meta": { "assetClass": "Equity", "sector": "Tech" },
      "daily_data": [ /* DailyInputData for AAPL */ ]
    }
  ],

  // For 'by_group' mode:
  // "portfolio_groups_data": [ ... ],

  "benchmark_groups_data": [
    {
      "key": {"assetClass": "Equity", "sector": "Tech"},
      "observations": [
        {"date": "2025-01-31", "return": 0.032, "weight_bop": 0.245}
      ]
    }
  ]
}
```

### 5.3 Response Model

`AttributionResponse.json`

```json
{
  "portfolio_number": "ATTRIB_001",
  "model": "BF",
  "linking": "carino",
  "levels": [
    {
      "dimension": "assetClass",
      "groups": [
        {
          "key": {"assetClass": "Equity"},
          "allocation": 0.0031,
          "selection": 0.0047,
          "interaction": -0.0002,
          "total_effect": 0.0076
        }
      ],
      "totals": { /* Sums for the assetClass level */ }
    }
  ],
  "reconciliation": {
    "total_active_return": 0.0076,
    "sum_of_effects": 0.0076,
    "residual": 0.0
  }
}
```

-----

## 6\. Implementation Plan

  * **Phase 1: Foundations & Models:** Create all new files (`attribution.py`, request/response models) and define the API contract and endpoint structure.
  * **Phase 2: Core Engine - Single Level:** Implement the `by_group` mode first for a single `groupBy` level. Implement BF/BHB logic and reuse the Carino linker. Author comprehensive unit tests.
  * **Phase 3: Engine Enhancement:** Implement the `by_instrument` mode, orchestrating calls to `engine.compute.run_calculations` for each instrument before performing weight-based aggregation. Add the multi-level, top-down logic.
  * **Phase 4: Finalization & Integration:** Connect the complete engine to the API, harden all edge cases, and add integration, characterization, and benchmark tests.

-----

## 7\. Testing & Validation Strategy

  * **Unit Tests:** Every pure function in `engine/attribution.py` will be tested in isolation.
  * **Integration Tests:** The full API endpoint will be tested for schema validation, correct handling of both modes, and proper error responses.
  * **Characterization Tests:** A new test suite will validate end-to-end results against a pre-calculated, known-good spreadsheet or notebook. This is the ultimate guarantee of correctness.
  * **Performance Benchmarks:** A benchmark test will assert performance targets for a large hierarchy.

-----

## 8\. Acceptance Criteria

The project is complete when:

1.  This RFC is formally approved by all stakeholders via pull request review **before** Phase 1 coding begins.
2.  Unit test coverage for `engine/attribution.py` exceeds **95%**.
3.  Test coverage for all new API-level code exceeds **90%**.
4.  All characterization tests pass, proving correctness against an external, validated source.
5.  All performance benchmarks pass their defined targets.
6.  A new guide, **`docs/guides/attribution_methodology.md`**, is created, and the main `README.md` is updated to reflect the new API endpoint. All documentation must be current.