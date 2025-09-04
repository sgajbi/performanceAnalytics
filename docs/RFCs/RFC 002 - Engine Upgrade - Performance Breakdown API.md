
# RFC 002: V3 Engine Upgrade - Performance Breakdown API

**Status:** Draft
**Author:** Gemini
**Date:** 2025-09-05

## 1. Executive Summary

This document proposes a new plan to upgrade the `performanceAnalytics` engine to be API-compatible with the `portfolio-analytics-system`. This RFC supersedes all previous V3 proposals.

The primary goal is to refactor our API to return a **performance breakdown object**. Instead of a flat list of daily results, the engine will aggregate performance data into different time frequencies (**daily, monthly, quarterly, yearly**) as requested by the user.

This version also expands the list of supported **period types** to include `ITD` and rolling timeframes (`Y1`, `Y3`, `Y5`), ensuring full alignment with the target system's capabilities.

## 2. Gap Analysis

A deep review of the `portfolio-analytics-system` reveals the following gaps:

#### 2.1 API Contract & Output Structure
-   **Input:** The `PerformanceRequest` in the target system accepts a `frequencies: list[Frequency]` parameter to specify the desired time aggregations.
-   **Output:** The target system returns a `breakdowns` object, a dictionary mapping frequencies to aggregated performance data, which includes nested summaries for each period. Our current API returns a flat list of daily results.
-   **Data Models:** New Pydantic models (`PerformanceBreakdown`, `PerformanceResultItem`) are required to support the breakdown structure.

#### 2.2 Engine Features
-   **Aggregation Logic:** Our engine lacks the **post-processing logic** to aggregate daily results into monthly, quarterly, or yearly breakdowns.
-   **Expanded Period Types:** The target system supports `ITD`, `Y1`, `Y3`, and `Y5` period types. Our engine must be updated to calculate the correct effective start dates for these periods.

#### 2.3 Project Structure
-   The target system uses a `common/` directory for shared enums (`Frequency`, `PeriodType`). Adopting this improves organization.

## 3. Proposed Changes

#### 3.1 Phase 1: Models, Enums, and Period Logic

1.  **Create `common/` module**:
    -   Create `common/enums.py`.
    -   Define the `Frequency` enum (`DAILY`, `MONTHLY`, etc.).
    -   Define the expanded `PeriodType` enum, including `ITD`, `Y1`, `Y3`, and `Y5`.
2.  **Update API Models**:
    -   In `app/models/requests.py`, add `frequencies: list[Frequency]` to `PerformanceRequest`.
    -   In `app/models/responses.py`, refactor `PerformanceResponse` to use the new `PerformanceBreakdown` and `PerformanceResultItem` models.
3.  **Enhance `engine/periods.py`**:
    -   Update the `get_effective_period_start_dates` function with `elif` blocks for `ITD` and the rolling year types (`Y1`, `Y3`, `Y5`). The logic will calculate a single start date and apply it to all rows, which is highly efficient.

#### 3.2 Phase 2: Implement the Aggregation Layer

1.  **Create `engine/breakdown.py`**:
    -   This new file will contain a `generate_performance_breakdowns` function that takes the daily performance DataFrame as input.
2.  **Implement Aggregation Logic**:
    -   This function will use pandas `resample()` to group daily data into the requested frequencies. For each period, it will calculate a summary containing `period`, `beginning_mv`, `ending_mv`, total `cash_flows`, and the `cumulative_return`.

#### 3.3 Phase 3: Integration and Documentation

1.  **Update the API Endpoint**:
    -   The main performance endpoint will orchestrate the process: first calling the daily calculation engine, then passing the results to the new breakdown aggregation function.
2.  **Update `README.md`**:
    -   Revise the documentation to reflect the new API that accepts `frequencies` and `period_type` and returns a `breakdowns` object.

## 4. Impact on Methodology

This plan maintains a clean separation of concerns.
- The core daily calculation engine's vectorized methodology remains untouched.
- The new period types are handled in the highly efficient, vectorized pre-calculation step.
- The new breakdown feature is a **post-processing aggregation layer**.

## 5. Testing Strategy

-   The unit tests for `engine/periods.py` will be expanded with parameterized cases for `ITD`, `Y1`, `Y3`, and `Y5`.
-   A new suite of unit tests for `engine/breakdown.py` will be created to validate that the monthly, quarterly, and yearly aggregations are correct.

***

This updated RFC now covers all the required features for compatibility. Please review it for final approval.