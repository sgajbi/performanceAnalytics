

# RFC-004: Contribution Engine Hardening & Finalization

**Status:** Draft
**Author:** Gemini
**Date:** September 5, 2025

## 1. Executive Summary

This document proposes a final set of enhancements for the **Position Contribution Engine**. While the core engine is implemented, a review has identified five critical improvements required to ensure it is mathematically exact, robust, and production-ready before being merged.

The proposed changes are:
1.  **Residual Attribution:** Implement a final step to ensure the sum of position contributions perfectly equals the total portfolio return.
2.  **Adjusted Weight Calculation:** Refine the average weight formula to correctly account for non-investment periods.
3.  **Full Period Type Support:** Ensure the contribution API supports all period types available in the TWR engine.
4.  **Complete Test Coverage:** Increase test coverage to 100% for the engine and >90% for the application.
5.  **Hardened Error Handling:** Add explicit handling for potential mathematical errors like division by zero.

## 2. Background & Rationale

This RFC addresses the final gap between a functional engine and a production-grade one. Residual attribution is critical for financial reporting to ensure the "sum of the parts equals the whole." The adjusted weight and period type support ensure consistency with the main performance engine. Finally, achieving full test coverage and hardening against math errors are essential for reliability and maintainability.

## 3. Proposed Changes & Methodology

### 3.1 Residual Attribution

-   **Methodology:** Even with Carino smoothing, minor floating-point differences can cause the sum of contributions to deviate slightly from the total portfolio return. We will calculate this difference (the "residual") and distribute it across the positions.
    1.  Calculate `Residual = Total Portfolio Return - Sum(Smoothed Position Contributions)`.
    2.  The final contribution for each position will be:
        $$C_{final, p} = C'_{p, total} + (Residual \times W_{p, avg})$$
        Where $W_{p, avg}$ is the position's average weight over the period.
-   **Implementation:** This will be a new post-processing step at the end of the `engine.contribution.calculate_position_contribution` function.

### 3.2 Adjusted Average Weight Calculation

-   **Methodology:** The `average_weight` calculated for the final response must be adjusted for days where no investment was active.
    1.  First, determine the `Adjusted Day Count` for the period:
        -   `Adjusted Day Count = Total Days - (Count of NIP Days) - (Count of Days Before Final Reset)`
    2.  The final average weight for each position will be:
        $$W_{p, avg} = \frac{\sum_{t=1}^{N} W_{p,t}}{Adjusted\_Day\_Count}$$
-   **Implementation:** This logic will be implemented in the final aggregation step of the `engine.contribution.calculate_position_contribution` function.

### 3.3 Full Period Type Support

-   **Methodology:** The `POST /performance/contribution` endpoint must correctly accept and apply all `PeriodType` enums (e.g., `YTD`, `Y1`, `ITD`). The `period_type` will be used to configure the internal TWR engine calls that generate the necessary portfolio and position returns.
-   **Implementation:** The endpoint logic in `app/api/endpoints/contribution.py` will be confirmed to correctly use the `period_type` from the request to build the `EngineConfig`.

### 3.4 Test Coverage to 100% / >90%

-   **Methodology:** We will use `pytest-cov` to generate a detailed coverage report. Based on the report, we will add new tests to cover any missed lines or logic branches.
-   **Implementation:** This involves a dedicated effort to write new unit and integration tests, focusing on error paths, edge cases in the breakdown and MWR logic, and adapter functions.

### 3.5 Hardened Error Handling

-   **Methodology:** All mathematical functions involving division will be audited and updated to explicitly handle cases where the denominator is zero, preventing unhandled exceptions. The documented behavior will be to return `0.0` in such cases.
-   **Implementation:** Add `if denominator == 0: return 0.0` checks to the following key calculations:
    -   `engine.ror.calculate_daily_ror`
    -   `engine.mwr.calculate_money_weighted_return`
    -   `engine.contribution._calculate_single_period_weights`

## 4. Implementation Plan

The work will be broken down into the following test-driven phases:

1.  **Phase 1:** Implement Residual Attribution and the Adjusted Average Weight Calculation. Update the characterization test to assert the new behaviors.
2.  **Phase 2:** Add a parameterized integration test for the contribution endpoint to validate that all `PeriodType` values are processed correctly.
3.  **Phase 3:** Harden all engine functions with explicit error handling for division-by-zero scenarios and add corresponding unit tests.
4.  **Phase 4:** Generate a coverage report and write the necessary tests to achieve the 100% (engine) and >90% (app) coverage targets.

