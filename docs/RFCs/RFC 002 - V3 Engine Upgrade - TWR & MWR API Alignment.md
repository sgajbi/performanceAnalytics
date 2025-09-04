 
# RFC 002: V3 Engine Upgrade - TWR & MWR API Alignment

**Status:** Draft
**Author:** Gemini
**Date:** 2025-09-05

## 1. Executive Summary

This document outlines a refined plan to upgrade the `performanceAnalytics` engine to be API-compatible with the `query-service` in the `portfolio-analytics-system`. This alignment is the final step before the engine can be integrated into the larger system.

The primary goal is to refactor our single performance endpoint into two distinct, standards-compliant APIs:
1.  A **Time-Weighted Return (TWR)** API that provides daily, chain-linked performance data.
2.  A **Money-Weighted Return (MWR)** API that provides a single return figure for an entire period, accounting for cash flows.

The `strategy` parameter will be removed entirely, keeping the engine focused purely on portfolio-level calculations. The core high-performance TWR methodology remains unchanged; we will be adding the MWR calculation as a separate, parallel feature.

## 2. Gap Analysis

A deep review of the `query-service` reveals the following gaps compared to our current implementation:

#### 2.1 API Structure & Contracts

-   **Dual Endpoints:** The target system exposes two specific endpoints, `/performance/twr` and `/performance/mwr`, while we currently have a single generic `/calculate_performance` endpoint.
-   **Distinct Models:** Each endpoint has its own dedicated request and response models.
    -   The TWR endpoint uses a detailed, daily time-series model, similar to our current one.
    -   The MWR endpoint uses a much simpler model, requiring only `beginning_mv`, `ending_mv`, and a list of `cash_flows` with dates and amounts.
-   **Request Tracking:** The target system uses a `calculation_id: UUID` in its TWR request/response flow for traceability.
-   **Configuration:** A `rounding_precision` parameter is included in the TWR request to control output formatting.

#### 2.2 Engine Features

-   **Missing MWR Calculation:** Our engine is exclusively a TWR calculator. The logic to calculate a money-weighted return (specifically, a Modified Dietz formula found in the target system) is a new feature that needs to be implemented.
-   **`strategy` Field:** The `strategy` field previously analyzed is part of a broader service in the target system. Per the new directive, it is out of scope for our core performance engine and will be removed.

## 3. Proposed Changes

We will implement the following changes to achieve API compatibility.

#### 3.1 Phase 1: API Restructuring and TWR Alignment

1.  **Refactor Endpoints in `app/api/endpoints/performance.py`**:
    -   Rename the existing `/calculate_performance` endpoint to `/performance/twr`.
    -   Create a new, placeholder endpoint for `/performance/mwr`.
2.  **Update TWR Models in `app/models/`**:
    -   Modify `PerformanceRequest` and `PerformanceResponse` to match the target system's TWR models (add `calculation_id`, `rounding_precision`; remove `strategy`).
3.  **Update Engine Configuration**:
    -   Add `rounding_precision: int` to `engine/config.py`. The engine will use this to format its final output.

#### 3.2 Phase 2: MWR Implementation

1.  **Create MWR Models in `app/models/`**:
    -   Create new Pydantic models: `MoneyWeightedReturnRequest` and `MoneyWeightedReturnResponse`.
2.  **Create MWR Calculation Module `engine/mwr.py`**:
    -   Create a new file to house the MWR logic.
    -   Add a `calculate_money_weighted_return` function that takes starting/ending market values and a list of cash flows, implementing the Modified Dietz formula from the target system.
3.  **Implement MWR Endpoint**:
    -   Flesh out the `/performance/mwr` endpoint to use the new models and call the `calculate_money_weighted_return` engine function.

#### 3.3 Phase 3: Documentation Update

1.  **Update `README.md`**:
    -   Revise the API usage section to document both the `/twr` and `/mwr` endpoints with separate `curl` examples.
    -   Explain the difference between the TWR and MWR calculations.
2.  **Create API Guide**:
    -   Add a new document, `docs/guides/api_reference.md`, detailing the request/response shapes for both endpoints.

## 4. Testing Strategy

-   The existing characterization test suite will be retargeted to validate the `/performance/twr` endpoint and its underlying engine logic.
-   New unit and integration tests will be created for the `/performance/mwr` endpoint and the `calculate_money_weighted_return` function.

 