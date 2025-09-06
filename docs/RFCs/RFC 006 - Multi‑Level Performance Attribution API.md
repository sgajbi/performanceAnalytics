# RFC 006: Multi-Level Performance Attribution API

**Status:** Final (As Implemented)
**Owner:** Senior Architect
**Reviewers:** Perf Engine, Risk, Platform
**Target Release:** v0.3.0
**Related:** RFC-001, RFC-002, RFC-003, RFC-004

## 1. Executive Summary

This document specifies the design and implementation of a new, high-performance **Multi-Level Performance Attribution Engine** and its corresponding API endpoint, `/performance/attribution`. This engine provides stakeholders with Brinson-style attribution, decomposing a portfolio's active return against a benchmark into **Allocation, Selection, and Interaction** effects.

The implementation adheres to the principles established in previous RFCs: a decoupled, standalone `engine` module, vectorized computations, and a clean separation of concerns. The engine supports configurable attribution models (Brinson-Fachler, Brinson-Hood-Beebower) and multi-period linking to ensure effects correctly reconcile to the total geometric active return over the horizon.

## 2. Core Principles & Cohesion

* **Methodological Consistency:** The attribution engine is an explanatory layer built upon our core TWR engine. All returns used in its calculations are identical to those produced by `engine.compute.run_calculations`.
* **Unified Data Model:** The API contract for providing time series data reuses the established data models from the TWR and Contribution engines.
* **Architectural Purity:** The final implementation prioritizes mathematical correctness and perfect reconciliation to the true geometric active return ($TWR_P - TWR_B$).

## 3. Target Architecture & Data Flow

The new components are integrated into our existing architecture, maintaining a strict separation of concerns, with the core logic residing in `engine/attribution.py`.

### Data Flow

1.  **Request:** The `/performance/attribution` endpoint receives the request.
2.  **Mode Handling:**
    * If `mode` is `by_instrument`, the engine first calls our TWR calculator (`engine.compute`) for each instrument to derive daily returns, then aggregates these returns and weights to the specified group levels.
    * If `mode` is `by_group`, the engine uses the pre-aggregated data directly.
3.  **Computation (`engine/attribution.py`):**
    a. **Data Alignment:** The engine aligns portfolio and benchmark time series based on the requested `frequency`.
    b. **Single-Period Effects:** For each period, it computes A/S/I effects using the specified Brinson model.
    c. **Multi-Period Linking:** It applies the specified linking algorithm to the single-period effects.
    d. **Reconciliation:** The final result ensures the sum of attribution effects perfectly matches the total active return.

## 4. Core Methodology

### 4.1 Single-Period Effects

* **Brinson-Fachler (BF, default)**
    * Allocation ($A_{i,t}$): $(w^p_{i,t} - w^b_{i,t}) \cdot (R^b_{i,t} - R^b_t)$
    * Selection ($S_{i,t}$): $w^b_{i,t} \cdot (R^p_{i,t} - R^b_{i,t})$
    * Interaction ($I_{i,t}$): $(w^p_{i,t} - w^b_{i,t}) \cdot (R^p_{i,t} - R^b_{i,t})$

### 4.2 Multi-Period Linking

To ensure effects properly reconcile over time, the **Menchero linking algorithm** is used for geometric linking. This method correctly accounts for the compounding effect of benchmark returns over the horizon, ensuring that the sum of the linked effects equals the true total active return ($TWR_{Portfolio} - TWR_{Benchmark}$). Arithmetic summation is used when `linking` is set to `none`.

## 5. API Contract

The API contract is defined by the Pydantic models in `app/models/attribution_requests.py` and `app/models/attribution_responses.py`. It supports `by_instrument` and `by_group` modes.

## 6. Implementation & Testing

The implementation followed a test-driven development approach. The final engine is validated by a suite of unit and integration tests that confirm the correctness of the single-period formulas, the `by_instrument` aggregation, and the multi-period Menchero linking, ensuring the final results reconcile to the total active return with near-zero residual.